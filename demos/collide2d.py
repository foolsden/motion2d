"""
collide2d/abccollision.py — v7.1.1
====================================================================
Pure 2D AABB collision primitives. No framework. No policy.

CONVENTION:
    All x, y are the TOP-LEFT corner of the AABB.
    Rects span [x, x+w] × [y, y+h].

PUBLIC API:
    resolve_swept(...)    one mover vs static solids. Resolves.
    contact(...)          two movers. Reports. Does not resolve.
    swept_overlap(...)    detection only. Returns bool.
    float_colliderect()   primitive AABB overlap test.
    query_* / find_*      proximity queries.
    resolve_many(...)     batch resolve.

TWO MATHEMATICAL FOUNDATIONS:
    resolve_swept uses sampled A/B/C sub-stepping. Its job is to
    RESOLVE a motion (find the new position). Sampling is appropriate.

    contact and swept_overlap use the exact slab method (relative
    motion, closed-form time of first contact). Their job is to
    REPORT geometry. Exactness is appropriate.

    They deliberately do not share implementation. Each uses the
    mathematics suited to its purpose. This is not a violation of
    separation; it is separation.

CONSEQUENCE / POLICY (feeding frenzy, tiers, chains) lives OUTSIDE
this module. This module reports facts. The caller decides meaning.

SEMANTIC CONTRACT — CONTACT DEFINITION
    float_colliderect treats touching as NOT overlap (strict <, >).

    contact() follows the same rule:
        - A contact requires the beginning of a strict-overlap interval
          within the frame.
        - Exactly touching is not a contact.
        - Touching-then-separating is not a contact.
        - Touching-then-immediately-overlapping IS a contact. In this
          case contact() reports t=0. This means "the strict-overlap
          interval begins immediately after t=0." It does NOT mean the
          rectangles strictly overlap at t=0 itself.
        - A single-instant corner graze is not a contact.
        - Already-overlapping at frame start is reported as embedded.

    This contract is shared by contact() and swept_overlap().
"""

from dataclasses import dataclass
from typing import List, Tuple, Any, Optional, Iterable, Dict
import math


# ============================================================================
# 1. Primitives
# ============================================================================

def float_colliderect(ax: float, ay: float, aw: float, ah: float,
                      bx: float, by: float, bw: float, bh: float) -> bool:
    """Strict AABB overlap test. Touching is NOT collision."""
    return ax < bx + bw and ax + aw > bx and ay < by + bh and ay + ah > by


# ============================================================================
# 2. Shared classification table (used by resolve_swept only)
# ============================================================================

def _classify_contact(a_hit: bool, b_hit: bool, c_hit: bool) -> Tuple[bool, bool]:
    """
    Interpret A/B/C probe booleans into (blocked_x, blocked_y).

    A probe: mover displaced on x only.
    B probe: mover displaced on y only.
    C probe: mover displaced on both axes.

    Truth table:
      c_hit=False         → no contact
      not a and not b     → corner graze, both axes
      a and not b         → x blocked
      b and not a         → y blocked
      a and b             → corner, both axes

    Internal to resolve_swept. contact() does not use this.
    """
    if not c_hit:
        return (False, False)
    if not a_hit and not b_hit:
        return (True, True)
    if a_hit and not b_hit:
        return (True, False)
    if b_hit and not a_hit:
        return (False, True)
    return (True, True)


# ============================================================================
# 3. Result types
# ============================================================================

@dataclass
class Hit:
    entity: Any
    side: str
    rect: Tuple[float, float, float, float]


@dataclass
class ResolveResult:
    x: float
    y: float
    dx_used: float
    dy_used: float
    hits: List[Hit]
    blocked_x: bool
    blocked_y: bool


