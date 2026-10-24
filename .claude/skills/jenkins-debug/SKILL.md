---
name: jenkins-debug
description: Diagnose failed Jenkins pipeline builds in this project. Use when the user asks why a Jenkins build or branch failed, what is broken in Jenkins, or to debug a Jenkins console log.
---

# Jenkins build debugging

## Tools
Scripts live in `.claude/skills/jenkins-debug/scripts/`. They load credentials themselves; never read `.env`.
- `list_builds.sh`: every branch of the `calculator` job with its last build number and result.
- `get_build_log.sh <branch> [build-number|lastBuild] [--raw]`: the console log of a build, trimmed by default.
- To use a saved log file instead (for example `eval/cases/<case>/console.log`), trim it with `python3 .claude/skills/jenkins-debug/scripts/trim_log.py <file>`.

## Investigation steps
1. **Identify the build.** If no branch is given, run `list_builds.sh` and pick the failed or aborted builds.
2. **Read the log.** Find the failed stage and the first real error, not the generic lines that follow it (such as "script returned exit code 1"). For a timeout, look at what the stage was doing before it was cancelled.
3. **Find what changed.** Run `git log main..<branch>` and `git diff main...<branch>` (three dots). `main` is green, so the branch's own changes are the prime suspects.
4. **Read the relevant files on that branch** with `git show <branch>:<path>`, never by switching branches: the file named in the error, the files changed in the diff, and the Jenkinsfile stage that failed.
5. **Decide the root cause from evidence:** log lines, diff lines and file contents.
6. **Choose one fix.** If a recent commit broke a previously green build, prefer restoring the previous working behavior, unless the evidence shows the change was intended and something else must adapt to it. Never weaken or delete tests, remove timeouts, or simply retry.

## Rules
- Read-only: do not edit files, commit, switch branches or trigger builds. Propose the fix; don't apply it.
- Keep evidence and assumptions separate.
- Use confidence "high" only when the log, the code and the diff together confirm both the cause and the fix.

## Output
First, a short summary for a human (3 to 5 sentences). Then a JSON object in a ```json code block with exactly these fields:
- `failed_stage`: stage name as shown in the log
- `build_result`: "FAILURE", "ABORTED" or "UNSTABLE"
- `category`: one of "test_failure", "credential_error", "terraform_error", "timeout", "dependency_error", "syntax_error", "infrastructure_error", "other"
- `root_cause`: one or two sentences
- `key_evidence`: list of exact lines from the log, the diff or the files
- `suggested_fix`: the single best fix
- `confidence`: "high", "medium" or "low"
- `assumptions`: list of things not verified; empty if none
- `next_checks`: list of what a human should verify next