# kompagnon-algo

This repository contains the **multi-criteria matching algorithm** for Kompagnon — a service that pairs passengers with companions for shared journeys.

## Roadmap

- [x] Setup rule set
- [x] Swagger for the algo API
- [x] Setup API
- [x] Setup DB connection
- [x] Add tests for API & DB connection
- [x] Implement algo logic
- [x] Multi-criteria scoring algorithm (geo + time + address)

## Proposed Architecture

```text
kompagnon-algo/
├── doc/                     # Documentation directory
│   └── README_algo.md       # Detailed algorithm documentation
├── src/                     # Source code directory
│   ├── algorithm/           # Core matching algorithm
│   │   ├── config.py        # Algorithm configuration (reads env vars)
│   │   ├── main.py          # Batch matching entry point & DB saver
│   │   └── matcher.py       # Multi-criteria scoring engine (geo, time, address)
│   ├── api/                 # API layer
│   │   ├── routes/          # API endpoint routes
│   │   │   ├── __init__.py
│   │   │   ├── get_invalid.py
│   │   │   ├── get_valid.py
│   │   │   ├── match.py         # API Route to trigger matching for a single journey
│   │   │   ├── put_journey.py
│   │   │   ├── root.py
│   │   │   └── status.py
│   │   ├── main.py          # FastAPI application instance & routing setup
│   │   └── schema.py        # Pydantic models for API requests/responses
│   └── db/                  # Database layer
│       ├── models.py        # SQLAlchemy models (T1: Accompanied, T2: Accompanists, T3: FoundJourney)
│       └── session.py       # Database connection and session management
├── tests/                   # Unit and integration tests
│   ├── algorithm/           # Algorithm unit tests (matcher, main batch)
│   │   ├── test_main.py
│   │   └── test_matcher.py
│   ├── __init__.py
│   ├── conftest.py          # Fixtures and DB setup
│   ├── test_get_invalid.py  # Tests for get-invalid route
│   ├── test_get_valid.py    # Tests for get-valid route
│   ├── test_match.py        # Tests for new /match API route
│   ├── test_put_journey.py  # Tests for put-journey route
│   ├── test_root.py         # Tests for root route
│   └── test_status.py       # Tests for status route
├── .env                     # Local environment variables (created from sample.env)
├── .gitignore               # Git ignore rules
├── CHANGELOG.md             # Project changelog
├── configure.sh             # Environment setup (venv & dependencies)
├── pyproject.toml           # Project configuration
├── pytest.ini               # Pytest configuration
├── README.md                # Global documentation
├── render.yaml              # Render deployment configuration
├── requirements.txt         # Project and testing dependencies
├── sample.env               # Template for environment variables
├── start.sh                 # API launcher (Uvicorn)
└── test.sh                  # Shell script to run tests
```

## How to access Swagger Documentation

Once the server is running (see [Project Setup](#project-setup)), you can access the automatic interactive documentation:

- **Swagger UI**: [http://localhost:8000/api/docs](http://localhost:8000/api/docs)
- **ReDoc**: [http://localhost:8000/api/redoc](http://localhost:8000/api/redoc)

> **Note:** All API routes are prefixed with `/api`.

## Matching Algorithm

The matching engine uses a **weighted multi-criteria scoring system** (0.0 → 1.0) to pair companions and passengers:

| Criterion | Weight | Method | Rejection threshold |
|-----------|--------|--------|--------------------|
| 🌍 Geographic proximity | 40% | Haversine distance (departure + arrival) | > 5 km |
| ⏰ Time compatibility | 40% | Departure time difference | > 30 min |
| 📝 Address match | 20% | Case-insensitive text comparison | None (bonus) |

A pair is considered a valid match when `score ≥ 0.5`. Results are sorted by score descending (best matches first).

All thresholds and weights are **configurable via environment variables** (see [Configuration](#algorithm-configuration)).

### Workflow

1. **Trigger**: The main API calls `POST /api/match` with a `journey_id` and `role` (companion or passenger).
2. **Fetch**: The algo fetches the target journey and all unmatched candidates of the opposite role.
3. **Score**: Every (companion, passenger) pair is scored across three dimensions.
4. **Filter**: Only pairs with `score ≥ MIN_MATCH_SCORE` are retained.
5. **Storage**: Valid matches are saved in `found_journeys` linking the two journey IDs.
6. **Response**: The algo returns the IDs of the created matches.

### Batch mode

To run the algorithm on **all** unmatched journeys at once:

```bash
python -m src.algorithm.main
```

## Project Setup & Running the API

### 1. Configuration

Run the setup script to create the virtual environment and install all dependencies:

```bash
sh configure.sh
```

Start the venv:

```bash
source .venv/bin/activate
```

### 2. Launch the API

Use the provided launch script:

```bash
sh start.sh
```

_Note: You can also launch the API manually if the environment is already activated:_

```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

### Algorithm Configuration

All matching parameters are configurable via environment variables in `.env` (or `sample.env` as template):

| Variable | Default | Description |
|----------|---------|-------------|
| `MATCH_MAX_DISTANCE_KM` | `5.0` | Maximum distance (km) for a geographic match |
| `MATCH_PERFECT_DISTANCE_KM` | `0.5` | Distance (km) for a perfect geo score (1.0) |
| `MATCH_TIME_TOLERANCE_MINUTES` | `30` | Maximum departure time difference (minutes) |
| `MATCH_MIN_SCORE` | `0.5` | Minimum combined score to accept a match |
| `MATCH_WEIGHT_GEO` | `0.40` | Weight of geographic proximity |
| `MATCH_WEIGHT_TIME` | `0.40` | Weight of time compatibility |
| `MATCH_WEIGHT_ADDRESS` | `0.20` | Weight of textual address match |

Modify these values in your `.env` file and restart the server — no code changes needed.

## Testing

A professional test suite is available to ensure API reliability and data integrity.

### 1. Run the Tests

Execute the following command to run all tests with a verbose output:

```bash
sh test.sh
```

### 2. Test Coverage

The test suite includes:
- **FastAPI TestClient**: Full integration tests for all routes.
- **SQLite In-Memory**: A clean, isolated database for each test session.
- **Fixtures**: Automated setup/teardown for database tables and test data.
- **Happy & Sad Path**: Coverage for successful requests, validation errors (422), and edge cases.
- **Algorithm unit tests**: Haversine distance, geo/time/address scoring, combined scoring, and threshold behavior.

The testing configuration is managed via `pytest.ini`.
