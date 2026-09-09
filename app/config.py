"""Application configuration from environment variables and defaults."""

import os
import secrets
import re
from pathlib import Path


PRODUCTION = os.environ.get("APP_ENV", "development") == "production"
ROOT_PATH = os.environ.get("ROOT_PATH", "").rstrip("/")
if ROOT_PATH and not re.fullmatch(r"(?:/[a-z0-9][a-z0-9-]*)+", ROOT_PATH):
    raise RuntimeError("ROOT_PATH must be empty or a lowercase URL path")

_secret_file = os.environ.get("SESSION_SECRET_FILE")
if _secret_file and os.environ.get("SESSION_SECRET"):
    raise RuntimeError("Set only one of SESSION_SECRET and SESSION_SECRET_FILE")
SESSION_SECRET = (Path(_secret_file).read_text().strip() if _secret_file
                  else os.environ.get("SESSION_SECRET", ""))
if PRODUCTION and (len(SESSION_SECRET) < 32 or SESSION_SECRET in {"change-me-too", "local"}):
    raise RuntimeError("Production requires a persistent SESSION_SECRET of at least 32 characters")
SESSION_SECRET = SESSION_SECRET or secrets.token_hex(32)
SESSION_COOKIE = "quacktuaries_session"
DB_PATH = Path(os.environ.get("DB_PATH", "/data/app.db"))
if not DB_PATH.is_absolute():
    raise RuntimeError("DB_PATH must be absolute")
PORT: int = int(os.environ.get("PORT", "8000"))

# Game defaults (Medium preset)
DEFAULT_DEVICE_COUNT: int = 10
DEFAULT_MAX_TURNS: int = 20
DEFAULT_TEST_BUDGET: int = 400
DEFAULT_MIN_N: int = 5
DEFAULT_MAX_N: int = 80
DEFAULT_PREMIUM_SCALE: int = 120
DEFAULT_CONFIDENCE_BONUS: dict[str, float] = {"0.90": 1.0, "0.95": 1.2, "0.99": 1.5}
DEFAULT_MISS_PENALTY: dict[str, int] = {"0.90": 150, "0.95": 350, "0.99": 600}
DEFAULT_REQUIRE_PRIOR_TEST: bool = True
DEFAULT_TIME_LIMIT_MINUTES: int = 15

# Purchase costs (score-as-currency)
TURN_COST: int = 40          # points to buy 1 extra turn
BUDGET_COST: int = 20        # points to buy BUDGET_PURCHASE_AMOUNT extra budget
BUDGET_PURCHASE_AMOUNT: int = 50  # budget units gained per purchase
