# Build Prompt: AI Resume Screening Agent

> Living spec — updated 2026-08-18 to reflect the actual implemented system, including
> requirements that emerged after the initial build. Where this differs from the original
> version, it's because real usage surfaced a gap or the user asked for a change.

## Objective
A Python-based resume screening pipeline that ingests `.docx` resumes, ranks them against a
job description using cheap vector embeddings, sends only a configurable top-N% shortlist to
an LLM (any provider — model-agnostic) for deep qualitative scoring, and exposes the results
over a REST API for consumption by a **Spring MVC 5.0 + JSP web application** (also built, in
the sibling `recruitment-webapp/` project).

## Tech Stack
- Python 3.11+
- `python-docx` — parse resume paragraphs and tables
- `langchain` — orchestration of embedding + LLM calls
- **Embeddings: `fastembed`** (Qdrant's ONNX-runtime-based library), default model
  `BAAI/bge-small-en-v1.5`, run locally — **not** `sentence-transformers`/torch, which was
  tried first and caused an out-of-memory error on this machine. `OpenAIEmbeddings` is
  available as a config toggle (`embedding.provider: openai`) if preferred.
- `numpy` / `scikit-learn` — cosine similarity
- `FastAPI` + `uvicorn` — REST API layer
- `pydantic` — request/response schemas
- **LLM for deep analysis: provider-agnostic.** `llm_scorer.get_llm()` builds a LangChain chat
  model based on `config.yaml`'s `llm.provider`:
  - `deepseek` (default) — `deepseek-chat` via `langchain_openai.ChatOpenAI` pointed at
    DeepSeek's OpenAI-compatible base URL; key via `DEEPSEEK_API_KEY`
  - `openai` — via `langchain_openai.ChatOpenAI`; key via `OPENAI_API_KEY`
  - `anthropic` — via `langchain_anthropic.ChatAnthropic`; key via `ANTHROPIC_API_KEY`
  - `openai_compatible` — any other OpenAI-compatible endpoint (Groq, Together, local
    Ollama/vLLM); requires `llm.base_url` in config; key via `LLM_API_KEY`

  Switching providers is config-only (`llm.provider` + `llm.model` in `config.yaml`, plus the
  matching env var) — no code changes. An unknown provider or missing key raises a clear
  error at request time.

## Pipeline

### 1. Resume Ingestion & Parsing
- Read all `*.docx` files from `SampleResumes/` (path is configurable via `config.yaml`'s
  `resume_folder`, resolved relative to the project directory)
- For each file, extract text from both:
  - Body paragraphs (`document.paragraphs`)
  - All tables (`document.tables`, iterate rows/cells)
  - **Gap found in real resumes and fixed**: some resumes put an entire multi-paragraph
    section (e.g. all of "Experience") inside a *single table cell*; `cell.text` joins that
    cell's internal paragraphs with `\n` into one blob. The parser splits multi-line cell
    content back into individual lines (while still joining simple same-row `label | value`
    cells on one line) so line-anchored label matching still works.
- Concatenate into a single normalized text blob per resume; keep the source filename and
  full file path for later linking
- Also extract, via heuristics (best-effort, not guaranteed — see README for known
  limitations):
  - **Candidate name** — first short (1-5 word) non-label line, scanning both paragraphs and
    table content; falls back to the filename if nothing matches
  - **Location** — a `Location:`/`Address:`/`City:`/`Based in:` labeled line; blank if none
    exists in the resume (a real, observed data gap, not a bug)
  - **Skills** — aggregated from `Skills:`/`Technical Skills:`/`Technology:`/`Environment:`
    labeled lines (real resumes often list tech stack per-project as "Environment: X, Y, Z"
    rather than one dedicated skills section); deduplicated, capped at 400 characters
- Handle corrupt/unreadable or empty files gracefully — log and skip, don't crash the batch

### 2. Job Description Input
- Accept JD as three structured fields: `location`, `skills` (free text), `other_details`
  (free text: experience level, domain, certifications, etc.)
- Combine into a single JD text block for embedding

### 3. Location Filtering (hard filter, before ranking) — *added after initial build*
- If the JD's `location` resolves to a known metro cluster, resumes are **excluded** (not
  just down-weighted) unless their extracted location resolves to the same cluster. Clusters
  (`location_matcher.py`):
  - `delhi_ncr`: Delhi, New Delhi, NCR, Noida, Gurgaon/Gurugram, Ghaziabad, Faridabad
  - `mumbai_pune`: Mumbai, Pune, Navi Mumbai, Thane
