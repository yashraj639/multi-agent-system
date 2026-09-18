"""Tools for web research and deterministic page extraction."""

import re
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional
import requests
from bs4 import BeautifulSoup
from langchain_core.tools import tool
from tavily import TavilyClient

from src.research_system.config import get_settings
from src.research_system.schemas import Extract, Source

# Standard headers to prevent scraping blocks
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# Tags to strip out completely before extracting text
UNWANTED_TAGS = [
    "script",
    "style",
    "nav",
    "header",
    "footer",
    "svg",
    "noscript",
    "aside",
    "form",
    "iframe",
    "button",
]


def tavily_search(
    query: str,
    max_results: Optional[int] = None,
    api_key: Optional[str] = None,
) -> List[Source]:
    """Execute a search via Tavily Search API and return structured Source items.

    Args:
        query: The search term or question.
        max_results: Max results to return. Defaults to settings.tavily_k.
        api_key: Optional explicit Tavily API key.

    Returns:
        List of Source objects containing url, title, and snippet.
    """
    settings = get_settings()
    key = api_key or settings.tavily_api_key
    k = max_results or settings.tavily_k

    if not key or key.startswith("your_"):
        raise ValueError(
            "Tavily API key is missing or set to placeholder. "
            "Please configure TAVILY_API_KEY in your .env file."
        )

    client = TavilyClient(api_key=key)
    response = client.search(
        query=query,
        max_results=k,
        search_depth="advanced",
    )

    results = response.get("results", [])
    sources: List[Source] = []
    seen_urls = set()

    for item in results:
        url = item.get("url", "").strip()
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)

        title = item.get("title", "").strip()
        snippet = item.get("content", "").strip()
        sources.append(Source(url=url, title=title, snippet=snippet))

    return sources


def fetch_page(
    url: str,
    max_chars: Optional[int] = None,
    timeout: int = 10,
) -> Extract:
    """Safely fetch a webpage, parse clean text using BeautifulSoup, and truncate.

    Args:
        url: The webpage URL to fetch.
        max_chars: Maximum characters to retain. Defaults to settings.max_chars_per_page.
        timeout: HTTP request timeout in seconds.

    Returns:
        Extract object containing the cleaned content or an error message.
    """
    settings = get_settings()
    limit = max_chars or settings.max_chars_per_page

    try:
        response = requests.get(
            url,
            headers=DEFAULT_HEADERS,
            timeout=timeout,
            allow_redirects=True,
        )
        response.raise_for_status()

        # Parse HTML with built-in html.parser
        soup = BeautifulSoup(response.text, "html.parser")

        # Extract page title
        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()

        # Remove clutter / non-content elements
        for tag in soup.find_all(UNWANTED_TAGS):
            tag.decompose()

        # Focus on main content container if available
        main_content = (
            soup.find("main")
            or soup.find("article")
            or soup.find(id=re.compile(r"content|main", re.I))
            or soup.find(class_=re.compile(r"content|post|article", re.I))
            or soup.body
            or soup
        )

        raw_text = main_content.get_text(separator="\n", strip=True)

        # Normalize redundant blank lines and spaces
        cleaned_text = re.sub(r"\n{3,}", "\n\n", raw_text)
        cleaned_text = re.sub(r"[ \t]{2,}", " ", cleaned_text).strip()

        # Truncate to avoid exploding LLM context window
        if len(cleaned_text) > limit:
            cleaned_text = cleaned_text[:limit] + "\n... [content truncated]"

        return Extract(url=url, title=title, content=cleaned_text)

    except requests.RequestException as e:
        return Extract(
            url=url,
            title="",
            content="",
            error=f"Network error fetching {url}: {str(e)}",
        )
    except Exception as e:
        return Extract(
            url=url,
            title="",
            content="",
            error=f"Unexpected error parsing {url}: {str(e)}",
        )


def fetch_pages_parallel(
    urls: List[str],
    max_chars: Optional[int] = None,
    max_workers: int = 5,
) -> List[Extract]:
    """Fetch multiple webpages concurrently using ThreadPoolExecutor.

    Maintains the input URL order in the returned results list.

    Args:
        urls: List of URLs to scrape.
        max_chars: Maximum characters per page.
        max_workers: Concurrent thread worker pool size.

    Returns:
        List of Extract objects matching the input URL ordering.
    """
    if not urls:
        return []

    workers = min(len(urls), max_workers)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(fetch_page, url, max_chars) for url in urls]
        return [f.result() for f in futures]


@tool
def tavily_search_tool(query: str) -> str:
    """Search the web for up-to-date information on a given topic."""
    try:
        sources = tavily_search(query)
        if not sources:
            return "No search results found."
        formatted = []
        for i, s in enumerate(sources, 1):
            formatted.append(f"{i}. [{s.title}]({s.url})\n   Snippet: {s.snippet}")
        return "\n\n".join(formatted)
    except Exception as e:
        return f"Error conducting search: {str(e)}"


@tool
def fetch_page_tool(url: str) -> str:
    """Fetch and extract clean text content from a specific webpage URL."""
    extract = fetch_page(url)
    if extract.error:
        return f"Failed to retrieve page: {extract.error}"
    return f"Title: {extract.title}\nContent:\n{extract.content}"
