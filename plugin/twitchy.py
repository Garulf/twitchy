from flox import Flox, utils, ICON_APP_ERROR
from twitch import TwitchClient

from requests.exceptions import HTTPError


LOGO_300 = '300x300'
LOGO_50 = '50x50'
LOGO_28 = '28x28'
LIMIT = 10
FILTER_CHAR = ":"
GAMES_KEYWORD = "games"


def is_live(channel, streams):
    for stream in streams:
        if channel['id'] == stream['channel']['id']:
            return True
    return False

class Twitchy(Flox):
    def __init__(self):
        super().__init__()
        self.client = TwitchClient(self.settings.get("client_id"))

    def query(self, query):
        try:
            if query != "":
                channels = self.client.search.channels(query, limit=LIMIT)
                # This gets us a list of live streams
                streams = self.client.search.streams(query, limit=LIMIT)
                for channel in channels:
                    self.result(channel, streams)
 
        except HTTPError as e:
            self.add_item(
                title="Something went wrong!",
                subtitle="Please double check your Client ID or internet connection.",
                icon=ICON_APP_ERROR,
            )
            self.logger.error(e)

    def result(self, channel, streams):
        subtitle = channel['description']
        if is_live(channel, streams):
            subtitle = f"[LIVE] {channel['status']}"
        img = channel['logo'].replace(LOGO_300, LOGO_28)
        icon = utils.get_icon(img, self.name, file_name=f"{channel['id']}.png")
        url = channel['url']
        self.add_item(
            title=channel['display_name'],
            subtitle=subtitle,
            icon=icon,
            method=self.browser_open,
            parameters=[url],
        )