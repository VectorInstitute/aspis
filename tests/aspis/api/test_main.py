"""Test for the API main module."""

import pytest
from fastapi.testclient import TestClient

from aspis.api.main import app


@pytest.mark.integration_test
def test_api_main() -> None:
    """Test the API main module."""
    with TestClient(app) as client:
        response = client.get("/test")
        assert response.status_code == 200
        assert response.json() == {"message": "Hello World"}
