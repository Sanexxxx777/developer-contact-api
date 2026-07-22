from types import SimpleNamespace

from app.models.contact import AIAnalysis
from app.services.ai_service import AIService


class FakeResponses:
    def __init__(self, result: AIAnalysis) -> None:
        self.result = result
        self.call: dict[str, object] | None = None

    async def parse(self, **kwargs):
        self.call = kwargs
        return SimpleNamespace(output_parsed=self.result)


async def test_ai_service_uses_structured_responses_contract():
    expected = AIAnalysis(
        sentiment="positive",
        category="project",
        priority=4,
        suggested_reply="Thanks — I will review the project details.",
    )
    responses = FakeResponses(expected)
    service = AIService(api_key=None, model="gpt-5.6-luna", timeout_seconds=1)
    service.client = SimpleNamespace(responses=responses)

    result, fallback_used = await service.analyze("We have a backend project.", "Alex")

    assert result == expected
    assert fallback_used is False
    assert responses.call["model"] == "gpt-5.6-luna"
    assert responses.call["reasoning"] == {"effort": "none"}
    assert responses.call["text_format"] is AIAnalysis
    assert responses.call["input"][1] == {
        "role": "user",
        "content": "We have a backend project.",
    }
