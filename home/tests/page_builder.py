from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from typing import Any, ClassVar, Generic, TypeVar

from taggit.models import Tag  # type: ignore
from wagtail.blocks import RichTextBlock, StructBlock  # type: ignore
from wagtail.models import Page  # type: ignore

from home.models import (
    ContentPage,
    ContentPageIndex,
    ContentQuickReply,
    ContentTrigger,
    MessengerBlock,
    ViberBlock,
    WhatsappBlock,
)

TPage = TypeVar("TPage", bound=Page)


@dataclass
class VarMsg:
    message: str
    # Variation restrictions:
    gender: str | None = None
    age: str | None = None
    relationship: str | None = None

    def variations(self) -> Iterable[dict[str, str]]:
        if self.gender:
            yield {"type": "gender", "value": self.gender}
        if self.age:
            yield {"type": "age", "value": self.age}
        if self.relationship:
            yield {"type": "relationship", "value": self.relationship}

    def to_dict(self) -> Any:
        return {"message": self.message, "variation_restrictions": self.variations()}


@dataclass
class ContentBlock:
    BLOCK_TYPE_STR: ClassVar[str]
    BLOCK_TYPE: ClassVar[type[StructBlock]]

    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_block(self) -> Any:
        return (self.BLOCK_TYPE_STR, self.BLOCK_TYPE().to_python(self.to_dict()))


TCBlk = TypeVar("TCBlk", bound=ContentBlock, covariant=True)


@dataclass
class ContentBody(Generic[TCBlk]):
    ATTR_STR: ClassVar[str]
    title: str
    blocks: list[TCBlk]
    enable: bool = True

    def set_on(self, page: ContentPage) -> None:
        setattr(page, f"enable_{self.ATTR_STR}", self.enable)
        setattr(page, f"{self.ATTR_STR}_title", self.title)
        page_body = getattr(page, f"{self.ATTR_STR}_body")
        for body in self.blocks:
            page_body.append(body.to_block())


@dataclass
class WABlk(ContentBlock):
    BLOCK_TYPE_STR = "Whatsapp_Message"
    BLOCK_TYPE = WhatsappBlock

    # TODO: More body things.
    variation_messages: list[VarMsg] = field(default_factory=list)
    next_prompt: str | None = None

    def to_dict(self) -> dict[str, Any]:
        varmsgs = [vm.to_dict() for vm in self.variation_messages]
        return asdict(self) | {"variation_messages": varmsgs}


@dataclass
class MBlk(ContentBlock):
    BLOCK_TYPE_STR = "messenger_block"
    BLOCK_TYPE = MessengerBlock

    # TODO: More body things.


@dataclass
class VBlk(ContentBlock):
    BLOCK_TYPE_STR = "viber_message"
    BLOCK_TYPE = ViberBlock

    # TODO: More body things.


class WABody(ContentBody[WABlk]):
    ATTR_STR = "whatsapp"


class MBody(ContentBody[MBlk]):
    ATTR_STR = "messenger"


class VBody(ContentBody[VBlk]):
    ATTR_STR = "viber"


class PageBuilder(Generic[TPage]):
    """
    Builder for various Page objects.

    NOTE: Related pages need to be linked after all relevant pages are saved,
        so that's handled separately.
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
    def build_cpi(
        cls,
        parent: Page,
        slug: str,
        title: str,
        translated_from: ContentPageIndex | None = None,
    ) -> ContentPageIndex:
        builder = cls.cpi(parent, slug, title)
        if translated_from:
            builder = builder.translated_from(translated_from)
        return builder.build()

    @classmethod
    def build_cp(
        cls,
        parent: Page,
        slug: str,
        title: str,
        bodies: Iterable[ContentBody[TCBlk]],
        web_body: Iterable[str] | None = None,
        tags: Iterable[str] | None = None,
        triggers: Iterable[str] | None = None,
        quick_replies: Iterable[str] | None = None,
        translated_from: ContentPage | None = None,
    ) -> ContentPage:
        builder = cls.cp(parent, slug, title).add_bodies(*bodies)
        if web_body:
            builder = builder.add_web_body(*web_body)
        if tags:
            builder = builder.add_tags(*tags)
        if triggers:
            builder = builder.add_triggers(*triggers)
        if quick_replies:
            builder = builder.add_quick_replies(*quick_replies)
        if translated_from:
            builder = builder.translated_from(translated_from)
        return builder.build()

    def build(self, publish: bool = True) -> TPage:
        self.parent.add_child(instance=self.page)
        rev = self.page.save_revision()
        if publish:
            rev.publish()
        # The page instance is out of date after revision operations, so reload.
        self.page.refresh_from_db()
        return self.page

    def add_web_body(self, *paragraphs: str) -> "PageBuilder[TPage]":
        # TODO: Support images?
        self.page.enable_web = True
        for paragraph in paragraphs:
            self.page.body.append(("paragraph", RichTextBlock().to_python(paragraph)))
        return self

    def add_bodies(self, *bodies: ContentBody[TCBlk]) -> "PageBuilder[TPage]":
        for body in bodies:
            body.set_on(self.page)
        return self

    def add_tags(self, *tag_strs: str) -> "PageBuilder[TPage]":
        for tag_str in tag_strs:
            tag, _ = Tag.objects.get_or_create(name=tag_str)
            self.page.tags.add(tag)
        return self

    def add_triggers(self, *trigger_strs: str) -> "PageBuilder[TPage]":
        for trigger_str in trigger_strs:
            trigger, _ = ContentTrigger.objects.get_or_create(name=trigger_str)
            self.page.triggers.add(trigger)
        return self

    def add_quick_replies(self, *qr_strs: str) -> "PageBuilder[TPage]":
        for qr_str in qr_strs:
            qr, _ = ContentQuickReply.objects.get_or_create(name=qr_str)
            self.page.quick_replies.add(qr)
        return self

    def translated_from(self, page: TPage) -> "PageBuilder[TPage]":
        self.page.translation_key = page.translation_key
        return self

    @staticmethod
    def link_related(
        page: ContentPage, related_pages: Iterable[Page], publish: bool = True
    ) -> ContentPage:
        for related_page in related_pages:
            page.related_pages.append(("related_page", related_page))
        rev = page.save_revision()
        if publish:
            rev.publish()
        page.refresh_from_db()
        return page
