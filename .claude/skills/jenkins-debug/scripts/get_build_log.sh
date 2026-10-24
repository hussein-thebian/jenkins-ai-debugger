#!/usr/bin/env bash
# Usage: get_build_log.sh <branch> [build-number|lastBuild] [--raw]
# Prints the console log of a build of the 'calculator' job, trimmed unless --raw is given.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"

set -a
source "$PROJECT_ROOT/.env"
set +a

branch="${1:?Usage: get_build_log.sh <branch> [build-number|lastBuild] [--raw]}"
build="${2:-lastBuild}"
mode="${3:-}"

job_path="job/calculator/job/${branch//\//%252F}"
log_file="$(mktemp)"
trap 'rm -f "$log_file"' EXIT

curl -fsS -u "$JENKINS_USER:$JENKINS_TOKEN" "$JENKINS_URL/$job_path/$build/consoleText" -o "$log_file"

if [[ "$mode" == "--raw" ]]; then
  cat "$log_file"
else
  python3 "$SCRIPT_DIR/trim_log.py" "$log_file"
fi