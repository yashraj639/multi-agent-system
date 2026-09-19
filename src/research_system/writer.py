"""Writer chain: synthesizes verified research into humanized academic reports with Mermaid diagrams."""

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from src.research_system.config import get_settings
from src.research_system.schemas import CritiqueReport, Extract, Report, Source
from src.research_system.tools import invoke_structured

WRITER_SYSTEM_PROMPT = """You are an elite academic researcher and technical writer preparing a rigorous research report for university submission.

CRITICAL WRITING RULES (HUMAN-GRADE, AI-DETECTOR RESISTANT):
1. BANNED AI CLICHES: Never use these dead-giveaway AI words or phrases:
   - "delve", "testament", "tapestry", "landscape" (metaphorical), "plethora", "myriad"
   - "foster", "pivotal", "groundbreaking", "revolutionize", "seamless", "cutting-edge"
   - "furthermore", "moreover", "in conclusion", "it is important to note", "underscores"
2. NATURAL RHYTHM: Vary sentence lengths deliberately. Throw in short, punchy statements. Mix them with detailed technical analysis. Avoid metronomic 20-word sentence cadence.
3. FACT-FIRST GROUNDING: Lead with hard facts, verifiable metrics, dates, and named labs or organizations from the provided sources. Do not pad with vague generalities.
4. INLINE CITATIONS: Use bracketed numeric citations like [1], [2] throughout each section corresponding to the source order.
5. MERMAID DIAGRAM: In the `diagram` field, generate a clean, syntactically valid Mermaid.js diagram (e.g. flowchart TD or graph LR) that illustrates the primary architecture, mechanism, or process discussed in the report. Do NOT wrap it in markdown backticks; provide the raw mermaid code.
6. NO ROBOTIC SUMMARY SECTIONS: Do not end sections with formulaic "Key Takeaways" or "In summary". Let the analysis conclude naturally.
"""

DRAFT_USER_PROMPT = """Topic: {query}

SOURCES AND EXTRACTED CONTENT:
{context}

Generate a comprehensive, deeply researched report adhering strictly to the human-writing and citation rules. Include a valid Mermaid diagram illustrating the core concept.
"""

REVISION_USER_PROMPT = """Topic: {query}

SOURCES AND EXTRACTED CONTENT:
{context}

PREVIOUS DRAFT:
Title: {draft_title}
Summary: {draft_summary}
Sections:
{draft_sections}

EDITORIAL CRITIQUE & REVIEW FEEDBACK:
Assessment: {critique_assessment}
Issues identified to fix:
{critique_issues}

Revise and upgrade this report. Address every identified critique: supply missing data, eliminate unverified claims, and sharpen the analysis and diagram. Maintain natural human writing and rigorous citations throughout.
"""


def format_context(sources: list[Source], extracts: list[Extract]) -> str:
    """Format sources and webpage extracts into context for the prompt."""
    sections = []
    extract_map = {e.url: e for e in extracts}

    for idx, src in enumerate(sources, 1):
        ext = extract_map.get(src.url)
        content = ext.content if ext and ext.content else src.snippet
        sections.append(
            f"[{idx}] {src.title}\nURL: {src.url}\nExcerpt / Content:\n{content}\n"
        )
    return "\n---\n".join(sections) if sections else "No extracted source content available."


def write_report(
    query: str,
    sources: list[Source],
    extracts: list[Extract],
    critique: CritiqueReport | None = None,
    previous_report: Report | None = None,
    llm: ChatOpenAI | None = None,
) -> Report:
    """Draft or revise a research report using structured LLM output."""
    settings = get_settings()
    model = llm or ChatOpenAI(
        model=settings.model_name,
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
        temperature=0.3,
    )

    context = format_context(sources, extracts)

    if critique and previous_report:
        issues_text = "\n".join(
            f"- [{item.severity}] {item.category}: {item.description} -> Suggestion: {item.suggestion}"
            for item in critique.items
        )
        sections_text = "\n\n".join(
            f"### {s.heading}\n{s.body}" for s in previous_report.sections
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", WRITER_SYSTEM_PROMPT),
                ("human", REVISION_USER_PROMPT),
            ]
        )
        vars = {
            "query": query,
            "context": context,
            "draft_title": previous_report.title,
            "draft_summary": previous_report.summary,
            "draft_sections": sections_text,
            "critique_assessment": critique.overall_assessment,
            "critique_issues": issues_text or "General polish requested.",
        }
    else:
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", WRITER_SYSTEM_PROMPT),
                ("human", DRAFT_USER_PROMPT),
            ]
        )
        vars = {
            "query": query,
            "context": context,
        }

    report: Report = invoke_structured(model, prompt, vars, Report)

    if not report.sources:
        report.sources = sources

    return report
