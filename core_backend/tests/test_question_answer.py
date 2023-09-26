from fastapi.testclient import TestClient


def test_question_answer(client: TestClient) -> None:
    response = client.post(
        "/embeddings-search", json={"query_text": "How many road must a man walk down?"}
    )
    assert response.status_code == 200
