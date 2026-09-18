"""Tools for web research and parallel webpage scraping."""

from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional
import requests
from bs4 import BeautifulSoup
from tavily import TavilyClient

from src.research_system.config import get_settings
from src.research_system.schemas import Extract, Source

UNWANTED_TAGS = ["script", "style", "nav", "header", "footer", "svg", "noscript", "aside", "form"]
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def tavily_search(query: str, max_results: Optional[int] = None) -> List[Source]:
    """Execute search via Tavily and return deduplicated Source items."""
    settings = get_settings()
    key = settings.tavily_api_key
    if not key or key.startswith("your_"):
        raise ValueError("Tavily API key missing or invalid. Set TAVILY_API_KEY in .env.")

    client = TavilyClient(api_key=key)
    res = client.search(query=query, max_results=max_results or settings.tavily_k)

    sources = []
    seen = set()
    for item in res.get("results", []):
        url = item.get("url", "").strip()
        if url and url not in seen:
            seen.add(url)
            sources.append(
                Source(
                    url=url,
                    title=item.get("title", "").strip(),
                    snippet=item.get("content", "").strip(),
                )
            )
    return sources


def fetch_page(url: str, max_chars: Optional[int] = None, timeout: int = 10) -> Extract:
    """Fetch a webpage, extract cleaned text, and truncate."""
    settings = get_settings()
    limit = max_chars or settings.max_chars_per_page

    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else ""

        for tag in soup.find_all(UNWANTED_TAGS):
            tag.decompose()

        body = soup.body or soup
        text = "\n\n".join(line.strip() for line in body.get_text().splitlines() if line.strip())

        if len(text) > limit:
            text = text[:limit] + "\n... [truncated]"

        return Extract(url=url, title=title, content=text)
    except Exception as e:
        return Extract(url=url, title="", content="", error=str(e))


def fetch_pages_parallel(
    urls: List[str],
    max_chars: Optional[int] = None,
    max_workers: int = 5,
) -> List[Extract]:
    """Fetch multiple webpages concurrently using ThreadPoolExecutor."""
    if not urls:
        return []
    with ThreadPoolExecutor(max_workers=min(len(urls), max_workers)) as executor:
        return list(executor.map(lambda u: fetch_page(u, max_chars), urls))
