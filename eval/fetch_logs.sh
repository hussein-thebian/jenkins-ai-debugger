#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

set -a
source .env
set +a

for case in broken-test missing-credential bad-terraform timeout; do
  mkdir -p "eval/cases/$case"
  curl -fsS -u "$JENKINS_USER:$JENKINS_TOKEN" \
    "$JENKINS_URL/job/calculator/job/fail%252F$case/lastBuild/consoleText" \
    -o "eval/cases/$case/console.log"
  echo "Saved eval/cases/$case/console.log ($(wc -l < "eval/cases/$case/console.log") lines)"
done