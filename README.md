# Multi-Agent Research System

Type a question into your terminal, get back a structured research report with citations. That's the idea.

This is a CLI tool that chains together four agents in a pipeline: one searches the web (via Tavily), one scrapes and cleans the pages in parallel, one writes a structured report from the extracted content, and one critiques the draft so the writer can revise it. The final report renders in the terminal with Rich and auto-saves as markdown.

Built with [LangChain](https://www.langchain.com/), [Tavily](https://tavily.com/), and [Rich](https://github.com/Textualize/rich).

---

## What It Does

- Breaks your question into multiple search queries to get better coverage from Tavily
- Fetches all source pages concurrently with `ThreadPoolExecutor` + BeautifulSoup. No LLM tokens burned on what's just HTTP requests and HTML parsing.
- Uses `.with_structured_output()` at every stage, with a JSON-extraction fallback for free models that don't support tool calling. Data flows through typed Pydantic models either way.
- Generates a Mermaid diagram in each report to visualize the core concept or architecture being discussed
- Runs a critic/revision loop: the Writer produces a draft, the Critic flags problems (missing info, unsupported claims, structural issues, accuracy, diagram quality, AI writing tells), and the Writer revises
- Renders the report in a Rich markdown panel with a color-coded critique table
- Saves reports to `output/report_<timestamp>.md` automatically
- Pass `--fast` to skip the critique loop, or `-k N` to change how many sources get fetched

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Query (CLI)                         │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
               ┌───────────────────────────────┐
               │        Research Agent          │
               │  Decomposes query → sub-queries│
               │  Searches Tavily → ResearchPlan│
               └───────────────┬───────────────┘
                               │
                               ▼
               ┌───────────────────────────────┐
               │        Parallel Reader         │
               │  ThreadPoolExecutor + BS4      │
               │  Fetches & cleans all pages    │
               │  → list[Extract]               │
               └───────────────┬───────────────┘
                               │
                               ▼
               ┌───────────────────────────────┐
               │         Writer Chain           │
               │  LCEL → structured Report      │
               │  (executive summary, sections, │
               │   inline citations)            │
               └───────────────┬───────────────┘
                               │
                    ┌──────────┴──────────┐
                    │  Critique enabled?   │
                    └──────────┬──────────┘
                         yes / │ \ no
                             │   └──────────────────────┐
                             ▼                          │
               ┌───────────────────────────────┐        │
               │         Critic Chain           │        │
               │  Evaluates draft across 4      │        │
               │  dimensions → CritiqueReport   │        │
               └───────────────┬───────────────┘        │
                               │                        │
                               ▼                        │
               ┌───────────────────────────────┐        │
               │       Writer (Revision)        │        │
               │  Incorporates feedback →       │        │
               │  revised Report                │        │
               └───────────────┬───────────────┘        │
                               │                        │
                               ◀────────────────────────┘
                               │
                               ▼
               ┌───────────────────────────────┐
               │       CritiquedReport          │
               │  → Rich terminal render        │
               │  → Auto-save to output/*.md    │
               └───────────────────────────────┘
```

---

## Project Structure

```
multi-agent-system/
├── .env.example          # Template for required API keys
├── .env                  # Your real secrets (gitignored)
├── .gitignore
├── architect.md          # Architecture plan & design decisions
├── requirements.txt
├── output/               # Auto-saved markdown reports
└── src/
    └── research_system/
        ├── __init__.py
        ├── config.py         # Settings via pydantic-settings (.env loading)
        ├── schemas.py        # Pydantic models for every pipeline stage
        ├── tools.py          # Tavily search wrapper + parallel scraper
        ├── research_agent.py # Query decomposition & Tavily search
        ├── writer.py         # LCEL chain: sources + extracts → Report
        ├── critic.py         # LCEL chain: draft + extracts → CritiqueReport
        ├── pipeline.py       # Orchestrates all stages
        └── cli.py            # Rich CLI with spinners & rendering
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- An [OpenRouter](https://openrouter.ai/) API key (free tier works)
- A [Tavily](https://tavily.com/) API key (free tier gives you 1,000 searches/month)

### Installation

```bash
git clone https://github.com/yashraj639/multi-agent-system.git
cd multi-agent-system

python -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows

pip install -r requirements.txt
```

### Configuration

```bash
cp .env.example .env
```

Open `.env` and fill in your keys:

```env
OPENROUTER_API_KEY=sk-or-v1-your-key-here
TAVILY_API_KEY=tvly-your-key-here
MODEL_NAME=openrouter/free
TAVILY_K=5
```

---

## Usage

Interactive mode (prompts you for a query):

```bash
python -m src.research_system.cli
```

Or pass the query directly:

```bash
python -m src.research_system.cli "Mixture of Experts vs Dense Transformers"
```

Skip the critique/revision pass:

```bash
python -m src.research_system.cli --fast "your topic here"
```

Override the number of sources (default is 5):

```bash
python -m src.research_system.cli -k 10 "your topic here"
```

If you use `uv`:

```bash
uv pip install -r requirements.txt
uv run python -m src.research_system.cli
```

---

## Configuration Reference

All settings load from environment variables or `.env` via `pydantic-settings`.

| Variable | Default | Description |
| :--- | :--- | :--- |
| `OPENROUTER_API_KEY` | required | Your OpenRouter API key |
| `TAVILY_API_KEY` | required | Your Tavily search API key |
| `MODEL_NAME` | `openrouter/free` | LLM model identifier used across all chains |
| `TAVILY_K` | `5` | Number of search results per query (1-15) |
| `MAX_CHARS_PER_PAGE` | `8000` | Max characters extracted per webpage |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | OpenRouter API endpoint |

---

## Tech Stack

| Layer | Technology | Why |
| :--- | :--- | :--- |
| Orchestration | LangChain / LCEL | Chain composition and structured output |
| LLM | OpenRouter | OpenAI-compatible API, has free models |
| Search | Tavily | Search API that returns clean snippets |
| Scraping | BeautifulSoup4 + requests | HTML parsing and text extraction |
| Diagrams | Mermaid.js (generated by LLM) | Visual architecture/flow diagrams in reports |
| Data models | Pydantic | Typed schemas and validation |
| Config | pydantic-settings | Loads `.env` into typed settings |
| Terminal UI | Rich | Spinners, markdown rendering, tables |

---

## Data Flow

Each stage produces a typed Pydantic model that the next stage consumes:

```
User query (str)
    → ResearchPlan { query, search_queries, sources[] }
        → Extract[] { url, title, content }
            → Report { title, summary, sections[], diagram, sources[] }
                → CritiqueReport { items[], overall_assessment }
                    → CritiquedReport { report, critique }
```

---

## Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes
4. Push and open a PR

---

## License

Open source. See the repository for license details.

---

## Acknowledgments

- [LangChain](https://www.langchain.com/)
- [Tavily](https://tavily.com/)
- [Rich](https://github.com/Textualize/rich)
- [OpenRouter](https://openrouter.ai/)