- A JD location that doesn't match any cluster (e.g. "Remote", "Hyderabad", blank) applies no
  filter — all resumes are considered, same as the original no-filter behavior.
- This runs *before* embedding, so `top_percent` is computed against the filtered pool, not
  the whole resume set.

### 4. Embedding & Cosine Similarity Ranking
- Embed the JD text block and every (location-filtered) resume text using the configured
  embedding provider
- Compute cosine similarity between the JD vector and each resume vector
- Rank descending by similarity score
- **Select the top `top_percent`% (configurable in `config.yaml`, default 50% — originally
  10%, raised after real usage; minimum `min_candidates`, default 1, rounded up)** — this is
  the shortlist that proceeds to LLM analysis
- This stage runs no LLM calls — pure vector math
- The embedding provider is constructed once per process (`@lru_cache`) and reused across
  requests — it does **not** reload the model on every request (an early version did; fixed)

### 5. LLM Deep Analysis (shortlist only)
- Uses whichever LLM provider is configured (see Tech Stack above), called via LangChain
- For each shortlisted resume, send resume text + JD to the LLM with a scoring prompt that
  evaluates:
  - Soft skills (communication, leadership, collaboration — inferred from language/
    achievements described)
  - Project relevance (how closely past projects map to the JD's actual needs, not just
    keyword overlap)
  - Culture fit signals (working style, team context, values alignment where evidenced)
- Returns a structured score (0-100) plus a short justification per dimension, and an overall
  recommendation, via `with_structured_output(ResumeScoreResult, method="function_calling")`
  (Pydantic-enforced, no free-text parsing)
- **Shortlisted candidates are scored concurrently** (`ThreadPoolExecutor`, up to 8 workers),
  not one-at-a-time — sequential scoring was a real, user-reported slowdown once the
  shortlist grew past 1-2 candidates (fixed 2026-08-18; cut a 4-candidate scoring stage from
  ~15-17s to ~4s)
- A failed LLM call (bad/missing key, network error, malformed response) doesn't crash the
  request — that candidate gets a fallback score of 0 with an explanatory recommendation, and
  the API still returns 200 with the rest of the results. A missing/invalid API key at
  startup (not per-call) returns `503` with a clear `detail` message instead of a bare 500.

### 6. Results & Output
Final output per candidate, sorted by LLM overall score:
- Candidate name (extracted from resume, not filename)
- Location
- **Skills** (added after initial build — was missing from the original response shape)
- Link to resume file (served by the API itself at `/resumes/<filename>`, so it's an
  accessible URL, not just a local path)
- Cosine similarity score (stage 4)
- LLM nuanced score + recommendation (stage 5)

### 7. REST API
- `POST /screen` — body: JD fields (`location`, `skills`, `other_details`); runs the full
  pipeline synchronously and returns results
- `GET /screen/{job_id}/results` — polls a completed job from an in-memory store (single-
  process only; swap for Redis/a DB if this needs to run behind multiple workers)
- `GET /health` — liveness check
- `GET /resumes/{filename}` — static file serving for resume downloads (mounted from the
  configured `resume_folder`)