@dataclass
class Block:
    """
    Per-body report from contact().

    Two independent pieces of information:

    axis (pair-level, same on both blocks):
        (contact_x, contact_y) — which axes the first contact occurred on.
        (True, False) → x-axis contact
        (False, True) → y-axis contact
        (True, True)  → corner contact (both axes at the same t)
        (False, False)→ no contact, OR embedded (undefined)

        Use this for bounce logic, contact-axis decisions.

    blocked (per-body, differs between blocks):
        Which axes of THIS body's continued motion are obstructed by
        the contact. A stationary body has blocked=(False, False) even
        when it is being hit — because it wasn't moving.

        Use this to decide "should I zero my velocity on this axis?"

    When embedded=True:
        axis    = (False, False)  — undefined for embedded
        blocked = (True, True)    — ambiguous, both axes involved
        time    = 0.0
        pos     = starting position (no motion applied)
        unspent = full delta
    """
    hit: bool
    embedded: bool
    time: Optional[float]
    axis: Tuple[bool, bool]
    blocked: Tuple[bool, bool]
    pos_x: float
    pos_y: float
    unspent_x: float
    unspent_y: float


# ============================================================================
# 4. Adapters
# ============================================================================

def _get_rect(e: Any) -> Tuple[float, float, float, float]:
    """
    Accepts:
    - (x, y, w, h) tuple/list
    - dict with keys x, y, w/width, h/height
    - object with .x, .y, .w/.width, .h/.height
    """
    # pygame Rect (has .x, .y, .w, .h as attributes)
    if hasattr(e, 'rect'):
        r = e.rect
        if isinstance(r, (list, tuple)):
            return tuple(map(float, r))
        # pygame.Rect / FRect
        return (float(r.x), float(r.y), float(r.w), float(r.h))

    if isinstance(e, (list, tuple)) and len(e) == 4:
        return tuple(map(float, e))
    if isinstance(e, dict):
        x = e.get('x', e.get('left', 0))
        y = e.get('y', e.get('top', 0))
        w = e.get('w', e.get('width', 0))
        h = e.get('h', e.get('height', 0))
        return (float(x), float(y), float(w), float(h))
    if hasattr(e, 'x') and hasattr(e, 'y'):
        x = float(e.x)
        y = float(e.y)
        if hasattr(e, 'w'):
            w = float(e.w)
        elif hasattr(e, 'width'):
            w = float(e.width)
        else:
            raise ValueError(f"_get_rect: {e} has x,y but no w/width")
        if hasattr(e, 'h'):
            h = float(e.h)
        elif hasattr(e, 'height'):
            h = float(e.height)
        else:
            raise ValueError(f"_get_rect: {e} has x,y but no h/height")
        return (x, y, w, h)
    raise TypeError(
        f"Can't get rect from {type(e)} {e} — expected (x,y,w,h) tuple, "
        f"dict, or object with x,y,w,h"
    )


# ============================================================================
# 5. resolve_swept — one mover vs static solids (sampled A/B/C)
# ============================================================================

def _hits_at(tx: float, ty: float, w: float, h: float,
             solids: Iterable[Tuple[Any, Tuple[float, float, float, float]]]) -> List[Tuple[Any, Tuple[float, float, float, float]]]:
    out = []
    for ent, (rx, ry, rw, rh) in solids:
        if float_colliderect(tx, ty, w, h, rx, ry, rw, rh):
            out.append((ent, (rx, ry, rw, rh)))
    return out


def _resolve_step(sx: float, sy: float, w: float, h: float,
                  dx: float, dy: float,
                  solids: Iterable[Tuple[Any, Tuple[float, float, float, float]]]) -> ResolveResult:
    """One sub-step. Probes from the known-safe (sx, sy)."""
    x_new = sx + dx
    y_new = sy + dy

    c_hits = _hits_at(x_new, y_new, w, h, solids)
    if not c_hits:
        return ResolveResult(x_new, y_new, dx, dy, [], False, False)

    a_hits = _hits_at(x_new, sy, w, h, solids)
    b_hits = _hits_at(sx, y_new, w, h, solids)

    blocked_x, blocked_y = _classify_contact(
        bool(a_hits), bool(b_hits), True
    )

    if blocked_x and blocked_y:
        return ResolveResult(
            sx, sy, 0, 0,
            [Hit(e, 'corner', r) for e, r in c_hits],
            True, True,
        )
    if blocked_x:
        side = 'right' if dx > 0 else 'left'
        return ResolveResult(
            sx, y_new, 0, dy,
            [Hit(e, side, r) for e, r in a_hits],
            True, False,
        )
    if blocked_y:
        side = 'bottom' if dy > 0 else 'top'
        return ResolveResult(
            x_new, sy, dx, 0,
            [Hit(e, side, r) for e, r in b_hits],
            False, True,
        )
    return ResolveResult(sx, sy, 0, 0, [], False, False)


