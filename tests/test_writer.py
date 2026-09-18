from unittest.mock import MagicMock
from src.research_system.schemas import CritiqueItem, CritiqueReport, Extract, Report, Section, Source
from src.research_system.writer import format_context, write_report


def test_format_context():
    sources = [
        Source(url="https://source1.com", title="Title 1", snippet="Snippet 1"),
        Source(url="https://source2.com", title="Title 2", snippet="Snippet 2"),
    ]
    extracts = [
        Extract(url="https://source1.com", title="Title 1", content="Detailed article body."),
    ]
    formatted = format_context(sources, extracts)
    assert "[1] Title 1" in formatted
    assert "Detailed article body." in formatted
    assert "[2] Title 2" in formatted
    assert "Snippet 2" in formatted


def test_write_report_draft_mock():
    mock_llm = MagicMock()
    mock_chain = MagicMock()
    mock_llm.with_structured_output.return_value = mock_chain

    expected_report = Report(
        title="Solid-State Batteries in 2026",
        summary="A major step forward in energy density.",
        sections=[Section(heading="Electrolyte Stability", body="Ceramic separators yield 400 Wh/kg [1].")],
        diagram="graph TD\n  A[Cathode] --> B[Solid Electrolyte]",
        sources=[],
    )
    mock_chain.invoke.return_value = expected_report
    mock_chain.return_value = expected_report

    sources = [Source(url="https://battery.com", title="Battery Tech", snippet="Snippet")]
    extracts = [Extract(url="https://battery.com", title="Battery Tech", content="Full text")]

    report = write_report(
        query="solid state batteries",
        sources=sources,
        extracts=extracts,
        llm=mock_llm,
    )

    assert report.title == "Solid-State Batteries in 2026"
    assert report.diagram is not None
    assert "Cathode" in report.diagram
    assert len(report.sources) == 1
    assert report.sources[0].url == "https://battery.com"


def test_write_report_revision_mock():
    mock_llm = MagicMock()
    mock_chain = MagicMock()
    mock_llm.with_structured_output.return_value = mock_chain

    revised_report = Report(
        title="Solid-State Batteries: Revised",
        summary="Updated analysis with cost data.",
        sections=[Section(heading="Cost Analysis", body="Costs dropped to $80/kWh [1].")],
        diagram="graph LR\n  A --> B",
        sources=[],
    )
    mock_chain.invoke.return_value = revised_report
    mock_chain.return_value = revised_report

    draft = Report(
        title="Draft",
        summary="Initial draft",
        sections=[Section(heading="Cost", body="Costs are unknown.")],
        sources=[],
    )
    critique = CritiqueReport(
        items=[CritiqueItem(category="Missing Information", severity="High", description="Missing cost data", suggestion="Add $80/kWh metric")],
        overall_assessment="Needs cost figures.",
    )

    result = write_report(
        query="batteries",
        sources=[Source(url="https://data.com", title="Data", snippet="")],
        extracts=[],
        critique=critique,
        previous_report=draft,
        llm=mock_llm,
    )

    assert result.title == "Solid-State Batteries: Revised"
    assert len(result.sections) == 1
    assert "80/kWh" in result.sections[0].body
