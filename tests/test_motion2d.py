"""
test_motion2d.py
================
Minimal test suite for Motion2D v1.0.

Covers:
- The three workflow primitives (step_velocity, authority, update)
- Core behavior of each public class
- A syntax check for the demos

Deliberately skips: parameter validation, private attributes,
performance benchmarks, and type-hint checks. If a change breaks
one of those, the runtime behavior tests will usually catch the
downstream effect anyway.
"""

import pytest
import math
from pygame.math import Vector2

from motion2d import (
    Rotator,
    Facing,
    NoHeading,
    KinematicBody,
    SimpleMotion,
    PlatformerMotion,
    TopDownMotion,
    BaseMotion,
    Motion2D,
)


@pytest.fixture
def dt():
    return 1 / 60


# ============================================================================
# Workflow primitives — the invariants the library is built on
# ============================================================================

class TestWorkflowPrimitives:
    """These three tests define the shape of the library.

    If any of them fails, something fundamental has changed.
    """

    def test_step_velocity_does_not_move_position(self, dt):
        """step_velocity returns a delta but leaves position untouched."""
        m = Motion2D.top_down(pos=(100, 100), speed=300)
        m.move_right()
        pos_before = Vector2(m.position)

        delta = m.step_velocity(dt)

        assert m.position == pos_before
        assert delta.x > 0
        assert delta.y == 0

    def test_update_commits_position(self, dt):
        """update() advances position by the proposed delta."""
        m = Motion2D.top_down(pos=(0, 0), speed=300)
        m.move_right()

        m.update(dt)

        assert m.position.x > 0
        assert m.position.y == 0

    def test_authority_overrides_velocity(self, dt):
        """authority() returns delta from given velocity, skipping physics."""
        m = Motion2D.top_down(pos=(100, 100), speed=300)

        delta = m.authority(dt, velocity=(500, 0))

        assert delta.x == pytest.approx(500 / 60)
        assert delta.y == 0

    def test_authority_skips_gravity(self, dt):
        """Unlike step_velocity, authority does not apply gravity."""
        m = Motion2D.platformer(pos=(100, 100), gravity=1000)

        # step_velocity applies gravity
        m.step_velocity(dt)
        assert m.velocity.y > 0

        # authority with a fixed velocity skips gravity
        m.authority(dt, velocity=(0, 0))
        assert m.velocity.y == 0

    def test_step_velocity_clears_intent(self, dt):
        """After step_velocity, intent is empty for the next frame."""
        m = Motion2D.top_down(speed=300)
        m.move_right()

        m.step_velocity(dt)

        assert m._move_intent == Vector2(0, 0)


# ============================================================================
# Headings
# ============================================================================

class TestRotator:
    def test_vector_at_cardinal_angles(self):
        assert Rotator(angle=0).vector == Vector2(1, 0)

        v = Rotator(angle=90).vector
        assert v.x == pytest.approx(0, abs=1e-6)
        assert v.y == pytest.approx(1)

        v = Rotator(angle=180).vector
        assert v.x == pytest.approx(-1)
        assert v.y == pytest.approx(0, abs=1e-6)

        v = Rotator(angle=270).vector
        assert v.x == pytest.approx(0, abs=1e-6)
        assert v.y == pytest.approx(-1)

    def test_rotate_at_fixed_speed(self):
        r = Rotator(angle=0, rotate_speed=180)
        r.rotate(1, 1 / 60)
        assert r.angle == pytest.approx(3.0)

    def test_turn_toward_moves_gradually(self):
        r = Rotator(angle=0, rotate_speed=180)
        r.turn_toward(90, 1 / 60)
        assert r.angle == pytest.approx(3.0)

    def test_turn_toward_snaps_when_close(self):
        r = Rotator(angle=89.5, rotate_speed=180)
        r.turn_toward(90, 1 / 60)
        assert r.angle == 90.0

    def test_aim_with_snap(self):
        r = Rotator(angle=0)
        r.aim(Vector2(0, 1), snap=True)
        assert r.angle == 90

    def test_aim_ignores_zero_vector(self):
        r = Rotator(angle=45)
        r.aim(Vector2(0, 0), snap=True)
        assert r.angle == 45


