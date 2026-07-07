"""
Renders the final shareable "wrapped" card as a PNG using Pillow.

Deliberately NOT using a headless browser (Playwright/Puppeteer) here - for a
single, fairly simple card layout, Pillow is far lighter to deploy (no
Chromium binary, works fine on a free-tier instance with 512MB RAM) and gives
full pixel control. If you later want richer layouts (gradients, custom
fonts per section, etc.) swap this for an HTML-to-image render - the
WrappedResult model is already the only input this function needs, so the
swap doesn't touch any other file.
"""
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from app.models import WrappedResult

CARD_W, CARD_H = 1080, 1920  # Instagram Story dimensions - this is the whole point

FONT_DIR = "static/assets/fonts"
COLORS = {
    "takeout": {"bg_top": (20, 18, 38), "bg_bottom": (46, 24, 64), "accent": (208, 168, 255)},
    "taste": {"bg_top": (10, 30, 32), "bg_bottom": (13, 66, 56), "accent": (120, 230, 190)},
    "creator": {"bg_top": (36, 20, 10), "bg_bottom": (75, 40, 15), "accent": (255, 176, 90)},
}


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(f"{FONT_DIR}/Poppins-{name}.ttf", size)


def _vertical_gradient(draw: ImageDraw.Draw, top: tuple, bottom: tuple):
    for y in range(CARD_H):
        t = y / CARD_H
        r = int(top[0] + (bottom[0] - top[0]) * t)
        g = int(top[1] + (bottom[1] - top[1]) * t)
        b = int(top[2] + (bottom[2] - top[2]) * t)
        draw.line([(0, y), (CARD_W, y)], fill=(r, g, b))


def _wrap_text(draw: ImageDraw.Draw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    lines, current = [], ""
    for word in words:
        trial = f"{current} {word}".strip()
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def generate_card(result: WrappedResult, year_label: str = "2026") -> BytesIO:
    palette = COLORS.get(result.path_type, COLORS["takeout"])
    img = Image.new("RGB", (CARD_W, CARD_H), palette["bg_top"])
    draw = ImageDraw.Draw(img)
    _vertical_gradient(draw, palette["bg_top"], palette["bg_bottom"])
    accent = palette["accent"]

    margin = 80
    y = 140

    # Eyebrow label
    draw.text((margin, y), f"YOUR {year_label} YOUTUBE WRAPPED", font=_font("Medium", 34), fill=accent)
    y += 90

    # Persona - the headline moment
    # Note: the persona emoji is deliberately NOT drawn here. Poppins (like most
    # text fonts) has no emoji glyphs, so PIL silently falls back to a blank
    # placeholder box instead of the real character - and on a minimal Linux
    # deploy target there's often no system emoji font to fall back to either.
    # The emoji still comes through fine in the JSON response and renders
    # correctly in the browser reveal, since browsers always ship a real
    # color emoji font. If you want it on the card image too, bundle a color
    # emoji font (e.g. Noto Color Emoji) and draw it as a separate image layer.
    persona_font = _font("Bold", 72)
    for line in _wrap_text(draw, result.persona_name, persona_font, CARD_W - 2 * margin):
        draw.text((margin, y), line, font=persona_font, fill=(255, 255, 255))
        y += 84
    y += 10

    tagline_font = _font("Regular", 36)
    for line in _wrap_text(draw, result.persona_tagline, tagline_font, CARD_W - 2 * margin):
        draw.text((margin, y), line, font=tagline_font, fill=(220, 220, 220))
        y += 48
    y += 60

    # Divider
    draw.line([(margin, y), (CARD_W - margin, y)], fill=accent, width=3)
    y += 60

    # Headline stat - the big number
    draw.text((margin, y), result.headline_stat, font=_font("Bold", 58), fill=(255, 255, 255))
    y += 110

    # Top categories
    if result.top_categories:
        draw.text((margin, y), "TOP CATEGORIES", font=_font("Medium", 30), fill=accent)
        y += 56
        for i, (cat, _count) in enumerate(result.top_categories[:5], start=1):
            draw.text((margin, y), f"{i}.  {cat}", font=_font("Regular", 40), fill=(235, 235, 235))
            y += 58
        y += 30

    # Peak hour fact
    if result.peak_hour_label:
        draw.text(
            (margin, y),
            f"Peak watching hour: {result.peak_hour_label}",
            font=_font("Regular", 32),
            fill=(200, 200, 200),
        )
        y += 60

    # Footer
    footer_y = CARD_H - 100
    draw.text((margin, footer_y), "yourapp.com/wrapped", font=_font("Medium", 28), fill=accent)

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer
