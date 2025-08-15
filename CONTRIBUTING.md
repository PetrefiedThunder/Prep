# Contributing to Prep

Thank you for your interest in contributing! This document will guide you through the process.

## Getting Started

### Python projects

1. **Clone the repository.**
2. **Install dependencies:** `pip install -e .`
3. **Run the tests:** `pytest`

### Node projects

1. **Install dependencies:** `npm install`
2. **Create a `.env` file:** Copy `.env.example` and fill in secrets (never commit actual secrets).
3. **Run the tests:** `npm test`

## Linting and Type Checks

Shared configurations are provided for both ecosystems. Run these checks locally before submitting changes.

### Python

- Lint with [Ruff](https://github.com/astral-sh/ruff): `ruff .`
- Type-check with [mypy](http://mypy-lang.org/): `mypy .`

### Node

- Lint with [ESLint](https://eslint.org/): `npx eslint .`
- Type-check with the TypeScript compiler: `npx tsc --noEmit`

## Code Style

- Use Prettier for formatting.
- Typescript for backend/services, Python for some modules.
- Write clear commit messages (e.g., `feat(auth): add JWT refresh tokens`).

## Pull Requests

- Fork the repo and create your feature branch (`git checkout -b feat/my-feature`)
- Write tests for new features or bug fixes.
- Open a PR and fill out the template.
- Wait for review and CI to pass.

## Reporting Bugs / Requesting Features

- Use the issue templates provided.
- For security issues, refer to [SECURITY.md](SECURITY.md).

## Community

- Be respectful and inclusive.
- Use Discussions for ideas or architectural questions.

Thanks for helping make Prep better!
