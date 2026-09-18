from unittest.mock import MagicMock
from src.research_system.critic import critique_report
from src.research_system.schemas import (
    CritiqueItem,
    CritiqueReport,
    Extract,
    Report,
    Section,
    Source,
)


def test_critique_report_mock():
    mock_llm = MagicMock()
    mock_chain = MagicMock()
    mock_llm.with_structured_output.return_value = mock_chain

    expected_critique = CritiqueReport(
        items=[
            CritiqueItem(
                category="Unsupported Claim",
                severity="High",
                description="The 500 Wh/kg number is not in the source text.",
                suggestion="Cite the actual 400 Wh/kg benchmark from Source [1].",
            ),
            CritiqueItem(
                category="Tone & Style",
                severity="Low",
                description="Section 2 uses the word 'delve'.",
                suggestion="Replace with direct analytical phrasing.",
            ),
        ],
        overall_assessment="Promising draft with two specific inaccuracies to correct.",
    )
    mock_chain.invoke.return_value = expected_critique
    mock_chain.return_value = expected_critique

    report = Report(
        title="Solid State Analysis",
        summary="Overview of progress",
        sections=[Section(heading="Density", body="Cells reach 500 Wh/kg as we delve into the physics.")],
        diagram="graph TD\n  A --> B",
        sources=[],
    )
    sources = [Source(url="https://source.com", title="Battery", snippet="Cells reach 400 Wh/kg.")]
    extracts = [Extract(url="https://source.com", title="Battery", content="Cells reach 400 Wh/kg.")]

    result = critique_report(
        query="solid state batteries",
        report=report,
        sources=sources,
        extracts=extracts,
        llm=mock_llm,
    )

    assert len(result.items) == 2
    assert result.items[0].severity == "High"
    assert "500 Wh/kg" in result.items[0].description
    assert result.items[1].category == "Tone & Style"
    assert "Promising draft" in result.overall_assessment


def test_critique_report_empty_items():
    mock_llm = MagicMock()
    mock_chain = MagicMock()
    mock_llm.with_structured_output.return_value = mock_chain

    expected_critique = CritiqueReport(
        items=[],
        overall_assessment="Flawless draft.",
    )
    mock_chain.invoke.return_value = expected_critique
    mock_chain.return_value = expected_critique

    report = Report(title="T", summary="S", sections=[])
    res = critique_report("q", report, [], [], llm=mock_llm)
    assert res.overall_assessment == "Flawless draft."
