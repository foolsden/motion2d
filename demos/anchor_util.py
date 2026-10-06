# anchor_util.py
"""
Anchor / coordinate conversion helpers.

The collision core works in TOP-LEFT space: an AABB is
(x, y, w, h) where (x, y) is the top-left corner.

Games often store entity positions as CENTER, or BOTTOM-CENTER,
or some other anchor. This module bridges the two.

Design notes:
- Pure functions only. No state, no classes, no dependencies.
- Meant to be copy-pasted into your project or vendored as a single file.
- If you need additional anchors, add them here — don't expand this
  file's dependencies.
- Nothing here knows about collision, motion, or your game.
"""
from typing import Tuple


def center_to_topleft(cx: float, cy: float, w: float, h: float) -> Tuple[float, float]:
    """Given a rect's center and size, return its top-left corner."""
    return (cx - w / 2, cy - h / 2)


def topleft_to_center(x: float, y: float, w: float, h: float) -> Tuple[float, float]:
    """Given a rect's top-left and size, return its center."""
    return (x + w / 2, y + h / 2)


def bottomcenter_to_topleft(cx: float, by: float, w: float, h: float) -> Tuple[float, float]:
    """Given bottom-center + size, return top-left."""
    return (cx - w / 2, by - h)


def topleft_to_bottomcenter(x: float, y: float, w: float, h: float) -> Tuple[float, float]:
    """Given top-left + size, return bottom-center."""
    return (x + w / 2, y + h)


def topleft_to_topright(x: float, y: float, w: float, h: float) -> Tuple[float, float]:
    """Given top-left + size, return top-right."""
    return (x + w, y)