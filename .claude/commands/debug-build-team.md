---
description: Diagnose a failed Jenkins build with a team of subagents (log-reader, jenkinsfile-checker, git-investigator)
argument-hint: <branch> | <saved-console.log> <branch>
---

Diagnose this failed Jenkins build: $ARGUMENTS

You are the orchestrator. Do not read the log, the Jenkinsfile or the git history yourself. Delegate to the subagents and reason over their reports.

Input:
- If the first argument is a branch name, the log comes from Jenkins for that branch.
- If the first argument is the path to a saved console log, the log comes from that file, and the second argument is the branch to investigate. In that case, never fetch the log from Jenkins.

Steps:
1. Launch the log-reader subagent with the log source.
2. When it reports, launch the jenkinsfile-checker and git-investigator subagents in parallel. Give both the branch, the failed stage and the first error from the log-reader's report.
3. Combine the three reports. Base the root cause only on evidence they quote. If the reports disagree or something important is missing, you may launch one follow-up subagent with a specific question.
4. Choose one fix. If a recent commit broke a previously green build, prefer restoring the previous behavior, unless the evidence shows the change was intended. If the branch's changes are unrelated to the failure, say so and identify the cause elsewhere (for example Jenkins configuration). Never weaken or delete tests, remove timeouts, or simply retry.
5. Read-only: propose the fix; do not apply it.

Output: first a short summary for a human (3 to 5 sentences), then a JSON object in a ```json code block with exactly these fields:
- `failed_stage`: stage name as shown in the log
- `build_result`: "FAILURE", "ABORTED" or "UNSTABLE"
- `category`: one of "test_failure", "credential_error", "terraform_error", "timeout", "dependency_error", "syntax_error", "infrastructure_error", "other"
- `root_cause`: one or two sentences
- `key_evidence`: list of exact lines quoted in the subagents' reports
- `suggested_fix`: the single best fix
- `confidence`: "high", "medium" or "low"
- `assumptions`: list of things not verified; empty if none
- `next_checks`: list of what a human should verify next