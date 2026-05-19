# kompagnon-algo

This repository is the part of the algorithm of matching for users in kompagnon.

## Roadmap

- [x] Setup rule set
- [x] Swagger for the algo API
- [x] Setup API
- [x] Setup DB connection
- [x] Add tests for API & DB connection
- [x] Implement algo logic

## Proposed Architecture

```text
kompagnon-algo/
├── doc/                     # Documentation directory
│   └── README_algo.md       # Detailed algorithm documentation
├── src/                     # Source code directory
│   ├── algorithm/           # Core matching algorithm
│   │   ├── main.py          # Batch matching entry point & DB saver
│   │   └── matcher.py       # Core matching logic (Orchestrates T1/T2 search)
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

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Workflow Description

1. **Trigger**: The main API calls `kompagnon-algo` on Route **G** (Accompanist) or **H** (Accompanied) with a `journey_id` (A).
2. **Fetch**: The algo fetches the data for journey A from **Table T1** (or T2 depending on the type).
3. **Match**:
   - If **Accompanied (H)**: The algo searches for candidates in **Table T2** (Accompanists).
   - If **Accompanist (G)**: The algo searches for candidates in **Table T1** (Accompanied).
4. **Calculations**: Scikit-learn/Pandas are used to rank candidates.
5. **Storage**: A new entry is created in **Table T3** (`foundJourney`) linking the two journeys.
6. **Response**: The algo returns the ID of the matched journeys from **Table T3** to the caller.

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

## Running the Matching Algorithm (Dry-run)

To manually run the core matching algorithm logic with mock data and see the logging output (as part of the initial issue 28 setup):

```bash
python -m src.algorithm.main
```

This will run the `run_algorithm` function, match mock passengers and companions based on origin and destination coordinates, and output the result to the console.

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

The testing configuration is managed via `pytest.ini`.
