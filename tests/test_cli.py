from unittest.mock import MagicMock, patch
from src.research_system.cli import print_banner, print_critique_table
from src.research_system.schemas import CritiqueItem, CritiqueReport


def test_print_banner():
    with patch("src.research_system.cli.console.print") as mock_print:
        print_banner("openrouter/free", 5)
        assert mock_print.called


def test_print_critique_table():
    critique = CritiqueReport(
        items=[
            CritiqueItem(
                category="Unsupported Claim",
                severity="High",
                description="Test issue",
                suggestion="Test suggestion",
            )
        ],
        overall_assessment="Needs revisions",
    )
    with patch("src.research_system.cli.console.print") as mock_print:
        print_critique_table(critique)
        assert mock_print.call_count >= 1


def test_print_critique_table_empty():
    with patch("src.research_system.cli.console.print") as mock_print:
        print_critique_table(None)
        mock_print.assert_not_called()