def _swept_with_solids(start_x: float, start_y: float, w: float, h: float,
                       dx: float, dy: float,
                       solids: Iterable[Tuple[Any, Tuple[float, float, float, float]]],
                       max_step: float = 1.0, allow_slide: bool = True) -> ResolveResult:
    if dx == 0 and dy == 0:
        return ResolveResult(start_x, start_y, 0, 0, [], False, False)

    steps = max(1, math.ceil(max(abs(dx), abs(dy)) / max_step))
    sx = dx / steps
    sy = dy / steps
    x, y = start_x, start_y
    all_hits: List[Hit] = []
    blocked_x = False
    blocked_y = False

    for _ in range(steps):
        r = _resolve_step(x, y, w, h, sx, sy, solids)
        x, y = r.x, r.y
        all_hits.extend(r.hits)

        if r.blocked_x and r.blocked_y:
            blocked_x = blocked_y = True
            break
        if r.blocked_x:
            blocked_x = True
            if allow_slide:
                sx = 0
            else:
                break
        if r.blocked_y:
            blocked_y = True
            if allow_slide:
                sy = 0
            else:
                break

    seen = set()
    unique = []
    for hh in all_hits:
        key = (id(hh.entity), hh.side)
        if key not in seen:
            seen.add(key)
            unique.append(hh)

    return ResolveResult(x, y, x - start_x, y - start_y,
                         unique, blocked_x, blocked_y)


def resolve_swept(start_x: float, start_y: float, w: float, h: float,
                  dx: float, dy: float, collidables: Iterable[Any],
                  max_step: float = 1.0, allow_slide: bool = True) -> ResolveResult:
    """
    Move a single AABB by (dx, dy) against static solids.

    allow_slide=True  (default) — collision blocks one axis; the free
                                  axis continues. Standard movement.
    allow_slide=False           — collision stops both axes. Pure push.
    """
    if dx == 0 and dy == 0:
        return ResolveResult(start_x, start_y, 0, 0, [], False, False)
    solids = [(c, _get_rect(c)) for c in collidables]
    return _swept_with_solids(start_x, start_y, w, h, dx, dy, solids,
                              max_step, allow_slide)


# ============================================================================
# 6. Exact slab method (private)
# ============================================================================

