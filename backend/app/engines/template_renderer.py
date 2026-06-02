"""Visual template renderer — generates template frames/images for video composition.

Renders 5 template types to PNG/MP4 using Pillow:
- photo_card: Blurred poster background + title/subtitle overlay
- emotion_card: Gradient background + emoji + emotion text
- split_comparison: Two-panel comparison layout
- timeline: Horizontal timeline progression
- subtitle_card: Styled subtitle card (Douyin/Kuaishou style)
"""

from __future__ import annotations

import math
import os
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont, ImageFilter


TEMPLATE_DIR = Path(__file__).parent.parent.parent / 'output' / 'templates'
TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)

# Default canvas sizes
CANVAS = {
    'douyin': (1080, 1920),
    'bilibili': (1920, 1080),
    'kuaishou': (1080, 1920),
    'xiaohongshu': (1080, 1440),
}


def _get_default_font(size: int) -> ImageFont.FreeTypeFont:
    """Get a font, falling back to default."""
    font_paths = [
        'C:/Windows/Fonts/msyh.ttc',   # Microsoft YaHei (Windows Chinese)
        'C:/Windows/Fonts/simhei.ttf',  # SimHei
        'C:/Windows/Fonts/arial.ttf',
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    return ImageFont.load_default()


@dataclass
class PhotoCardConfig:
    """Configuration for photo card template."""
    image_path: Optional[str] = None  # Background image path
    title: str = ''
    subtitle: str = ''
    blur_radius: int = 15
    overlay_opacity: float = 0.4


@dataclass
class EmotionCardConfig:
    """Configuration for emotion card template."""
    emotion: str = 'shock'
    emoji: str = '😱'
    text: str = ''
    gradient_colors: tuple[str, str] = ('#1a1a2e', '#16213e')


@dataclass
class SplitComparisonConfig:
    """Configuration for split comparison template."""
    left_label: str = ''
    right_label: str = ''
    left_text: str = ''
    right_text: str = ''


@dataclass
class TimelineConfig:
    """Configuration for timeline progression template."""
    events: list[str] = None
    title: str = ''


@dataclass
class TemplateRenderResult:
    """Result of rendering a template."""
    image_path: str
    width: int
    height: int
    duration_sec: float


class TemplateRenderer:
    """Renders visual templates to images for video composition."""

    def __init__(self, canvas_size: tuple[int, int] = (1080, 1920)):
        self.width, self.height = canvas_size

    # ===== Photo Card =====

    def render_photo_card(self, config: PhotoCardConfig) -> TemplateRenderResult:
        """Render a photo card template — blurred background + centered text."""
        img = Image.new('RGB', (self.width, self.height), '#0a0a0a')
        draw = ImageDraw.Draw(img)

        # Load and blur background if available
        if config.image_path and os.path.exists(config.image_path):
            bg = Image.open(config.image_path).convert('RGB')
            bg = bg.resize((self.width, self.height), Image.LANCZOS)
            bg = bg.filter(ImageFilter.GaussianBlur(config.blur_radius))
            # Darken overlay
            overlay = Image.new('RGBA', (self.width, self.height), (0, 0, 0, int(255 * config.overlay_opacity)))
            bg.paste(overlay, mask=overlay.split()[3] if overlay.mode == 'RGBA' else None)
            img = bg
            draw = ImageDraw.Draw(img)

        # Title
        title_font = _get_default_font(72)
        title_lines = textwrap.wrap(config.title, width=15)
        y_offset = self.height // 2 - 120
        for line in title_lines:
            bbox = draw.textbbox((0, 0), line, font=title_font)
            text_width = bbox[2] - bbox[0]
            draw.text(
                ((self.width - text_width) // 2, y_offset),
                line,
                fill='#ffffff',
                font=title_font,
                stroke_width=2,
                stroke_fill='#000000',
            )
            y_offset += 90

        # Subtitle
        if config.subtitle:
            sub_font = _get_default_font(36)
            sub_lines = textwrap.wrap(config.subtitle, width=30)
            for line in sub_lines:
                bbox = draw.textbbox((0, 0), line, font=sub_font)
                text_width = bbox[2] - bbox[0]
                draw.text(
                    ((self.width - text_width) // 2, y_offset + 20),
                    line,
                    fill='#b3b3b3',
                    font=sub_font,
                )
                y_offset += 50

        # Save
        output_path = TEMPLATE_DIR / f'photo_card_{hash(config.title) % 100000}.png'
        img.save(str(output_path), 'PNG')
        return TemplateRenderResult(str(output_path), self.width, self.height, 5.0)

    # ===== Emotion Card =====

    def render_emotion_card(self, config: EmotionCardConfig) -> TemplateRenderResult:
        """Render an emotion card — gradient + emoji + emotion text."""
        img = Image.new('RGB', (self.width, self.height))
        draw = ImageDraw.Draw(img)

        # Parse gradient colors
        c1 = _hex_to_rgb(config.gradient_colors[0])
        c2 = _hex_to_rgb(config.gradient_colors[1])

        # Draw vertical gradient
        for y in range(self.height):
            ratio = y / self.height
            r = int(c1[0] + (c2[0] - c1[0]) * ratio)
            g = int(c1[1] + (c2[1] - c1[1]) * ratio)
            b = int(c1[2] + (c2[2] - c1[2]) * ratio)
            draw.line([(0, y), (self.width, y)], fill=(r, g, b))

        # Emoji (render as large text)
        emoji_font = _get_default_font(180)
        bbox = draw.textbbox((0, 0), config.emoji, font=emoji_font)
        emoji_width = bbox[2] - bbox[0]
        draw.text(
            ((self.width - emoji_width) // 2, self.height // 3),
            config.emoji,
            fill='#ffffff',
            font=emoji_font,
        )

        # Emotion text
        emotion_font = _get_default_font(64)
        bbox = draw.textbbox((0, 0), config.emotion.upper(), font=emotion_font)
        text_width = bbox[2] - bbox[0]
        draw.text(
            ((self.width - text_width) // 2, self.height // 2),
            config.emotion.upper(),
            fill='#ffffff',
            font=emotion_font,
        )

        # Description text
        if config.text:
            desc_font = _get_default_font(36)
            desc_lines = textwrap.wrap(config.text, width=25)
            y = self.height // 2 + 100
            for line in desc_lines[:3]:  # Max 3 lines
                bbox = draw.textbbox((0, 0), line, font=desc_font)
                line_width = bbox[2] - bbox[0]
                draw.text(
                    ((self.width - line_width) // 2, y),
                    line,
                    fill='#cccccc',
                    font=desc_font,
                )
                y += 50

        output_path = TEMPLATE_DIR / f'emotion_card_{hash(config.emotion) % 100000}.png'
        img.save(str(output_path), 'PNG')
        return TemplateRenderResult(str(output_path), self.width, self.height, 5.0)

    # ===== Subtitle Card (Douyin/Kuaishou style) =====

    def render_subtitle_card(self, text: str, highlight_words: list[str] = None) -> TemplateRenderResult:
        """Render a subtitle card with keyword highlighting."""
        highlight_words = highlight_words or []
        img = Image.new('RGBA', (self.width, 200), (0, 0, 0, 180))
        draw = ImageDraw.Draw(img)

        font = _get_default_font(42)
        words = text.split(' ')
        x, y = 40, 80

        for word in words:
            is_highlighted = any(hw in word for hw in highlight_words) if highlight_words else False
            color = '#FFD700' if is_highlighted else '#ffffff'
            bbox = draw.textbbox((x, y), word + ' ', font=font)
            draw.text((x, y), word + ' ', fill=color, font=font)
            x = bbox[2]

            if x > self.width - 80:
                x = 40
                y += 60

        output_path = TEMPLATE_DIR / f'subtitle_{hash(text) % 100000}.png'
        img.save(str(output_path), 'PNG')
        return TemplateRenderResult(str(output_path), self.width, 200, 3.0)


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def create_template_renderer(platform: str = 'douyin') -> TemplateRenderer:
    """Factory: create a TemplateRenderer for the given platform."""
    size = CANVAS.get(platform, (1080, 1920))
    return TemplateRenderer(canvas_size=size)
