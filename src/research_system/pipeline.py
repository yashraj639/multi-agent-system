"""Pipeline orchestration: connects research, parallel extraction, drafting, critique, and revision."""

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from langchain_openai import ChatOpenAI

from src.research_system.config import get_settings
from src.research_system.critic import critique_report
from src.research_system.research_agent import research
from src.research_system.schemas import CritiquedReport, Report
from src.research_system.tools import fetch_pages_parallel
from src.research_system.writer import write_report


class ResearchPipeline:
    """Orchestrates the multi-agent research workflow."""

    def __init__(
        self,
        llm: ChatOpenAI | None = None,
        output_dir: str | Path = "output",
    ):
        settings = get_settings()
        self.llm = llm or (
            ChatOpenAI(
                model=settings.model_name,
                api_key=settings.openrouter_api_key,
                base_url=settings.openrouter_base_url,
                temperature=0.2,
            )
            if settings.openrouter_api_key
            else None
        )
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run(
        self,
        query: str,
        max_sources: int | None = None,
        skip_critique: bool = False,
        on_stage_start: Callable[[str], None] | None = None,
    ) -> CritiquedReport:
        """Execute full research pipeline with optional critique and live callbacks."""
        def notify(stage: str):
            if on_stage_start:
                on_stage_start(stage)

        # 1. Research planning and search
        notify("research")
        plan = research(query, max_sources=max_sources, llm=self.llm)
        if not plan.sources:
            return CritiquedReport(
                report=Report(
                    title=f"Research on: {query}",
                    summary="No web sources could be retrieved for this topic.",
                    sections=[],
                    sources=[],
                ),
                critique=None,
            )

        # 2. Parallel webpage reading
        notify("reading")
        extracts = fetch_pages_parallel([s.url for s in plan.sources])

        # 3. Initial report drafting
        notify("drafting")
        draft = write_report(
            query=query,
            sources=plan.sources,
            extracts=extracts,
            llm=self.llm,
        )

        # 4. Critique & revision pass
        critique = None
        final_report = draft

        if not skip_critique:
            notify("critiquing")
            critique = critique_report(
                query=query,
                report=draft,
                sources=plan.sources,
                extracts=extracts,
                llm=self.llm,
            )

            notify("revising")
            final_report = write_report(
                query=query,
                sources=plan.sources,
                extracts=extracts,
                critique=critique,
                previous_report=draft,
                llm=self.llm,
            )

        notify("completed")
        return CritiquedReport(report=final_report, critique=critique)

    def save_report(
        self,
        result: CritiquedReport,
        query: str,
        filename: str | None = None,
    ) -> Path:
        """Save the generated markdown report to the output directory."""
        if not filename:
            safe = "".join(c for c in query[:30] if c.isalnum() or c == " ").strip().replace(" ", "_") or "research"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"report_{safe}_{timestamp}.md"

        filepath = self.output_dir / filename
        filepath.write_text(result.to_markdown(), encoding="utf-8")
        return filepath
