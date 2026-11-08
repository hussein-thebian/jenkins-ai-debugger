import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime

from diagnose import MODEL, PROJECT_ROOT, Diagnosis
from evaluate import CASES_DIR, FIX_POINTS, MAX_POINTS_PER_CASE, RESULTS_DIR, RUBRIC_VERSION, cost_of, judge, mark, same

JSON_BLOCK = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)
BLOCK_JENKINS = "Bash(.claude/skills/jenkins-debug/scripts/get_build_log.sh:*)"


def run_claude_code(command, log_path, branch, model=None):
    env = {key: value for key, value in os.environ.items() if key != "ANTHROPIC_API_KEY"}
    cmd = ["claude", "-p", f"{command} {log_path} {branch}", "--output-format", "json", "--disallowedTools", BLOCK_JENKINS]
    if model:
        cmd += ["--model", model]
    completed = subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=900,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"claude exited with {completed.returncode}: {completed.stderr[-500:]}")
    return json.loads(completed.stdout)


def extract_diagnosis(answer_text):
    blocks = JSON_BLOCK.findall(answer_text)
    if not blocks:
        raise ValueError("no ```json block found in the answer")
    return Diagnosis.model_validate_json(blocks[-1])


def evaluate_case(case_dir, command, model=None):
    name = case_dir.name
    expected = json.loads((case_dir / "expected.json").read_text())
    log_path = f"eval/cases/{name}/console.log"

    try:
        started = time.monotonic()
        run = run_claude_code(command, log_path, expected["branch"], model)
        wall_seconds = time.monotonic() - started
        diagnosis = extract_diagnosis(run["result"])
    except Exception as error:
        return {"case": name, "error": str(error), "points": 0, "judge_cost": 0}

    judge_response = judge(expected, diagnosis)
    verdict = judge_response.parsed_output
    judge_cost = cost_of(judge_response.usage)
    if verdict is None:
        return {"case": name, "error": "no verdict from judge", "points": 0, "judge_cost": judge_cost}

    checks = {
        "stage": same(diagnosis.failed_stage, expected["failed_stage"]),
        "result": same(diagnosis.build_result, expected["expected_result"]),
        "category": same(diagnosis.category, expected["category"]),
        "root_cause": verdict.root_cause_correct,
    }
    points = checks["stage"] + checks["result"] + checks["category"] + 2 * checks["root_cause"] + FIX_POINTS[verdict.fix_verdict]

    return {
        "case": name,
        "checks": checks,
        "fix_verdict": verdict.fix_verdict,
        "confidence": diagnosis.confidence,
        "overconfident": diagnosis.confidence == "high" and verdict.fix_verdict != "correct",
        "judge_explanation": verdict.explanation,
        "points": points,
        "judge_cost": judge_cost,
        "claude_code": {
            "num_turns": run.get("num_turns"),
            "duration_ms": run.get("duration_ms"),
            "wall_seconds": round(wall_seconds, 1),
            "estimated_cost_usd": run.get("total_cost_usd"),
            "models": sorted(run.get("modelUsage", {}).keys()),
        },
        "diagnosis": diagnosis.model_dump(),
    }


def latest_v1_points():
    v1_files = sorted(RESULTS_DIR.glob("v1_*.json"))
    if not v1_files:
        return {}
    try:
        data = json.loads(v1_files[-1].read_text())
    except json.JSONDecodeError as error:
        print(f"Warning: could not read {v1_files[-1].name} ({error}); skipping V1 comparison", file=sys.stderr)
        return {}
    return {r["case"]: r["points"] for r in data["results"]}


def main():
    parser = argparse.ArgumentParser(description="Evaluate a Claude Code diagnosis command on the eval set.")
    parser.add_argument("--command", default="/debug-build", help="slash command to evaluate (default /debug-build)")
    parser.add_argument("--label", default="v2", help="label for the results file, e.g. v2 or v3 (default v2)")
    parser.add_argument("--model", default=None, help="model for Claude Code, e.g. claude-sonnet-5-5 (default: Claude Code's own default)")
    args = parser.parse_args()

    case_dirs = sorted(d for d in CASES_DIR.iterdir() if d.is_dir())
    results = []
    for case_dir in case_dirs:
        print(f"[{args.label}] Running {args.command} on {case_dir.name} (fresh session)...", file=sys.stderr)
        results.append(evaluate_case(case_dir, args.command, args.model))

    total = sum(r["points"] for r in results)
    max_total = MAX_POINTS_PER_CASE * len(results)
    judge_cost = sum(r["judge_cost"] for r in results)
    runs = [r["claude_code"] for r in results if "claude_code" in r]
    est_cost = sum(run["estimated_cost_usd"] or 0 for run in runs)
    avg_seconds = sum(run["wall_seconds"] for run in runs) / len(runs) if runs else 0

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_file = RESULTS_DIR / f"{args.label}_{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    out_file.write_text(json.dumps(
        {"version": args.label, "command": args.command, "rubric": RUBRIC_VERSION, "judge_model": MODEL,
         "total": total, "max": max_total, "estimated_cost_usd": est_cost, "avg_seconds": avg_seconds, "timing": "wall", "results": results},
        indent=2,
    ))
    print(f"Saved {out_file.relative_to(PROJECT_ROOT)}", file=sys.stderr)

    v1 = latest_v1_points()
    label = args.label.upper()
    print(f"\n{'case':<20} stage result categ cause  fix         conf    {label:<5} V1")
    for r in results:
        if "error" in r:
            print(f"{r['case']:<20} ERROR: {r['error']}")
            continue
        c = r["checks"]
        flag = " ⚠️ overconfident" if r["overconfident"] else ""
        print(
            f"{r['case']:<20} {mark(c['stage']):^5} {mark(c['result']):^6} {mark(c['category']):^5} "
            f"{mark(c['root_cause']):^5} {r['fix_verdict']:<11} {r['confidence']:<7} "
            f"{r['points']}/{MAX_POINTS_PER_CASE}   {v1.get(r['case'], '-')}/{MAX_POINTS_PER_CASE}{flag}"
        )

    v1_total = sum(v1.values()) if v1 else None
    print(f"\n{label} TOTAL: {total}/{max_total} ({100 * total / max_total:.0f}%)   |   V1 TOTAL: {v1_total}/{max_total}")
    print(f"{label}: ~{avg_seconds:.0f}s per case, ~${est_cost:.2f} API-equivalent (subscription) | judge: ${judge_cost:.4f} (API credits)")

    print("\nJudge notes:")
    for r in results:
        if "judge_explanation" in r:
            print(f"- {r['case']}: {r['judge_explanation']}")


if __name__ == "__main__":
    main()