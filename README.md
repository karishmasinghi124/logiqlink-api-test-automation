# LogiQlink — Test Automation Engineer Assessment

## Overview
This submission contains a contract-driven API regression suite for the supplied Order API. Tests assert the requirements in `API_CONTRACT.md`, not the current implementation. Known product defects are intentionally represented by failing tests; `server.py` is kept unchanged.

## Prerequisites
- Python 3.9+
- pip
- No external runtime dependency for the API fixture; `pytest` is used by the test suite.

## Run locally
Open a terminal in this directory:

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\\Scripts\\activate
python -m pip install -r requirements.txt
```

Terminal 1 — start the API:

```bash
python server.py
```

Terminal 2 — run the suite:

```bash
python -m pytest -v
```

The suite resets API state before each test. The service must be running at `http://127.0.0.1:8765`.
To use another host, set `BASE_URL`, for example `BASE_URL=http://localhost:8765 python -m pytest -v`.

## Test design
- Shared request helper centralizes HTTP handling, JSON parsing, auth, and timeouts.
- Each test receives isolated state through `/test/reset`.
- Unique request IDs avoid accidental idempotency collisions.
- Parameterized tests cover boundary and invalid values.
- Assertions cover status codes, response payloads, calculated totals, and persisted state.

## Expected outcome
The provided fixture contains deliberate contract defects. The tests for quantity zero, cancellation after shipment, and status filtering are expected to fail until the API is corrected. A non-zero test exit is therefore meaningful and must not be hidden or converted into a green build.

See `TEST_REPORT.md` for the observed execution results and defect details.
