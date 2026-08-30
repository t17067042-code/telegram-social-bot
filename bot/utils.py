import html
import re
from datetime import timedelta

TIME_RE = re.compile(
    r"(\d+)\s*(сек|секунд|с|мин|минут|м|ч|час|часа|часов|д|день|дня|дней)",
    re.I,
)

def parse_time(text):
    m = TIME_RE.search(text.lower())
    if not m:
        return None
    amount = int(m.group(1))
    unit = m.group(2)
    if unit in {"сек", "секунд", "с"}:
        return timedelta(seconds=amount)
    if unit in {"мин", "минут", "м"}:
        return timedelta(minutes=amount)
    if unit in {"ч", "час", "часа", "часов"}:
        return timedelta(hours=amount)
    return timedelta(days=amount)

def level_from_xp(xp):
    return max(1, xp // 100 + 1)

def esc(value):
    return html.escape(str(value or ""))

def target_from_reply(update):
    if update.message and update.message.reply_to_message:
        return update.message.reply_to_message.from_user
    return None
