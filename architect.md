# Multi-Agent Generative AI Research System — Architecture Plan

## What we are building

A CLI-based research system that takes a user's research query, runs it through an intelligent, streamlined pipeline — **Research Agent** (decomposes query and conducts web search via Tavily), **Parallel Reader** (high-speed parallel page fetch + BeautifulSoup extraction, zero token waste), **Writer Chain** (structured report generation), and **Critic Chain** (structured quality evaluation + revision pass) — and outputs a beautiful Rich-rendered report in the terminal while auto-saving it as a markdown file.

---

## Language we agreed on

- **Research Agent** — an intelligent planner/agent equipped with Tavily search that generates targeted search queries, searches the web, and returns a structured list of deduplicated sources (`ResearchPlan`).
- **Research output** — typed `ResearchPlan` containing structured `Source` items (`url`, `title`, `snippet`).
- **Parallel Reader** — deterministic, high-throughput extractor: parallel page fetching via `ThreadPoolExecutor` and `BeautifulSoup` cleaning (stripping scripts, styles, nav, headers, footers), capping content to 8,000 chars per URL. (No wasteful LLM ReAct loops for deterministic scraping).
- **Reader output** — list of typed `Extract` items (`url`, `title`, `content`).
- **Writer / Report** — Pydantic-structured report generated via LCEL `.with_structured_output(Report)`: title, executive summary, sections with headings/body, and inline source citations.
- **Critic** — structured evaluation via LCEL `.with_structured_output(CritiqueReport)`: missing information, unsupported claims, structural issues, and accuracy concerns with severity ratings and actionable suggestions.
- **Revision Pass** — Writer incorporates Critic feedback and original research context to output the final revised `CritiquedReport`.

---

## Decisions made

1. **Structured Outputs over Double-Parsing:** Use `.with_structured_output(Schema)` directly on LCEL chains instead of running an LLM to generate loose text and a second LLM to parse it into Pydantic.
2. **Deterministic Parallel Scraping:** The Reader does NOT use a ReAct agent loop. Fetching URLs is 100% deterministic: `ThreadPoolExecutor` fetches all pages in parallel in < 1 second with 0 LLM tokens, 0 formatting errors, and 100% reliability.
3. **Critic Loop:** Writer runs $\rightarrow$ Critic evaluates $\rightarrow$ Writer revises with critique $\rightarrow$ final `CritiquedReport`.
4. **CLI with Rich:** Interactive prompt via `rich.prompt.Prompt`, live spinners for each stage, final report rendered inside a Rich Markdown panel, and critique rendered as a color-coded Rich Table.
5. **Auto-Save:** Saves final report to `output/report_<timestamp>.md`.
6. **Model Configuration:** Configurable via `.env` (`MODEL_NAME=openrouter/free` or any preferred model), shared across all chains via OpenRouter.
7. **Fast Mode Flag:** CLI supports `--fast` / `--skip-critique` to bypass the critique/revision round-trips when running on strict free-tier rate limits.
8. **Sources & Content Caps:** Tavily `k=5` sources (configurable), content capped at ~8,000 chars per page to protect context limits.

---

## Tech stack

```text
langchain              # LangChain core & orchestration
langchain-core         # LCEL runnables, prompts, structured output
langchain-openai       # ChatOpenAI (configured with OpenRouter base_url)
langchain-openrouter   # ChatOpenRouter support
tavily-python          # Tavily search API client
beautifulsoup4         # HTML parsing and clean body extraction
requests               # HTTP page fetching
rich                   # Terminal UI, spinners, markdown panel, tables
pydantic               # Typed data schemas and validation
pydantic-settings      # Environment and .env configuration management
```

---

## Project structure

```text
multi-agent-system/
├── .env.example          # OPENROUTER_API_KEY, TAVILY_API_KEY, MODEL_NAME, TAVILY_K
├── .env                  # Real secrets (gitignored)
├── .gitignore
├── architect.md          # System architecture and roadmap
├── requirements.txt      # Project dependencies
├── output/               # Auto-created directory for saved markdown reports
└── src/
    └── research_system/
        ├── __init__.py
        ├── config.py         # Settings via pydantic-settings: model, keys, limits
        ├── schemas.py        # Source, ResearchPlan, Extract, Report, CritiqueReport, CritiquedReport
        ├── tools.py          # Tavily search + BeautifulSoup parallel page fetcher
        ├── research_agent.py # Intelligent search planner / Tavily agent → ResearchPlan
        ├── writer.py         # LCEL chain: context → Report (draft & revision)
        ├── critic.py         # LCEL chain: report + extracts → CritiqueReport
        ├── pipeline.py       # Orchestrates: research → read → write → critique → revise
        └── cli.py            # Rich CLI: input prompt → live spinners → render + auto-save
```

