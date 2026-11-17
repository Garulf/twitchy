from __future__ import annotations

from typing import Any, Dict
from urllib.parse import quote

from pyflowlauncher import Result
from pyflowlauncher.api import open_url

BASE_URL = "https://twitch.tv"
ICON = "icon.png"
ICON_SIZE = "28x28"
PROFILE_IMAGE_SIZE = "300x300"


def icon_url(thumbnail: str) -> str:
    if "{width}x{height}" in thumbnail:
        return thumbnail.replace("{width}x{height}", ICON_SIZE)
    return thumbnail.replace(PROFILE_IMAGE_SIZE, ICON_SIZE)


def channel_url(path: str) -> str:
    return f"{BASE_URL}/{path}"


def _result(title: str, subtitle: str, thumbnail: str, path: str) -> Result:
    return Result(
        title=title,
        subtitle=subtitle,
        icon=icon_url(thumbnail) or ICON,
        context_data=[path],
    ).add_action(open_url(channel_url(path)))


def channel_result(channel: Dict[str, Any]) -> Result:
    login = channel.get("broadcaster_login", "")
    if channel.get("is_live"):
        subtitle = f"{channel.get('game_name')} - {channel.get('title')}"
    else:
        subtitle = "Offline"
    return _result(channel.get("display_name") or login, subtitle, channel.get("thumbnail_url", ""), login)


def game_result(game: Dict[str, Any]) -> Result:
    name = game.get("name", "")
    return _result(name, "Game", game.get("box_art_url", ""), f"directory/game/{quote(name)}")


def user_result(user: Dict[str, Any]) -> Result:
    login = user.get("login", "")
    return _result(user.get("display_name") or login, user.get("description", ""), user.get("profile_image_url", ""), login)


def stream_result(stream: Dict[str, Any]) -> Result:
    login = stream.get("user_login", "")
    subtitle = f"{stream.get('game_name')}: {stream.get('title')}"
    return _result(stream.get("user_name") or login, subtitle, stream.get("thumbnail_url", ""), login)
