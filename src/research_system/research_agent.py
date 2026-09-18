"""Research agent: decomposes queries and gathers verified web sources."""

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from src.research_system.config import get_settings
from src.research_system.schemas import ResearchPlan, Source
from src.research_system.tools import tavily_search


class QueryPlan(BaseModel):
    """Sub-queries generated for research topic."""

    queries: list[str] = []


def plan_search_queries(topic: str, llm: ChatOpenAI | None = None) -> list[str]:
    """Decompose research topic into 2-3 targeted web search queries."""
    settings = get_settings()
    if not settings.openrouter_api_key or settings.openrouter_api_key.startswith("your_"):
        return [topic]

    try:
        model = llm or ChatOpenAI(
            model=settings.model_name,
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            temperature=0.1,
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Generate 2 to 3 concise, distinct web search queries to thoroughly research this topic.",
                ),
                ("human", "Topic: {topic}"),
            ]
        )

        plan: QueryPlan = (prompt | model.with_structured_output(QueryPlan)).invoke({"topic": topic})
        return [q.strip() for q in plan.queries if q.strip()] or [topic]
    except Exception:
        return [topic]


def research(
    query: str,
    max_sources: int | None = None,
    llm: ChatOpenAI | None = None,
) -> ResearchPlan:
    """Decompose query, search the web, deduplicate, and return a ResearchPlan."""
    settings = get_settings()
    limit = max_sources or settings.tavily_k
    queries = plan_search_queries(query, llm=llm)

    sources: list[Source] = []
    seen = set()

    for q in queries:
        try:
            for src in tavily_search(q, max_results=limit):
                if src.url not in seen:
                    seen.add(src.url)
                    sources.append(src)
        except Exception:
            continue

        if len(sources) >= limit:
            break

    return ResearchPlan(query=query, search_queries=queries, sources=sources[:limit])


class ResearchAgent:
    """Compatibility wrapper around research() function."""

    def __init__(self, llm: ChatOpenAI | None = None):
        self.llm = llm

    def research(self, query: str, max_sources: int | None = None) -> ResearchPlan:
        return research(query, max_sources=max_sources, llm=self.llm)
