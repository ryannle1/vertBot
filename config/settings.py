"""
Centralized settings and path management for VertBot.
Handles environment variables and file paths.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables once at module import
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"

# Configuration file paths
CHANNELS_FILE = CONFIG_DIR / "channels.json"
TICKERS_FILE = CONFIG_DIR / "tickers.json"
TICKERS_CSV_FILE = DATA_DIR / "tickers.csv"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# Environment variables
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "deepseek-r1:1.5b")
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")

# Docker environment detection
IS_DOCKER = os.getenv("DOCKER_ENV", "false").lower() == "true"
