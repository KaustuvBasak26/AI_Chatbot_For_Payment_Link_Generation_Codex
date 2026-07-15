import re
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from dateutil import parser as date_parser

from app.schemas.payment import CustomerDraft, ExtractedPaymentDraft, ItemDraft

NUMBER_WORDS = {
    "a": 1,
    "an": 1,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
}
QUANTITY = r"\d+|a|an|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty"
CURRENCY = r"₹|INR\b|Rs\.?(?=\s|\d)|rupees?\b"
AMOUNT = r"[\d,]+(?:\.\d{1,2})?(?:\s*(?:k|thousand|lakh|lakhs))?"
ITEM_NAME = r"[A-Za-z][A-Za-z0-9/&'’().+\-\s]{0,100}?"

ITEM_PATTERNS = (
    re.compile(
        rf"\b(?P<qty>{QUANTITY})\b\s*[x×]\s*(?P<name>{ITEM_NAME})\s*(?:@|at)?\s*"
        rf"(?P<currency>{CURRENCY})?\s*(?P<price>{AMOUNT})(?:\s*(?:each|per\s+(?:unit|item)))?",
        re.IGNORECASE,
    ),
    re.compile(
        rf"\b(?P<qty>{QUANTITY})\b\s+(?P<name>{ITEM_NAME})\s+"
        rf"(?:at|for|priced\s+at|price\s+of)\s*(?P<currency>{CURRENCY})?\s*(?P<price>{AMOUNT})\s*(?:each|per\s+(?:unit|item))",
        re.IGNORECASE,
    ),
    re.compile(
        rf"\b(?P<qty>{QUANTITY})\b\s+(?P<name>{ITEM_NAME})\s+"
        rf"(?:at|for|priced\s+at|price\s+of)\s*(?P<currency>{CURRENCY})\s*(?P<price>{AMOUNT})(?:\s*(?:each|per\s+(?:unit|item)))?",
        re.IGNORECASE,
    ),
    re.compile(
        rf"\b(?P<qty>{QUANTITY})\b\s+(?P<name>{ITEM_NAME})\s+"
        rf"(?:costing|costs?|@)\s*(?P<currency>{CURRENCY})?\s*(?P<price>{AMOUNT})(?:\s*(?:each|per\s+(?:unit|item)))?",
        re.IGNORECASE,
    ),
    re.compile(
        rf"(?P<currency>{CURRENCY})\s*(?P<price>{AMOUNT})\s*(?:each|per\s+(?:unit|item))?\s+"
        rf"(?:for\s+)?(?P<qty>{QUANTITY})\b\s+(?P<name>{ITEM_NAME})(?=\s*(?:,|\.|;|\band\b|$))",
        re.IGNORECASE,
    ),
    re.compile(
        rf"(?P<name>{ITEM_NAME})\s*[,;:]?\s*(?:quantity|qty)\s*[:=]?\s*(?P<qty>{QUANTITY})\b"
        rf".*?(?:unit\s+price|price|rate)\s*[:=]?\s*(?P<currency>{CURRENCY})?\s*(?P<price>{AMOUNT})",
        re.IGNORECASE,
    ),
)


@dataclass(frozen=True)
class ItemMatch:
    item: ItemDraft
    start: int
    end: int


def parse_quantity(value: str) -> int | None:
    normalized = value.strip().lower()
    return int(normalized) if normalized.isdigit() else NUMBER_WORDS.get(normalized)


def money_to_minor(value: str) -> int | None:
    normalized = value.lower().replace(",", "").strip()
    multiplier = Decimal(1)
    for suffix, factor in (("lakhs", 100_000), ("lakh", 100_000), ("thousand", 1_000), ("k", 1_000)):
        if normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)].strip()
            multiplier = Decimal(factor)
            break
    try:
        return int(Decimal(normalized) * multiplier * 100)
    except (InvalidOperation, ValueError):
        return None


