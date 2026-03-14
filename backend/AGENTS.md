# Backend Agent Instructions

## Tech Stack
- Python 3.11 + FastAPI
- PostgreSQL (via SQLAlchemy)
- Testing: Pytest

## Critical Rules
- **Security:** Never commit plain-text passwords. Use `.env` mocks.
- **Database:** Every new table must have `created_at` and `updated_at` timestamps.
- **Style:** Follow PEP 8. Use Type Hints for all function signatures.
- **Verification:** Run `bandit -r .` before marking a task as complete.

