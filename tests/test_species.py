"""Unit tests for species lookups, using the real Wikipedia and OpenPlantbook shapes."""

import asyncio
import importlib.util
import sys
import unittest
from pathlib import Path


PACKAGE_PATH = Path(__file__).parents[1] / "custom_components" / "plant_manager"
SPEC = importlib.util.spec_from_file_location("plant_manager_species", PACKAGE_PATH / "species.py")
SPECIES = importlib.util.module_from_spec(SPEC)
# Dataclasses look their module up while being created.
sys.modules[SPEC.name] = SPECIES
SPEC.loader.exec_module(SPECIES)

# Answer of fr.wikipedia.org/w/rest.php/v1/search/title?q=ficus%20elastica.
WIKIPEDIA_SEARCH = {
    "pages": [{
        "id": 563586,
        "key": "Ficus_elastica",
        "title": "Ficus elastica",
        "excerpt": "Ficus elastica",
        "matched_title": None,
        "anchor": None,
        "description": "arbre sempervirent de la famille des Moracées",
        "thumbnail": {
            "mimetype": "image/jpeg",
            "width": 60,
            "height": 83,
            "duration": None,
            "url": "//thumb.wikimedia.org/wikipedia/commons/thumb/8/84/Ficus.jpg/60px-Ficus.jpg",
        },
    }],
}
# Answer of fr.wikipedia.org/api/rest_v1/page/summary/Ficus_elastica (trimmed).
WIKIPEDIA_SUMMARY = {
    "type": "standard",
    "title": "Ficus elastica",
    "description": "arbre sempervirent de la famille des Moracées",
    "thumbnail": {
        "source": "https://thumb.wikimedia.org/wikipedia/commons/thumb/8/84/Ficus.jpg/330px-Ficus.jpg",
        "width": 330,
        "height": 458,
    },
    "extract": "Le figuier à caoutchouc…",
}
# OpenPlantbook answers, as asserted by the official openplantbook-sdk tests.
PLANTBOOK_SEARCH = {
    "count": 1,
    "next": None,
    "previous": None,
    "results": [{
        "pid": "abelia chinensis",
        "display_pid": "Abelia chinensis",
        "alias": "chinese abelia",
        "category": "Caprifoliaceae, Abelia",
    }],
}
PLANTBOOK_DETAIL = {
    "pid": "abelia chinensis", "display_pid": "Abelia chinensis", "alias": "chinese abelia",
    "category": "Caprifoliaceae, Abelia", "max_light_mmol": 4500, "min_light_mmol": 2500,
    "max_light_lux": 30000, "min_light_lux": 3500, "max_temp": 35, "min_temp": 8,
    "max_env_humid": 85, "min_env_humid": 30, "max_soil_moist": 60, "min_soil_moist": 15,
    "max_soil_ec": 2000, "min_soil_ec": 350,
    "image_url": "https://opb-img.plantbook.io/abelia%20chinensis.jpg",
}


class FakeContent:
    """Delivers the body in small chunks, as a network stream does."""

    def __init__(self, body, chunk=7):
        self.body = body
        self.chunk = chunk

    async def read(self, limit=-1):
        # Like aiohttp: only what has "arrived", never the whole body at once.
        return self.body[: min(self.chunk, limit if limit >= 0 else self.chunk)]

    async def iter_chunked(self, size):
        for start in range(0, len(self.body), self.chunk):
            yield self.body[start:start + self.chunk]


class FakeResponse:
    def __init__(self, status=200, json_data=None, headers=None, body=b"", error=None):
        self.status = status
        self._json = json_data
        self.headers = headers or {}
        self.content = FakeContent(body)
        self._error = error

    async def __aenter__(self):
        if self._error:
            raise self._error
        return self

    async def __aexit__(self, *exc):
        return False

    async def json(self):
        if isinstance(self._json, Exception):
            raise self._json
        return self._json


class FakeSession:
    """Answers requests from a {(method, url): response} map and records them."""

    def __init__(self, responses):
        self.responses = responses
        self.requests = []

    def _answer(self, method, url, kwargs):
        self.requests.append((method, url, kwargs))
        return self.responses[(method, url)]

    def get(self, url, **kwargs):
        return self._answer("GET", url, kwargs)

    def post(self, url, **kwargs):
        return self._answer("POST", url, kwargs)


def run(coroutine):
    return asyncio.run(coroutine)


