# kompagnon-algo

This repository is the part of the algorithm of matching for users in kompagnon.

## Roadmap

- [x] Setup rule set
- [x] Swagger for the algo API
- [x] Setup API
- [ ] Implement algo logic

## Proposed Architecture

```text
kompagnon-algo/
├── setup.py                 # Project setup and automatic server launcher
├── src/
│   ├── api/
│   │   ├── main.py          # FastAPI application instance & routing setup
│   │   ├── routes.py        # Routes G (Accompanist) and H (Accompanied)
│   │   └── schema.py        # Pydantic models for API requests/responses
│   ├── db/
│   │   ├── session.py       # Database connection and session management
│   │   └── models.py        # SQLAlchemy models (T1: Accompanied, T2: Accompanists, T3: FoundJourney)
│   ├── algorithm/
│   │   ├── matcher.py       # Core matching logic (Orchestrates T1/T2 search)
│   │   └── scoring.py       # Math/Algo logic for compatibility calculation
│   └── config.py            # Environment variables and configuration
├── tests/                   # Unit and integration tests
├── requirements.txt         # Project dependencies
└── README.md
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

A unified script is provided to automatically create the virtual environment, install the required dependencies, and launch the server.

Simply run the following command at the root of the project:

```bash
# Automatic setup and server launch
python3 setup.py
```

_Note: If you prefer to launch the API manually after the environment has been created, you can use:_

```bash
# Activate virtual environment (Mac/Linux)
source .venv/bin/activate

# Run the API
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```
