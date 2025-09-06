import os
import logging
from dotenv import load_dotenv

load_dotenv()

# Configure logging
def setup_logging():
    """Configure logging with file and console handlers"""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_formatter = logging.Formatter(
        '%(levelname)s - %(name)s - %(message)s'
    )

    # File handler
    file_handler = logging.FileHandler('newsdetection.log')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(file_formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)  # Only warnings and errors to console
    console_handler.setFormatter(console_formatter)

    # Handle Unicode encoding issues on Windows
    if hasattr(console_handler.stream, 'reconfigure'):
        try:
            console_handler.stream.reconfigure(encoding='utf-8')
        except Exception:
            pass  # Fallback to default encoding

    # Add filter to remove emojis from console logs on Windows
    class EmojiFilter(logging.Filter):
        def filter(self, record):
            # Remove common emojis that cause encoding issues
            emoji_chars = ['❌', '✅', '🔍', '🤖', '⚠️', '🎯', '📋', '🔐', '💰', '🧪', '🎯', '🛠️', '⚠️', '📊', '📰', '🚨', '🎯']
            if hasattr(record, 'msg') and isinstance(record.msg, str):
                for emoji in emoji_chars:
                    record.msg = record.msg.replace(emoji, '')
            return True

    console_handler.addFilter(EmojiFilter())

    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

# Initialize logging
logger = setup_logging()

# API Keys
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Model Settings
HUGGINGFACE_MODEL = "google/flan-t5-large"  # Better for analytical and instructional tasks
NLI_MODEL_NAME = "microsoft/deberta-v3-base"

# Search Settings
SEARCH_NUM_RESULTS = 7
SEARCH_EXCLUDE_SITES = ["twitter.com", "youtube.com", "facebook.com", "tiktok.com", "reddit.com", "pinterest.com"]

# Evidence Settings
MAX_EVIDENCE_SENTENCES_PER_ARTICLE = 4
MIN_ENTAILMENT_SCORE = 0.65
MIN_CONTRADICTION_SCORE = 0.65

# System Settings
REQUEST_TIMEOUT = 35
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

# Reasoning Settings
ENABLE_AI_REASONING = True
MIN_ARTICLES_FOR_REASONING = 1

# Cache Settings
CACHE_TTL_SECONDS = 3600  # 1 hour
CACHE_MAX_SIZE = 1000  # Maximum cache entries

# Credible Sources (for scoring)
CREDIBLE_DOMAINS = [
    'reuters.com', 'ap.org', 'bbc.com', 'bbc.co.uk', 'nytimes.com',
    'theguardian.com', 'wsj.com', 'bloomberg.com', 'politico.com',
    'factcheck.org', 'snopes.com', 'mea.gov.in', 'pib.gov.in',
    'whitehouse.gov', 'gov.uk', 'who.int', 'un.org'
]
