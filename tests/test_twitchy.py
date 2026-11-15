import asyncio
import json
from pathlib import Path

import pytest

import helix
import twitchy

ROOT = Path(__file__).resolve().parents[1]


def run_query(text):
    return asyncio.run(twitchy.plugin._event_handler.trigger_event("query", text))


def titles(response):
    return [result["Title"] for result in response["Result"]]


def actions(response):
    return [result["JsonRPCAction"] for result in response["Result"]]


def test_manifest_keeps_plugin_identity():
    manifest = json.loads((ROOT / "data" / "plugin.json").read_text())
    assert manifest["ID"] == "477F16413D374364A4D5D36DCE68ED45"
    assert manifest["ActionKeyword"] == "tw"
    assert manifest["Language"] == "python_v2"
    assert manifest["ExecuteFileName"] == "run.py"


def test_search_lists_matching_channels(twitch, settings):
    response = run_query("speedrun")
    assert titles(response) == ["SpeedrunsDaily"]
    result = response["Result"][0]
    assert result["SubTitle"] == "Celeste - Any% practice"
    assert result["IcoPath"] == "https://static-cdn.example/speedrunsdaily-profile_image-28x28.png"
    assert result["ContextData"] == ["speedrunsdaily"]
    assert result["JsonRPCAction"]["Method"] == "Flow.Launcher.OpenUrl"
    assert result["JsonRPCAction"]["Parameters"][0] == "https://twitch.tv/speedrunsdaily"


def test_offline_channel_says_offline(twitch, settings):
    response = run_query("cozy")
    assert response["Result"][0]["SubTitle"] == "Offline"


def test_colon_lists_top_games_across_pages(twitch, settings):
    response = run_query(":")
    assert titles(response) == ["Just Chatting", "Celeste", "Hades II", "Stardew Valley"]
    assert response["Result"][0]["IcoPath"] == "https://static-cdn.example/box/1-28x28.jpg"
    assert actions(response)[0]["Parameters"][0] == "https://twitch.tv/directory/game/Just%20Chatting"


def test_colon_filters_top_games_by_name(twitch, settings):
    assert titles(run_query(":hades")) == ["Hades II"]


def test_empty_query_without_username_shows_nothing(twitch, settings):
    assert run_query("")["Result"] == []


def test_empty_query_with_username_lists_followed_live_streams(twitch, settings):
    settings["username"] = "viewer"
    response = run_query("")
    assert titles(response) == ["SpeedrunsDaily"]
    assert response["Result"][0]["SubTitle"] == "Celeste: Any% practice"


def test_hash_with_username_lists_followed_channels(twitch, settings):
    settings["username"] = "viewer"
    response = run_query("#")
    assert titles(response) == ["SpeedrunsDaily"]
    assert response["Result"][0]["SubTitle"] == "Daily speedruns"


def test_valid_token_is_kept(twitch, settings):
    response = run_query("speedrun")
    assert response["SettingsChange"] is None
    assert not [call for call in twitch.calls if call[0] == "POST"]


def test_token_is_validated_once_per_hour(twitch, settings):
    run_query("speedrun")
    run_query("cozy")
    validations = [call for call in twitch.calls if call[1] == f"{helix.OAUTH_URL}/validate"]
    assert len(validations) == 1


def test_invalid_token_is_replaced_and_saved(twitch, settings):
    settings["oauth_token"] = "expired"
    response = run_query("speedrun")
    assert response["SettingsChange"] == {"oauth_token": "app-token"}
    assert titles(response) == ["SpeedrunsDaily"]
    token_request = next(call for call in twitch.calls if call[0] == "POST")
    assert token_request[2] == {"client_id": "client", "client_secret": "secret", "grant_type": "client_credentials"}


def test_blank_token_is_fetched_from_client_credentials(twitch, settings):
    settings["oauth_token"] = ""
    assert run_query("speedrun")["SettingsChange"] == {"oauth_token": "app-token"}


@pytest.mark.parametrize("missing", ["client_id", "client_secret"])
def test_missing_credentials_are_reported(twitch, settings, missing):
    settings["oauth_token"] = ""
    settings[missing] = ""
    response = run_query("speedrun")
    assert titles(response) == ["Missing credentials"]
    assert actions(response) == [{"Method": "Flow.Launcher.OpenSettingDialog", "Parameters": [], "DontHideAfterAction": False}]


def test_token_without_client_id_reports_missing_credentials(twitch, settings):
    settings["client_id"] = None
    assert titles(run_query("speedrun")) == ["Missing credentials"]


def test_twitch_error_is_reported(twitch, settings):
    twitch.failing = "search/channels"
    assert titles(run_query("speedrun")) == ["ERROR: Unable to login!"]


def run_context_menu(path):
    return asyncio.run(twitchy.plugin._event_handler.trigger_event("context_menu", [path]))


def test_context_menu_is_empty_without_program(twitch, settings):
    assert run_context_menu("speedrunsdaily")["Result"] == []


def test_context_menu_opens_stream_in_program(twitch, settings):
    settings["program_path"] = r"C:\Tools\mpv\mpv.exe"
    settings["program_args"] = "{url}"
    (result,) = run_context_menu("speedrunsdaily")["Result"]
    assert result["Title"] == "Open Stream in mpv.exe"
    assert result["SubTitle"] == "https://twitch.tv/speedrunsdaily"
    assert result["JsonRPCAction"]["Method"] == "open_program"
    assert result["JsonRPCAction"]["Parameters"] == [r"C:\Tools\mpv\mpv.exe", "https://twitch.tv/speedrunsdaily"]


class FakeStream:
    def __init__(self, url):
        self.url = url


def test_context_menu_resolves_stream_quality_urls(twitch, settings, monkeypatch):
    import streamlink

    monkeypatch.setattr(
        streamlink,
        "streams",
        lambda url: {"best": FakeStream(f"{url}/best.m3u8"), "worst": FakeStream(f"{url}/worst.m3u8")},
    )
    settings["program_path"] = "/usr/bin/mpv"
    settings["program_args"] = "{best} --title {url}"
    (result,) = run_context_menu("speedrunsdaily")["Result"]
    assert result["SubTitle"] == "https://twitch.tv/speedrunsdaily/best.m3u8 --title https://twitch.tv/speedrunsdaily"


def test_open_program_starts_the_program(monkeypatch):
    started = []
    monkeypatch.setattr(twitchy, "Popen", started.append)
    asyncio.run(twitchy.plugin._event_handler.trigger_event("open_program", "/usr/bin/mpv", "https://twitch.tv/x"))
    assert started == [["/usr/bin/mpv", "https://twitch.tv/x"]]