- Response JSON — flat enough for JSTL `<c:forEach>` to consume directly:
```json
{
  "jobId": "uuid-string",
  "results": [
    {
      "candidateName": "string",
      "location": "string",
      "skills": "string",
      "resumeLink": "string",
      "similarityScore": 0.0,
      "llmScore": 0,
      "recommendation": "string"
    }
  ]
}
```
- CORS-enabled (`cors_origins` in `config.yaml`, default `*`)
- **Optional API key auth** (`RECRUITMENT_API_KEY` env var), added after initial build —
  the original spec assumed no auth. If set, `POST /screen` and `GET /screen/{job_id}/results`
  require a matching `X-API-Key` header (401 if missing/wrong); unset (default) means no auth,
  matching the original assumption. The Spring MVC webapp sends this header automatically
  when its own `RECRUITMENT_API_KEY` env var is set.

## Non-Functional Requirements
- Keep cost low: embeddings are free/local by default; LLM calls strictly limited to the
  shortlist, never the full resume pool
- Pipeline is runnable as a standalone script (`run_screen.py`) and importable as a module
  (`pipeline.run_screening`, used by `api.py`)
- Every stage logs timing and resume counts (parse, location filter, embed+rank, shortlist,
  LLM scoring, total)
- Config is fully externalized in `config.yaml` (resume folder, embedding provider/model,
  LLM provider/model/base_url/temperature, shortlist %, CORS, log level) and `.env`
  (all API keys — DeepSeek/OpenAI/Anthropic/generic LLM/RECRUITMENT_API_KEY) — nothing
  hardcoded
- `.env.example` documents which key(s) are needed for the *chosen* provider only; a real
  secret must never be committed there (this was violated once during development and fixed
  — see project memory)

## Deliverables
1. `resume_parser.py` — docx paragraph + table extraction, name/location/skills heuristics
2. `location_matcher.py` — metro-area location clustering (Delhi NCR, Mumbai/Pune)
3. `embedding_ranker.py` — embedding generation (cached provider) + cosine similarity ranking
4. `llm_scorer.py` — LangChain-based nuanced scoring, provider-agnostic, concurrent
5. `pipeline.py` — orchestrates all stages with per-stage timing/count logs
6. `api.py` — FastAPI app (`/screen`, `/screen/{job_id}/results`, `/health`, `/resumes/*`)
7. `models.py` — Pydantic request/response schemas
8. `config.py` — loads `config.yaml` + `.env` into an `AppConfig`
9. `run_screen.py` — standalone CLI runner
10. `config.yaml`, `.env.example`, `requirements.txt`, `pyproject.toml`
11. README covering setup, how to run, and how the Spring MVC/JSP app calls the API
12. **`recruitment-webapp/`** — a Spring MVC 5.0.9.RELEASE + JSP client (built, not just
    described): job-description form → results table with candidate name, location, skills,
    similarity/LLM score, recommendation, resume link, and a "Completed in Xs" timing
    display. XML config (`web.xml` + `spring-servlet.xml`), `RestTemplate` + Jackson, JSTL
    views, Maven `war` packaging, `mvn tomcat7:run` for local dev.

## Acceptance Criteria
- Given a folder of `.docx` resumes (mixed paragraph + table content, including resumes
  where an entire section lives in one multi-paragraph table cell) and a JD, the system
  returns only the top-`top_percent`%-by-similarity candidates (within the location-filtered
  pool, if the JD location matches a known cluster) scored by the LLM
- No LLM call is made for resumes outside the shortlist
- LLM calls for the shortlist run concurrently, not sequentially
- Switching the LLM provider requires only a `config.yaml` + `.env` change
- API response is consumable by a JSP page with a table (name, location, skills, resume
  link, scores, recommendation) without additional transformation
- If `RECRUITMENT_API_KEY` is configured, requests without a matching `X-API-Key` header are
  rejected with 401; if unset, no auth is required
- A missing/invalid LLM API key surfaces as a clear `503` from the API, not a bare 500 or a
  silent hang
