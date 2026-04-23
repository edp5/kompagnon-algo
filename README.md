# kompagnon-algo

This repository is the part of the algorithm of matching for users in kompagnon.

## Roadmap

- [ ] Setup rule set
- [ ] Swagger for the algo API

## Proposed Structure

```text
kompagnon-algo/
├── .venv                # Virtual environment
├── .gitignore           # To ignore .venv, __pycache__, etc.
├── requirements.txt     # Project dependencies
├── main.py              # Entry point of your application/API
├── src/                 # Source code of the algorithm
│   ├── __init__.py
│   ├── config.py        # Loading environment variables
│   ├── db/              # Database connection code
│   ├── models/          # Data structures
│   ├── services/        # Business logic
│   └── algorithm/       # The core of your system!
│       ├── __init__.py
│       ├── scoring.py   # Functions to calculate compatibility
│       └── matcher.py   # System that matches users together
└── tests/               # Test the algo
    ├── __init__.py
    └── test_algorithm.py
```

## Project Setup

Run the following commands to set up the project:
```bash
sh scripts/configure.sh
```