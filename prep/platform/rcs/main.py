"""Entry point for running the Realtime Config Service with Uvicorn."""

import uvicorn

from prep.settings import get_settings

from .service import app


def run() -> None:
    """Run the Realtime Config Service using uvicorn."""

    settings = get_settings()
    uvicorn.run(app, host=settings.rcs_bind_host, port=8080)


if __name__ == "__main__":
    run()