def _exact_contact_time(a_x: float, a_y: float, a_w: float, a_h: float, a_dx: float, a_dy: float,
                        b_x: float, b_y: float, b_w: float, b_h: float, b_dx: float, b_dy: float) -> Optional[Tuple[float, Tuple[bool, bool], Tuple[Optional[str], Optional[str]], Tuple[Optional[str], Optional[str]]]]:
    """
    Slab method in relative-motion space. Exact time of first contact.

    SEMANTIC CONTRACT (matches float_colliderect):
        - Touching (exactly adjacent) is not overlap.
        - A contact is reported when a strict-overlap interval begins
          within the frame, including the case where the bodies begin
          exactly touching at t=0 and move immediately into strict
          overlap.
        - "Returns t=0" for the touch-then-overlap case means "the
          strict-overlap interval begins immediately after t=0." It
          does NOT mean the rectangles strictly overlap at t=0 itself.
        - A single-instant touch (corner graze or edge graze that
          does not continue into overlap) is not a contact.

    Returns None if there is no contact during [0, 1], or:
        (t, axis, a_sides, b_sides)

    axis    = (axis_x, axis_y) — which axes the first contact occurred on
    a_sides = (a_contact_x, a_contact_y) — which side of A participated
              ('left'/'right'/'top'/'bottom', or None)
    b_sides = same for B
    """
    rdx = a_dx - b_dx
    rdy = a_dy - b_dy

    a_contact_x = b_contact_x = None
    a_contact_y = b_contact_y = None

    # --- X slab ----------------------------------------------------------
    if rdx == 0:
        # No relative x motion. X-ranges must overlap (strictly) for the
        # whole frame, or the pair cannot contact via x.
        if a_x + a_w <= b_x or b_x + b_w <= a_x:
            return None
        tx_enter = -math.inf
        tx_exit = math.inf
    else:
        t1 = (b_x - (a_x + a_w)) / rdx      # A.right meets B.left
        t2 = ((b_x + b_w) - a_x) / rdx      # A.left meets B.right
        tx_enter = min(t1, t2)
        tx_exit = max(t1, t2)
        if t1 <= t2:
            a_contact_x, b_contact_x = 'right', 'left'
        else:
            a_contact_x, b_contact_x = 'left', 'right'

    # --- Y slab ----------------------------------------------------------
    if rdy == 0:
        if a_y + a_h <= b_y or b_y + b_h <= a_y:
            return None
        ty_enter = -math.inf
        ty_exit = math.inf
    else:
        t1 = (b_y - (a_y + a_h)) / rdy
        t2 = ((b_y + b_h) - a_y) / rdy
        ty_enter = min(t1, t2)
        ty_exit = max(t1, t2)
        if t1 <= t2:
            a_contact_y, b_contact_y = 'bottom', 'top'
        else:
            a_contact_y, b_contact_y = 'top', 'bottom'

    # --- Overall interval -------------------------------------------------
    t_enter = max(tx_enter, ty_enter)
    t_exit = min(tx_exit, ty_exit)

    # Intersect with [0, 1]. Strict inequality: a single-instant touch
    # (t_enter_in_frame == t_exit_in_frame) is NOT a contact.
    t_enter_in_frame = max(t_enter, 0.0)
    t_exit_in_frame = min(t_exit, 1.0)

    if t_enter_in_frame >= t_exit_in_frame:
        return None

    t = t_enter_in_frame

    # --- Axis of first contact -------------------------------------------
    # If both slabs entered at -inf, both axes were already overlapping
    # before the frame (embedded). Report corner.
    # Otherwise, the axis of first contact is the one whose t_enter
    # produced the max.
    EPS = 1e-9
    if tx_enter == -math.inf and ty_enter == -math.inf:
        axis = (True, True)
    elif abs(tx_enter - ty_enter) < EPS:
        axis = (True, True)
    elif tx_enter > ty_enter:
        axis = (True, False)
        a_contact_y = b_contact_y = None
    else:
        axis = (False, True)
        a_contact_x = b_contact_x = None

    return t, axis, (a_contact_x, a_contact_y), (b_contact_x, b_contact_y)


def _is_blocked_by_contact(contact_side: Optional[str], delta: float) -> bool:
    """Is this body's continued motion on this axis obstructed?"""
    if contact_side is None:
        return False
    if delta == 0:
        return False
    if contact_side in ('right', 'bottom'):
        return delta > 0
    return delta < 0


# ============================================================================
# 7. contact — two movers, report only
# ============================================================================

