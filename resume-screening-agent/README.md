# AI Resume Screening Agent

Two-stage resume screening pipeline:

1. **Cheap ranking** — embed every `.docx` resume in `SampleResumes/` and the job description, rank by cosine similarity. No LLM calls.
2. **Deep scoring** — send only the top N% (by similarity) to an LLM (any provider — see below) for structured scoring on soft skills, project relevance, and culture fit, run concurrently across the shortlist.

Results are exposed over a small FastAPI REST API for a legacy Spring MVC 5.0 / JSP frontend to consume.

### LLM provider (model-agnostic)

`llm_scorer.py`'s `get_llm()` builds a LangChain chat model based on `llm.provider` +
`llm.model` in `config.yaml` — swapping providers never touches code, just config + the
matching API key in `.env`:

| `llm.provider` | `llm.model` example | API key env var | `base_url` |
|---|---|---|---|
| `deepseek` (default) | `deepseek-chat` | `DEEPSEEK_API_KEY` | optional (defaults to DeepSeek's) |
| `openai` | `gpt-4o-mini` | `OPENAI_API_KEY` | not used |
| `anthropic` | `claude-3-5-haiku-latest` | `ANTHROPIC_API_KEY` | not used |
| `openai_compatible` | e.g. `llama-3.3-70b-versatile` | `LLM_API_KEY` | **required** (Groq/Together/local Ollama/vLLM/etc.) |

See the commented examples in `config.yaml`. An unknown/misspelled provider or a missing API
key raises a clear error at request time (not a silent fallback).

### Location filtering

If the JD's `location` matches a known metro cluster, resumes are **hard-filtered** to that
cluster before ranking (not just down-weighted) — a Delhi search only considers Delhi NCR
resumes; a Mumbai or Pune search considers both cities. Clusters are defined in
`location_matcher.py`:

- `delhi_ncr`: Delhi, New Delhi, NCR, Noida, Gurgaon/Gurugram, Ghaziabad, Faridabad
- `mumbai_pune`: Mumbai, Pune, Navi Mumbai, Thane

A JD location that isn't in any cluster (e.g. "Remote", "Hyderabad", blank) applies no filter —
all resumes are considered, same as before. To add more clusters, edit `LOCATION_CLUSTERS` in
`location_matcher.py`.

## Files

| File | Purpose |
|---|---|
| `resume_parser.py` | Extracts text from `.docx` paragraphs + tables, guesses candidate name/location |
| `location_matcher.py` | Metro-area location clustering (e.g. Delhi NCR, Mumbai/Pune) — see below |
| `embedding_ranker.py` | Embeds JD + resumes, cosine-similarity ranking, top-N% shortlist selection |
| `llm_scorer.py` | LangChain structured scoring, provider-agnostic (DeepSeek/OpenAI/Anthropic/any OpenAI-compatible endpoint) |
| `pipeline.py` | Orchestrates the full run, with per-stage timing/count logs |
| `api.py` | FastAPI app (`/screen`, `/screen/{job_id}/results`) |
| `models.py` | Pydantic request/response schemas |
| `config.py` | Loads `config.yaml` + `.env` into an `AppConfig` |
| `run_screen.py` | Standalone CLI runner (no API needed) |
| `config.yaml` | Non-secret config: resume folder, model choices, shortlist %, CORS |
| `.env.example` | Secret config template — set only the API key(s) for your chosen `llm.provider`/`embedding.provider` |
| `pyproject.toml` | Project metadata + dependencies (use this or `requirements.txt`, whichever fits your workflow) |
| `requirements.txt` | Same dependency list in plain pip-installable form |

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
# or: pip install -e .   (uses pyproject.toml instead)
copy .env.example .env
```

Edit `.env` and set `DEEPSEEK_API_KEY`. Get a key at https://platform.deepseek.com.

`RECRUITMENT_API_KEY` is optional: leave it unset/empty for no-auth (the default). Set it to require an
`X-API-Key` header matching that value on `POST /screen` and `GET /screen/{job_id}/results` — the
`recruitment-webapp` Spring app is already wired to send it if configured (see its README).

Drop candidate `.docx` files into `SampleResumes/`.

By default embeddings run **locally** via [`fastembed`](https://github.com/qdrant/fastembed) (`BAAI/bge-small-en-v1.5`, ONNX runtime) — no torch, no API cost, no external calls for stage 1. This intentionally avoids `sentence-transformers`/torch, which pulls in a much heavier runtime and previously caused out-of-memory errors on this machine. To use OpenAI embeddings instead, set `embedding.provider: openai` in `config.yaml` and provide `OPENAI_API_KEY` in `.env`.

## Running

**As a script:**

```bash
python run_screen.py --location "Remote" --skills "Python, FastAPI" --other-details "3+ years experience"
```

**As an API:**

```bash
uvicorn api:app --reload --port 8000
```

Then:

```bash
curl -X POST http://localhost:8000/screen ^
  -H "Content-Type: application/json" ^
  -d "{\"location\": \"Remote\", \"skills\": \"Python, FastAPI\", \"other_details\": \"3+ years experience\"}"
```

Response:

```json
{
  "jobId": "e3b0c...",
  "results": [
    {
      "candidateName": "Jane Doe",
      "location": "Austin, TX",
      "skills": "Python, FastAPI, PostgreSQL, Docker, AWS",
      "resumeLink": "/resumes/jane_doe.docx",
      "similarityScore": 0.8123,
      "llmScore": 87,
      "recommendation": "Strong candidate — recommend interview."
    }
  ]
}
```

`resumeLink` is served by the same API at `GET /resumes/<filename>` (static file mount), so the Spring/JSP app can link/download directly — prefix it with the API's base URL, e.g. `http://api-host:8000/resumes/jane_doe.docx`.

## Calling from Spring MVC 5.0 / JSP

- POST the JD fields as JSON to `/screen` (e.g. via `RestTemplate` or `HttpClient` from a Spring `@Controller`), get back `results` directly — no nested objects, just a flat array of objects with `candidateName`, `location`, `skills`, `resumeLink`, `similarityScore`, `llmScore`, `recommendation`.
- A ready-to-run example client app lives in [`../recruitment-webapp/`](../recruitment-webapp/) — a Spring MVC 5 + JSP app that submits the JD form and renders `candidateName`, `location`, `skills`, and a resume download link in a table.
- Put that list on the model (`model.addAttribute("results", response.getResults())`) and iterate with JSTL `<c:forEach>` in the JSP — no extra unwrapping needed.
- `jobId` is also returned so you can poll `GET /screen/{jobId}/results` later if you want to decouple submission from display (e.g. AJAX poll from the JSP page).

## Assumptions

- **No auth** on the API — add an API gateway / reverse-proxy auth layer before exposing this beyond a trusted internal network.
- The pipeline runs **synchronously** inside `POST /screen` (fine for small resume batches); results are also cached in-memory under `jobId` for the polling endpoint. Restart the API process and job history is lost — swap in Redis/a DB if that matters.
- Candidate name and location are extracted from resume text using heuristics (first short, non-label paragraph line for name; a `Location:`/`Address:`/`City:` label for location). Unusual resume formats may need the heuristics in `resume_parser.py` tuned.
- `top_percent` rounds up and always includes at least `min_candidates` (default 1), so even a batch of 1-9 resumes gets at least one LLM-scored result.

## Observability

Every run logs, per stage: resume count and elapsed seconds for parsing, embedding+ranking, shortlist selection, and LLM scoring (see `pipeline.py`). Check stdout/uvicorn logs.
