from src.research_system.schemas import (
    CritiqueItem,
    CritiqueReport,
    CritiquedReport,
    Extract,
    Report,
    ResearchPlan,
    Section,
    Source,
)


def test_source_schema():
    src = Source(url="https://example.com", title="Example", snippet="Snippet text")
    assert src.url == "https://example.com"
    assert src.title == "Example"
    assert src.snippet == "Snippet text"


def test_research_plan_schema():
    src = Source(url="https://example.com", title="Example", snippet="Snippet text")
    plan = ResearchPlan(
        query="quantum computing",
        search_queries=["quantum computing breakthrough", "qubit stability"],
        sources=[src],
    )
    assert plan.query == "quantum computing"
    assert len(plan.search_queries) == 2
    assert len(plan.sources) == 1


def test_extract_schema():
    extract = Extract(url="https://example.com", title="Example", content="Main body")
    assert extract.error is None
    assert extract.content == "Main body"

    failed = Extract(url="https://bad.com", content="", error="404 Not Found")
    assert failed.error == "404 Not Found"


def test_report_and_markdown_serialization():
    src = Source(url="https://example.com/ai", title="AI 2026", snippet="Progress")
    report = Report(
        title="State of AI",
        summary="AI has advanced rapidly.",
        sections=[
            Section(heading="Key Breakthroughs", body="Models reason with high accuracy [1]."),
            Section(heading="Challenges", body="Compute efficiency remains crucial [1]."),
        ],
        sources=[src],
    )

    critique = CritiqueReport(
        items=[
            CritiqueItem(
                category="Missing Information",
                severity="Medium",
                description="Need specific cost figures",
                suggestion="Add cloud pricing comparison",
            )
        ],
        overall_assessment="Well written draft with solid core structure.",
    )

    critiqued_report = CritiquedReport(report=report, critique=critique)
    markdown = critiqued_report.to_markdown()

    assert "# State of AI" in markdown
    assert "## Executive Summary" in markdown
    assert "## Key Breakthroughs" in markdown
    assert "## Editorial Critique & Review Log" in markdown
    assert "| Missing Information | Medium | Need specific cost figures |" in markdown
    assert "1. [AI 2026](https://example.com/ai)" in markdown


def test_parse_json_response():
    from src.research_system.schemas import parse_json_response

    # Test markdown backticks
    raw_markdown = "```json\n{\"title\": \"Parsed Title\", \"summary\": \"Summary\", \"sections\": []}\n```"
    res1 = parse_json_response(raw_markdown, Report)
    assert res1.title == "Parsed Title"

    # Test raw text without markdown
    raw_text = "Here is the result: {\"title\": \"Plain Title\", \"summary\": \"Summary\", \"sections\": []} Hope it helps!"
    res2 = parse_json_response(raw_text, Report)
    assert res2.title == "Plain Title"
