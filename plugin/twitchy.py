from flox import Flox, utils, ICON_APP_ERROR
from twitch import TwitchHelix
from itertools import islice

from .item import ChannelItem, GameItem


from requests.exceptions import HTTPError


LIMIT = 10
TEN_MINUTES = '600'
MAX_THREAD_WORKERS = 10
BASE_URL = 'https://twitch.tv'


class Twitchy(Flox):
    def __init__(self):
        super().__init__()
        self.client = TwitchHelix(
            client_id=self.settings.get("client_id"), oauth_token=self.settings.get("oauth_token")
        )
        # self.username = self.settings.get("username")

    def _query(self, query):
        try:
            self.query(query)
        except HTTPError as e:
            self.add_item(
                title='ERROR: Unable to login!',
                subtitle="Please check your Client ID and OAuth token in settings.",
                method=self.open_setting_dialog
            )

    def query(self, query):
        limit = None
        with utils.ThreadPoolExecutor(max_workers=MAX_THREAD_WORKERS) as executor:
            if query.startswith(':'):
                _iterator = self.client.get_top_games(page_size=100)
                limit = 50
                if len(query) > 1:
                    _iterator = (i for i in islice(_iterator, 0, 5000) if query[1:].lower() in i['name'].lower())
                item_obj = GameItem
            elif query != '':
                _iterator = self.client.search_channels(query=query)
                item_obj = ChannelItem
                limit = LIMIT
            else:
                return []
            for item in islice(_iterator, 0, limit or LIMIT):
                self.add_item(**item_obj(
                    item,
                    cache_name=self.name,
                    method=self.open_channel,
                    executor=executor
                ).as_dict()
                )

    def open_channel(self, path):
        self.logger.warning(f"Opening channel {path}")
        self.browser_open(f"{BASE_URL}/{path}")
