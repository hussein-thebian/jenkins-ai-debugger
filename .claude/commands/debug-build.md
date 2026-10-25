---
description: Diagnose a failed Jenkins build of the calculator job
argument-hint: <branch> | <saved-console.log> <branch>
---

Use the jenkins-debug skill to diagnose this build: $ARGUMENTS

- If the first argument is a branch name, fetch its latest build log with the skill's `get_build_log.sh` script.
- If the first argument is the path to a saved console log, use that file instead of Jenkins (trim it with the skill's `trim_log.py`), and use the second argument as the branch to compare against `main`.
- Follow the skill's investigation steps and output format exactly. Propose the fix; do not apply it.