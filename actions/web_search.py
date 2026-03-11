"""
actions/web_search.py — open the default browser with a search query.
"""
import webbrowser
import urllib.parse
import logging

logger = logging.getLogger(__name__)

_ENGINES: dict[str, str] = {
    "google":     "https://www.google.com/search?q={}",
    "bing":       "https://www.bing.com/search?q={}",
    "youtube":    "https://www.youtube.com/results?search_query={}",
    "duckduckgo": "https://duckduckgo.com/?q={}",
}


def execute(intent: dict) -> None:
    """
    Open the user's default browser with the search URL.

    Expected intent keys
    --------------------
    query  : str   — the search term
    engine : str   — one of google | bing | youtube | duckduckgo  (optional)
    """
    query = intent.get("query", "").strip()
    if not query:
        logger.warning("search intent has an empty query — skipping")
        return

    engine = intent.get("engine", "google").lower()
    template = _ENGINES.get(engine, _ENGINES["google"])
    url = template.format(urllib.parse.quote_plus(query))

    logger.info("Opening search: %s", url)
    webbrowser.open(url)
