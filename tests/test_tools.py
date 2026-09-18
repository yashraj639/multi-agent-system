from unittest.mock import MagicMock, patch
import pytest
from src.research_system.config import Settings
from src.research_system.tools import fetch_page, fetch_pages_parallel, tavily_search


def test_fetch_page_success():
    extract = fetch_page("https://example.com")
    assert extract.url == "https://example.com"
    assert extract.title == "Example Domain"
    assert "Example Domain" in extract.content
    assert extract.error is None


def test_fetch_page_error_handling():
    extract = fetch_page("https://this-domain-does-not-exist-xyz12345.org", timeout=2)
    assert extract.error is not None
    assert extract.content == ""


def test_fetch_pages_parallel():
    urls = ["https://example.com", "https://example.com"]
    extracts = fetch_pages_parallel(urls)
    assert len(extracts) == 2
    assert extracts[0].title == "Example Domain"
    assert extracts[1].title == "Example Domain"


def test_tavily_search_missing_key():
    mock_settings = Settings(openrouter_api_key="", tavily_api_key="")
    with patch("src.research_system.tools.get_settings", return_value=mock_settings):
        with pytest.raises(ValueError, match="Tavily API key missing"):
            tavily_search("query")


def test_tavily_search_success():
    mock_settings = Settings(openrouter_api_key="valid", tavily_api_key="tvly-mock-key")
    mock_client = MagicMock()
    mock_client.search.return_value = {
        "results": [
            {
                "url": "https://python.org",
                "title": "Python Programming",
                "content": "Python is a high-level programming language.",
            },
            {
                "url": "https://python.org",  # Duplicate to test deduplication
                "title": "Python Duplicate",
                "content": "Duplicate content",
            },
        ]
    }

    with patch("src.research_system.tools.get_settings", return_value=mock_settings):
        with patch("src.research_system.tools.TavilyClient", return_value=mock_client):
            sources = tavily_search("python", max_results=5)
            assert len(sources) == 1
            assert sources[0].url == "https://python.org"
            assert sources[0].title == "Python Programming"
            assert "Python is a high-level" in sources[0].snippet
