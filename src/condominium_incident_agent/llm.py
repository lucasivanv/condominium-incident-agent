import logging
import os

from dotenv import load_dotenv
from langchain_ollama import ChatOllama

load_dotenv()

logger = logging.getLogger(__name__)


def get_llm() -> ChatOllama:
    """Retorna o LLM base (ChatOllama) sem wrapper de retry.

    Use esta função quando precisar chamar ``bind_tools`` antes de invocar
    o modelo, pois ``with_retry`` retorna um ``RunnableRetry`` que não
    expõe ``bind_tools``.
    """
    model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    logger.info("Initializing Ollama model: %s", model)

    return ChatOllama(
        model=model,
        temperature=0,
        timeout=60,
    )


def get_llm_with_retry() -> ChatOllama:
    """Retorna o LLM com retry automático configurado.

    Use esta função em nós que invocam o LLM diretamente, sem necessidade
    de ``bind_tools``.
    """
    return get_llm().with_retry(
        stop_after_attempt=3,
        wait_exponential_jitter=True,
    )
