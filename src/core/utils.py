"""
Utility functions for config loading, artifact management, etc.
"""

import hashlib
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


def load_config(config_path: str = "config/settings.yaml") -> Dict[str, Any]:
    """Load YAML configuration file"""
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        logger.info(f"Loaded config from {config_path}")
        return config
    except FileNotFoundError:
        logger.error(f"Config file not found: {config_path}")
        raise
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML: {e}")
        raise


def get_env_var(key: str, required: bool = False) -> Optional[str]:
    """Get environment variable with optional requirement check"""
    value = os.getenv(key)
    if required and not value:
        raise ValueError(f"Required environment variable {key} not set")
    return value


def create_artifacts_dir(symbol: str, timestamp: Optional[datetime] = None) -> Path:
    """
    Create artifacts directory for a run.
    Format: artifacts/{symbol}/{YYYY-MM-DD}/{HH-MM-SS}/
    
    Uses Eastern Time (EST/EDT) and separate time folders for each run.
    """
    import pytz
    
    if timestamp is None:
        timestamp = datetime.utcnow()
    
    # Convert UTC to Eastern Time
    utc_tz = pytz.UTC
    eastern_tz = pytz.timezone('US/Eastern')
    
    if timestamp.tzinfo is None:
        timestamp = utc_tz.localize(timestamp)
    
    timestamp_est = timestamp.astimezone(eastern_tz)
    
    # Format: date folder, then time subfolder
    date_str = timestamp_est.strftime("%Y-%m-%d")
    time_str = timestamp_est.strftime("%H-%M-%S")
    
    artifacts_root = Path(get_env_var("ARTIFACTS_DIR") or "./artifacts")
    run_dir = artifacts_root / symbol / date_str / time_str

    run_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Created artifacts directory: {run_dir} (EST: {timestamp_est.strftime('%Y-%m-%d %H:%M:%S %Z')})")

    return run_dir


def save_json(data: Dict[str, Any], filepath: Path) -> None:
    """Save JSON data to file"""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)
    logger.debug(f"Saved JSON to {filepath}")


def load_json(filepath: Path) -> Dict[str, Any]:
    """Load JSON data from file"""
    with open(filepath, "r") as f:
        return json.load(f)


def compute_content_hash(data: Any) -> str:
    """Compute SHA256 hash of data for audit trail"""
    content = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(content.encode()).hexdigest()


def setup_logging(level: str = "INFO", log_file: Optional[str] = None) -> None:
    """Configure logging"""
    log_level = getattr(logging, level.upper(), logging.INFO)

    handlers = [logging.StreamHandler()]
    if log_file:
        log_dir = Path(log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )


def ensure_utc_index(df):
    """Ensure DataFrame index is UTC-aware datetime"""
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    elif df.index.tz != "UTC":
        df.index = df.index.tz_convert("UTC")
    return df


def get_polygon_api_key() -> str:
    """Get Polygon API key from environment"""
    api_key = get_env_var("POLYGON_API_KEY")
    if not api_key:
        logger.warning("POLYGON_API_KEY not set, will use cached data only")
    return api_key or ""


def get_alpaca_credentials() -> Dict[str, Optional[str]]:
    """
    Get Alpaca credentials and defaults from environment.
    
    Returns:
        Dict with key_id, secret_key, base_url, data_feed
    """
    key_id = (
        get_env_var("ALPACA_KEY_ID", required=False)
        or get_env_var("ALPACA_API_KEY", required=False)
        or get_env_var("APCA_API_KEY_ID", required=False)
    )
    secret_key = (
        get_env_var("ALPACA_SECRET_KEY", required=False)
        or get_env_var("ALPACA_API_SECRET", required=False)
        or get_env_var("APCA_API_SECRET_KEY", required=False)
    )

    credentials = {
        "key_id": key_id,
        "secret_key": secret_key,
        "base_url": get_env_var("ALPACA_BASE_URL", required=False),
        "data_feed": get_env_var("ALPACA_DATA_FEED", required=False) or "iex",
    }

    if not credentials["key_id"] or not credentials["secret_key"]:
        logger.warning("Alpaca credentials not fully configured; API calls may fail")

    return credentials


def get_openai_api_key() -> str:
    """Get OpenAI API key from environment"""
    return get_env_var("OPENAI_API_KEY", required=False) or ""


def get_telegram_token() -> str:
    """Get Telegram bot token from environment"""
    return get_env_var("TELEGRAM_BOT_TOKEN", required=False) or ""


def get_huggingface_token() -> str:
    """Get Hugging Face API token from environment"""
    return get_env_var("HUGGINGFACE_API_TOKEN", required=False) or ""


def get_perplexity_api_key() -> str:
    """Get Perplexity API key from file or environment"""
    # Try file first
    try:
        key_file = Path("perp_key.txt")
        if key_file.exists():
            return key_file.read_text().strip()
    except Exception:
        pass
    
    # Fallback to environment variable
    return get_env_var("PERPLEXITY_API_KEY", required=False) or ""
