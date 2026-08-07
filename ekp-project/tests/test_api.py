from fastapi.testclient import TestClient
from app.api.routes import app

client = TestClient(app)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the EKP API!"}

def test_some_endpoint():
    response = client.post("/some-endpoint", json={"key": "value"})
    assert response.status_code == 200
    assert "expected_key" in response.json()

def test_invalid_endpoint():
    response = client.get("/invalid-endpoint")
    assert response.status_code == 404