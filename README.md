# 🦆 Quacktuaries

A self-hosted, single-container web game for teaching statistical inference through proportions estimation. Students play as insurance actuaries at a rubber duck factory — inspecting batches of ducks for defects, estimating hidden defect rates, and selling insurance policies to maximize their score.

Built with **Python/FastAPI**, **Jinja2** server-rendered templates, and **SQLite**.

## Quick Start (Docker)

```bash
# 1. Clone and enter the project
cd quacktuaries

# 2. Generate a persistent local key in your shell (save it securely for reuse)
export SESSION_SECRET="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"

# 3. Build and run
docker compose up -d --build

# 4. Open in browser
open http://localhost:8000
```

## Quick Start (Local Development)

```bash
# 1. Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.lock

# 3. Set environment variables
export SESSION_SECRET="your-secret"
export DB_PATH="$PWD/dev.db"

# 4. Run the server
uvicorn app.main:app --reload --port 8000

# 5. Open http://localhost:8000
```

## Athenaeum integration

For the local HTTPS ecosystem, use the sibling Athenaeum checkout and its `docs/local-ecosystem.md`. This application remains independently buildable and still supports standalone root-path development. See [deployment contract](docs/deployment.md) for prefix, cookie, data, health, and ARM details. No Cloud Run cutover is included.

## How to Play

### Teacher Setup
1. Go to `/admin` and enter your name to start a teacher session
2. Create a new session — choose a difficulty preset (Easy / Medium / Hard) which configures batch count, turn limits, inspection budget, and time limit
3. Share the **join code** (e.g., `AB12CD`) with students
4. Click **Start Game** when everyone has joined — the countdown timer begins
5. The game **auto-ends** when the timer expires, or click **End Game** manually — this reveals the true defect rates
6. Use the **Show/Hide** toggle on your dashboard to peek at defect rates mid-game

### Student Gameplay
1. Go to `/join` and enter the join code + your name
2. Each turn, you can either:
   - **INSPECT** a duck batch: choose batch + sample size *n*, pull *n* ducks and find *x* defective ones (uses 1 turn + *n* budget)
   - **SELL POLICY**: estimate a confidence interval [L, U] for a batch's true defect rate *p* (one policy per batch)
   - **BUY RESOURCES**: spend score 🪙 to purchase extra turns (40 pts) or inspection budget (20 pts for 50 units)
3. Selling earns a premium based on interval width, but penalizes misses based on confidence level
4. Once you sell a policy on a batch, that batch is locked — no more inspections or policies on it
5. Maximize your score within the turn, budget, and time limits 🦆

A full **Student Guide** is available in-app at `/guide`.

### Difficulty Presets

| Setting | Easy | Medium | Hard |
|---|---|---|---|
| Duck Batches | 8 | 10 | 12 |
| Max Turns | 20 | 20 | 18 |
| Inspection Budget | 500 | 400 | 300 |
| Min Sample Size | 5 | 5 | 10 |
| Max Sample Size | 100 | 80 | 60 |
| Time Limit | 15 min | 15 min | 15 min |

### Scoring
- **Premium** = `floor(premium_scale × (1 - width)² × confidence_bonus)`
- **Penalty** (if *p* not in [L, U]) = `miss_penalty[confidence]`
- **Net** = premium - penalty

| Confidence | Bonus | Miss Penalty |
|-----------|-------|-------------|
| 0.90      | 1.0×  | 150         |
| 0.95      | 1.2×  | 350         |
| 0.99      | 1.5×  | 600         |

## Configuration

All settings are controlled via environment variables:

| Variable         | Default       | Description                          |
|-----------------|---------------|--------------------------------------|
| `SESSION_SECRET` | random in development | Stable signing key; required in production unless supplied by file |
| `DB_PATH`        | `/data/app.db` | Path to SQLite database file         |
| `PORT` | `8000` | Server port when started with `python -m app` |
| `ROOT_PATH` | empty | Public prefix, e.g. `/quacktuaries`; proxy strips it upstream |
| `APP_ENV` | `development` | `production` requires a strong stable secret and Secure cookies |
| `SESSION_SECRET_FILE` | unset | Read signing secret from a protected file; exclusive with `SESSION_SECRET` |
| `FORWARDED_ALLOW_IPS` | `127.0.0.1` | Trusted proxy IPs; Athenaeum sets only its edge address |

## Project Structure

```
quacktuaries/
├── app/
│   ├── __init__.py
│   ├── config.py          # Environment variables & defaults
│   ├── database.py        # SQLAlchemy engine & session
│   ├── game.py            # Core game logic (inspect, sell, scoring)
│   ├── main.py            # FastAPI app entry point
│   ├── models.py          # ORM models (sessions, players, events)
│   ├── templating.py      # Jinja2 template config
│   ├── routes/
│   │   ├── admin.py       # Teacher routes
│   │   ├── public.py      # Home, join, guide, state API
│   │   └── student.py     # Student dashboard & actions
│   ├── templates/         # Jinja2 HTML templates
│   └── static/            # Static assets
├── docs/
│   ├── scoring-analysis.md # Statistical analysis of the scoring formula
│   └── student-guide.md    # Full student guide (rendered at /guide)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## License

MIT
