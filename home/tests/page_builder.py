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
    SMSBlock,
    USSDBlock,
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
class Btn:
    BLOCK_TYPE_STR: ClassVar[str]

    title: str

    def value_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.BLOCK_TYPE_STR, "value": self.value_dict()}


@dataclass
class NextBtn(Btn):
    BLOCK_TYPE_STR = "next_message"


@dataclass
class PageBtn(Btn):
    BLOCK_TYPE_STR = "go_to_page"

    page: Page

    def value_dict(self) -> dict[str, Any]:
        return asdict(self) | {"page": self.page.id}


@dataclass
class ContentBlock:
    BLOCK_TYPE_STR: ClassVar[str]
    BLOCK_TYPE: ClassVar[type[StructBlock]]

    message: str
    image: int | None = None

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
    next_prompt: str | None = None
    variation_messages: list[VarMsg] = field(default_factory=list)
    example_values: list[str] = field(default_factory=list)
    buttons: list[Btn] = field(default_factory=list)
    list_items: list[str] = field(default_factory=list)
    media: int | None = None
    footer: str = ""

    def to_dict(self) -> dict[str, Any]:
        varmsgs = [vm.to_dict() for vm in self.variation_messages]
        buttons = [b.to_dict() for b in self.buttons]
        return super().to_dict() | {"variation_messages": varmsgs, "buttons": buttons}


@dataclass
class SBlk(ContentBlock):
    BLOCK_TYPE_STR = "SMS_Message"
    BLOCK_TYPE = SMSBlock

    # TODO: More body things.


@dataclass
class MBlk(ContentBlock):
    BLOCK_TYPE_STR = "messenger_block"
    BLOCK_TYPE = MessengerBlock

    # TODO: More body things.


@dataclass
class UBlk(ContentBlock):
    BLOCK_TYPE_STR = "USSD_Message"
    BLOCK_TYPE = USSDBlock

    # TODO: More body things.


@dataclass
class VBlk(ContentBlock):
    BLOCK_TYPE_STR = "viber_message"
    BLOCK_TYPE = ViberBlock

    # TODO: More body things.


class WABody(ContentBody[WABlk]):
    ATTR_STR = "whatsapp"


class SBody(ContentBody[SBlk]):
    ATTR_STR = "sms"


class UBody(ContentBody[UBlk]):
    ATTR_STR = "ussd"


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
        whatsapp_template_name: str | None = None,
        whatsapp_template_category: str | None = None,
        translated_from: ContentPage | None = None,
        publish: bool = True,
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
        if whatsapp_template_name:
            builder = builder.set_whatsapp_template_name(whatsapp_template_name)
        if whatsapp_template_category:
            builder = builder.set_whatsapp_template_category(whatsapp_template_category)
        if translated_from:
            builder = builder.translated_from(translated_from)
        return builder.build(publish=publish)

    def build(self, publish: bool = True) -> TPage:
        self.parent.add_child(instance=self.page)
        rev = self.page.save_revision()
        if publish:
            rev.publish()
        else:
            self.page.unpublish()
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

    def set_whatsapp_template_name(self, name: str) -> "PageBuilder[TPage]":
        self.page.is_whatsapp_template = True
        self.page.whatsapp_template_name = name
        return self

    def set_whatsapp_template_category(self, category: str) -> "PageBuilder[TPage]":
        self.page.is_whatsapp_template = True
        self.page.whatsapp_template_category = category
        return self

    def translated_from(self, page: TPage) -> "PageBuilder[TPage]":
        self.page.translation_key = page.translation_key
        return self

    @staticmethod
    def link_related(
        page: ContentPage, related_pages: Iterable[Page], publish: bool = True
    ) -> ContentPage:
        for related_page in related_pages:
            # If we don't fetch all existing related pages before adding new
            # ones, we get an inexplicable TypeError deep in the bowels of
            # wagtail/blocks/stream_block.py. Good going, wagtail.
            list(page.related_pages)
            page.related_pages.append(("related_page", related_page))
        rev = page.save_revision()
        if publish:
            rev.publish()
        page.refresh_from_db()
        return page
