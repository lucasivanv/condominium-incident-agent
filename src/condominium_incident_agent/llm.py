import logging
import os
from typing import Any

from dotenv import load_dotenv
from httpx import NetworkError, TimeoutException
from langchain_ollama import ChatOllama

load_dotenv()

logger = logging.getLogger(__name__)

OLLAMA_TIMEOUT_SECONDS = 60
LLM_MAX_ATTEMPTS = 3
TRANSIENT_LLM_EXCEPTIONS = (
    TimeoutError,
    ConnectionError,
    TimeoutException,
    NetworkError,
)


def with_llm_retry(runnable: Any) -> Any:
    """Aplica retry limitado somente para falhas transitórias do LLM."""
    return runnable.with_retry(
        retry_if_exception_type=TRANSIENT_LLM_EXCEPTIONS,
        stop_after_attempt=LLM_MAX_ATTEMPTS,
        wait_exponential_jitter=True,
    )


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
        timeout=float(os.getenv("OLLAMA_TIMEOUT_SECONDS", OLLAMA_TIMEOUT_SECONDS)),
    )


def get_llm_with_retry() -> ChatOllama:
    """Retorna o LLM com retry automático configurado.

    Use esta função em nós que invocam o LLM diretamente, sem necessidade
    de ``bind_tools``.
    """
    return with_llm_retry(get_llm())
