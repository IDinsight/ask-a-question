from fastapi.testclient import TestClient


async def test_healthcheck(client: TestClient) -> None:
    response = client.get("/healthcheck")
    assert response.status_code == 200, f"response: {response.json()}"
    assert response.json() == {"status": "ok"}
