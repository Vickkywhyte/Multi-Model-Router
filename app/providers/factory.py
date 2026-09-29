"""Provider registry — resolves a provider name to a BaseProvider instance."""

from app.providers.base import BaseProvider
from app.providers.gemini_provider import GeminiProvider

_REGISTRY: dict[str, type[BaseProvider]] = {
    "google": GeminiProvider,
}


def register_provider(name: str, cls: type[BaseProvider]) -> None:
    _REGISTRY[name] = cls


def get_provider(provider_name: str = "google") -> BaseProvider:
    if provider_name not in _REGISTRY:
        raise ValueError(
            f"Unknown provider '{provider_name}'. "
            f"Registered providers: {list(_REGISTRY)}"
        )
    return _REGISTRY[provider_name]()
