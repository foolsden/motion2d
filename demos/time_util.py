"""
time_utils.py
-------------
Three flat primitives for time and quantities in games.

    Timer        - countdown that fires when it reaches its duration
    Resource     - pool between 0 and maximum, can be spent / restored
    Stopwatch    - counts up while running, no target
    TimeSequence - countdown to for sequence stage / phase

They all share an `update(dt)` method, so a game loop can tick them
uniformly. They deliberately do NOT share a base class — see the
Progressor experiment for why. Keep them flat until real pain forces
otherwise.
"""

from __future__ import annotations

from typing import Callable, Optional, Sequence

__all__ = ["Ticker", "Timer", "Resource", "Stopwatch", "TimerSequence"]

import time


class Ticker:
    """
    A lightweight dt provider — the `clock.tick()` idea without pygame.

    Uses `time.perf_counter()` (monotonic, high-resolution), so it's safe
    for measuring durations. Do NOT use this for save-file timestamps —
    use `time.time()` for that.

    Usage:
        ticker = Ticker()
        while running:
            dt = ticker.tick()
            ...
    """

    __slots__ = ("_last",)

    def __init__(self) -> None:
        self._last: float = time.perf_counter()

    def tick(self) -> float:
        """Return seconds elapsed since the last tick (or construction)."""
        now = time.perf_counter()
        dt = now - self._last
        self._last = now
        return dt

    def reset(self) -> None:
        """Reset the reference point. Next tick() returns ~0."""
        self._last = time.perf_counter()


# ===================================================================
# Timer — counts toward a duration, fires when it arrives
# ===================================================================
class Timer:
    """
    Counts time toward `duration`. Fires when it reaches the target.

    - `repeat=True`  → fires every duration, never stops.
    - `spill_over=True` (default) → carries overshoot into the next
      cycle, so repeating timers don't drift over time.
    - `autostart=True` (default) → starts counting immediately.
      Set to False if the timer should be idle until `reset()`.

    `update(dt)` returns True on the frame it fires.
    """

    __slots__ = (
        "duration", "repeat", "spill_over", "active",
        "_value", "on_complete", "on_repeat",
    )

    def __init__(
        self,
        duration: float,
        repeat: bool = False,
        autostart: bool = True,
        spill_over: bool = True,
        on_complete: Optional[Callable[["Timer"], None]] = None,
        on_repeat: Optional[Callable[["Timer"], None]] = None,
    ):
        self.duration = max(0.0, float(duration))
        self.repeat = repeat
        self.spill_over = spill_over
        self.active = autostart
        self._value = 0.0
        self.on_complete = on_complete
        self.on_repeat = on_repeat

    # --- tick ---
    def update(self, dt: float) -> bool:
        """Advance the timer. Returns True on the frame it fires."""
        if not self.active:
            return False

        self._value += dt

        if self._value < self.duration:
            return False

        if self.repeat:
            self._value = (
                self._value - self.duration if self.spill_over else 0.0
            )
            if self.on_repeat:
                self.on_repeat(self)
            return True

        self.active = False
        self._value = self.duration
        if self.on_complete:
            self.on_complete(self)
        return True

    # --- control ---
    def reset(self, duration: Optional[float] = None) -> None:
        if duration is not None:
            self.duration = max(0.0, float(duration))
        self._value = 0.0
        self.active = True

    def start(self) -> None:
        self.active = True

    def pause(self) -> None:
        self.active = False

    def stop(self) -> None:
        self.active = False
        self._value = 0.0

    # --- views ---
    @property
    def elapsed(self) -> float:
        return self._value

    @elapsed.setter
    def elapsed(self, value: float) -> None:
        self._value = max(0.0, min(float(value), self.duration))

    @property
    def remaining_time(self) -> float:
        return self.duration - self._value

    @remaining_time.setter
    def remaining_time(self, value: float) -> None:
        self._value = self.duration - max(0.0, min(float(value), self.duration))

    @property
    def progress(self) -> float:
        return self._value / self.duration if self.duration > 0 else 1.0

    @property
    def remaining_fraction(self) -> float:
        return 1.0 - self.progress

    @property
    def done(self) -> bool:
        return self._value >= self.duration


