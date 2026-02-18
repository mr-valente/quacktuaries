"""Application configuration from environment variables and defaults."""

import os
import secrets


SESSION_SECRET: str = os.environ.get("SESSION_SECRET", secrets.token_hex(32))
DATABASE_URL: str = os.environ.get("DATABASE_URL", "sqlite:////data/app.db")
BASE_URL: str = os.environ.get("BASE_URL", "http://localhost:8000")
PORT: int = int(os.environ.get("PORT", "8000"))

# Game defaults (Medium preset)
DEFAULT_DEVICE_COUNT: int = 10
DEFAULT_MAX_TURNS: int = 20
DEFAULT_TEST_BUDGET: int = 400
DEFAULT_MIN_N: int = 5
DEFAULT_MAX_N: int = 80
DEFAULT_PREMIUM_SCALE: int = 120
DEFAULT_CONFIDENCE_BONUS: dict[str, float] = {"0.90": 1.0, "0.95": 1.2, "0.99": 1.5}
DEFAULT_MISS_PENALTY: dict[str, int] = {"0.90": 150, "0.95": 300, "0.99": 500}
DEFAULT_REQUIRE_PRIOR_TEST: bool = True
