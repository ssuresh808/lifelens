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
