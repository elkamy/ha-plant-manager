"""OpenPlantbook credentials, shared by all plants."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN

STORE_KEY = f"{DOMAIN}.openplantbook"
STORE_VERSION = 1


def _store(hass: HomeAssistant) -> Store:
    return Store(hass, STORE_VERSION, STORE_KEY, private=True)


async def async_load_plantbook(hass: HomeAssistant) -> tuple[str, str] | None:
    """Return (client_id, client_secret), or None when no account is set up."""
    data = await _store(hass).async_load() or {}
    client_id, secret = data.get("client_id"), data.get("client_secret")
    return (client_id, secret) if client_id and secret else None


async def async_save_plantbook(
    hass: HomeAssistant, client_id: str | None, client_secret: str | None
) -> None:
    """Save the credentials, or forget them when either is empty."""
    store = _store(hass)
    if client_id and client_secret:
        await store.async_save({"client_id": client_id, "client_secret": client_secret})
    else:
        await store.async_remove()
