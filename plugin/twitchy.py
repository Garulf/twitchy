import os
import tempfile
import webbrowser

from flox import Flox, ICON_SETTINGS, ICON_APP_ERROR, ICON_CANCEL
import requests
from twitch import TwitchClient, client

# from streamlink import streams

from requests.exceptions import HTTPError

LIMIT = 10
FILTER_CHAR = ":"
GAMES_KEYWORD = "games"


class Twitchy(Flox):
    def __init__(self):
        super().__init__()
        self.client = TwitchClient(self.settings.get("client_id"))
        self.logger.warning(self.settings.get("client_id"))
        try:
            self.client.ingests.get_server_list()
        except HTTPError:
            pass

    def query(self, query):
        if query != "":
            channels = self.client.search.channels(query, limit=LIMIT)
            for channel in channels:
                self.add_item(
                    title=channel['display_name'],
                    subtitle=channel['name'],
                )