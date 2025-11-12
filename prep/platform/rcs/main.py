"""Entry point for running the Realtime Config Service with Uvicorn."""

import uvicorn

from .service import app


def run() -> None:
    """Run the Realtime Config Service using uvicorn."""

    uvicorn.run(app, host="0.0.0.0", port=8080)


if __name__ == "__main__":
    run()
