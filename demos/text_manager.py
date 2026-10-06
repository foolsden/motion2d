"""
text_manager.py
---------------
Small text-drawing helper for Pygame demos.

Design:
    - `screen` and `default_size` are bound at init and can be overridden
      per call. Changing the default is a plain attribute assignment.
    - One primitive (`write`) with a numeric/string anchor (numpad layout).
    - One multi-line variant (`write_multiple_line`) that anchors the block.
    - One convenience wrapper (`write_centered`) for screen-centered text.
    - No persistence flags, no wrapping, no rich text. Freeze here.
    - Instantiate the module and bind the screen later with bind()
"""

from __future__ import annotations

from typing import Optional, Sequence, Union, Tuple

import pygame


# Numpad layout:
#     7 8 9      top-left     top-center     top-right
#     4 5 6  =   mid-left     center         mid-right
#     1 2 3      bottom-left  bottom-center  bottom-right
_ANCHOR_NAMES: dict[int, str] = {
    1: "bottomleft",  2: "midbottom",  3: "bottomright",
    4: "midleft",     5: "center",     6: "midright",
    7: "topleft",     8: "midtop",     9: "topright",
}

# A `text` argument may be a single string, a list/tuple of lines,
# or a string containing "\n". We normalize to a list of lines.
TextInput = Union[str, Sequence[str]]
Anchor = Union[int, str]
Color = Union[Tuple[int, int, int], Tuple[int, int, int, int]]


class TextManager:
    """Draw text to a screen with cached fonts and simple anchoring."""
    def __init__(
        self,
        screen: Optional[pygame.Surface] = None,
        default_size: int = 24,
        font_path: Optional[str] = None,
    ) -> None:
        self.screen: Optional[pygame.Surface] = screen
        self.default_size: int = default_size
        self.font_path: Optional[str] = font_path
        self._fonts: dict[int, pygame.font.Font] = {}

    # -----------------------------------------------------------------
    # Internal
    # -----------------------------------------------------------------
    def _font(self, size: int) -> pygame.font.Font:
        f = self._fonts.get(size)
        if f is None:
            f = pygame.font.Font(self.font_path, size)
            self._fonts[size] = f
        return f

    @staticmethod
    def _anchor_name(anchor: Anchor) -> str:
        if isinstance(anchor, str):
            return anchor
        return _ANCHOR_NAMES.get(anchor, "topleft")

    @staticmethod
    def _resolve_screen(
        screen: Optional[pygame.Surface],
        bound: Optional[pygame.Surface],
    ) -> pygame.Surface:
        s = screen if screen is not None else bound
        if s is None:
            raise ValueError(
                "TextManager: no screen bound at init and none supplied per call"
            )
        return s

    @staticmethod
    def _split_lines(text: TextInput) -> list[str]:
        if isinstance(text, str):
            return text.split("\n")
        if isinstance(text, (list, tuple)):
            return list(text)
        raise TypeError(
            f"text must be str, list, or tuple; got {type(text).__name__}"
        )

    # -----------------------------------------------------------------
    # Primitive: render to a Surface (no blit)
    # -----------------------------------------------------------------
    def render(
        self,
        text: str,
        size: Optional[int] = None,
        color: Color = (255, 255, 255),
    ) -> pygame.Surface:
        """Return a rendered Surface. Useful when you want to blit manually."""
        s = size if size is not None else self.default_size
        return self._font(s).render(text, True, color)

    # -----------------------------------------------------------------
    # Single-line draw
    # -----------------------------------------------------------------
    def write(
        self,
        x: int,
        y: int,
        text: str,
        size: Optional[int] = None,
        color: Color = (255, 255, 255),
        screen: Optional[pygame.Surface] = None,
        anchor: Anchor = 7,
    ) -> pygame.Rect:
        """
        Draw a single line of text. Returns the Rect that was drawn.

        `anchor` selects the alignment point using the numpad layout
        (default 7 = top-left). Accepts an int 1-9 or a string like
        "center", "midtop", etc.
        """
        target = self._resolve_screen(screen, self.screen)
        surf = self.render(text, size, color)
        rect = surf.get_rect(**{self._anchor_name(anchor): (x, y)})
        target.blit(surf, rect)
        return rect

    # -----------------------------------------------------------------
    # Multi-line draw
    # -----------------------------------------------------------------
    def write_multiple_line(
        self,
        x: int,
        y: int,
        text: TextInput,
        size: Optional[int] = None,
        color: Color = (255, 255, 255),
        screen: Optional[pygame.Surface] = None,
        anchor: Anchor = 7,
        line_spacing: int = 4,
    ) -> pygame.Rect:
        """
        Draw a block of lines. `text` may be a string with "\\n",
        or a list/tuple of strings. `anchor` positions the whole block.
        Returns the Rect covering the block.
        """
        target = self._resolve_screen(screen, self.screen)
        s = size if size is not None else self.default_size
        font = self._font(s)

        lines = self._split_lines(text)
        if not lines:
            return pygame.Rect(x, y, 0, 0)

        line_h = font.get_linesize() + line_spacing
        surfaces = [font.render(line, True, color) for line in lines]

        block_w = max(surf.get_width() for surf in surfaces)
        block_h = line_h * (len(surfaces) - 1) + surfaces[0].get_height()

        block_rect = pygame.Rect(0, 0, block_w, block_h)
        setattr(block_rect, self._anchor_name(anchor), (x, y))

        cy = block_rect.y
        for surf in surfaces:
            target.blit(surf, (block_rect.x, cy))
            cy += line_h

        return block_rect

    # -----------------------------------------------------------------
    # Convenience: screen-centered
    # -----------------------------------------------------------------
    def write_centered(
        self,
        y: int,
        text: TextInput,
        size: Optional[int] = None,
        color: Color = (255, 255, 255),
        screen: Optional[pygame.Surface] = None,
        anchor: Anchor = 8,
        line_spacing: int = 4,
    ) -> pygame.Rect:
        """
        Draw horizontally centered on the screen at vertical position `y`.
        Accepts either a single string or a multi-line block.
        Default `anchor=8` puts the block's top-center at (center_x, y);
        pass `anchor=5` to center the block vertically on `y` too.
        """
        target = self._resolve_screen(screen, self.screen)
        cx = target.get_width() // 2

        is_multiline = (
            isinstance(text, (list, tuple)) or "\n" in text
        )
        if is_multiline:
            return self.write_multiple_line(
                cx, y, text, size, color, target, anchor, line_spacing,
            )
        return self.write(cx, y, text, size, color, target, anchor)

    # -----------------------------------------------------------------
    # Define the module without the screen first, than use this to bind the screen
    # -----------------------------------------------------------------
    def bind(self, screen: pygame.Surface) -> None:
        """Attach a screen so per-call `screen=` becomes optional."""
        self.screen = screen