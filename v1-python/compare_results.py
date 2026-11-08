import json

from evaluate import MAX_POINTS_PER_CASE, RESULTS_DIR, RUBRIC_VERSION

VERSIONS = {
    "v1": "V1: Claude API, log only",
    "v2": "V2: Claude Code, one agent + skill",
    "v3": "V3: Claude Code, agent team + hooks",
}


def runs_for(label):
    runs = []
    for path in sorted(RESULTS_DIR.glob(f"{label}_*.json")):
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        if data.get("rubric") == RUBRIC_VERSION:
            runs.append(data)
    return runs


def summarize(label, data):
    results = data["results"]
    ok = [r for r in results if "error" not in r]
    n = len(results)
    if label == "v1":
        cost = f"${data['cost'] / n:.3f} (billed)"
        seconds = "-"
        models = data.get("model", "?")
    else:
        cost = f"${(data.get('estimated_cost_usd') or 0) / n:.2f} (API-equiv.)"
        seconds = f"{data['avg_seconds']:.0f}s" if data.get("timing") == "wall" else "-"
        models = ", ".join(sorted({m for r in ok for m in r["claude_code"]["models"]})) or "?"
    return {
        "score": f"{data['total']}/{data['max']}",
        "fixes": f"{sum(r['fix_verdict'] == 'correct' for r in ok)}/{n}",
        "overconfident": str(sum(r["overconfident"] for r in ok)),
        "cost": cost,
        "time": seconds,
        "models": models,
    }


def main():
    lines = [f"## Evaluation results (rubric: {RUBRIC_VERSION})", ""]
    lines += ["| Version | Score | Fixes fully correct | Overconfident | Cost per case | Time per case | All runs |",
              "|---|---|---|---|---|---|---|"]
    latest = {}
    models = []
    for label, title in VERSIONS.items():
        runs = runs_for(label)
        if not runs:
            continue
        latest[label] = runs[-1]
        s = summarize(label, runs[-1])
        all_scores = ", ".join(str(r["total"]) for r in runs)
        lines.append(f"| {title} | {s['score']} | {s['fixes']} | {s['overconfident']} | {s['cost']} | {s['time']} | {all_scores} |")
        models.append(f"{label.upper()}: {s['models']}")

    lines += ["", "Models: " + "; ".join(models), "", "### Points per case (latest run)", ""]
    labels = list(latest)
    lines += ["| Case | " + " | ".join(l.upper() for l in labels) + " |", "|---" * (len(labels) + 1) + "|"]
    cases = [r["case"] for r in next(iter(latest.values()))["results"]]
    for case in cases:
        cells = []
        for label in labels:
            match = next((r for r in latest[label]["results"] if r["case"] == case), None)
            cells.append(f"{match['points']}/{MAX_POINTS_PER_CASE}" if match else "-")
        lines.append(f"| {case} | " + " | ".join(cells) + " |")

    summary = "\n".join(lines) + "\n"
    (RESULTS_DIR / "summary.md").write_text(summary)
    print(summary)


if __name__ == "__main__":
    main()