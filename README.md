# Prep
This is how you Prep

## Continuous Integration

This repository uses a GitHub Actions workflow at `.github/workflows/ci.yml` to automatically run linting and tests. The workflow:

1. Checks out the code.
2. Sets up Python.
3. Installs dependencies from `requirements.txt`.
4. Runs `flake8` for linting.
5. Executes the test suite with `pytest`.

The workflow triggers on pushes and pull requests to the `main` branch.
