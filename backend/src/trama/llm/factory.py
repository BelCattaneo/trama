from trama.config import settings
from trama.llm.gemini import GeminiClient
from trama.llm.stub import StubLLMClient


def get_llm_client() -> GeminiClient | StubLLMClient:
    if settings.llm_provider == "gemini":
        if not settings.google_api_key:
            raise RuntimeError("GOOGLE_API_KEY required when LLM_PROVIDER=gemini")
        return GeminiClient(api_key=settings.google_api_key, model=settings.llm_model)
    if settings.llm_provider == "stub":
        return StubLLMClient()
    raise RuntimeError(f"unsupported LLM_PROVIDER={settings.llm_provider}")