def contact(a_x: float, a_y: float, a_w: float, a_h: float, a_dx: float, a_dy: float,
            b_x: float, b_y: float, b_w: float, b_h: float, b_dx: float, b_dy: float) -> Tuple[Block, Block]:
    """
    Report the geometric contact between two moving AABBs during one frame.

    Pure geometry. Does NOT resolve. Does NOT move either body.

    If the AABBs overlap at frame start, reports embedded=True for both
    with axis=(False, False) (undefined). The caller decides correction.

    Follows the semantic contract of _exact_contact_time (and of
    float_colliderect): touching is not contact. A contact requires a
    strict-overlap interval to begin within the frame.

    Returns (a_block, b_block). See Block for field semantics.
    """

    # --- Embedded at frame start -----------------------------------------
    if float_colliderect(a_x, a_y, a_w, a_h, b_x, b_y, b_w, b_h):
        return (
            Block(True, True, 0.0, (False, False), (True, True),
                  a_x, a_y, a_dx, a_dy),
            Block(True, True, 0.0, (False, False), (True, True),
                  b_x, b_y, b_dx, b_dy),
        )

    # --- Exact contact ---------------------------------------------------
    result = _exact_contact_time(a_x, a_y, a_w, a_h, a_dx, a_dy,
                                 b_x, b_y, b_w, b_h, b_dx, b_dy)

    if result is None:
        return (
            Block(False, False, None, (False, False), (False, False),
                  a_x + a_dx, a_y + a_dy, 0.0, 0.0),
            Block(False, False, None, (False, False), (False, False),
                  b_x + b_dx, b_y + b_dy, 0.0, 0.0),
        )

    t, axis, a_sides, b_sides = result

    # --- Positions at contact --------------------------------------------
    a_cx = a_x + a_dx * t
    a_cy = a_y + a_dy * t
    b_cx = b_x + b_dx * t
    b_cy = b_y + b_dy * t

    # --- Unspent ---------------------------------------------------------
    a_un_x = a_dx * (1 - t)
    a_un_y = a_dy * (1 - t)
    b_un_x = b_dx * (1 - t)
    b_un_y = b_dy * (1 - t)

    # --- Per-body blocked (from contact side + delta) --------------------
    a_contact_x, a_contact_y = a_sides
    b_contact_x, b_contact_y = b_sides

    blocked_a = (
        _is_blocked_by_contact(a_contact_x, a_dx),
        _is_blocked_by_contact(a_contact_y, a_dy),
    )
    blocked_b = (
        _is_blocked_by_contact(b_contact_x, b_dx),
        _is_blocked_by_contact(b_contact_y, b_dy),
    )

    return (
        Block(True, False, t, axis, blocked_a,
              a_cx, a_cy, a_un_x, a_un_y),
        Block(True, False, t, axis, blocked_b,
              b_cx, b_cy, b_un_x, b_un_y),
    )


# ============================================================================
# 8. swept_overlap — detection only
# ============================================================================

def swept_overlap(ax: float, ay: float, aw: float, ah: float, adx: float, ady: float,
                  bx: float, by: float, bw: float, bh: float, bdx: float, bdy: float) -> bool:
    """
    True if two moving AABBs begin a strict-overlap interval during the
    frame. Follows the same semantic contract as contact().
    """
    return _exact_contact_time(ax, ay, aw, ah, adx, ady,
                               bx, by, bw, bh, bdx, bdy) is not None


# ============================================================================
# 9. Queries
# ============================================================================

def _probe_hits(x: float, y: float, w: float, h: float, collidables: Iterable[Any],
                _parsed_solids: Optional[Iterable[Tuple[Any, Tuple[float, float, float, float]]]] = None) -> List[Tuple[Any, Tuple[float, float, float, float]]]:
    solids = (_parsed_solids if _parsed_solids is not None
              else [(c, _get_rect(c)) for c in collidables])
    return [(ent, r) for ent, r in solids
            if float_colliderect(x, y, w, h, *r)]


def query_down(x: float, y: float, w: float, h: float, collidables: Iterable[Any],
               distance: float = 1.0, _parsed_solids: Optional[Iterable[Tuple[Any, Tuple[float, float, float, float]]]] = None) -> bool:
    return len(_probe_hits(x, y + distance, w, h, collidables, _parsed_solids)) > 0


def query_up(x: float, y: float, w: float, h: float, collidables: Iterable[Any],
             distance: float = 1.0, _parsed_solids: Optional[Iterable[Tuple[Any, Tuple[float, float, float, float]]]] = None) -> bool:
    return len(_probe_hits(x, y - distance, w, h, collidables, _parsed_solids)) > 0


