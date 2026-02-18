# 🦆 Quacktuaries

A self-hosted, single-container web game for teaching statistical inference through proportions estimation. Students play as insurance actuaries at a rubber duck factory — inspecting batches of ducks for defects, estimating hidden defect rates, and selling insurance policies to maximize their score.

Built with **Python/FastAPI**, **Jinja2** server-rendered templates, and **SQLite**.

## Quick Start (Docker)

```bash
# 1. Clone and enter the project
cd quacktuaries

# 2. Set SESSION_SECRET in docker-compose.yml (or use env vars)

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
pip install -r requirements.txt

# 3. Set environment variables
export SESSION_SECRET="your-secret"
export DB_PATH="./dev.db"

# 4. Run the server
uvicorn app.main:app --reload --port 8000

# 5. Open http://localhost:8000
```

## How to Play

### Teacher Setup
1. Go to `/admin` and enter your name to start a teacher session
2. Create a new session — choose a difficulty preset (Easy / Medium / Hard) which configures batch count, turn limits, and inspection budget
3. Share the **join code** (e.g., `AB12CD`) with students
4. Click **Start Game** when everyone has joined
5. Click **End Game** when time is up — this reveals the true defect rates
6. Use the **Show/Hide** toggle on your dashboard to peek at defect rates mid-game

### Student Gameplay
1. Go to `/join` and enter the join code + your name
2. Each turn, you can either:
   - **INSPECT** a duck batch: choose batch + sample size *n*, pull *n* ducks and find *x* defective ones (uses 1 turn + *n* budget)
   - **SELL POLICY**: estimate a confidence interval [L, U] for a batch's true defect rate *p* (one policy per batch)
3. Selling earns a premium based on interval width, but penalizes misses based on confidence level
4. Once you sell a policy on a batch, that batch is locked — no more inspections or policies on it
5. Maximize your score within the turn and budget limits 🦆

A full **Student Guide** is available in-app at `/guide`.

### Difficulty Presets

| Setting | Easy | Medium | Hard |
|---|---|---|---|
| Duck Batches | 8 | 10 | 12 |
| Max Turns | 20 | 20 | 18 |
| Inspection Budget | 500 | 400 | 300 |
| Min Sample Size | 5 | 5 | 10 |
| Max Sample Size | 100 | 80 | 60 |

### Scoring
- **Premium** = `floor(premium_scale × (1 - width) × confidence_bonus)`
- **Penalty** (if *p* not in [L, U]) = `miss_penalty[confidence]`
- **Net** = premium - penalty

| Confidence | Bonus | Miss Penalty |
|-----------|-------|-------------|
| 0.90      | 1.0×  | 150         |
| 0.95      | 1.2×  | 300         |
| 0.99      | 1.5×  | 500         |

## Configuration

All settings are controlled via environment variables:

| Variable         | Default       | Description                          |
|-----------------|---------------|--------------------------------------|
| `SESSION_SECRET` | (random)      | Secret key for signed cookies        |
| `DB_PATH`        | `/data/app.db` | Path to SQLite database file         |
| `PORT`           | `8000`        | Server port                          |
| `BASE_URL`       | `http://localhost:8000` | Base URL for generated links |

## Exposing Publicly

### Option A: Caddy Reverse Proxy (recommended for home server)

1. Edit the included `Caddyfile` — replace `yourdomain.com` with your domain
2. Add Caddy to your `docker-compose.yml`:

```yaml
services:
  quacktuaries:
    build: .
    container_name: quacktuaries
    environment:
      - SESSION_SECRET=change-me-too
    volumes:
      - quack_data:/data
    expose:
      - "8000"
    restart: unless-stopped

  caddy:
    image: caddy:2
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
    restart: unless-stopped

volumes:
  quack_data:
  caddy_data:
```

### Option B: Cloudflare Tunnel

```bash
# Install cloudflared, then:
cloudflared tunnel --url http://localhost:8000
```

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
│   └── student-guide.md   # Full student guide (rendered at /guide)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## License

MIT
