"""Request and response schemas. The contract between phone and server."""

from typing import Literal

from pydantic import BaseModel, Field

Mode = Literal["auto", "document", "fixit", "nutrition", "translate"]
ALLOWED_MEDIA = {"image/jpeg", "image/png", "image/webp", "image/gif"}


class Source(BaseModel):
    title: str = ""
    url: str


class ScanRequest(BaseModel):
    mode: Mode = "auto"
    media_type: str = Field(default="image/jpeg")
    image_base64: str = Field(min_length=100)
    note: str = Field(default="", max_length=500)
    web_search: bool = False

    def model_post_init(self, __context) -> None:
        if self.media_type not in ALLOWED_MEDIA:
            raise ValueError(f"media_type must be one of {sorted(ALLOWED_MEDIA)}")


class ScanResult(BaseModel):
    category: str
    title: str
    confidence: Literal["high", "medium", "low"]
    summary: str
    steps: list[str] = []
    warnings: list[str] = []
    followUp: list[str] = []
    sources: list[Source] = []


Tab = Literal["cook", "ask"]


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    text: str = Field(default="", max_length=4000)
    image_base64: str | None = Field(default=None, min_length=100)
    media_type: str | None = None

    def model_post_init(self, __context) -> None:
        if self.image_base64 is not None:
            if self.role != "user":
                raise ValueError("images are only allowed on user messages")
            if self.media_type not in ALLOWED_MEDIA:
                raise ValueError(f"media_type must be one of {sorted(ALLOWED_MEDIA)}")


class ChatRequest(BaseModel):
    tab: Tab = "ask"
    web_search: bool = False
    messages: list[ChatMessage] = Field(min_length=1, max_length=30)

    def model_post_init(self, __context) -> None:
        if sum(1 for m in self.messages if m.image_base64 is not None) > 2:
            raise ValueError("at most 2 images per request")


class DishCard(BaseModel):
    id: str
    name: str
    cuisine: str = ""
    minutes: int = 0
    serves: int = 0
    difficulty: str = ""
    have: list[str] = []
    nice_to_add: list[str] = []


class RecipeIngredient(BaseModel):
    item: str
    amount: str = ""


class Recipe(BaseModel):
    name: str
    cuisine: str = ""
    minutes: int = 0
    serves: int = 0
    ingredients: list[RecipeIngredient] = []
    steps: list[str] = []


class ChatReply(BaseModel):
    message: str
    dishes: list[DishCard] = []
    recipe: Recipe | None = None
    chips: list[str] = []
    goal: str = ""
    sources: list[Source] = []
