# 🔬 Multi-Agent Research System

A CLI-powered research assistant that takes a plain-English query and produces a polished, source-cited research report — entirely in your terminal. Under the hood, four specialized agents collaborate through a structured pipeline: a **Research Agent** plans and searches the web, a **Parallel Reader** fetches and cleans pages at high speed, a **Writer** synthesizes findings into a structured report, and a **Critic** evaluates the draft before a final revision pass.

Built with [LangChain](https://www.langchain.com/), [Tavily](https://tavily.com/), and [Rich](https://github.com/Textualize/rich).

---

## ✨ Features

- **Intelligent Query Decomposition** — The Research Agent breaks your question into targeted sub-queries for broader, more relevant coverage.
- **Parallel Web Scraping** — Pages are fetched concurrently via `ThreadPoolExecutor` and cleaned with BeautifulSoup. Zero LLM tokens wasted on deterministic I/O.
- **Structured Outputs** — Every stage uses Pydantic schemas with `.with_structured_output()` — no double-parsing, no brittle text extraction.
- **Critic → Revision Loop** — A dedicated Critic chain evaluates the draft across four dimensions (missing info, unsupported claims, structure, accuracy) before the Writer revises.
- **Beautiful Terminal UI** — Live spinners, styled Markdown panels, and color-coded critique tables powered by Rich.
- **Auto-Save** — Reports are automatically saved as timestamped Markdown files in `output/`.
- **Fast Mode** — Skip the critique/revision round-trip with `--fast` for quicker results on rate-limited free tiers.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Query (CLI)                         │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
               ┌───────────────────────────────┐
               │       🔍 Research Agent        │
               │  Decomposes query → sub-queries│
               │  Searches Tavily → ResearchPlan│
               └───────────────┬───────────────┘
                               │
                               ▼
               ┌───────────────────────────────┐
               │      📖 Parallel Reader        │
               │  ThreadPoolExecutor + BS4      │
               │  Fetches & cleans all pages    │
               │  → list[Extract]               │
               └───────────────┬───────────────┘
                               │
                               ▼
               ┌───────────────────────────────┐
               │        ✍️ Writer Chain          │
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
               │        🧐 Critic Chain         │        │
               │  Evaluates draft across 4      │        │
               │  dimensions → CritiqueReport   │        │
               └───────────────┬───────────────┘        │
                               │                        │
                               ▼                        │
               ┌───────────────────────────────┐        │
               │      🛠️ Writer (Revision)      │        │
               │  Incorporates feedback →       │        │
               │  revised Report                │        │
               └───────────────┬───────────────┘        │
                               │                        │
                               ◀────────────────────────┘
                               │
                               ▼
               ┌───────────────────────────────┐
               │     📄 CritiquedReport         │
               │  → Rich terminal render        │
               │  → Auto-save to output/*.md    │
               └───────────────────────────────┘
```

---

## 📁 Project Structure

```
multi-agent-system/
├── .env.example          # Template for required API keys
├── .env                  # Your real secrets (gitignored)
├── .gitignore
├── architect.md          # Detailed architecture plan & design decisions
├── requirements.txt      # Python dependencies
├── output/               # Auto-saved markdown reports
└── src/
    └── research_system/
        ├── __init__.py
        ├── config.py         # Settings via pydantic-settings (.env loading)
        ├── schemas.py        # Pydantic data contracts for every pipeline stage
        ├── tools.py          # Tavily search wrapper + parallel BeautifulSoup scraper
        ├── research_agent.py # Query decomposition & Tavily search agent
        ├── writer.py         # LCEL chain: sources + extracts → Report
        ├── critic.py         # LCEL chain: draft + extracts → CritiqueReport
        ├── pipeline.py       # Orchestrates all stages with progress callbacks
        └── cli.py            # Rich interactive CLI with spinners & rendering
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.10+**
- An [OpenRouter](https://openrouter.ai/) API key (free tier works)
- A [Tavily](https://tavily.com/) API key (free tier: 1,000 searches/month)

### Installation

```bash
# Clone the repository
git clone https://github.com/yashraj639/multi-agent-system.git
cd multi-agent-system

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Copy the example environment file and add your API keys:

```bash
cp .env.example .env
```

Then edit `.env`:

```env
OPENROUTER_API_KEY=sk-or-v1-your-key-here
TAVILY_API_KEY=tvly-your-key-here
MODEL_NAME=openrouter/free
TAVILY_K=5
```

---

## 💻 Usage

### Run a research query

```bash
python -m src.research_system.cli
```

You'll get an interactive prompt. Type your research question and watch the pipeline work through each stage with live status spinners.

### Fast mode (skip critique)

```bash
python -m src.research_system.cli --fast
```

This bypasses the Critic evaluation and revision pass — useful when running on free-tier rate limits or when you just need a quick draft.

### Using `uv` (alternative)

```bash
uv pip install -r requirements.txt
uv run python -m src.research_system.cli
```

---

## ⚙️ Configuration Reference

All settings are loaded from environment variables or `.env` via `pydantic-settings`.

| Variable | Default | Description |
| :--- | :--- | :--- |
| `OPENROUTER_API_KEY` | — | **Required.** Your OpenRouter API key |
| `TAVILY_API_KEY` | — | **Required.** Your Tavily search API key |
| `MODEL_NAME` | `openrouter/free` | LLM model identifier used across all chains |
| `TAVILY_K` | `5` | Number of search results per query (1–15) |
| `MAX_CHARS_PER_PAGE` | `8000` | Max characters extracted per webpage |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | OpenRouter API endpoint |

---

## 🧩 Tech Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Orchestration** | LangChain / LCEL | Chain composition & structured output |
| **LLM Provider** | OpenRouter (OpenAI-compatible) | Model inference (supports free models) |
| **Web Search** | Tavily | High-quality search results with snippets |
| **Web Scraping** | BeautifulSoup4 + requests | HTML parsing & clean text extraction |
| **Data Validation** | Pydantic | Typed schemas for every pipeline stage |
| **Configuration** | pydantic-settings | `.env` and environment variable management |
| **Terminal UI** | Rich | Spinners, markdown panels, styled tables |

---

## 📊 Pipeline Data Flow

Each stage produces a typed Pydantic model that feeds into the next:

```
User query (str)
    → ResearchPlan { query, search_queries, sources[] }
        → Extract[] { url, title, content }
            → Report { title, summary, sections[], sources[] }
                → CritiqueReport { missing_info[], unsupported_claims[], ... }
                    → CritiquedReport { report, critique }
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'Add your feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

---

## 📝 License

This project is open source. See the repository for license details.

---

## 🙏 Acknowledgments

- [LangChain](https://www.langchain.com/) for the composable AI framework
- [Tavily](https://tavily.com/) for the research-optimized search API
- [Rich](https://github.com/Textualize/rich) for beautiful terminal rendering
- [OpenRouter](https://openrouter.ai/) for unified LLM access with free-tier support