def query_left(x: float, y: float, w: float, h: float, collidables: Iterable[Any],
               distance: float = 1.0, _parsed_solids: Optional[Iterable[Tuple[Any, Tuple[float, float, float, float]]]] = None) -> bool:
    return len(_probe_hits(x - distance, y, w, h, collidables, _parsed_solids)) > 0


def query_right(x: float, y: float, w: float, h: float, collidables: Iterable[Any],
                distance: float = 1.0, _parsed_solids: Optional[Iterable[Tuple[Any, Tuple[float, float, float, float]]]] = None) -> bool:
    return len(_probe_hits(x + distance, y, w, h, collidables, _parsed_solids)) > 0


def is_grounded(x: float, y: float, w: float, h: float, collidables: Iterable[Any],
                distance: float = 1.0, _parsed_solids: Optional[Iterable[Tuple[Any, Tuple[float, float, float, float]]]] = None) -> bool:
    return query_down(x, y, w, h, collidables, distance, _parsed_solids)


def is_on_wall(x: float, y: float, w: float, h: float, collidables: Iterable[Any],
               distance: float = 1.0, _parsed_solids: Optional[Iterable[Tuple[Any, Tuple[float, float, float, float]]]] = None) -> bool:
    return (query_left(x, y, w, h, collidables, distance, _parsed_solids) or
            query_right(x, y, w, h, collidables, distance, _parsed_solids))


def find_down(x: float, y: float, w: float, h: float, collidables: Iterable[Any],
              distance: float = 1.0, _parsed_solids: Optional[Iterable[Tuple[Any, Tuple[float, float, float, float]]]] = None) -> Optional[Any]:
    hits = _probe_hits(x, y + distance, w, h, collidables, _parsed_solids)
    return hits[0][0] if hits else None


def find_up(x: float, y: float, w: float, h: float, collidables: Iterable[Any],
            distance: float = 1.0, _parsed_solids: Optional[Iterable[Tuple[Any, Tuple[float, float, float, float]]]] = None) -> Optional[Any]:
    hits = _probe_hits(x, y - distance, w, h, collidables, _parsed_solids)
    return hits[0][0] if hits else None


def find_left(x: float, y: float, w: float, h: float, collidables: Iterable[Any],
              distance: float = 1.0, _parsed_solids: Optional[Iterable[Tuple[Any, Tuple[float, float, float, float]]]] = None) -> Optional[Any]:
    hits = _probe_hits(x - distance, y, w, h, collidables, _parsed_solids)
    return hits[0][0] if hits else None


def find_right(x: float, y: float, w: float, h: float, collidables: Iterable[Any],
               distance: float = 1.0, _parsed_solids: Optional[Iterable[Tuple[Any, Tuple[float, float, float, float]]]] = None) -> Optional[Any]:
    hits = _probe_hits(x + distance, y, w, h, collidables, _parsed_solids)
    return hits[0][0] if hits else None


# ============================================================================
# 10. Batch
# ============================================================================

def _unpack_entity(item: Any) -> Tuple[Any, float, float, float, float, float, float]:
    if isinstance(item, dict):
        e = item.get('entity', item)
        w = item.get('w', item.get('width', 0))
        h = item.get('h', item.get('height', 0))
        return (e, float(item['x']), float(item['y']), float(w), float(h),
                float(item.get('dx', 0)), float(item.get('dy', 0)))
    elif isinstance(item, (list, tuple)) and len(item) >= 7:
        return (item[0], float(item[1]), float(item[2]), float(item[3]),
                float(item[4]), float(item[5]), float(item[6]))
    else:
        e = item
        x = float(e.x)
        y = float(e.y)
        if hasattr(e, 'w'):
            w = float(e.w)
        elif hasattr(e, 'width'):
            w = float(e.width)
        else:
            raise ValueError(f"_unpack_entity: {e} has x,y but no w/width")
        if hasattr(e, 'h'):
            h = float(e.h)
        elif hasattr(e, 'height'):
            h = float(e.height)
        else:
            raise ValueError(f"_unpack_entity: {e} has x,y but no h/height")
        return (e, x, y, w, h,
                float(getattr(e, 'dx', 0)), float(getattr(e, 'dy', 0)))


