from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Any, Generic, TypeVar

from wagtail.models import Page  # type: ignore

from home.models import (
    ContentPage,
    ContentPageIndex,
    MessengerBlock,
    ViberBlock,
    WhatsappBlock,
)

TPage = TypeVar("TPage", bound=Page)


@dataclass
class ContentBlock(ABC):
    message: str

    @abstractmethod
    def to_body(self) -> Any:
        ...


TCBlk = TypeVar("TCBlk", bound=ContentBlock)


@dataclass
class ContentBody(ABC, Generic[TCBlk]):
    ATTR_STR = "REPLACEME"

    title: str
    blocks: list[ContentBlock]
    enable: bool = True

    def set_on(self, page: ContentPage) -> None:
        setattr(page, f"enable_{self.ATTR_STR}", self.enable)
        setattr(page, f"{self.ATTR_STR}_title", self.title)
        page_body = getattr(page, f"{self.ATTR_STR}_body")
        for body in self.blocks:
            page_body.append(body.to_body())


@dataclass
class WABlk(ContentBlock):
    # TODO: More body things.

    def to_body(self) -> Any:
        return ("Whatsapp_Message", WhatsappBlock().to_python(asdict(self)))


@dataclass
class MBlk(ContentBlock):
    # TODO: More body things.

    def to_body(self) -> Any:
        return ("messenger_block", MessengerBlock().to_python(asdict(self)))


@dataclass
class VBlk(ContentBlock):
    # TODO: More body things.

    def to_body(self) -> Any:
        return ("viber_message", ViberBlock().to_python(asdict(self)))


class WABody(ContentBody[WABlk]):
    ATTR_STR = "whatsapp"


class MBody(ContentBody[MBlk]):
    ATTR_STR = "messenger"


class VBody(ContentBody[VBlk]):
    ATTR_STR = "viber"


class PageBuilder(Generic[TPage]):
    """
    Builder for various Page objects.
    """

    page: TPage
    parent: Page

    def __init__(self, parent: Page, slug: str, title: str, page_type: TPage):
        self.parent = parent
        self.page = page_type(title=title, slug=slug)

    @classmethod
    def cpi(
        cls, parent: Page, slug: str, title: str
    ) -> "PageBuilder[ContentPageIndex]":
        return cls(parent, slug, title, page_type=ContentPageIndex)

    @classmethod
    def cp(cls, parent: Page, slug: str, title: str) -> "PageBuilder[ContentPage]":
        return cls(parent, slug, title, page_type=ContentPage)

    @classmethod
    def build_cpi(cls, parent: Page, slug: str, title: str) -> ContentPageIndex:
        return cls.cpi(parent, slug, title).build()

    @classmethod
    def build_cp(
        cls, parent: Page, slug: str, title: str, bodies: list[ContentBody[TCBlk]]
    ) -> ContentPage:
        return cls.cp(parent, slug, title).add_bodies(*bodies).build()

    def build(self, publish: bool = True) -> TPage:
        self.parent.add_child(instance=self.page)
        rev = self.page.save_revision()
        if publish:
            rev.publish()
        return self.page

    def add_bodies(self, *bodies: ContentBody[TCBlk]) -> "PageBuilder[TPage]":
        for body in bodies:
            body.set_on(self.page)
        return self
