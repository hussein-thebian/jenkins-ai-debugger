## Evaluation results (rubric: strict-fallbacks-v2)

| Version | Score | Fixes fully correct | Overconfident | Cost per case | Time per case | All runs |
|---|---|---|---|---|---|---|
| V1: Claude API, log only | 31/35 | 2/5 | 1 | $0.022 (billed) | - | 30, 31 |
| V2: Claude Code, one agent + skill | 35/35 | 5/5 | 0 | $0.20 (API-equiv.) | 29s | 35, 35 |
| V3: Claude Code, agent team + hooks | 35/35 | 5/5 | 0 | $0.34 (API-equiv.) | 61s | 35, 35 |

Models: V1: claude-sonnet-5-5; V2: claude-opus-5-5; V3: claude-opus-5-5

### Points per case (latest run)

| Case | V1 | V2 | V3 |
|---|---|---|---|
| bad-terraform | 5/7 | 7/7 | 7/7 |
| broken-test | 7/7 | 7/7 | 7/7 |
| innocent-commit | 6/7 | 7/7 | 7/7 |
| missing-credential | 7/7 | 7/7 | 7/7 |
| timeout | 6/7 | 7/7 | 7/7 |
