from fastapi.testclient import TestClient

from app.api.routes import get_provider
from app.main import app
from app.providers.base import LLMProvider


class FakeProvider(LLMProvider):
    async def generate(self, messages: list[dict], **kwargs) -> str:
        return f"echo: {messages[-1]['content']}"


app.dependency_overrides[get_provider] = lambda: FakeProvider()
client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat():
    response = client.post("/chat", json={"message": "hello"})
    assert response.status_code == 200
    assert response.json() == {"response": "echo: hello"}