class ParsingTests(unittest.TestCase):
    def test_wikipedia_search_results(self):
        [match] = SPECIES.parse_wikipedia_search(WIKIPEDIA_SEARCH, "fr")
        self.assertEqual(match.name, "Ficus elastica")
        self.assertEqual(match.description, "arbre sempervirent de la famille des Moracées")
        self.assertEqual(match.value, "wikipedia:fr:Ficus_elastica")
        self.assertEqual(SPECIES.parse_match_value(match.value), ("wikipedia", "fr", "Ficus_elastica"))

    def test_wikipedia_summary_uses_the_https_thumbnail(self):
        details = SPECIES.parse_wikipedia_summary(WIKIPEDIA_SUMMARY)
        self.assertEqual(details.name, "Ficus elastica")
        self.assertTrue(details.image_url.startswith("https://thumb.wikimedia.org/"))
        self.assertIsNone(details.thresholds)

    def test_wikipedia_page_without_image(self):
        details = SPECIES.parse_wikipedia_summary({"title": "Kentia"})
        self.assertIsNone(details.image_url)

    def test_plantbook_search_results(self):
        [match] = SPECIES.parse_plantbook_search(PLANTBOOK_SEARCH)
        self.assertEqual(match.name, "Abelia chinensis")
        self.assertEqual(match.description, "chinese abelia")
        self.assertEqual(match.value, "openplantbook:abelia chinensis")
        self.assertEqual(SPECIES.parse_match_value(match.value), ("openplantbook", "", "abelia chinensis"))

    def test_plantbook_detail_gives_moisture_thresholds_and_photo(self):
        details = SPECIES.parse_plantbook_detail(PLANTBOOK_DETAIL)
        self.assertEqual(details.thresholds, (15.0, 60.0))
        self.assertEqual(details.image_url, "https://opb-img.plantbook.io/abelia%20chinensis.jpg")
        self.assertEqual(details.pid, "abelia chinensis")

    def test_plantbook_detail_gives_temperatures(self):
        self.assertEqual(SPECIES.parse_plantbook_detail(PLANTBOOK_DETAIL).temperatures, (8.0, 35.0))
        for low, high in ((35, 8), (None, 35), (8, "hot")):
            with self.subTest(low=low, high=high):
                data = {**PLANTBOOK_DETAIL, "min_temp": low, "max_temp": high}
                self.assertIsNone(SPECIES.parse_plantbook_detail(data).temperatures)

    def test_plantbook_invalid_thresholds_are_ignored(self):
        for low, high in ((70, 20), (None, 60), (-5, 60), (15, "n/a")):
            with self.subTest(low=low, high=high):
                data = {**PLANTBOOK_DETAIL, "min_soil_moist": low, "max_soil_moist": high}
                self.assertIsNone(SPECIES.parse_plantbook_detail(data).thresholds)

    def test_malformed_answers(self):
        self.assertEqual(SPECIES.parse_wikipedia_search(None, "fr"), [])
        self.assertEqual(SPECIES.parse_wikipedia_search({"pages": [{"title": "x"}]}, "fr"), [])
        self.assertEqual(SPECIES.parse_plantbook_search({"results": [{}]}), [])
        with self.assertRaises(SPECIES.SpeciesError):
            SPECIES.parse_plantbook_detail({"detail": "Not found"})

    def test_non_plant_results_are_dropped(self):
        # Real case: searching "Kentia" also returned Kentucky, KFC and Kenya.
        data = {"pages": [
            {"key": "Kentia", "title": "Kentia", "description": "espèce de plantes"},
            {"key": "Cyphophoenix_elegans", "title": "Cyphophoenix elegans"},
            {"key": "Kentucky", "title": "Kentucky", "description": "État des États-Unis"},
            {"key": "KFC", "title": "Kentucky Fried Chicken",
             "description": "chaîne de restauration rapide américaine"},
            {"key": "Kenya", "title": "Kenya", "description": "pays d'Afrique de l'Est"},
        ]}
        matches = SPECIES.keep_plants(SPECIES.parse_wikipedia_search(data, "fr"))
        self.assertEqual([m.name for m in matches], ["Kentia", "Cyphophoenix elegans"])

    def test_results_are_kept_when_none_looks_like_a_plant(self):
        data = {"pages": [{"key": "Pilea", "title": "Pilea", "description": "nom commun"}]}
        matches = SPECIES.keep_plants(SPECIES.parse_wikipedia_search(data, "fr"))
        self.assertEqual([m.name for m in matches], ["Pilea"])

    def test_wikipedia_language_follows_home_assistant(self):
        self.assertEqual(SPECIES.wikipedia_language("fr"), "fr")
        self.assertEqual(SPECIES.wikipedia_language("pt-BR"), "pt")
        self.assertEqual(SPECIES.wikipedia_language("ja"), "en")
        self.assertEqual(SPECIES.wikipedia_language(None), "en")


