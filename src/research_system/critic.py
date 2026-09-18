"""Critic chain: rigorous academic review and AI-tell detection for draft reports."""

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from src.research_system.config import get_settings
from src.research_system.schemas import CritiqueReport, Extract, Report, Source
from src.research_system.writer import format_context

CRITIC_SYSTEM_PROMPT = """You are a rigorous academic peer-reviewer and senior thesis editor. 
Your objective is to critically audit the draft research report against the raw source materials.

EVALUATION CRITERIA:
1. UNSUPPORTED CLAIMS & FACT CHECKING:
   - Identify any claim, statistic, or date in the report that is NOT backed up by the provided source extracts.
   - Verify that citations [1], [2] actually support the specific sentences they are attached to.
2. MISSING INFORMATION:
   - Identify crucial context, counterarguments, numerical benchmarks, or limitations present in the source extracts that the writer failed to mention.
3. HUMAN WRITING & AI DETECTOR AUDIT:
   - Flag any presence of dead AI buzzwords ("delve", "testament", "tapestry", "landscape", "pivotal", "foster", "groundbreaking", "seamless", "furthermore", "moreover", "in conclusion").
   - Flag metronomic, monotonous sentence cadence or generic filler paragraphs.
4. DIAGRAM QUALITY:
   - Check if the Mermaid diagram exists, is syntactically sound, and directly clarifies the report's core mechanism or process.
5. LOGICAL STRUCTURE:
   - Flag redundant sections, jarring transitions, or superficial summaries.

Categorize each critique item with clear severity (High, Medium, Low) and provide actionable suggestions to fix it in the next revision.
"""

CRITIC_USER_PROMPT = """RESEARCH TOPIC: {query}

RAW SOURCE MATERIALS & EXTRACTS:
{context}

DRAFT REPORT TO CRITIQUE:
Title: {title}
Executive Summary: {summary}

Sections:
{sections}

Mermaid Diagram:
{diagram}

Conduct your peer review and output a structured CritiqueReport with prioritized items and an overall assessment.
"""


def critique_report(
    query: str,
    report: Report,
    sources: list[Source],
    extracts: list[Extract],
    llm: ChatOpenAI | None = None,
) -> CritiqueReport:
    """Critique a draft report against the original source materials."""
    settings = get_settings()
    model = llm or ChatOpenAI(
        model=settings.model_name,
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
        temperature=0.1,
    )

    context = format_context(sources, extracts)
    sections_text = "\n\n".join(
        f"### {s.heading}\n{s.body}" for s in report.sections
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", CRITIC_SYSTEM_PROMPT),
            ("human", CRITIC_USER_PROMPT),
        ]
    )

    chain = prompt | model.with_structured_output(CritiqueReport)
    return chain.invoke(
        {
            "query": query,
            "context": context,
            "title": report.title,
            "summary": report.summary,
            "sections": sections_text,
            "diagram": report.diagram or "None provided",
        }
    )
