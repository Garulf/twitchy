from __future__ import annotations

from typing import Any, Dict, Iterable, Iterator, List, Optional

from requests import Session

OAUTH_URL = "https://id.twitch.tv/oauth2"
HELIX_URL = "https://api.twitch.tv/helix"
PAGE_SIZE = 100
TIMEOUT = 10


class MissingCredentials(Exception):
    pass


def request_app_token(client_id: str, client_secret: str, session: Optional[Session] = None) -> str:
    if not client_id or not client_secret:
        raise MissingCredentials("A client ID and client secret are both required.")
    response = (session or Session()).post(
        f"{OAUTH_URL}/token",
        data={"client_id": client_id, "client_secret": client_secret, "grant_type": "client_credentials"},
        timeout=TIMEOUT,
    )
    payload = response.json()
    if "access_token" not in payload:
        raise MissingCredentials(payload.get("message") or "Twitch did not return an access token.")
    return payload["access_token"]


def token_is_valid(token: str, session: Optional[Session] = None) -> bool:
    response = (session or Session()).get(
        f"{OAUTH_URL}/validate", headers={"Authorization": f"OAuth {token}"}, timeout=TIMEOUT
    )
    return response.status_code != 401


class Helix:
    def __init__(self, client_id: str, token: str, session: Optional[Session] = None) -> None:
        self._session = session or Session()
        self._headers = {"Client-Id": client_id, "Authorization": f"Bearer {token}"}

    def _get(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        response = self._session.get(f"{HELIX_URL}/{path}", params=params, headers=self._headers, timeout=TIMEOUT)
        response.raise_for_status()
        return response.json()

    def _paginate(self, path: str, params: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
        params = dict(params)
        while True:
            page = self._get(path, params)
            yield from page.get("data", [])
            cursor = (page.get("pagination") or {}).get("cursor")
            if not cursor:
                return
            params["after"] = cursor

    def search_channels(self, query: str, first: int) -> Iterator[Dict[str, Any]]:
        return self._paginate("search/channels", {"query": query, "first": first})

    def top_games(self) -> Iterator[Dict[str, Any]]:
        return self._paginate("games/top", {"first": PAGE_SIZE})

    def users(self, logins: Iterable[str] = (), ids: Iterable[str] = ()) -> List[Dict[str, Any]]:
        return self._get("users", {"login": list(logins), "id": list(ids)}).get("data", [])

    def user_follows(self, from_id: str) -> Iterator[Dict[str, Any]]:
        return self._paginate("users/follows", {"from_id": from_id, "first": PAGE_SIZE})

    def streams(self, user_ids: Iterable[str]) -> List[Dict[str, Any]]:
        return self._get("streams", {"user_id": list(user_ids), "first": PAGE_SIZE}).get("data", [])