def resolve_many(entities: Iterable[Any], collidables: Iterable[Any],
                 max_step: float = 1.0, allow_slide: bool = True) -> List[Tuple[Any, ResolveResult]]:
    """
    Resolve N entities against the same solids, parsing solids once.

    Returns a list of (entity, ResolveResult) pairs in input order.
    """
    solids = [(c, _get_rect(c)) for c in collidables]
    out = []
    for item in entities:
        e, x, y, w, h, dx, dy = _unpack_entity(item)
        out.append((e, _swept_with_solids(x, y, w, h, dx, dy, solids,
                                          max_step, allow_slide)))
    return out


# ============================================================================
# 11. Convenience
# ============================================================================

def make_entity(x: float, y: float, w: float, h: float, name: str = "") -> Dict[str, Any]:
    """Create a pure dict entity compatible with all adapters."""
    return {"x": float(x), "y": float(y), "w": float(w), "h": float(h),
            "name": name}


# ============================================================================
# HISTORY
# ============================================================================
# v7.1.1:
# - Restored `.rect` adapter in _get_rect (was dropped during v5.3→v7.0
#   restructure). Entities with self.rect = pygame.Rect(...) or
#   self.rect = (x,y,w,h) work again as collidables.

# v7.1:
# - contact() uses exact slab method (_exact_contact_time), not sampling.
# - Block gains `axis` (pair-level contact axis) distinct from `blocked`
#   (per-body obstruction).
# - Embedded case reports axis=(False, False) (undefined) and blocked=(True, True).
# - blocked derived from contact side + per-body delta (robust for unequal sizes).
# - swept_hit_time removed. swept_overlap uses _exact_contact_time.
# - resolve_swept keeps sampled A/B/C internally (appropriate for resolution).
# - _classify_contact is now resolve_swept-internal only.
# - Semantic contract documented in module docstring and in
#   _exact_contact_time docstring: touching is not contact; contact
#   requires a strict-overlap interval to begin within the frame

# V7.0:
# - Extracted _classify_contact into a shared internal helper.
# - contact() introduced for moving-vs-moving.

# V6.0:
# - Remove pygame dependency

# V5.3: REJECTED
# - auto detect if the coordinate is center point or top left
# - Checked by other AI, rejected because a lot of assumption
# - Revert back to V5.2

# V5.2:
# - allow_slide now implemented (was dead param)
# - _get_rect restores ValueError for missing w/h (no silent 0)
# - query_* accepts _parsed_solids for batch use
# - resolve_many restored (one parse, N entities)
# - find_down/up/left/right added for moving-platform support

# V5.1:
# - CLARIFIES: blocked_down confusion fixed by splitting into 2 systems
# - RESOLVER (movement): resolve() / resolve_swept() -> ResolveResult with blocked_x/y + hits
#   Answers: "If I move by dx,dy, where do I end up and what did I hit THIS FRAME?"
# - QUERY (probe): query_down/up/left/right(), is_grounded(), is_on_wall()
#   Answers: "From where I am NOW, is there solid N px away?" Works even when dx,dy=0
# - Old blocked_down / on_ground properties REMOVED from ResolveResult to force separation
#   (they were resolver-based and caused standing-still bug)
# - Keeps swept_overlap / swept_hit_time for bullet vs player (moving vs moving)

# V5.0:
# - NEW: probe(), probe_down/up/left/right() — separate query functions per A/B/C design doc
# - ground detection is now a QUERY, not folded into resolver results. Fixes 'folded convenience' trap
# - Usage: if probe_down(x,y,w,h,1,walls): on_ground=True  # independent of movement
# - NOTE: probe uses 1-step _resolve_internal, not swept. For fast falling use swept then probe.

