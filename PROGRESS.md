# Progress

| Phase | Status | Notes |
|---|---|---|
| 0: Environment setup | Partial | Scaffold, deps, `npm run build` done. Endpoints (a), (b), (e), (f) pass. (c) and (d) blocked on Earthdata credentials. |

## Phase 0 details

Done:
- Folder tree from Section 6, git initialised, `.gitignore`.
- `requirements.txt`, `.venv` (Python 3.11.9), `requirements.lock`.
- `frontend/package.json`, `npm install`, `npm run build` succeeds on a minimal scaffold.
- `.env.example` (Section 11.10) and `.env` copied from it.
- `scripts/check_env.py` and `scripts/verify_endpoints.py`.

Outstanding before Phase 1 (rule 1: verification must pass):
- Fill `EARTHDATA_USERNAME` and `EARTHDATA_PASSWORD` in `.env`.
- Re-run `python scripts/check_env.py` (currently exits 1) and `python scripts/verify_endpoints.py` (c and d currently fail). See `docs/data_sources.md`.

Notes:
- `npm install` reports 8 vulnerabilities (2 critical). Not addressed.
- Use `py -3.11` on this machine, since the `python3.11` shim is broken.
