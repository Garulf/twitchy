from flox import Flox, utils, ICON_APP_ERROR
from twitch import TwitchClient

from requests.exceptions import HTTPError


LOGO_300 = '300x300'
LOGO_50 = '50x50'
LOGO_28 = '28x28'
LIMIT = 10
FILTER_CHAR = ":"
GAMES_KEYWORD = "games"
TEN_MINUTES = '600'
MAX_THREAD_WORKERS = 10


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
            with utils.ThreadPoolExecutor(max_workers=MAX_THREAD_WORKERS) as executor:
                if query == "":
                    featured_streams = self.client.streams.get_featured(5)
                    for stream in featured_streams:
                        self.channel_result(executor, stream['stream']['channel'], live=True)
                else:
                    channels = self.client.search.channels(query, limit=LIMIT)
                    # This gets us a list of live streams
                    streams = self.client.search.streams(query, limit=LIMIT)
                    for channel in channels:
                        self.channel_result(executor, channel, streams)

        except HTTPError as e:
            self.add_item(
                title="Something went wrong!",
                subtitle="Please double check your Client ID or internet connection.",
                icon=ICON_APP_ERROR,
            )
            self.logger.error(e)

    def channel_result(self, executor, channel, streams=[], live=None):
        subtitle = channel['description']
        if live is None:
            live = is_live(channel, streams)
        if live:
            subtitle = f"[LIVE] {channel['status']}"
        img = channel['logo'].replace(LOGO_300, LOGO_28)
        icon = utils.get_icon(img, self.name, file_name=f"{channel['id']}.png", executor=executor)
        url = channel['url']
        self.add_item(
            title=channel['display_name'],
            subtitle=subtitle,
            icon=icon,
            method=self.browser_open,
            parameters=[url],
        )