# v4.9:
# - FIX: _swept_with_solids dedup now by (id, side) not just id — same tile corner keeps both wall+floor hits
# - Before: combined=[right,bottom] for same tile -> dedup kept only right -> blocked_down=False -> on_ground=False
# - After: keeps both hits -> blocked_down=True and blocked_right=True -> correct
# - DOCS: swept_hit_time note about `if t is not None` vs `if t`

# v4.8:
# - NEW: swept_overlap() and swept_hit_time() — CCD for 2 moving AABBs (player vs bullet)
# - Fixes tunneling when both move toward each other at high speed
# - Uses relative motion: A moves with (adx-bdx, ady-bdy) vs static B, substeps
# - Bullet should NOT be in walls solids list (blocking), use swept_overlap for hit detection

# v4.7:
# - OPTIMIZATION: resolve(), resolve_swept(), _swept_with_solids() all early-exit if dx==0 and dy==0 — no _get_rect parsing
# - Game-side optimization documented: skip calling resolver when idle (big win for 100 idle enemies)
# - No behavior change, just performance

# v4.6:
# - CORE IS NOW PLATFORMER-AGNOSTIC: collision reports geometry, game assigns meaning.
# - Added generic checks: blocked_down/up/left/right, is_blocked_down() etc — works for top-down and platformer
# - Platformer aliases kept: on_ground = blocked_down, on_ceiling = blocked_up, on_wall = blocked_left/right
# - ChatGPT suggestion applied: check_down / is_blocked_down is core, is_on_ground is semantic alias
# - Top-down usage: blocked_down = south obstacle, blocked_up = north, etc.

# v4.5:
# - BUGFIX: corner (A and B) now returns both wall+floor hits, not just 'corner'. Fixes is_grounded when sliding into wall on floor.
# - Added flags pattern: Hit.flags and ResolveResult.flags dict {top,bottom,left,right,corner}
# - Added ResolveResult.on_ground / on_ceiling / on_wall properties (replaces any(side=='bottom'))
# - True graze (not A and not B) still returns corner-only — not grounded by design

# v4.4:
# - Dropped _parsed_solids from resolve_swept public signature (was public-internal hybrid)
# - resolve_swept now clean: parses once, calls _swept_with_solids
# - resolve_many calls _swept_with_solids directly — no escape hatch
# - Added _unpack_entity helper to avoid duplicated unpack logic
# - Added docstring note about shared solids snapshot for moving platforms
# - Added note about dict key collision risk for tuple entities
# - No rect caching in this file — parse-once per frame is intentional (see note)

# v4.3:
# - Extracted _swept_with_solids() — one loop, two callers
# - Added _parsed_solids escape hatch on resolve_swept
# - resolve_many became thin wrapper (15 lines vs 30)

# v4.0:
# - Contains YOUR original SafeRegistry + SpatialManager (UNTOUCHED)
# - Adds fallback SimpleSpatialManager (commented usage)
# - Adds modular pure collision resolver (independent)

# v3.2:
# Philosophy:
# - Broad phase + rendering = pygame.Rect (int, fast, ecosystem)
# - Narrow phase A/B/C = float AABB (continuous, no 1px slack)

# - _probe_hit now uses float_colliderect, not colliderect
# - tiny-step guard checks dx==0 and dy==0, NOT floor(x) equality
# - eliminates logical vs visual desync (0.9px embedding bug)

# v3.1:
# - _probe_hit(base_rect, ix, iy, solids) -> bool
#   _step and is_on_ground both use it, no intermediate Rect leaking into API
# - A = probe(1,0), B = probe(0,1), C = probe(1,1) as you suggested

# v3 fixes:
# - single-axis collision no longer ends the whole frame, it continues on free axis
# - SpatialGrid.remove uses identity (is), not value equality
# - is_on_ground query helper included

# v2 fixes kept:
# - float authoritative pos (obj.x, obj.y), rect is int mirror
# - steps = ceil(max(|dx|,|dy|)) guarantees sub-step <= 1px
# - math.floor everywhere for negative-coord consistency
# - tiny-step guard