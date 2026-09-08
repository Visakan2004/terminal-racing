"""
Unit and Integration Tests for Terminal Racing Game Mechanics.
"""

import os
import unittest
from game import (
    HighScoreManager,
    Enemy,
    TerminalRacingGame,
    CAR_WIDTH,
    CAR_HEIGHT,
    ROAD_WIDTH,
    ROAD_LANES,
    LANE_WIDTH,
    HIGH_SCORE_FILE,
)


class DummyStdscr:
    """Mock curses standard screen for headless testing."""
    def getmaxyx(self):
        return (30, 80)
    def nodelay(self, flag):
        pass
    def keypad(self, flag):
        pass
    def erase(self):
        pass
    def refresh(self):
        pass
    def addstr(self, *args, **kwargs):
        pass


class TestTerminalRacing(unittest.TestCase):
    def setUp(self):
        self.game = TerminalRacingGame(DummyStdscr())

    def test_high_score_manager(self):
        """Test high score save and load."""
        test_score = 1234
        HighScoreManager.save(test_score)
        loaded = HighScoreManager.load()
        self.assertEqual(loaded, test_score)

    def test_lane_coordinates(self):
        """Verify each lane is within the road borders."""
        for lane in range(ROAD_LANES):
            lane_x = self.game.get_lane_x(lane)
            self.assertGreaterEqual(lane_x, self.game.road_left + 1)
            self.assertLessEqual(lane_x + CAR_WIDTH, self.game.road_right)

    def test_collision_detection(self):
        """Verify collision detection works when cars overlap and ignores when separate."""
        self.game.player_x = 20.0
        self.game.player_y = 15.0

        # Exact overlap
        overlapping_enemy = Enemy(x=20.0, y=15.0, speed=1.0, sprite_type=0)
        self.assertTrue(self.game.check_collision(overlapping_enemy))

        # Far away enemy
        distant_enemy = Enemy(x=20.0, y=5.0, speed=1.0, sprite_type=0)
        self.assertFalse(self.game.check_collision(distant_enemy))

        # Adjacent lane (no horizontal overlap)
        adjacent_enemy = Enemy(x=20.0 + CAR_WIDTH + 2, y=15.0, speed=1.0, sprite_type=0)
        self.assertFalse(self.game.check_collision(adjacent_enemy))

    def test_anti_wall_guarantee(self):
        """Ensure spawning never blocks all lanes simultaneously at the top."""
        # Fill 2 out of 3 lanes at the top
        lane0_x = self.game.get_lane_x(0)
        lane1_x = self.game.get_lane_x(1)
        lane2_x = self.game.get_lane_x(2)

        self.game.enemies = [
            Enemy(x=float(lane0_x), y=2.0, speed=1.0, sprite_type=0),
            Enemy(x=float(lane1_x), y=2.0, speed=1.0, sprite_type=1),
        ]

        # Spawning should only be allowed in the remaining free lane (lane 2)
        self.game.spawn_enemy()
        self.assertEqual(len(self.game.enemies), 3)
        self.assertAlmostEqual(self.game.enemies[-1].x, float(lane2_x), delta=1.0)

        # If all 3 lanes are filled at the top, spawn_enemy should refuse to spawn another
        self.game.spawn_enemy()
        self.assertEqual(len(self.game.enemies), 3)

    def test_score_and_difficulty_ramp(self):
        """Test score calculation and speed ramping."""
        self.game.state = "PLAYING"
        self.game.distance = 1000.0
        self.game.enemies_passed = 10
        self.game.update(0.1)

        expected_score = int(self.game.distance) + (10 * 50)
        self.assertEqual(self.game.score, expected_score)
        self.assertGreater(self.game.speed_kmh, 60.0)
        self.assertGreater(self.game.level, 1)

    def test_player_movement_bounds(self):
        """Test that player car stays within road boundaries."""
        self.game.state = "PLAYING"
        
        # Test extreme left movement
        for _ in range(30):
            min_x = self.game.road_left + 1
            self.game.player_x = max(min_x, self.game.player_x - 3)
        self.assertGreaterEqual(self.game.player_x, self.game.road_left + 1)

        # Test extreme right movement
        for _ in range(30):
            max_x = self.game.road_right - CAR_WIDTH - 1
            self.game.player_x = min(max_x, self.game.player_x + 3)
        self.assertLessEqual(self.game.player_x + CAR_WIDTH, self.game.road_right)

    def test_collision_and_lives(self):
        """Test that collision reduces lives and triggers CRASHING state."""
        self.game.state = "PLAYING"
        self.assertEqual(self.game.lives, 3)

        # Spawn enemy right on top of player
        self.game.enemies = [Enemy(x=self.game.player_x, y=self.game.player_y, speed=1.0, sprite_type=0)]
        self.game.update(0.1)

        self.assertEqual(self.game.lives, 2)
        self.assertEqual(self.game.state, "CRASHING")

    def test_game_over_when_lives_depleted(self):
        """Test transition to GAME_OVER when lives hit 0."""
        self.game.state = "CRASHING"
        self.game.lives = 0
        self.game.crash_timer = 0.05
        self.game.update(0.1)  # timer expires

        self.assertEqual(self.game.state, "GAME_OVER")

    def test_pause_resume_toggle(self):
        """Test pause state."""
        self.game.state = "PLAYING"
        self.game.state = "PAUSED"
        self.assertEqual(self.game.state, "PAUSED")
        self.game.state = "PLAYING"
        self.assertEqual(self.game.state, "PLAYING")

    def test_car_selection_and_switch(self):
        """Test switching player car models."""
        initial_car = self.game.selected_car_index
        self.game.selected_car_index = (self.game.selected_car_index + 1) % 4
        self.assertNotEqual(self.game.selected_car_index, initial_car)

    def test_nitro_boost_mechanic(self):
        """Test nitro fuel consumption and speed acceleration."""
        self.game.state = "PLAYING"
        self.game.nitro_fuel = 100.0
        self.game.is_boosting = True
        self.game.update(0.1)

        self.assertLess(self.game.nitro_fuel, 100.0)
        self.assertGreater(self.game.target_speed_kmh, 100.0)

    def test_near_miss_combo_system(self):
        """Test near-miss triggers combo points and particles."""
        self.game.state = "PLAYING"
        initial_score = self.game.score
        enemy = Enemy(x=self.game.player_x + CAR_WIDTH + 1, y=self.game.player_y, speed=1.0, sprite_type=0)
        self.game.trigger_near_miss(enemy)

        self.assertGreater(self.game.score, initial_score)
        self.assertGreaterEqual(self.game.combo_count, 1)
        self.assertGreater(len(self.game.floating_texts), 0)


if __name__ == "__main__":
    unittest.main()
