import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Literal

import anthropic
from pydantic import BaseModel

from diagnose import MODEL, PRICE_INPUT_PER_MTOK, PRICE_OUTPUT_PER_MTOK, PROJECT_ROOT, diagnose
from trim_log import trim_log

CASES_DIR = PROJECT_ROOT / "eval" / "cases"
RESULTS_DIR = PROJECT_ROOT / "eval" / "results"

FIX_POINTS = {"correct": 2, "acceptable": 1, "wrong": 0}
MAX_POINTS_PER_CASE = 7

JUDGE_SYSTEM_PROMPT = """You grade an AI's diagnosis of a failed Jenkins build against an answer key written by a human expert.
Judge meaning, not wording.

- root_cause_correct: true if the diagnosis identifies the same underlying cause as the answer key.
- fix_verdict:
  "correct" if the suggested fix matches the answer key's correct fix.
  "acceptable" if it matches one of the answer key's acceptable_fixes, or is a reasonable alternative that would genuinely fix the problem without bad side effects.  "wrong" if it matches one of the answer key's wrong fixes, or would not fix the problem.
  If the suggested fix offers several options, judge the first one it recommends.
- explanation: one short sentence."""


class Verdict(BaseModel):
    root_cause_correct: bool
    fix_verdict: Literal["correct", "acceptable", "wrong"]
    explanation: str


def cost_of(usage):
    return (usage.input_tokens * PRICE_INPUT_PER_MTOK + usage.output_tokens * PRICE_OUTPUT_PER_MTOK) / 1_000_000


def same(a, b):
    return a.strip().lower() == b.strip().lower()


def judge(expected, diagnosis):
    client = anthropic.Anthropic()
    content = (
        f"<answer_key>\n{json.dumps(expected, indent=2)}\n</answer_key>\n\n"
        f"<diagnosis>\n{diagnosis.model_dump_json(indent=2)}\n</diagnosis>"
    )
    return client.messages.parse(
        model=MODEL,
        max_tokens=1000,
        system=JUDGE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}],
        output_format=Verdict,
    )


def evaluate_case(case_dir):
    name = case_dir.name
    expected = json.loads((case_dir / "expected.json").read_text())
    log_text = trim_log((case_dir / "console.log").read_text())

    diag_response = diagnose(log_text)
    diagnosis = diag_response.parsed_output
    cost = cost_of(diag_response.usage)
    if diagnosis is None:
        return {"case": name, "error": f"no diagnosis ({diag_response.stop_reason})", "points": 0, "cost": cost}

    judge_response = judge(expected, diagnosis)
    verdict = judge_response.parsed_output
    cost += cost_of(judge_response.usage)
    if verdict is None:
        return {"case": name, "error": f"no verdict ({judge_response.stop_reason})", "points": 0, "cost": cost}

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
        "cost": cost,
        "diagnosis": diagnosis.model_dump(),
    }


def mark(ok):
    return "✅" if ok else "❌"


def main():
    case_dirs = sorted(d for d in CASES_DIR.iterdir() if d.is_dir())
    results = []
    for case_dir in case_dirs:
        print(f"Evaluating {case_dir.name}...", file=sys.stderr)
        results.append(evaluate_case(case_dir))

    print(f"\n{'case':<20} stage result categ cause  fix         conf    points")
    for r in results:
        if "error" in r:
            print(f"{r['case']:<20} ERROR: {r['error']}")
            continue
        c = r["checks"]
        flag = " ⚠️ overconfident" if r["overconfident"] else ""
        print(
            f"{r['case']:<20} {mark(c['stage']):^5} {mark(c['result']):^6} {mark(c['category']):^5} "
            f"{mark(c['root_cause']):^5} {r['fix_verdict']:<11} {r['confidence']:<7} "
            f"{r['points']}/{MAX_POINTS_PER_CASE}{flag}"
        )

    total = sum(r["points"] for r in results)
    max_total = MAX_POINTS_PER_CASE * len(results)
    total_cost = sum(r["cost"] for r in results)
    print(f"\nTOTAL: {total}/{max_total} ({100 * total / max_total:.0f}%) | cost ≈ ${total_cost:.4f}")

    print("\nJudge notes:")
    for r in results:
        if "judge_explanation" in r:
            print(f"- {r['case']}: {r['judge_explanation']}")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_file = RESULTS_DIR / f"v1_{timestamp}.json"
    out_file.write_text(
        json.dumps(
            {"version": "v1", "model": MODEL, "total": total, "max": max_total, "cost": total_cost, "results": results},
            indent=2,
        )
    )
    print(f"\nSaved {out_file.relative_to(PROJECT_ROOT)}", file=sys.stderr)


if __name__ == "__main__":
    main()