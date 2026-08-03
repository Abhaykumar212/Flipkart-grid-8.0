# Running the demo (judge / showcase guide)

One script brings up the entire system: dependencies, models, database, both
servers, and the browser tabs a judge needs. Everything else in this file is
the command reference behind that script, for when you want to run a step by
hand or something needs troubleshooting mid-demo.

## Prerequisites

- Python 3.13
- Node.js 22
- PowerShell 7+ (Windows PowerShell 5.1 also works for `scripts/showcase.ps1`)

## One command

```powershell
./scripts/showcase.ps1
```

First run installs Python and Node dependencies, trains the risk and
root-cause models if their `.joblib` artifacts are missing (a few minutes,
one time only), resets the demo database, frees ports `8000`/`5173` if a
previous run left them occupied, starts the API and the storefront/dashboard,
waits for `/ready`, and opens:

- Storefront — http://localhost:5173/
- Scenario theatre — http://localhost:5173/dashboard/scenarios
- Swagger API — http://localhost:8000/docs

Press `Ctrl+C` in that terminal to stop both servers cleanly.

Useful flags:

```powershell
./scripts/showcase.ps1 -SkipInstall   # repeat runs once the venv/node_modules are known-good
./scripts/showcase.ps1 -NoReset       # keep whatever session/decision history is already in the DB
./scripts/showcase.ps1 -NoBrowser     # don't auto-open tabs (e.g. presenting from a second machine)
```

## What to actually show

Full run-of-show with talking points: [docs/demo-script.md](docs/demo-script.md).
Short version:

1. Open **Scenario theatre** (`/dashboard/scenarios`) → **Run all eight**. Each
   row replays a real session through the live decision pipeline and shows
   expected vs. actual cause, intervention, decision, and A/B arm.
2. Open **Architecture** (`/dashboard/architecture`) to show the six-agent
   pipeline judges can point at while you talk.
3. Shop the storefront yourself (add to cart, reopen reviews, browse a few
   similar products) and open the assistant inspector (bottom-right FAB) to
   show live risk scoring and the reasoning behind whatever the agent decides
   — including deciding to stay silent.
4. Open **Live sessions** (`/dashboard`) and click into any decision's full
   trace; toggle **EN/हिंदी** to show localized explanations.
5. Press **Generate 40 sessions** in Scenario theatre to populate the A/B and
   latency panels with a documented synthetic response model (assumptions are
   printed on screen, never presented as production numbers).

If time is short: run scenario A (helpful review-summary nudge), F (honest
`UNKNOWN → ABSTAIN`), and G (two dismissals suppress further nudging). That
trio proves value, honesty, and governance in under two minutes.

## Command reference

| Task | Command |
|---|---|
| Full one-command bring-up | `./scripts/showcase.ps1` |
| Bring up without reinstalling deps | `./scripts/showcase.ps1 -SkipInstall` |
| Manual dev bring-up (no auto-reset/browser) | `./scripts/dev.ps1` |
| Train all models from scratch | `./scripts/train_all.ps1 -Scale full` |
| Reset the demo database only | `./scripts/reset_demo.ps1` |
| Replay one frozen scenario (A–H) | `./scripts/run_scenario.ps1 A` |
| Replay all eight scenarios headless | `foreach ($s in 'A','B','C','D','E','F','G','H') { ./scripts/run_scenario.ps1 $s }` |
| Full validation (tests, lint, typecheck, build, e2e) | `./scripts/test.ps1` |
| Backend unit/integration tests only | `./.venv/Scripts/python.exe -m pytest tests/unit tests/integration -q` |
| Frontend unit tests only | `npm test` |
| Frontend production build | `npm run build` |
| Frontend lint | `npm run lint` |

## Troubleshooting

- **Port 8000 or 5173 already in use** — `showcase.ps1` frees both
  automatically. To do it by hand:
  ```powershell
  Get-NetTCPConnection -LocalPort 8000 -State Listen | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
  ```
- **"Model artifacts are missing"** — run `./scripts/train_all.ps1 -Scale full`
  once; `showcase.ps1` and `test.ps1` both detect and rebuild missing
  artifacts automatically.
- **Stale data mid-demo** — `./scripts/reset_demo.ps1` is idempotent; run it
  any time between scenarios to return to a clean, seeded state.
- **No internet at the venue** — nothing here needs it. SQLite, local model
  artifacts, and deterministic template rendering are all offline by default;
  `GROQ_API_KEY` is optional and unset by default, which is the state you
  want for a guaranteed-deterministic demo.
- **Swagger/API check** — http://localhost:8000/ready confirms the database
  and both promoted models are live; http://localhost:8000/api/v1/metrics
  shows latency percentiles and SSE client count.