def parse_date(value: str, now: datetime, timezone: ZoneInfo) -> datetime | None:
    clean = value.strip().rstrip(".,").lower()
    if clean in {"today", "end of today"}:
        return datetime.combine(now.date(), time(23, 59, 59), timezone)
    if clean in {"tomorrow", "end of tomorrow"}:
        return datetime.combine(now.date() + timedelta(days=1), time(23, 59, 59), timezone)
    relative_days = re.fullmatch(r"(?:in|after)\s+(\d+)\s+days?", clean)
    if relative_days:
        return datetime.combine(now.date() + timedelta(days=int(relative_days.group(1))), time(23, 59, 59), timezone)
    weekdays = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6}
    weekday_name = clean.removeprefix("next ")
    if weekday_name in weekdays:
        days = (weekdays[weekday_name] - now.weekday()) % 7 or 7
        if clean.startswith("next ") and days < 7:
            days += 7
        return datetime.combine(now.date() + timedelta(days=days), time(23, 59, 59), timezone)
    try:
        parsed = date_parser.parse(clean, dayfirst=True, default=now.replace(hour=23, minute=59, second=59, microsecond=0))
        return parsed.replace(tzinfo=timezone) if parsed.tzinfo is None else parsed.astimezone(timezone)
    except (ValueError, OverflowError):
        return None


def clean_item_name(value: str) -> str:
    name = re.sub(r"\s+", " ", value).strip(" ,.;:-")
    name = re.sub(r"^(?:for|charge|bill|invoice|(?:payment\s+)?request\s+for|create(?:\s+a)?(?:\s+payment)?(?:\s+link)?\s+for)\s+", "", name, flags=re.IGNORECASE)
    return name


def spans_overlap(start: int, end: int, matches: list[ItemMatch]) -> bool:
    return any(start < existing.end and end > existing.start for existing in matches)


def extract_items(text: str) -> list[ItemDraft]:
    search_text = re.sub(
        r"\b(?:(?:create|send|make|generate)\s+)?(?:a\s+)?(?:payment\s+)?(?:request|link)\s+for\s+",
        "",
        text,
        flags=re.IGNORECASE,
    )
    matches: list[ItemMatch] = []
    for pattern in ITEM_PATTERNS:
        for match in pattern.finditer(search_text):
            if spans_overlap(match.start(), match.end(), matches):
                continue
            name = clean_item_name(match.group("name"))
            if not name or name.lower() in {"payment", "link", "deadline", "validity"}:
                continue
            item = ItemDraft(
                name=name,
                quantity=parse_quantity(match.group("qty")),
                unit_price_minor=money_to_minor(match.group("price")),
            )
            matches.append(ItemMatch(item, match.start(), match.end()))

    if not matches:
        partial_quantity = re.search(
            rf"(?<![\d,₹])\b(?P<qty>{QUANTITY})\b\s+(?P<name>[A-Za-z][A-Za-z0-9/&'’().+\- ]{{1,80}}?)(?=\s*(?:,|\.|;|$|\b(?:due|payable|valid|expires?)\b))",
            search_text,
            re.IGNORECASE,
        )
        if partial_quantity:
            partial_name = clean_item_name(partial_quantity.group("name"))
            if partial_name.lower() not in {"day", "days", "week", "weeks", "month", "months", "hours"}:
                matches.append(
                    ItemMatch(
                        ItemDraft(name=partial_name, quantity=parse_quantity(partial_quantity.group("qty"))),
                        partial_quantity.start(),
                        partial_quantity.end(),
                    )
                )
        if not matches:
            partial_price = re.search(
                rf"(?P<name>[A-Za-z][A-Za-z0-9/&'’().+\- ]{{1,80}}?)\s+(?:for|at|costing)\s*(?:{CURRENCY})\s*(?P<price>{AMOUNT})",
                search_text,
                re.IGNORECASE,
            )
            if partial_price:
                matches.append(
                    ItemMatch(
                        ItemDraft(name=clean_item_name(partial_price.group("name")), unit_price_minor=money_to_minor(partial_price.group("price"))),
                        partial_price.start(),
                        partial_price.end(),
                    )
                )
    return [match.item for match in sorted(matches, key=lambda candidate: candidate.start)]


