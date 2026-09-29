"""Provider registry — resolves a provider name to a BaseProvider instance."""

from app.providers.base import BaseProvider
from app.providers.gemini_provider import GeminiProvider

_REGISTRY: dict[str, type[BaseProvider]] = {
    "google": GeminiProvider,
}


def register_provider(name: str, cls: type[BaseProvider]) -> None:
    """Register a new provider class under the given name.

    Args:
        name: Short identifier (e.g. "openai").
        cls: A concrete BaseProvider subclass.
    """
    _REGISTRY[name] = cls


def get_provider(provider_name: str = "google") -> BaseProvider:
    """Return an instantiated provider for the given name.

    Args:
        provider_name: Key in the registry (default "google").

    Returns:
        A ready-to-use BaseProvider instance.

    Raises:
        ValueError: If provider_name is not registered.
    """
    if provider_name not in _REGISTRY:
        raise ValueError(
            f"Unknown provider '{provider_name}'. "
            f"Registered providers: {list(_REGISTRY)}"
        )
    return _REGISTRY[provider_name]()
