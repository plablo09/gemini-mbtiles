# Repository Guidelines

## Project Structure & Module Organization
- `backend/` holds the FastAPI tile server (`main.py`) and DuckDB bootstrap logic (`db.py`).
- `frontend/` contains the MapLibre viewer (`index.html`, `map.js`, `style.css`).
- `data/` stores inputs and outputs; `data/mexico_city.cleaned.3857.geoparquet` is expected to already exist locally.
- Root scripts include `prepare_data.py` (regenerate GeoParquet if needed) and `test_duckdb.py` (manual DuckDB checks).
- Tests live in `backend/test_main.py` and use the FastAPI test client.

## Build, Test, and Development Commands
- All commands must run inside an activated Python virtualenv.
- `python3 -m venv .venv && source .venv/bin/activate` create and activate the venv.
- `pip install -r requirements.txt` install Python dependencies into the venv.
- `pytest` run backend tests (expects `data/mexico_city.cleaned.3857.geoparquet` to exist).
- From repo root, `nohup ./.venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 &` starts the API in the background (logs to `uvicorn.log`).
- From `frontend/`, `python3 -m http.server` serves the viewer for local development.

## Coding Style & Naming Conventions
- Python uses 4-space indentation, `snake_case` for functions/variables, and `UPPER_SNAKE_CASE` for constants.
- JavaScript follows 4-space indentation and `lowerCamelCase` for variables and functions.
- Keep module-level constants near the top of files (see `backend/main.py`).
- No formatter or linter is enforced; keep changes consistent with existing style.

## Testing Guidelines
- Primary framework is `pytest` with FastAPI’s `TestClient`.
- Test files follow `test_*.py` naming; add new tests in `backend/` for API behavior.
- Tile tests require a populated GeoParquet file in `data/`.
- Use `test_duckdb.py` for manual validation of DuckDB spatial setup.

## Commit & Pull Request Guidelines
- Commit messages follow Conventional Commits: `feat:`, `docs:`, `chore:`, optionally scoped (e.g., `feat(backend): ...`).
- PRs should include a short summary, testing notes (commands run), and any data/setup changes.
- Include screenshots or a short clip for frontend/UI changes.

## Configuration & Data Notes
- Large datasets are excluded by `.gitignore`; document how to recreate them instead of committing.
- `backend/db.py` defaults to an in-memory DB; if persistence is needed, update `DB_PATH` and note it in the PR.
