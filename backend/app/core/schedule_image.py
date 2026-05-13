"""Generate a weekly schedule image for WhatsApp distribution."""
import io
import os
from datetime import date, timedelta

FONT_PATH = "/tmp/NotoSansHebrew-Regular.ttf"
FONT_URL = "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansHebrew/NotoSansHebrew-Regular.ttf"

DAY_NAMES = ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"]
SHIFT_LABEL = {"morning": "בוקר 🌅", "evening": "ערב 🌆"}
SHIFT_COLOR = {"morning": (29, 78, 216), "evening": (124, 58, 237)}


async def ensure_font() -> bool:
    if os.path.exists(FONT_PATH):
        return True
    try:
        import httpx
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(FONT_URL)
            if resp.status_code == 200:
                with open(FONT_PATH, "wb") as f:
                    f.write(resp.content)
                return True
    except Exception as e:
        print(f"[schedule_image] Font download failed: {e}", flush=True)
    return False


def _rtl(text: str) -> str:
    try:
        from bidi.algorithm import get_display
        return get_display(text)
    except Exception:
        return text


def generate_schedule_image(
    week_start: date,
    shifts_by_day: dict,
    operating_days: list[int],
) -> bytes:
    """
    shifts_by_day: {date_str: {"morning": [name1, name2], "evening": [name1]}}
    Returns PNG bytes.
    """
    from PIL import Image, ImageDraw, ImageFont

    # ── Fonts ──────────────────────────────────────────────────────────────────
    def load_font(size):
        if os.path.exists(FONT_PATH):
            try:
                return ImageFont.truetype(FONT_PATH, size)
            except Exception:
                pass
        return ImageFont.load_default()

    font_title  = load_font(26)
    font_header = load_font(18)
    font_body   = load_font(16)
    font_small  = load_font(13)

    # ── Layout ────────────────────────────────────────────────────────────────
    PAD        = 24
    TITLE_H    = 60
    COL_DAY    = 110
    COL_SHIFT  = 230
    ROW_H      = 70
    n_days     = len(operating_days)
    IMG_W      = PAD * 2 + COL_DAY + COL_SHIFT * 2
    IMG_H      = PAD * 2 + TITLE_H + ROW_H * (n_days + 1)  # +1 for header row

    img  = Image.new("RGB", (IMG_W, IMG_H), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # ── Title ─────────────────────────────────────────────────────────────────
    week_end  = week_start + timedelta(days=6)
    title_txt = _rtl(f"סידור שבוע  {week_start.strftime('%d/%m')} – {week_end.strftime('%d/%m')}")
    draw.rectangle([0, 0, IMG_W, TITLE_H], fill=(79, 70, 229))
    draw.text((IMG_W // 2, TITLE_H // 2), title_txt, fill="white",
              font=font_title, anchor="mm")

    # ── Header row ────────────────────────────────────────────────────────────
    y = TITLE_H + PAD // 2
    draw.rectangle([PAD, y, IMG_W - PAD, y + ROW_H], fill=(238, 242, 255))

    # Columns (RTL order: right=day, middle=morning, left=evening)
    x_day     = IMG_W - PAD - COL_DAY // 2
    x_morning = PAD + COL_SHIFT + COL_SHIFT // 2
    x_evening = PAD + COL_SHIFT // 2

    cy = y + ROW_H // 2
    draw.text((x_day,     cy), _rtl("יום"),   fill=(55, 65, 81),  font=font_header, anchor="mm")
    draw.text((x_morning, cy), _rtl("בוקר"),  fill=(29, 78, 216), font=font_header, anchor="mm")
    draw.text((x_evening, cy), _rtl("ערב"),   fill=(124, 58, 237), font=font_header, anchor="mm")
    draw.line([PAD, y + ROW_H, IMG_W - PAD, y + ROW_H], fill=(209, 213, 219), width=1)

    y += ROW_H

    # ── Day rows ──────────────────────────────────────────────────────────────
    for i, day_idx in enumerate(operating_days):
        day_date = week_start + timedelta(days=day_idx)
        day_str  = day_date.isoformat()
        bg       = (248, 250, 252) if i % 2 == 0 else (255, 255, 255)
        draw.rectangle([PAD, y, IMG_W - PAD, y + ROW_H], fill=bg)

        cy = y + ROW_H // 2

        # Day label
        day_label = _rtl(DAY_NAMES[day_idx])
        date_label = day_date.strftime("%d/%m")
        draw.text((x_day, cy - 10), day_label,  fill=(31, 41, 55), font=font_body,  anchor="mm")
        draw.text((x_day, cy + 10), date_label, fill=(107, 114, 128), font=font_small, anchor="mm")

        # Morning employees
        morning = shifts_by_day.get(day_str, {}).get("morning", [])
        m_text  = _rtl(", ".join(morning)) if morning else "—"
        draw.text((x_morning, cy), m_text, fill=(29, 78, 216) if morning else (156, 163, 175),
                  font=font_body, anchor="mm")

        # Evening employees
        evening = shifts_by_day.get(day_str, {}).get("evening", [])
        e_text  = _rtl(", ".join(evening)) if evening else "—"
        draw.text((x_evening, cy), e_text, fill=(124, 58, 237) if evening else (156, 163, 175),
                  font=font_body, anchor="mm")

        draw.line([PAD, y + ROW_H, IMG_W - PAD, y + ROW_H], fill=(229, 231, 235), width=1)
        y += ROW_H

    # ── Outer border ──────────────────────────────────────────────────────────
    draw.rectangle([PAD, TITLE_H + PAD // 2, IMG_W - PAD, y],
                   outline=(209, 213, 219), width=2)

    # ── Vertical dividers ─────────────────────────────────────────────────────
    x_div1 = PAD + COL_SHIFT
    x_div2 = PAD + COL_SHIFT * 2
    top    = TITLE_H + PAD // 2
    draw.line([x_div1, top, x_div1, y], fill=(209, 213, 219), width=1)
    draw.line([x_div2, top, x_div2, y], fill=(209, 213, 219), width=1)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
