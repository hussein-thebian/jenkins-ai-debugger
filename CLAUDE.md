# Jenkins AI Debugger

Learning project: an AI agent that diagnoses failed Jenkins pipeline builds.

## Layout
- `jenkins/`: Docker Compose and Dockerfile for the local Jenkins lab (http://localhost:8080)
- `sample-app/`: calculator app, Jenkinsfile, Terraform config (`infra/`), smoke test (`scripts/`)
- `eval/cases/<case>/`: saved failure logs (`console.log`) and answer keys (`expected.json`)
- `eval/results/`: saved evaluation scorecards
- `v1-python/`: V1, a Python script using the Claude API (diagnose, trim, evaluate)

## Git branches
- `main` is always green.
- `fail/broken-test`, `fail/missing-credential`, `fail/bad-terraform` and `fail/timeout` each add one commit that breaks the build.
- Inspect branches without switching: `git diff main...<branch>` (three dots: only the branch's own changes), `git log main..<branch>` (commits only on the branch), `git show <branch>:<path>`.- Inspect branches without switching: `git diff main..<branch>`, `git log main..<branch>`, `git show <branch>:<path>`.

## Jenkins
- The multibranch job `calculator` builds every branch.
- In branch job URLs, `/` is encoded as `%252F` (for example `fail%252Ftimeout`).

## Rules
- Investigation is read-only: never trigger Jenkins builds, change Jenkins configuration, or push.
- Never read, print or edit `.env`, and never echo tokens or keys.
- Never switch branches (`git checkout` / `git switch`). The working tree stays on `main`.
- Never modify or commit to the `fail/*` branches; they are fixed test cases.
- When diagnosing a case, never open `eval/cases/*/expected.json`. It is the answer key, and reading it invalidates the evaluation.
- Never change a test to make it pass; fix the code under test.