# ===================================================================
# Resource — a pool between 0 and maximum, spendable and restorable
# ===================================================================
class Resource:
    """
    A value between 0 and `maximum` that can be spent and restored.
    Optionally regenerates over time.

    Fires `on_empty` when it transitions to 0, and `on_full` when it
    transitions to maximum. Transitions only — not every frame.

    Use `spend(n)` for discrete costs (a dash costs 2), and `drain(n)`
    for continuous costs (draining while held, per frame).
    """

    __slots__ = (
        "_maximum", "regen_rate", "_value",
        "on_empty", "on_full", "_was_empty", "_was_full",
    )

    def __init__(
        self,
        maximum: float,
        start: Optional[float] = None,
        regen_rate: float = 0.0,
        on_empty: Optional[Callable[["Resource"], None]] = None,
        on_full: Optional[Callable[["Resource"], None]] = None,
    ):
        self._maximum = max(0.0, float(maximum))
        self.regen_rate = max(0.0, float(regen_rate))

        if start is None:
            start = self._maximum
        self._value = max(0.0, min(float(start), self._maximum))

        self.on_empty = on_empty
        self.on_full = on_full

        self._was_empty = self._value <= 0.0
        self._was_full = self._value >= self._maximum

    # --- internal ---
    def _check_transitions(self) -> None:
        now_empty = self._value <= 0.0
        now_full = self._maximum > 0.0 and self._value >= self._maximum

        if now_empty and not self._was_empty and self.on_empty:
            self.on_empty(self)
        if now_full and not self._was_full and self.on_full:
            self.on_full(self)

        self._was_empty = now_empty
        self._was_full = now_full

    # --- tick ---
    def update(self, dt: float) -> None:
        """Regenerate over time. Silent no-op if regen_rate is 0 or full."""
        dt = max(0.0, float(dt))
        if dt == 0.0 or self.regen_rate == 0.0:
            return
        if self._value >= self._maximum:
            return

        self._value = min(
            self._maximum, self._value + self.regen_rate * dt
        )
        self._check_transitions()

    # --- spend / restore ---
    def can_spend(self, amount: float) -> bool:
        return amount > 0.0 and amount <= self._value

    def spend(self, amount: float) -> bool:
        """All-or-nothing. Returns True if the full amount was spent."""
        if not self.can_spend(amount):
            return False
        self._value = max(0.0, self._value - float(amount))
        self._check_transitions()
        return True

    def drain(self, amount: float) -> float:
        """
        Spend as much as possible, up to `amount`.
        Returns how much was actually spent (may be less than requested).
        For continuous use, pass `rate * dt`.
        """
        if amount <= 0.0:
            return 0.0
        actual = min(self._value, float(amount))
        self._value -= actual
        self._check_transitions()
        return actual

    def restore(self, amount: float) -> None:
        if amount <= 0.0:
            return
        self._value = min(self._maximum, self._value + float(amount))
        self._check_transitions()

    def fill(self) -> None:
        self._value = self._maximum
        self._check_transitions()

    def empty(self) -> None:
        self._value = 0.0
        self._check_transitions()

    # --- views ---
    @property
    def maximum(self) -> float:
        return self._maximum

    @maximum.setter
    def maximum(self, value: float) -> None:
        self._maximum = max(0.0, float(value))
        self._value = max(0.0, min(self._value, self._maximum))
        self._check_transitions()

    @property
    def value(self) -> float:
        return self._value

    @value.setter
    def value(self, v: float) -> None:
        self._value = max(0.0, min(float(v), self._maximum))
        self._check_transitions()

    @property
    def fraction(self) -> float:
        return self._value / self._maximum if self._maximum > 0 else 1.0

    @property
    def progress(self) -> float:
        """Alias for `fraction` — same name as Timer/Stopwatch for UI."""
        return self.fraction

    @property
    def is_empty(self) -> bool:
        return self._value <= 0.0

    @property
    def is_full(self) -> bool:
        return self._maximum > 0.0 and self._value >= self._maximum


# ===================================================================
# Stopwatch — counts up while running, no target, no firing
# ===================================================================
class Stopwatch:
    """
    Counts elapsed time while running. Pause keeps the value, resume
    continues from where it stopped. No target, no completion.

    Use for: how long a state has been active, how long a key has been
    held, charge-up durations, sprint timers.
    """

    __slots__ = ("_elapsed", "running")

    def __init__(self, autostart: bool = False):
        self._elapsed = 0.0
        self.running = autostart

    # --- tick ---
    def update(self, dt: float) -> float:
        """Advance if running. Returns the current elapsed time."""
        if self.running:
            self._elapsed += max(0.0, float(dt))
        return self._elapsed

    # --- control ---
    def start(self) -> None:
        self.running = True

    def pause(self) -> None:
        self.running = False

    def reset(self, autostart: bool = True) -> None:
        self._elapsed = 0.0
        self.running = autostart

    def toggle(self) -> None:
        self.running = not self.running

    # --- views ---
    @property
    def elapsed(self) -> float:
        return self._elapsed

    @elapsed.setter
    def elapsed(self, value: float) -> None:
        self._elapsed = max(0.0, float(value))

    @property
    def progress(self) -> float:
        """
        Not really meaningful for a targetless stopwatch, but provided
        as a no-op-friendly alias so a shared UI doesn't crash on it.
        Always returns 0.0 — there's no target to divide by.
        """
        return 0.0

    def formatted(self) -> str:
        """MM:SS.mmm — handy for HUD display."""
        m, s = divmod(self._elapsed, 60)
        return f"{int(m):02d}:{s:06.3f}"


