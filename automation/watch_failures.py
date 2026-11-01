#!/usr/bin/env python3
"""Watch Jenkins for new failed builds and diagnose each one with the agent team."""
import argparse
import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LIST_BUILDS = PROJECT_ROOT / ".claude/skills/jenkins-debug/scripts/list_builds.sh"
STATE_FILE = PROJECT_ROOT / "automation" / "state.json"
FAILED_RESULTS = {"FAILURE", "ABORTED", "UNSTABLE"}


def log(message):
    print(f"[{datetime.now():%H:%M:%S}] {message}", flush=True)


def current_builds():
    output = subprocess.run([str(LIST_BUILDS)], cwd=PROJECT_ROOT, capture_output=True, text=True, check=True).stdout
    builds = []
    for line in output.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[1].startswith("#"):
            branch, number, result = parts[0], parts[1].lstrip("#"), parts[2]
            builds.append((branch, number, result))
    return builds


def load_state():
    return set(json.loads(STATE_FILE.read_text())) if STATE_FILE.exists() else set()


def save_state(state):
    STATE_FILE.write_text(json.dumps(sorted(state), indent=2))


def diagnose(branch, number):
    env = {key: value for key, value in os.environ.items() if key != "ANTHROPIC_API_KEY"}
    completed = subprocess.run(
        ["claude", "-p", f"/debug-build-team {branch} {number}", "--output-format", "json"],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=900,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"claude exited with {completed.returncode}: {completed.stderr[-300:]}")
    return json.loads(completed.stdout)


def check_once(state, mark_only):
    for branch, number, result in current_builds():
        key = f"{branch}#{number}"
        if result not in FAILED_RESULTS or key in state:
            continue
        if mark_only:
            log(f"Marking existing failure {key} as already seen")
        else:
            log(f"New failed build {key} ({result}): diagnosing with the agent team...")
            try:
                run = diagnose(branch, number)
                summary = run.get("result", "").split("```json")[0].strip()
                log(f"Done in {run.get('num_turns')} turns. Summary: {summary[:300]}")
            except Exception as error:
                log(f"Diagnosis failed for {key}: {error}")
        state.add(key)
        save_state(state)


def main():
    parser = argparse.ArgumentParser(description="Diagnose new failed Jenkins builds automatically.")
    parser.add_argument("--loop", action="store_true", help="keep checking until stopped with Ctrl+C")
    parser.add_argument("--interval", type=int, default=60, help="seconds between checks (default 60)")
    parser.add_argument("--mark-existing", action="store_true", help="record current failures as seen, without diagnosing them")
    args = parser.parse_args()

    state = load_state()
    if args.mark_existing:
        check_once(state, mark_only=True)
        return

    log(f"Watching Jenkins every {args.interval}s. Press Ctrl+C to stop.")
    try:
        while True:
            try:
                check_once(state, mark_only=False)
            except subprocess.CalledProcessError as error:
                log(f"Could not reach Jenkins ({error}); will retry")
            if not args.loop:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        log("Stopped.")


if __name__ == "__main__":
    main()