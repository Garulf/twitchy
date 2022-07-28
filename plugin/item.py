from abc import ABC, abstractmethod, abstractproperty
from flox import utils

THUMBNAIL_SIZES = {
    "largest": "600x600",
    "large": "300x300",
    "medium": "150x150",
    "small": "70x70",
    "smaller": "50x50",
    "smallest": "28x28"
}

THUMBNAIL_SIZE_VAR = '{width}x{height}'
DEFAULT_THUMBNAIL_SIZE = THUMBNAIL_SIZES["large"]

class ResultItem(ABC):
    def __init__(self, data:dict, cache_name:str, method:callable, executor:utils.ThreadPoolExecutor):
        self.data = data
        self.executor = executor
        self.method = method
        self.cache_name = cache_name

    @abstractproperty
    def icon(self):
        pass

    @abstractproperty
    def title(self):
        pass

    @abstractproperty
    def subtitle(self):
        pass

    @abstractproperty
    def parameters(self):
        pass

    @abstractproperty
    def thumbnail(self):
        pass


    def get_thumbnail(self, size:str=DEFAULT_THUMBNAIL_SIZE):
        if size not in THUMBNAIL_SIZES:
            raise ValueError(f"{size} is not a valid thumbnail size")
        if THUMBNAIL_SIZE_VAR in self.thumbnail:
            return self.thumbnail.format(width=THUMBNAIL_SIZES[size].split('x')[0], height=THUMBNAIL_SIZES[size].split('x')[1])
        return self.thumbnail.replace(DEFAULT_THUMBNAIL_SIZE, THUMBNAIL_SIZES[size])

    def as_dict(self):
        return {
            "icon": self.icon,
            "title": self.title,
            "subtitle": self.subtitle,
            "method": self.method,
            "parameters": self.parameters
        }

class ChannelItem(ResultItem):
    @property
    def icon(self) -> str:
        thumbnail = self.get_thumbnail("smallest")
        file = thumbnail.split('/')[-1]
        return utils.get_icon(thumbnail, self.cache_name, file, executor=self.executor)

    @property
    def thumbnail(self):
        return self.data.get("thumbnail_url", "")

    @property
    def title(self) -> str:
        return self.data.get("display_name")

    @property
    def subtitle(self) -> str:
        if self.data.get("is_live"):
            return f"{self.data.get('game_name')} - {self.data.get('title')}"
        return "Offline"

    @property
    def path(self):
        return self.data.get("broadcaster_login", '')

    @property
    def parameters(self) -> list:
        return [self.path]

class GameItem(ChannelItem):
    
    @property
    def thumbnail(self):
        return self.data.get("box_art_url", "").replace('{width}x{height}', DEFAULT_THUMBNAIL_SIZE)

    @property
    def title(self) -> str:
        return self.data.get("name")

    @property
    def subtitle(self) -> str:
        return "Game"

    @property
    def path(self):
        name = self.data.get("name")
        return f'directory/game/{name}'

class UserItem(ResultItem):

    @property
    def title(self) -> str:
        return self.data.get("display_name")

    @property
    def subtitle(self) -> str:
        return self.data.get("description")

    @property
    def thumbnail(self):
        return self.data.get("profile_image_url", "")

    @property
    def icon(self) -> str:
        thumbnail = self.get_thumbnail("smallest")
        file = thumbnail.split('/')[-1]
        return utils.get_icon(thumbnail, self.cache_name, file, executor=self.executor)

    @property
    def parameters(self) -> list:
        return [self.data.get("login")]

class StreamItem(ResultItem):

    @property
    def title(self) -> str:
        return self.data.get("user_name")

    @property
    def subtitle(self) -> str:
        game = self.data.get("game_name")
        title = self.data.get("title")
        return f"{game}: {title}"

    @property
    def thumbnail(self):
        return self.data.get("thumbnail_url", "")

    @property
    def icon(self) -> str:
        thumbnail = self.get_thumbnail("smallest")
        file = thumbnail.split('/')[-1]
        return utils.get_icon(thumbnail, self.cache_name, file, executor=self.executor)

    @property
    def parameters(self) -> list:
        return [self.data.get("user_login")]