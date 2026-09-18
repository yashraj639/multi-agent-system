from unittest.mock import MagicMock, patch
from src.research_system.config import Settings
from src.research_system.research_agent import QueryPlan, ResearchAgent, plan_search_queries
from src.research_system.schemas import Source


def test_plan_search_queries_fallback_on_missing_key():
    mock_settings = Settings(openrouter_api_key="", tavily_api_key="")
    with patch("src.research_system.research_agent.get_settings", return_value=mock_settings):
        queries = plan_search_queries("solid-state batteries")
        assert queries == ["solid-state batteries"]


def test_plan_search_queries_with_mock_llm():
    mock_settings = Settings(openrouter_api_key="valid_key", tavily_api_key="valid_tavily")
    mock_llm = MagicMock()
    mock_chain = MagicMock()
    mock_chain.invoke.return_value = QueryPlan(
        queries=["batteries commercialization 2026", "battery energy density benchmarks"]
    )

    with patch("src.research_system.research_agent.get_settings", return_value=mock_settings):
        with patch("src.research_system.research_agent.ChatPromptTemplate.from_messages") as mock_prompt:
            mock_prompt.return_value.__or__.return_value = mock_chain
            queries = plan_search_queries("solid-state batteries", llm=mock_llm)
            assert len(queries) == 2
            assert "batteries commercialization 2026" in queries


def test_research_agent_deduplication_and_limit():
    agent = ResearchAgent()

    mock_sources_1 = [
        Source(url="https://source1.com", title="Source 1", snippet="Snippet 1"),
        Source(url="https://source2.com", title="Source 2", snippet="Snippet 2"),
    ]
    mock_sources_2 = [
        Source(url="https://source2.com", title="Duplicate Source", snippet="Snippet 2"),
        Source(url="https://source3.com", title="Source 3", snippet="Snippet 3"),
    ]

    with patch(
        "src.research_system.research_agent.plan_search_queries",
        return_value=["query1", "query2"],
    ):
        with patch(
            "src.research_system.research_agent.tavily_search",
            side_effect=[mock_sources_1, mock_sources_2],
        ):
            plan = agent.research("test topic", max_sources=2)
            assert plan.query == "test topic"
            assert plan.search_queries == ["query1", "query2"]
            assert len(plan.sources) == 2
            assert plan.sources[0].url == "https://source1.com"
            assert plan.sources[1].url == "https://source2.com"
