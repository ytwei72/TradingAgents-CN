import sys
from pathlib import Path
import logging

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from tradingagents.utils.logging_manager import get_logger
from tradingagents.news_engine.news_prov_googlenews import GoogleNewsProvider

# Configure logging to stdout
logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
logger = get_logger("news_engine.googlenews")
# Also configure 'agents' logger used by googlenews_utils
agents_logger = logging.getLogger('agents')
agents_logger.setLevel(logging.DEBUG)
agents_logger.addHandler(logging.StreamHandler(sys.stdout))

def test_google_news():
    print("Testing Google News Provider...")
    provider = GoogleNewsProvider()
    if not provider.is_available():
        print("Google News Provider is not available.")
        return

    print("Fetching news for NVDA...")
    try:
        items = provider.get_news("NVDA", max_news=5)
        print(f"Got {len(items)} items.")
        for item in items:
            print(f"- {item.title} ({item.publish_time})")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_google_news()
