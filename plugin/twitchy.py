import sys
from flox import Flox, utils, ICON_APP_ERROR
from twitch import TwitchHelix
from twitch.exceptions import TwitchOAuthException
from itertools import islice

from .item import ChannelItem, GameItem, UserItem, StreamItem


from requests.exceptions import HTTPError


LIMIT = 10
TEN_MINUTES = '600'
MAX_THREAD_WORKERS = 10
BASE_URL = 'https://twitch.tv'


class Twitchy(Flox):
    def __init__(self):
        super().__init__()
        self.oauth_token = self.settings.get("oauth_token")
        self.client_id = self.settings.get("client_id")
        self.client_secret = self.settings.get("client_secret")
        self.username = self.settings.get("username")
        self.client = TwitchHelix(
            client_id=self.client_id, client_secret=self.client_secret, oauth_token=self.oauth_token
        )
        if not self.oauth_token or not self.client.validate_token():
            self.logger.debug("Attempting to refresh blank or invalid token.")
            try:
                self.oauth_token = self.client.get_oauth()
            except TwitchOAuthException:
                self.logger.error("Missing credentials")
                self.add_item(
                    title="Missing credentials",
                    subtitle="Please set your credentials in the settings",
                    icon=ICON_APP_ERROR
                )
                sys.exit(0)
            self.settings["oauth_token"] = self.client._oauth_token
            self.logger.debug(f"New OAUTH token assigned: {self.client._oauth_token[0:4]}{'x' * 10}")



    def _query(self, query):
        try:
            self.query(query)
        except HTTPError as e:
            self.logger.exception(e)
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
            elif query.startswith('#'):
                _iterator = self.follows()
                item_obj = UserItem
                limit = 100
            elif query != '':
                _iterator = self.client.search_channels(query=query)
                item_obj = ChannelItem
                limit = LIMIT
            else:
                _iterator = self.live_streams()
                item_obj = StreamItem
                limit = 100
            for item in islice(_iterator, 0, limit or LIMIT):
                self.add_item(**item_obj(
                    item,
                    cache_name=self.name,
                    method=self.open_channel,
                    executor=executor
                ).as_dict()
                )

    def get_user_id(self, username):
        return self.client.get_users(login_names=[username])[0]['id']

    def get_following_ids(self, id):
        return [follow['to_id'] for follow in self.client.get_user_follows(from_id=id, page_size=100)]

    def follows(self):
        id = self.get_user_id(self.username)
        following_ids = self.get_following_ids(id)
        return self.client.get_users(ids=following_ids)

    def live_streams(self):
        id = self.get_user_id(self.username)
        following_ids = self.get_following_ids(id)
        return self.client.get_streams(user_ids=following_ids)

    def open_channel(self, path):
        self.logger.warning(f"Opening channel {path}")
        self.browser_open(f"{BASE_URL}/{path}")
