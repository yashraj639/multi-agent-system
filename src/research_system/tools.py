"""Tools for web research and parallel webpage scraping."""

from concurrent.futures import ThreadPoolExecutor
from pydantic import BaseModel
import requests
from bs4 import BeautifulSoup
from tavily import TavilyClient

from src.research_system.config import get_settings
from src.research_system.schemas import Extract, Source, parse_json_response

UNWANTED_TAGS = ["script", "style", "nav", "header", "footer", "svg", "noscript", "aside", "form"]
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def tavily_search(query: str, max_results: int | None = None) -> list[Source]:
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


def fetch_page(url: str, max_chars: int | None = None, timeout: int = 10) -> Extract:
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
    urls: list[str],
    max_chars: int | None = None,
    max_workers: int = 5,
) -> list[Extract]:
    """Fetch multiple webpages concurrently using ThreadPoolExecutor."""
    if not urls:
        return []
    with ThreadPoolExecutor(max_workers=min(len(urls), max_workers)) as executor:
        return list(executor.map(lambda u: fetch_page(u, max_chars), urls))


def invoke_structured(model, prompt, variables: dict, schema: type[BaseModel]):
    """Invoke LLM with structured output, falling back to JSON extraction for free models."""
    try:
        return (prompt | model.with_structured_output(schema)).invoke(variables)
    except Exception:
        resp = (prompt | model).invoke(variables)
        return parse_json_response(resp.content, schema)