class TestFacing:
    def test_free_direction_normalizes(self):
        f = Facing(Vector2(2, 2))
        assert f.vector.x == pytest.approx(0.70710678)
        assert f.vector.y == pytest.approx(0.70710678)

    def test_two_direction_horizontal(self):
        f = Facing(directions=2, axis='horizontal')
        f.aim(Vector2(0.7, 0.7))
        assert f.vector == Vector2(1, 0)
        assert f.is_right()

    def test_four_direction_prefers_horizontal_on_tie(self):
        f = Facing(directions=4)
        f.aim(Vector2(1, 1))
        assert f.vector == Vector2(1, 0)

    def test_eight_direction_snaps_to_diagonal(self):
        f = Facing(directions=8)
        f.aim(Vector2(1, 1))
        expected = math.sqrt(0.5)
        assert f.vector.x == pytest.approx(expected)
        assert f.vector.y == pytest.approx(expected)

    def test_zero_vector_is_ignored(self):
        f = Facing(Vector2(1, 0))
        f.aim(Vector2(0, 0))
        assert f.vector == Vector2(1, 0)


class TestNoHeading:
    def test_returns_default_vector(self):
        n = NoHeading(Vector2(1, 0))
        assert n.vector == Vector2(1, 0)

    def test_aim_does_nothing(self):
        n = NoHeading(Vector2(1, 0))
        n.aim(Vector2(0, 1))
        assert n.vector == Vector2(1, 0)


# ============================================================================
# KinematicBody
# ============================================================================

class TestKinematicBody:
    def test_basic_integration(self, dt):
        b = KinematicBody(pos=(0, 0))
        b.velocity = Vector2(60, 120)
        b.update(dt)
        assert b.position == Vector2(1, 2)

    def test_step_velocity_returns_delta(self, dt):
        b = KinematicBody(pos=(0, 0))
        b.velocity = Vector2(60, 120)
        delta = b.step_velocity(dt)
        assert delta == Vector2(1, 2)
        assert b.position == Vector2(0, 0)

    def test_max_speed_clamp(self, dt):
        b = KinematicBody(max_speed=100)
        b.velocity = Vector2(200, 0)
        b.update(dt)
        assert b.speed == pytest.approx(100)

    def test_drag_applies_when_inactive(self, dt):
        b = KinematicBody(drag=0.1)
        b.velocity = Vector2(100, 0)
        b.update(dt)
        assert b.velocity.x < 100

    def test_drag_skipped_when_active(self, dt):
        b = KinematicBody(drag=0.1)
        b.velocity = Vector2(100, 0)
        b.mark_active(x=True)
        b.update(dt)
        assert b.velocity.x == 100

    def test_apply_impulse(self):
        b = KinematicBody()
        b.apply_impulse(Vector2(50, 100))
        assert b.velocity == Vector2(50, 100)

    def test_apply_force(self, dt):
        b = KinematicBody()
        b.apply_force(Vector2(60, 120), dt)
        assert b.velocity == Vector2(1, 2)

    def test_stop(self):
        b = KinematicBody()
        b.velocity = Vector2(50, 100)
        b.stop(x=True, y=False)
        assert b.velocity == Vector2(0, 100)


# ============================================================================
# SimpleMotion
# ============================================================================

