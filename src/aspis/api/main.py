"""Functions for the programmatic API of the Aspis application."""

from typing import Any

from fastapi import FastAPI


app = FastAPI()


@app.get("/api")
async def api_root() -> dict[str, Any]:
    """Root endpoint for the API."""
    return {"message": "Hello World"}
