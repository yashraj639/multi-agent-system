from unittest.mock import MagicMock, patch
from src.research_system.pipeline import ResearchPipeline
from src.research_system.schemas import CritiqueItem, CritiqueReport, Extract, Report, Section, Source


def test_pipeline_run_end_to_end_mock(tmp_path):
    mock_llm = MagicMock()
    mock_sources = [
        Source(url="https://test.com", title="Test Tech", snippet="Snippet text"),
    ]
    mock_draft = Report(
        title="Draft Report",
        summary="Draft Summary",
        sections=[Section(heading="Intro", body="Content [1]")],
        sources=mock_sources,
    )
    mock_critique = CritiqueReport(
        items=[CritiqueItem(category="Missing Information", severity="Low", description="Add year", suggestion="Include 2026")],
        overall_assessment="Good draft",
    )
    mock_revised = Report(
        title="Final Report",
        summary="Revised Summary",
        sections=[Section(heading="Intro", body="Content 2026 [1]")],
        sources=mock_sources,
    )

    stages_recorded = []

    def callback(stage: str):
        stages_recorded.append(stage)

    with patch("src.research_system.pipeline.research") as mock_research:
        mock_research.return_value.sources = mock_sources
        with patch("src.research_system.pipeline.fetch_pages_parallel") as mock_fetch:
            mock_fetch.return_value = [Extract(url="https://test.com", content="Full text")]
            with patch("src.research_system.pipeline.write_report", side_effect=[mock_draft, mock_revised]):
                with patch("src.research_system.pipeline.critique_report", return_value=mock_critique):
                    pipeline = ResearchPipeline(llm=mock_llm, output_dir=tmp_path)
                    result = pipeline.run("quantum AI", on_stage_start=callback)

                    assert result.report.title == "Final Report"
                    assert result.critique is not None
                    assert "research" in stages_recorded
                    assert "reading" in stages_recorded
                    assert "drafting" in stages_recorded
                    assert "critiquing" in stages_recorded
                    assert "revising" in stages_recorded
                    assert "completed" in stages_recorded


def test_pipeline_skip_critique_fast_mode(tmp_path):
    mock_llm = MagicMock()
    mock_sources = [Source(url="https://test.com", title="T", snippet="S")]
    mock_draft = Report(title="Fast Draft", summary="S", sections=[], sources=mock_sources)

    with patch("src.research_system.pipeline.research") as mock_research:
        mock_research.return_value.sources = mock_sources
        with patch("src.research_system.pipeline.fetch_pages_parallel", return_value=[]):
            with patch("src.research_system.pipeline.write_report", return_value=mock_draft):
                with patch("src.research_system.pipeline.critique_report") as mock_critique:
                    pipeline = ResearchPipeline(llm=mock_llm, output_dir=tmp_path)
                    result = pipeline.run("fast topic", skip_critique=True)

                    assert result.report.title == "Fast Draft"
                    assert result.critique is None
                    mock_critique.assert_not_called()


def test_pipeline_save_report(tmp_path):
    pipeline = ResearchPipeline(output_dir=tmp_path)
    report = Report(title="Test", summary="Summary", sections=[], sources=[])
    from src.research_system.schemas import CritiquedReport
    result = CritiquedReport(report=report, critique=None)

    saved_path = pipeline.save_report(result, query="sample query")
    assert saved_path.exists()
    assert saved_path.is_file()
    assert "# Test" in saved_path.read_text(encoding="utf-8")