class TimerSequence:
    """
    TimerSequence — a sequence of Timers run one after another.

    Invariant: update(dt) advances the sequence by exactly `dt` of simulated
    time (subject to sequence completion). Overshoot from a finishing stage
    carries into the next stage, matching Timer's own spill-over semantics.

    Level-triggered: poll `stage` / `stage_name` to know where you are.
    `update(dt)` returns True on the frame a stage ends.

    The "escape hatch" trick if you need on_complete:
    seq = TimerSequence([0.25, 1.5, 0.5], names=["slowmo", "boom", "fade"])
    seq.timers[1].on_complete = lambda t: play_sound("explosion.wav")

    Note:
    1. It only fires for the stage it's attached to
    2. Don't do it while the sequence is running!
    """

    __slots__ = ("timers", "names", "repeat", "active", "_index")

    def __init__(
        self,
        durations: Sequence[float],
        names: Optional[Sequence[str]] = None,
        repeat: bool = False,
        autostart: bool = True,
    ) -> None:
        if not durations:
            raise ValueError("TimerSequence: durations cannot be empty")
        if any(d <= 0 for d in durations):
            raise ValueError("TimerSequence: all durations must be > 0")

        self.timers: list[Timer] = [
            Timer(d, autostart=False) for d in durations
        ]
        self.names: list[str] = (
            list(names) if names is not None
            else [str(i) for i in range(len(durations))]
        )
        if len(self.timers) != len(self.names):
            raise ValueError(
                "TimerSequence: names and durations must have the same length"
            )

        self.repeat: bool = repeat
        self.active: bool = autostart
        self._index: int = 0

        if autostart:
            self.timers[0].reset()

    # ------------------------------------------------------------------
    # Tick
    # ------------------------------------------------------------------
    def update(self, dt: float) -> bool:
        """Advance the sequence by `dt`. Returns True on a stage transition."""
        if not self.active:
            return False

        finished_any = False
        remaining_dt = dt

        while self.active and remaining_dt > 0:
            current = self.timers[self._index]
            stage_remaining = current.remaining_time

            if remaining_dt < stage_remaining:
                current.update(remaining_dt)
                break

            # Consume this stage exactly, carry the rest forward.
            current.update(stage_remaining)
            remaining_dt -= stage_remaining
            self._advance()
            finished_any = True

        return finished_any

    def _advance(self) -> None:
        if self._index + 1 < len(self.timers):
            self._index += 1
            self.timers[self._index].reset()
        elif self.repeat:
            self._index = 0
            self.timers[0].reset()
        else:
            self.active = False

    # ------------------------------------------------------------------
    # Control
    # ------------------------------------------------------------------
    def reset(self) -> None:
        self._index = 0
        self.active = True
        for t in self.timers:
            t.stop()
        self.timers[0].reset()

    def stop(self) -> None:
        self.active = False
        for t in self.timers:
            t.stop()

    # ------------------------------------------------------------------
    # Views
    # ------------------------------------------------------------------
    @property
    def stage(self) -> int:
        return self._index

    @property
    def stage_name(self) -> str:
        return self.names[self._index]

    @property
    def done(self) -> bool:
        return (not self.repeat) and (not self.active)

    @property
    def stage_progress(self) -> float:
        return self.timers[self._index].progress

    @property
    def total_progress(self) -> float:
        total: float = sum(t.duration for t in self.timers)
        if total <= 0:
            return 1.0
        done: float = sum(
            self.timers[i].duration for i in range(self._index)
        )
        return min(1.0, (done + self.timers[self._index].elapsed) / total)

    @property
    def current_timer(self) -> Timer:
        """The Timer for the current stage. Escape hatch for advanced use —
        read/modify it directly when the sequence API doesn't cover what
        you need. Always returns the last stage's timer after completion."""
        return self.timers[self._index]