def extract_customer_name(text: str) -> str | None:
    patterns = (
        r"\b(?i:customer|client)\s+(?:(?i:is|named)\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})",
        r"\b(?i:charge|bill)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})(?=\s+(?i:for)\b|\s+(?:₹|INR|Rs\.|rupees?)|[,.'’]|$)",
        r"\b(?i:payment\s+(?:link|request)|invoice)\s+(?i:for)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})(?=\s+(?i:for)\b|\s+(?:₹|INR|Rs\.|rupees?)|[,.'’]|$)",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None


def extract_adjustment(text: str, label: str) -> int | None:
    patterns = (
        rf"\b{label}\s*(?:of|is|:)?\s*(?:{CURRENCY})\s*(?P<amount>{AMOUNT})",
        rf"(?:{CURRENCY})\s*(?P<amount>{AMOUNT})\s+{label}\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return money_to_minor(match.group("amount"))
    return None


class DeterministicExtractor:
    async def extract_payment_request(
        self, user_message: str, conversation_context: list[dict[str, str]], current_date: str, timezone: str
    ) -> ExtractedPaymentDraft:
        zone = ZoneInfo(timezone)
        now = datetime.fromisoformat(current_date).replace(tzinfo=zone) if "T" not in current_date else datetime.fromisoformat(current_date).astimezone(zone)
        text = re.sub(r"[.!?]\s+(?=(?:₹|INR\b|Rs\.|rupees?\b))", " at ", user_message)
        items = extract_items(text)

        email_match = re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text)
        phone_match = re.search(r"(?<!\d)(?:\+91[-\s]?)?[6-9](?:[\s-]?\d){9}(?!\d)", text)

        pay_by = None
        deadline_match = re.search(
            r"(?:due|payable|payment\s+(?:is\s+)?due|pay)\s*(?:by|on|before)?\s+(.+?)(?=\s+and\b|[,.]|$)",
            text,
            re.IGNORECASE,
        )
        if deadline_match:
            pay_by = parse_date(deadline_match.group(1), now, zone)

        validity_match = re.search(
            rf"(?:valid|active|available|lasts?)\s*(?:for)?\s*(?P<days>\d+|{'|'.join(NUMBER_WORDS)})\s+days?",
            text,
            re.IGNORECASE,
        )
        validity_days = parse_quantity(validity_match.group("days")) if validity_match else None
        expiry_match = re.search(
            r"(?:expires?|valid\s+(?:until|till|through)|expiry\s+(?:is|on)?)\s*(?:on|at|by)?\s*(.+?)(?=\s+and\b|[,.]|$)",
            text,
            re.IGNORECASE,
        )
        expires_at = parse_date(expiry_match.group(1), now, zone) if expiry_match else None

        currency = "INR" if re.search(r"₹|\bINR\b|\bRs\.?\b|\brupees?\b", text, re.IGNORECASE) else None
        ambiguities: list[str] = []
        if re.search(r"\b(?:discount|tax|GST)\s*(?:of|is|:)?\s*\d+(?:\.\d+)?\s*%", text, re.IGNORECASE):
            ambiguities.append("Percentage-based tax or discount needs an explicit amount.")
        if re.search(r"\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b", text):
            ambiguities.append("A numeric date is ambiguous; please use a month name.")

        draft = ExtractedPaymentDraft(
            customer=CustomerDraft(
                name=extract_customer_name(text),
                email=email_match.group(0) if email_match else None,
                phone=re.sub(r"[\s-]", "", phone_match.group(0)) if phone_match else None,
            ),
            items=items,
            currency=currency,
            discount_minor=extract_adjustment(text, "discount") or 0,
            tax_minor=extract_adjustment(text, "(?:tax|GST)") or 0,
            pay_by=pay_by,
            expires_at=expires_at,
            validity_days=validity_days,
            ambiguities=ambiguities,
        )
        draft.missing_fields = required_missing_fields(draft)
        return draft


def required_missing_fields(draft: ExtractedPaymentDraft) -> list[str]:
    missing: list[str] = []
    if not draft.items:
        missing.append("items")
    for index, item in enumerate(draft.items):
        if not item.name:
            missing.append(f"items.{index}.name")
        if item.quantity is None:
            missing.append(f"items.{index}.quantity")
        if item.unit_price_minor is None:
            missing.append(f"items.{index}.unit_price_minor")
    if not draft.currency:
        missing.append("currency")
    if not draft.expires_at and not draft.validity_days:
        missing.append("expiration")
    return missing
