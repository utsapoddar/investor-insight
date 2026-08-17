import os
import yaml
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

# --- Secrets (from env vars / GitHub secrets) ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "")  # kept as cross-provider fallback
GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
ALPHA_DIGEST_TOKEN = os.environ.get("ALPHA_DIGEST_TOKEN", "")  # PAT for publishing to alpha-digest repo

# --- Paths ---
WATCHLIST_PATH = BASE_DIR / "watchlist.csv"
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
LAST_RUN_PATH = DATA_DIR / "last_run.json"
LAST_DIGEST_PATH = DATA_DIR / "last_digest.html"
TEMPLATES_DIR = BASE_DIR / "templates"
CONFIG_DIR = BASE_DIR / "config"

# --- EDGAR ---
EDGAR_USER_AGENT = os.environ.get("EDGAR_USER_AGENT", "AlphaDigest contact@example.com")
EDGAR_RATE_LIMIT_SLEEP = 0.15

# --- Recipients (DIGEST_RECIPIENTS env var, else local yaml) ---
# The yaml holds real addresses and is gitignored, so CI supplies them via the
# DIGEST_RECIPIENTS secret (comma-separated) instead.
def load_recipients() -> list[str]:
    env = os.environ.get("DIGEST_RECIPIENTS", "")
    if env.strip():
        return [r.strip() for r in env.split(",") if r.strip()]
    path = CONFIG_DIR / "recipients.yaml"
    if not path.exists():
        return []
    with open(path) as f:
        data = yaml.safe_load(f)
    return [r.strip() for r in data.get("recipients", []) if r and r.strip()]

# --- Sources config (from yaml) ---
def load_sources_config() -> dict:
    path = CONFIG_DIR / "sources.yaml"
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}
