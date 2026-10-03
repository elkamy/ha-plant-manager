"""Species lookup on Wikipedia (no account) and OpenPlantbook (optional account).

Parsing is kept separate from the HTTP calls so it can be tested with the real
response shapes, and the calls take any aiohttp-compatible session.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from urllib.parse import quote

USER_AGENT = "PlantManager (https://github.com/elkamy/ha-plant-manager)"
WIKIPEDIA_LANGUAGES = ("fr", "en", "de", "es", "it", "nl", "pt")
WIKIPEDIA_SEARCH_URL = "https://{lang}.wikipedia.org/w/rest.php/v1/search/title"
WIKIPEDIA_SUMMARY_URL = "https://{lang}.wikipedia.org/api/rest_v1/page/summary/{key}"
PLANTBOOK_URL = "https://open.plantbook.io/api/v1"
TIMEOUT = 15
MAX_IMAGE_BYTES = 5 * 1024 * 1024
IMAGE_EXTENSIONS = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
}

SOURCE_WIKIPEDIA = "wikipedia"
SOURCE_PLANTBOOK = "openplantbook"


class SpeciesError(Exception):
    """A species source could not be reached or answered unexpectedly."""


class PlantbookAuthError(SpeciesError):
    """OpenPlantbook rejected the client ID or secret."""


@dataclass(frozen=True)
class SpeciesMatch:
    source: str
    key: str
    name: str
    description: str = ""
    language: str = ""

    @property
    def value(self) -> str:
        """Identifier used as a select option in the config flow."""
        if self.source == SOURCE_WIKIPEDIA:
            return f"{SOURCE_WIKIPEDIA}:{self.language}:{self.key}"
        return f"{SOURCE_PLANTBOOK}:{self.key}"


@dataclass(frozen=True)
class SpeciesDetails:
    source: str
    name: str
    description: str = ""
    image_url: str | None = None
    # (low, high) moisture thresholds, only known from OpenPlantbook.
    thresholds: tuple[float, float] | None = None
    pid: str | None = None


def parse_match_value(value: str) -> tuple[str, str, str]:
    """Split a select value back into (source, language, key)."""
    source, _, rest = value.partition(":")
    if source == SOURCE_WIKIPEDIA:
        language, _, key = rest.partition(":")
        return source, language, key
    return source, "", rest


def wikipedia_language(language: str | None) -> str:
    """Return the Wikipedia edition to search for a Home Assistant language."""
    base = (language or "").split("-")[0].lower()
    return base if base in WIKIPEDIA_LANGUAGES else "en"


def parse_wikipedia_search(data, language: str) -> list[SpeciesMatch]:
    pages = data.get("pages") if isinstance(data, dict) else None
    matches = []
    for page in pages or []:
        if not isinstance(page, dict) or not page.get("key") or not page.get("title"):
            continue
        matches.append(SpeciesMatch(
            source=SOURCE_WIKIPEDIA,
            key=str(page["key"]),
            name=str(page["title"]),
            description=str(page.get("description") or ""),
            language=language,
        ))
    return matches


def parse_wikipedia_summary(data) -> SpeciesDetails:
    if not isinstance(data, dict) or not data.get("title"):
        raise SpeciesError("Unexpected Wikipedia summary")
    thumbnail = data.get("thumbnail") or {}
    image = thumbnail.get("source") if isinstance(thumbnail, dict) else None
    return SpeciesDetails(
        source=SOURCE_WIKIPEDIA,
        name=str(data["title"]),
        description=str(data.get("description") or ""),
        image_url=image if isinstance(image, str) and image.startswith("https://") else None,
    )


def parse_plantbook_search(data) -> list[SpeciesMatch]:
    results = data.get("results") if isinstance(data, dict) else None
    matches = []
    for plant in results or []:
        if not isinstance(plant, dict) or not plant.get("pid"):
            continue
        matches.append(SpeciesMatch(
            source=SOURCE_PLANTBOOK,
            key=str(plant["pid"]),
            name=str(plant.get("display_pid") or plant["pid"]),
            description=str(plant.get("alias") or ""),
        ))
    return matches


def _percentage(value) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if 0 <= number <= 100 else None


def parse_plantbook_detail(data) -> SpeciesDetails:
    if not isinstance(data, dict) or not data.get("pid"):
        raise SpeciesError("Unexpected OpenPlantbook detail")
    low = _percentage(data.get("min_soil_moist"))
    high = _percentage(data.get("max_soil_moist"))
    image = data.get("image_url")
    return SpeciesDetails(
        source=SOURCE_PLANTBOOK,
        name=str(data.get("display_pid") or data["pid"]),
        description=str(data.get("alias") or ""),
        image_url=image if isinstance(image, str) and image.startswith("https://") else None,
        thresholds=(low, high) if low is not None and high is not None and low < high else None,
        pid=str(data["pid"]),
    )


async def _get_json(session, url: str, **kwargs):
    try:
        async with asyncio.timeout(TIMEOUT):
            async with session.get(url, **kwargs) as response:
                if response.status in (401, 403):
                    raise PlantbookAuthError(f"HTTP {response.status}")
                if response.status == 404:
                    return None
                if response.status >= 400:
                    raise SpeciesError(f"HTTP {response.status} from {url}")
                return await response.json()
    except SpeciesError:
        raise
    except ValueError as err:
        raise SpeciesError(f"Invalid JSON from {url}") from err
    except Exception as err:  # noqa: BLE001 - timeouts and any aiohttp client error
        raise SpeciesError(str(err) or type(err).__name__) from err


async def wikipedia_search(session, language: str, query: str, limit: int = 6) -> list[SpeciesMatch]:
    data = await _get_json(
        session,
        WIKIPEDIA_SEARCH_URL.format(lang=language),
        params={"q": query, "limit": str(limit)},
        headers={"User-Agent": USER_AGENT},
    )
    return parse_wikipedia_search(data or {}, language)


async def wikipedia_summary(session, language: str, key: str) -> SpeciesDetails:
    data = await _get_json(
        session,
        WIKIPEDIA_SUMMARY_URL.format(lang=language, key=quote(key, safe="")),
        headers={"User-Agent": USER_AGENT},
    )
    return parse_wikipedia_summary(data)


class PlantbookClient:
    """Minimal OpenPlantbook client using the OAuth2 client credentials grant."""

    def __init__(self, session, client_id: str, client_secret: str) -> None:
        self._session = session
        self._client_id = client_id
        self._client_secret = client_secret
        self._token: str | None = None

    async def _authorization(self) -> dict:
        if self._token is None:
            try:
                async with asyncio.timeout(TIMEOUT):
                    async with self._session.post(
                        f"{PLANTBOOK_URL}/token/",
                        data={
                            "grant_type": "client_credentials",
                            "client_id": self._client_id,
                            "client_secret": self._client_secret,
                        },
                    ) as response:
                        if response.status in (400, 401, 403):
                            raise PlantbookAuthError(f"HTTP {response.status}")
                        if response.status >= 400:
                            raise SpeciesError(f"HTTP {response.status} from OpenPlantbook")
                        token = await response.json()
            except SpeciesError:
                raise
            except ValueError as err:
                raise SpeciesError("Invalid JSON from OpenPlantbook") from err
            except Exception as err:  # noqa: BLE001 - timeouts and any aiohttp client error
                raise SpeciesError(str(err) or type(err).__name__) from err
            if not isinstance(token, dict) or not token.get("access_token"):
                raise PlantbookAuthError("No access token")
            self._token = token["access_token"]
        return {"Authorization": f"Bearer {self._token}"}

    async def validate(self) -> None:
        """Raise PlantbookAuthError when the credentials are wrong."""
        await self._authorization()

    async def search(self, query: str) -> list[SpeciesMatch]:
        data = await _get_json(
            self._session,
            f"{PLANTBOOK_URL}/plant/search",
            params={"alias": query},
            headers=await self._authorization(),
        )
        return parse_plantbook_search(data or {})

    async def detail(self, pid: str) -> SpeciesDetails:
        data = await _get_json(
            self._session,
            f"{PLANTBOOK_URL}/plant/detail/{quote(pid, safe='')}/",
            headers=await self._authorization(),
        )
        return parse_plantbook_detail(data)


async def download_image(session, url: str) -> tuple[bytes, str]:
    """Return the image bytes and file extension, refusing non-images and huge files."""
    try:
        async with asyncio.timeout(TIMEOUT):
            async with session.get(url, headers={"User-Agent": USER_AGENT}) as response:
                if response.status >= 400:
                    raise SpeciesError(f"HTTP {response.status} from {url}")
                content_type = response.headers.get("Content-Type", "").split(";")[0].strip()
                extension = IMAGE_EXTENSIONS.get(content_type.lower())
                if extension is None:
                    raise SpeciesError(f"Not an image: {content_type or 'unknown type'}")
                body = await response.content.read(MAX_IMAGE_BYTES + 1)
    except SpeciesError:
        raise
    except Exception as err:  # noqa: BLE001 - timeouts and any aiohttp client error
        raise SpeciesError(str(err) or type(err).__name__) from err
    if len(body) > MAX_IMAGE_BYTES:
        raise SpeciesError("Image too large")
    return body, extension
