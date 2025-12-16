# Copilot / AI Agent Instructions for webchuyenlatex

Purpose
- Help an AI code agent get productive quickly in this repo: a small Flask backend + static frontend that converts images to LaTeX using Google Generative API (Gemini).

Quick architecture summary
- Backend: `app.py` (Flask) exposes two POST endpoints: `/convert_questions` and `/solve_problems`. It accepts multipart file uploads and returns JSON.
- Frontend: `index.html` (static) uploads images to the backend at `http://127.0.0.1:5000` and expects JSON keys `question_latex` and/or `answer_latex`.
- Model/check helper: `check_model.py` lists available Gemini models (used for debugging/verification).

Key workflows / run commands
- Start server locally: `python app.py` (Flask debug server on port 5000). Frontend expects backend at `127.0.0.1:5000`.
- Quick model check: `python check_model.py` to verify `gemini-2.5-flash` availability.
- Dependencies: See `requirements.txt` (install via `pip install -r requirements.txt`). Note: `app.py` uses `flask` and `python-dotenv` though `flask` is not listed; ensure `flask` is installed in the environment.

Important project-specific patterns
- API key rotation: `app.py` reads `GEMINI_API_KEYS` (comma-separated) or `GEMINI_API_KEY` from the environment. It rotates keys on 429/Quota/403 errors. See `rotate_key()` and `process_with_retry()` in `app.py`.
- Prompt-driven JSON output: The backend sends `generation_config` requesting `response_mime_type: application/json`. Prompts (`PROMPT_QUESTION` and `PROMPT_SOLVER`) instruct the model to return strictly-formed JSON like `{ "question_latex": "..." }` or `{ "answer_latex": "..." }`.
- JSON repair fallback: If parsing fails, `json_repair` is used as a fallback. Agents should prefer making the model output valid JSON but tolerate and sanitize imperfect responses.
- Frontend contract: `index.html` calls the endpoints with multipart files and expects JSON. If response contains `error` with "429" or "Quota" the frontend shows a quota modal and waits. Keep that UX in mind when modifying endpoints.

Files to inspect for examples
- Backend endpoints & prompts: [app.py](app.py)
- Frontend integration and Overleaf logic: [index.html](index.html)
- Model-check script: [check_model.py](check_model.py)
- Package list: [requirements.txt](requirements.txt)

Gotchas and non-obvious details
- `app.py` relies on environment variables `GEMINI_API_KEYS` (preferred) or `GEMINI_API_KEY`. If missing the server will start but API calls will fail. Secure keys — `check_model.py` currently contains a hardcoded API key; remove or replace before committing.
- The frontend is static and hardcodes the backend host (`http://127.0.0.1:5000`). For deployments or proxies, update fetch URLs or make them relative.
- Prompts are in Vietnamese and contain strict formatting rules (e.g., wrap tables/figures with `\resizebox`). Any change to prompts must preserve JSON-only output requirement.
- `requirements.txt` lists `streamlit` but the app uses `flask`. Confirm environment & update `requirements.txt` accordingly.

What the agent should do when editing model/prompt code
- Preserve the strict JSON output contract. If changing `PROMPT_QUESTION`/`PROMPT_SOLVER`, include explicit examples in the prompt showing the exact JSON structure.
- When adding new endpoints, update `index.html` fetch URLs and the Overleaf generation logic if the returned keys change.
- If adjusting key rotation, ensure `process_with_retry()` still returns proper HTTP error codes (429 for quota) so the frontend UX continues to work.

Small checklist for PRs
- Run `python app.py` and exercise the frontend upload flow locally.
- Run `python check_model.py` to validate model access (remove hardcoded key first).
- Add/adjust tests only if touching parsing/JSON handling; keep changes focused and minimal.

If anything is unclear or you want me to expand examples (prompt text, sample responses, or a CI/dev script), tell me which area to detail next.
