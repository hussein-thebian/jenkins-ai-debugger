#!/usr/bin/env bash
# Usage: list_builds.sh
# Lists every branch of the 'calculator' job with its last build number and result.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"

set -a
source "$PROJECT_ROOT/.env"
set +a

curl -fsSg -u "$JENKINS_USER:$JENKINS_TOKEN" \
  "$JENKINS_URL/job/calculator/api/json?tree=jobs[name,lastBuild[number,result]]" \
  | python3 -c '
import json, sys
from urllib.parse import unquote
for job in json.load(sys.stdin)["jobs"]:
    last = job.get("lastBuild") or {}
    name = unquote(job["name"])
    number = last.get("number", "-")
    result = last.get("result") or "IN PROGRESS"
    print(f"{name:<28} #{number:<4} {result}")
'