class TestSimpleMotion:
    def test_go_directions(self):
        m = SimpleMotion(speed=100)
        m.go_right()
        assert m.velocity == Vector2(100, 0)
        m.go_left()
        assert m.velocity == Vector2(-100, 0)
        m.go_up()
        assert m.velocity == Vector2(0, -100)
        m.go_down()
        assert m.velocity == Vector2(0, 100)

    def test_go_angle(self):
        m = SimpleMotion(speed=100)
        m.go_angle(90)
        assert m.velocity.x == pytest.approx(0, abs=1e-6)
        assert m.velocity.y == pytest.approx(100)

    def test_go_ignores_zero_vector(self):
        m = SimpleMotion(speed=100)
        m.go_right()
        m.go(Vector2(0, 0))
        assert m.velocity == Vector2(100, 0)

    def test_go_reverse(self):
        m = SimpleMotion(speed=100)
        m.go_right()
        m.go_reverse()
        assert m.velocity == Vector2(-100, 0)

    def test_update_moves_position(self, dt):
        m = SimpleMotion(pos=(0, 0), speed=60)
        m.go_right()
        m.update(dt)
        assert m.position == Vector2(1, 0)

    def test_damp(self):
        m = SimpleMotion()
        m.velocity = Vector2(100, 200)
        m.damp(x=0.5, y=0.5)
        assert m.velocity == Vector2(50, 100)

    def test_apply_gravity(self, dt):
        m = SimpleMotion()
        m.apply_gravity(dt, force=600)
        assert m.velocity.y == pytest.approx(10)


# ============================================================================
# PlatformerMotion
# ============================================================================

class TestPlatformerMotion:
    def test_default_heading_is_horizontal_facing(self):
        m = PlatformerMotion()
        assert isinstance(m.heading, Facing)
        assert m.heading.directions == 2
        assert m.heading.axis == "horizontal"

    def test_jump_sets_upward_velocity(self):
        m = PlatformerMotion(jump_strength=500)
        m.jump()
        assert m.velocity.y == -500

    def test_gravity_applies_without_intent(self, dt):
        m = PlatformerMotion(gravity=1000)
        m.update(dt)
        assert m.velocity.y == pytest.approx(1000 * dt)

    def test_horizontal_intent_accelerates(self, dt):
        m = PlatformerMotion(speed=300, acceleration=2000)
        m.move_right()
        m.update(dt)
        assert m.velocity.x > 0

    def test_max_fall_speed_caps_gravity(self, dt):
        m = PlatformerMotion(gravity=10000, max_fall_speed=500)
        # Apply many frames so gravity would exceed the cap
        for _ in range(60):
            m.update(dt)
        assert m.velocity.y == 500

    def test_auto_face_follows_movement(self, dt):
        m = PlatformerMotion(auto_face=True)
        m.move_right()
        m.update(dt)
        assert m.heading.vector == Vector2(1, 0)


# ============================================================================
# TopDownMotion
# ============================================================================

class TestTopDownMotion:
    def test_no_gravity(self, dt):
        m = TopDownMotion(speed=400)
        m.update(dt)
        assert m.velocity.y == 0

    def test_intent_accelerates(self, dt):
        m = TopDownMotion(speed=400, acceleration=2500)
        m.move_right()
        m.update(dt)
        assert m.velocity.x > 0

    def test_diagonal_intent_is_normalized(self, dt):
        m = TopDownMotion(speed=400, acceleration=10000)
        m.add_move(1, 1)
        m.update(dt)
        # Both axes should have equal velocity
        assert m.velocity.x == pytest.approx(m.velocity.y, rel=1e-3)

    def test_auto_aim_follows_intent(self, dt):
        heading = Facing(Vector2(1, 0))
        m = TopDownMotion(heading=heading, auto_aim=True)
        m.move_up()
        m.update(dt)
        assert m.heading.vector.x == pytest.approx(0, abs=1e-6)
        assert m.heading.vector.y == pytest.approx(-1)

    def test_grip_reduces_lateral_velocity(self, dt):
        """Grip pulls velocity toward heading direction."""
        heading = Rotator(angle=0)  # heading east
        m = TopDownMotion(heading=heading, auto_aim=False, grip=10.0)
        # Set velocity pointing northeast (diagonal to heading)
        m.velocity = Vector2(100, 100)
        initial_lateral = m.velocity.y
        m.step_velocity(dt)
        # Lateral component should shrink
        assert abs(m.velocity.y) < abs(initial_lateral)


# ============================================================================
# BaseMotion
# ============================================================================

