import json
from typing import Any, Dict, List, Optional

import pytest
import requests

import helix
import twitchy

CHANNELS = [
    {
        "broadcaster_login": "speedrunsdaily",
        "display_name": "SpeedrunsDaily",
        "is_live": True,
        "game_name": "Celeste",
        "title": "Any% practice",
        "thumbnail_url": "https://static-cdn.example/speedrunsdaily-profile_image-300x300.png",
    },
    {
        "broadcaster_login": "cozycrafts",
        "display_name": "CozyCrafts",
        "is_live": False,
        "game_name": "",
        "title": "",
        "thumbnail_url": "https://static-cdn.example/cozycrafts-profile_image-300x300.png",
    },
]
GAMES = [
    {"id": str(n), "name": name, "box_art_url": f"https://static-cdn.example/box/{n}-{{width}}x{{height}}.jpg"}
    for n, name in enumerate(["Just Chatting", "Celeste", "Hades II", "Stardew Valley"], start=1)
]
USERS = [
    {"id": "1", "login": "viewer", "display_name": "Viewer", "description": "", "profile_image_url": ""},
    {
        "id": "42",
        "login": "speedrunsdaily",
        "display_name": "SpeedrunsDaily",
        "description": "Daily speedruns",
        "profile_image_url": "https://static-cdn.example/speedrunsdaily-profile_image-300x300.png",
    },
]
STREAMS = [
    {
        "user_id": "42",
        "user_login": "speedrunsdaily",
        "user_name": "SpeedrunsDaily",
        "game_name": "Celeste",
        "title": "Any% practice",
        "thumbnail_url": "https://static-cdn.example/live_user_speedrunsdaily-{width}x{height}.jpg",
    }
]


class FakeResponse:
    def __init__(self, payload: Any, status_code: int = 200) -> None:
        self._payload = json.loads(json.dumps(payload))
        self.status_code = status_code

    def json(self) -> Any:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} error", response=self)


class FakeTwitch:
    def __init__(self) -> None:
        self.calls: List[tuple] = []
        self.valid_tokens = {"user-token", "app-token"}
        self.issued_token = "app-token"
        self.follows: List[str] = ["42"]
        self.pages: Dict[str, List[List[Dict[str, Any]]]] = {"games/top": [GAMES[:2], GAMES[2:]]}
        self.failing: Optional[str] = None

    def post(self, url: str, data: Optional[dict] = None, **kwargs: Any) -> FakeResponse:
        self.calls.append(("POST", url, data))
        if url == f"{helix.OAUTH_URL}/token":
            return FakeResponse({"access_token": self.issued_token, "expires_in": 5000000, "token_type": "bearer"})
        return FakeResponse({"status": 404}, 404)

    def get(self, url: str, params: Optional[dict] = None, headers: Optional[dict] = None, **kwargs: Any) -> FakeResponse:
        self.calls.append(("GET", url, params))
        if url == f"{helix.OAUTH_URL}/validate":
            token = (headers or {}).get("Authorization", "").split(" ", 1)[-1]
            if token in self.valid_tokens:
                return FakeResponse({"client_id": "client", "scopes": [], "expires_in": 1000})
            return FakeResponse({"status": 401, "message": "invalid access token"}, 401)
        path = url[len(helix.HELIX_URL) + 1:]
        if path == self.failing:
            return FakeResponse({"status": 410, "message": "Gone"}, 410)
        return FakeResponse(self.helix(path, dict(params or {})))

    def helix(self, path: str, params: dict) -> dict:
        if path in self.pages:
            index = int(params.get("after") or 0)
            pages = self.pages[path]
            cursor = {"cursor": str(index + 1)} if index + 1 < len(pages) else {}
            return {"data": pages[index], "pagination": cursor}
        if path == "search/channels":
            query = params["query"].lower()
            return {"data": [c for c in CHANNELS if query in c["broadcaster_login"]], "pagination": {}}
        if path == "users":
            logins, ids = params.get("login") or [], params.get("id") or []
            return {"data": [u for u in USERS if u["login"] in logins or u["id"] in ids]}
        if path == "users/follows":
            return {"data": [{"to_id": to_id} for to_id in self.follows], "pagination": {}}
        if path == "streams":
            ids = params.get("user_id") or []
            return {"data": [s for s in STREAMS if s["user_id"] in ids], "pagination": {}}
        return {"data": [], "pagination": {}}


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("tests must not reach the network")

    monkeypatch.setattr(requests.Session, "request", refuse)


@pytest.fixture
def twitch(monkeypatch):
    fake = FakeTwitch()
    monkeypatch.setattr(helix, "Session", lambda: fake)
    twitchy.validated_tokens.clear()
    return fake


@pytest.fixture
def settings():
    launcher = twitchy.plugin.launcher
    launcher._settings = {
        "client_id": "client",
        "client_secret": "secret",
        "oauth_token": "user-token",
        "username": "",
        "program_path": "",
        "program_args": "",
    }
    yield launcher._settings
    launcher._settings = {}
