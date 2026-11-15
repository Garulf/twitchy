from __future__ import annotations

import asyncio
import time
from functools import partial
from itertools import islice
from pathlib import PureWindowsPath
from subprocess import Popen
from typing import Any, Callable, Dict, Iterable, List, Optional

from pyflowlauncher import FlowLauncherV2, Plugin, Result, send_results
from pyflowlauncher.api import open_setting_dialog
from requests.exceptions import HTTPError

from helix import Helix, MissingCredentials, request_app_token, token_is_valid
from results import ICON, channel_result, channel_url, game_result, stream_result, user_result

LIMIT = 10
GAME_LIMIT = 50
FOLLOW_LIMIT = 100
GAME_SCAN_LIMIT = 5000
TOKEN_CHECK_INTERVAL = 3600

plugin = Plugin(launcher=FlowLauncherV2())
validated_tokens: Dict[str, float] = {}


def setting(name: str) -> str:
    return plugin.settings.get(name) or ""


async def run_blocking(func: Callable[..., Any], *args: Any) -> Any:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(func, *args))


def token_still_valid(token: str) -> bool:
    checked_at = validated_tokens.get(token)
    if checked_at is not None and time.monotonic() - checked_at < TOKEN_CHECK_INTERVAL:
        return True
    if token_is_valid(token):
        validated_tokens[token] = time.monotonic()
        return True
    validated_tokens.pop(token, None)
    return False


def access_token() -> str:
    if not setting("client_id"):
        raise MissingCredentials("A client ID is required.")
    token = setting("oauth_token")
    if token and token_still_valid(token):
        return token
    token = request_app_token(setting("client_id"), setting("client_secret"))
    validated_tokens[token] = time.monotonic()
    return token


def search_results(client: Helix, query: str) -> List[Result]:
    if query.startswith(":"):
        games: Iterable[Dict[str, Any]] = client.top_games()
        name = query[1:].lower()
        if name:
            games = (game for game in islice(games, GAME_SCAN_LIMIT) if name in game["name"].lower())
        return [game_result(game) for game in islice(games, GAME_LIMIT)]
    username = setting("username")
    if query.startswith("#") and username:
        return [user_result(user) for user in islice(followed_users(client, username), FOLLOW_LIMIT)]
    if query:
        return [channel_result(channel) for channel in islice(client.search_channels(query, LIMIT), LIMIT)]
    if username:
        return [stream_result(stream) for stream in islice(followed_streams(client, username), FOLLOW_LIMIT)]
    return []


def followed_ids(client: Helix, username: str) -> List[str]:
    user_id = client.users(logins=[username])[0]["id"]
    return [follow["to_id"] for follow in client.user_follows(user_id)]


def followed_users(client: Helix, username: str) -> List[Dict[str, Any]]:
    return client.users(ids=followed_ids(client, username))


def followed_streams(client: Helix, username: str) -> List[Dict[str, Any]]:
    return client.streams(followed_ids(client, username))


def missing_credentials_result() -> Result:
    return Result(
        title="Missing credentials",
        subtitle="Please set your credentials in the settings",
        icon=plugin.launcher.icons.app_error or ICON,
    ).add_action(open_setting_dialog())


def login_error_result() -> Result:
    return Result(
        title="ERROR: Unable to login!",
        subtitle="Please check your Client ID and OAuth token in settings.",
        icon=ICON,
    ).add_action(open_setting_dialog())


def lookup(query: str) -> Dict[str, Any]:
    saved_token = setting("oauth_token")
    try:
        token = access_token()
    except MissingCredentials:
        return send_results([missing_credentials_result()])
    settings_change: Optional[Dict[str, Any]] = {"oauth_token": token} if token != saved_token else None
    try:
        results = search_results(Helix(setting("client_id"), token), query)
    except HTTPError:
        plugin.logger.exception("Twitch request failed")
        results = [login_error_result()]
    return send_results(results, settings_change)


@plugin.on_method
async def query(query: str) -> Dict[str, Any]:
    return await run_blocking(lookup, query)


def stream_urls(url: str) -> Dict[str, str]:
    import streamlink

    streams = streamlink.streams(url)
    return {"best": streams["best"].url, "worst": streams["worst"].url}


def program_menu(path: str) -> List[Result]:
    program_path = setting("program_path")
    if not program_path:
        return []
    url = channel_url(path)
    program_args = setting("program_args") or "{url}"
    urls = {"best": "", "worst": ""}
    if "{best}" in program_args or "{worst}" in program_args:
        urls = stream_urls(url)
    args = program_args.format(url=url, **urls)
    return [
        Result(
            title=f"Open Stream in {PureWindowsPath(program_path).name}",
            subtitle=args,
            icon=program_path,
        ).add_action(open_program, parameters=[program_path, args])
    ]


@plugin.on_method
async def context_menu(data: List[str]) -> List[Result]:
    return await run_blocking(program_menu, data[0])


@plugin.on_method
def open_program(program_path: str, args: str) -> None:
    Popen([program_path, args])