class TestBaseMotion:
    def test_move_forward_uses_heading(self):
        m = TopDownMotion(heading=Facing(Vector2(0, 1)))
        m.move_forward()
        assert m._move_intent == Vector2(0, 1)

    def test_strafe_left_perpendicular_to_heading(self):
        m = TopDownMotion(heading=Facing(Vector2(0, 1)))  # facing down
        m.strafe_left()
        # Perpendicular to (0, 1) is (1, 0) or (-1, 0) depending on side
        assert m._move_intent.length() == pytest.approx(1.0)

    def test_add_move_normalizes_large_vector(self):
        m = TopDownMotion()
        m.add_move(2, 2)
        assert m._move_intent.x == pytest.approx(0.70710678)
        assert m._move_intent.y == pytest.approx(0.70710678)

    def test_set_intent_replaces(self):
        m = TopDownMotion()
        m.move_right()
        m.set_intent(Vector2(0, 1))
        assert m._move_intent == Vector2(0, 1)

    def test_clear_intent(self):
        m = TopDownMotion()
        m.move_right()
        m.clear_intent()
        assert m._move_intent == Vector2(0, 0)

    def test_dash_adds_to_velocity(self):
        m = TopDownMotion(heading=Facing(Vector2(1, 0)))
        m.velocity = Vector2(100, 0)
        m.dash(power=500)
        assert m.velocity == Vector2(600, 0)

    def test_approach(self):
        assert BaseMotion._approach(0, 10, 5) == 5
        assert BaseMotion._approach(0, 10, 15) == 10
        assert BaseMotion._approach(10, 0, 5) == 5


# ============================================================================
# Motion2D factory
# ============================================================================

class TestMotion2DFactory:
    def test_simple_returns_simple_motion(self):
        m = Motion2D.simple(pos=(10, 20), speed=100)
        assert isinstance(m, SimpleMotion)
        assert m.position == Vector2(10, 20)
        assert m.speed == 100

    def test_platformer_returns_platformer_motion(self):
        m = Motion2D.platformer(pos=(10, 20), speed=300)
        assert isinstance(m, PlatformerMotion)
        assert m.speed == 300

    def test_top_down_returns_top_down_motion(self):
        m = Motion2D.top_down(pos=(10, 20), speed=400)
        assert isinstance(m, TopDownMotion)
        assert m.speed == 400

    def test_custom_heading_is_passed_through(self):
        heading = Facing(Vector2(1, 0))
        m = Motion2D.top_down(heading=heading)
        assert m.heading is heading


# ============================================================================
# Edge cases
# ============================================================================

class TestEdgeCases:
    def test_zero_dt_clears_intent(self):
        m = TopDownMotion()
        m.move_right()
        m.update(0)
        assert m._move_intent == Vector2(0, 0)
        assert m.position == Vector2(0, 0)

    def test_large_dt_is_clamped(self):
        """A huge dt should not tunnel the position to absurd values."""
        m = TopDownMotion(speed=100)
        m.move_right()
        m.update(10.0)
        assert abs(m.position.x) < 100  # clamped to 0.1s of movement

    def test_rapid_direction_changes(self, dt):
        """No NaN, no crash, no explosion."""
        m = TopDownMotion(acceleration=10000)
        for _ in range(10):
            m.move_right()
            m.update(dt)
            m.clear_intent()
            m.move_left()
            m.update(dt)
        assert not math.isnan(m.position.x)
        assert not math.isnan(m.position.y)


# ============================================================================
# Demo syntax check
# ============================================================================

class TestDemos:
    """Verify that every demo file at least parses.

    Doesn't run them — just checks for syntax errors, so a broken demo
    doesn't reach the repo.
    """

    def test_all_demos_compile(self):
        import os
        demo_dir = os.path.join(os.path.dirname(__file__), "demos")
        if not os.path.isdir(demo_dir):
            pytest.skip("demos/ directory not found")

        for fname in sorted(os.listdir(demo_dir)):
            if fname.startswith("demo_") and fname.endswith(".py"):
                path = os.path.join(demo_dir, fname)
                with open(path, "r", encoding="utf-8") as f:
                    source = f.read()
                # compile() raises SyntaxError if the file is broken
                compile(source, path, "exec")