---

## Implementation steps

### Step 1 — Scaffolding & Config (`config.py`)
- Create project structure, `.env.example`, `.gitignore`, and `requirements.txt`.
- Build `config.py` using `pydantic-settings` to load `OPENROUTER_API_KEY`, `TAVILY_API_KEY`, `MODEL_NAME`, `TAVILY_K`, and `MAX_CHARS_PER_PAGE`.

### Step 2 — Pydantic Schemas (`schemas.py`)
Define clean data contracts:
- `Source(url: str, title: str, snippet: str)` — from search
- `ResearchPlan(query: str, search_queries: list[str], sources: list[Source])` — research output
- `Extract(url: str, title: str, content: str)` — cleaned webpage text
- `Section(heading: str, body: str)`
- `Report(title: str, summary: str, sections: list[Section], sources: list[Source])` — report structure
- `CritiqueItem(category: str, severity: str, description: str, suggestion: str)`
- `CritiqueReport(missing_info: list[CritiqueItem], unsupported_claims: list[CritiqueItem], structure_issues: list[CritiqueItem], accuracy_concerns: list[CritiqueItem], overall_assessment: str)`
- `CritiquedReport(report: Report, critique: CritiqueReport | None)`

### Step 3 — Tools (`tools.py`)
- `tavily_search(query: str, max_results: int = 5) -> list[Source]` — Tavily API wrapper returning typed sources.
- `fetch_page(url: str, max_chars: int = 8000) -> Extract` — requests.get + BeautifulSoup parsing, strips `<script>`, `<style>`, `<nav>`, `<header>`, `<footer>`, `<svg>`, `<noscript>`, truncates to 8,000 chars.
- `fetch_pages_parallel(urls: list[str], max_chars: int = 8000) -> list[Extract]` — `ThreadPoolExecutor` concurrently scraping all URLs in parallel.

### Step 4 — Research Agent (`research_agent.py`)
- Given a user query, generates optimal search queries and queries Tavily.
- Deduplicates and filters results into a structured `ResearchPlan`.

### Step 5 — Writer Chain (`writer.py`)
- Pure LCEL `RunnableSequence`: prompt $\rightarrow$ LLM $\rightarrow$ `.with_structured_output(Report)`.
- Handles both initial draft generation and revised generation incorporating critique feedback.
- Prompt enforces executive summary, logical sections, and inline citations `[Source 1]`.

### Step 6 — Critic Chain (`critic.py`)
- Pure LCEL `RunnableSequence`: prompt $\rightarrow$ LLM $\rightarrow$ `.with_structured_output(CritiqueReport)`.
- Reviews draft report against source extracts across 4 dimensions: missing info, unsupported claims, structure, and accuracy.

### Step 7 — Pipeline Orchestration (`pipeline.py`)
- `ResearchPipeline.run(query: str, skip_critique: bool = False) -> CritiquedReport`:
  1. Call research agent $\rightarrow$ get `ResearchPlan`.
  2. Call parallel reader with URLs $\rightarrow$ get list of `Extract`s.
  3. Call writer chain with sources + extracts $\rightarrow$ get draft `Report`.
  4. If critique enabled:
     - Call critic chain $\rightarrow$ get `CritiqueReport`.
     - Call writer revision chain $\rightarrow$ get revised `Report`.
  5. Return `CritiquedReport(report, critique)`.
- Exposes progress callbacks so CLI can update spinners in real-time.

### Step 8 — CLI Interface (`cli.py`)
- Uses `rich.console.Console` and `rich.prompt.Prompt`.
- Interactive prompt for query input, with `--fast` / `--skip-critique` support.
- Live status spinners per stage:
  - 🔍 *Researching sources with Tavily...*
  - 📖 *Fetching and reading pages in parallel...*
  - ✍️ *Drafting research report...*
  - 🧐 *Critiquing report for quality and accuracy...*
  - 🛠️ *Revising report based on feedback...*
- Renders final report inside a styled Rich `Markdown` panel.
- Renders critique table (`Category` | `Severity` | `Issue` | `Suggestion`).
- Auto-saves markdown report to `output/report_<timestamp>.md`.

### Step 9 — Verification
- Test all schemas, config loading, and parallel scraper with live/mock URLs.
- Run complete CLI query end-to-end to verify terminal rendering and file auto-saving.

---

## Assumptions

- Free OpenRouter models support structured output via JSON mode or tool calling.
- Tavily search provides high-quality sources for research topics.
- Parallel thread execution handles web I/O without blocking or requiring complex async loops.
- Context windows are respected by capping per-page content at 8,000 characters.
- `.env` is gitignored and never committed.

---

## Run it

```bash
uv pip install -r requirements.txt
uv run python -m src.research_system.cli
```