class RequestTests(unittest.TestCase):
    def test_wikipedia_search_request(self):
        url = "https://fr.wikipedia.org/w/rest.php/v1/search/title"
        session = FakeSession({("GET", url): FakeResponse(json_data=WIKIPEDIA_SEARCH)})
        matches = run(SPECIES.wikipedia_search(session, "fr", "ficus elastica"))
        self.assertEqual([m.name for m in matches], ["Ficus elastica"])
        _, _, kwargs = session.requests[0]
        self.assertEqual(kwargs["params"]["q"], "ficus elastica")
        self.assertIn("PlantManager", kwargs["headers"]["User-Agent"])

    def test_wikipedia_summary_escapes_the_page_key(self):
        url = "https://fr.wikipedia.org/api/rest_v1/page/summary/Ficus_%C3%A9lastique%2Fx"
        session = FakeSession({("GET", url): FakeResponse(json_data=WIKIPEDIA_SUMMARY)})
        self.assertEqual(
            run(SPECIES.wikipedia_summary(session, "fr", "Ficus_élastique/x")).name,
            "Ficus elastica",
        )

    def test_plantbook_client_gets_a_token_then_searches(self):
        base = "https://open.plantbook.io/api/v1"
        session = FakeSession({
            ("POST", f"{base}/token/"): FakeResponse(json_data={"access_token": "abc", "expires_in": 3600}),
            ("GET", f"{base}/plant/search"): FakeResponse(json_data=PLANTBOOK_SEARCH),
            ("GET", f"{base}/plant/detail/abelia%20chinensis/"): FakeResponse(json_data=PLANTBOOK_DETAIL),
        })
        client = SPECIES.PlantbookClient(session, "id", "secret")
        self.assertEqual(run(client.search("abelia"))[0].key, "abelia chinensis")
        self.assertEqual(run(client.detail("abelia chinensis")).thresholds, (15.0, 60.0))
        token_request = session.requests[0]
        self.assertEqual(token_request[2]["data"]["grant_type"], "client_credentials")
        self.assertEqual(session.requests[1][2]["headers"]["Authorization"], "Bearer abc")
        self.assertEqual(session.requests[1][2]["params"], {"alias": "abelia"})
        # The token is reused for the following requests.
        self.assertEqual([r[0] for r in session.requests], ["POST", "GET", "GET"])

    def test_plantbook_rejected_credentials(self):
        session = FakeSession({
            ("POST", "https://open.plantbook.io/api/v1/token/"): FakeResponse(status=401),
        })
        with self.assertRaises(SPECIES.PlantbookAuthError):
            run(SPECIES.PlantbookClient(session, "id", "wrong").validate())

    def test_network_errors_become_species_errors(self):
        url = "https://fr.wikipedia.org/w/rest.php/v1/search/title"
        for response in (
            FakeResponse(status=503),
            FakeResponse(error=asyncio.TimeoutError()),
            FakeResponse(error=ConnectionResetError("reset")),
            FakeResponse(json_data=ValueError("not json")),
        ):
            with self.subTest(response=response.status), self.assertRaises(SPECIES.SpeciesError):
                run(SPECIES.wikipedia_search(FakeSession({("GET", url): response}), "fr", "x"))


class DownloadImageTests(unittest.TestCase):
    URL = "https://opb-img.plantbook.io/x.jpg"

    def download(self, response):
        return run(SPECIES.download_image(FakeSession({("GET", self.URL): response}), self.URL))

    def test_returns_the_whole_image_and_its_extension(self):
        # Real case: a photo was saved truncated to its first network chunk.
        photo = b"\xff\xd8\xff" + bytes(range(256)) * 40 + b"\xff\xd9"
        body, extension = self.download(FakeResponse(
            headers={"Content-Type": "image/jpeg; charset=binary"}, body=photo
        ))
        self.assertEqual((body, extension), (photo, "jpg"))

    def test_refuses_non_images_and_huge_files(self):
        with self.assertRaises(SPECIES.SpeciesError):
            self.download(FakeResponse(headers={"Content-Type": "text/html"}, body=b"<html>"))
        with self.assertRaises(SPECIES.SpeciesError):
            self.download(FakeResponse(
                headers={"Content-Type": "image/png"}, body=b"x" * (SPECIES.MAX_IMAGE_BYTES + 1)
            ))


if __name__ == "__main__":
    unittest.main()
