"""Functions for the programmatic API of the Aspis application."""

from typing import Any

from fastapi import FastAPI


app = FastAPI()


@app.get("/test")
async def test_api() -> dict[str, Any]:
    """Test endpoint for the API."""
    return {"message": "Hello World"}
