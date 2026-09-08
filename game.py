#!/usr/bin/env python3
"""
Terminal Racing - An ASCII Arcade Racing Game for the Linux Terminal.
====================================================================
Designed for Docker and Linux terminals using Python standard library 'curses'.

Controls:
  - Left / A / H   : Steer Left
  - Right / D / L  : Steer Right
  - P / Space      : Pause / Resume
  - R              : Restart (after Game Over)
  - Q / Escape     : Quit
"""

try:
    import curses
except ImportError:
    try:
        import windows_curses as curses
    except ImportError:
        curses = None

import os
import random
import sys
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

# -----------------------------------------------------------------------------
# Configuration & Constants
# -----------------------------------------------------------------------------
TARGET_FPS = 30
FRAME_DELAY_MS = int(1000 / TARGET_FPS)

# Minimum required terminal dimensions
MIN_ROWS = 24
MIN_COLS = 54

# Road configuration
ROAD_WIDTH = 29          # Width of the asphalt including borders & dividers
ROAD_LANES = 3           # 3 lanes
LANE_WIDTH = 8           # Each lane is 8 characters wide (8 * 3 + 2 dividers + 2 borders = 28..29)
CAR_WIDTH = 5            # ASCII car width
CAR_HEIGHT = 3           # ASCII car height

HIGH_SCORE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "highscore.txt")

# ASCII Sprites (5 columns x 3 rows)
PLAYER_SPRITE = [
    r" /^\ ",
    r"|[P]|",
    r"d---b",
]

ENEMY_SPRITES = [
    # Sedan
    [
        r" .-. ",
        r"|[1]|",
        r"'-=-'",
    ],
    # Fast Racer
    [
        r" /V\ ",
        r"|[X]|",
        r"d---b",
    ],
    # Truck / Van
    [
        r"|===|",
        r"| T |",
        r"|===|",
    ],
    # Taxi
    [
        r" .T. ",
        r"|TXI|",
        r"'-=-'",
    ],
]

CRASH_SPRITE = [
    r"\ * /",
    r"*BOOM*",
    r"/ * /",
]

# Color Pair IDs
CP_DEFAULT = 1
CP_ROAD_BORDER = 2
CP_ROAD_LANE = 3
CP_PLAYER = 4
CP_ENEMY_1 = 5
CP_ENEMY_2 = 6
CP_ENEMY_3 = 7
CP_ENEMY_4 = 8
CP_HUD_LABEL = 9
CP_HUD_VALUE = 10
CP_CRASH = 11
CP_TITLE = 12
CP_GRASS = 13


@dataclass
class Enemy:
    x: float
    y: float
    speed: float
    sprite_type: int
    passed: bool = False

    @property
    def sprite(self) -> List[str]:
        return ENEMY_SPRITES[self.sprite_type % len(ENEMY_SPRITES)]

    @property
    def color_pair(self) -> int:
        return CP_ENEMY_1 + (self.sprite_type % 4)


class HighScoreManager:
    """Safely loads and saves local high score."""

    @staticmethod
    def load() -> int:
        try:
            if os.path.exists(HIGH_SCORE_FILE):
                with open(HIGH_SCORE_FILE, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    return int(content) if content.isdigit() else 0
        except Exception:
            pass
        return 0

    @staticmethod
    def save(score: int) -> None:
        try:
            with open(HIGH_SCORE_FILE, "w", encoding="utf-8") as f:
                f.write(str(int(score)))
        except Exception:
            pass


class TextBufferStdscr:
    """Virtual terminal screen for headless simulation and frame capturing."""
    def __init__(self, height: int = 24, width: int = 60):
        self.height = height
        self.width = width
        self.buffer = [[" " for _ in range(width)] for _ in range(height)]

    def getmaxyx(self) -> Tuple[int, int]:
        return (self.height, self.width)

    def nodelay(self, flag: bool) -> None:
        pass

    def keypad(self, flag: bool) -> None:
        pass

    def erase(self) -> None:
        self.buffer = [[" " for _ in range(self.width)] for _ in range(self.height)]

    def refresh(self) -> None:
        pass

    def addstr(self, y: int, x: int, text: str, attr: int = 0) -> None:
        if 0 <= y < self.height and 0 <= x < self.width:
            for i, ch in enumerate(text):
                if x + i < self.width:
                    self.buffer[y][x + i] = ch

    def render_to_string(self) -> str:
        return "\n".join("".join(row) for row in self.buffer)


class TerminalRacingGame:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.high_score = HighScoreManager.load()
        self.init_curses()
        self.reset_game_state()

    def init_curses(self) -> None:
        """Set up terminal attributes and color pairs."""
        if not curses:
            return

        try:
            curses.curs_set(0)          # Hide cursor
        except Exception:
            pass

        self.stdscr.nodelay(True)   # Non-blocking getch
        self.stdscr.keypad(True)    # Enable special keys (arrows)

        try:
            if hasattr(curses, "has_colors") and curses.has_colors():
                curses.start_color()
                curses.use_default_colors()

                # Initialize color pairs
                curses.init_pair(CP_DEFAULT, curses.COLOR_WHITE, -1)
                curses.init_pair(CP_ROAD_BORDER, curses.COLOR_CYAN, -1)
                curses.init_pair(CP_ROAD_LANE, curses.COLOR_YELLOW, -1)
                curses.init_pair(CP_PLAYER, curses.COLOR_GREEN, -1)
                curses.init_pair(CP_ENEMY_1, curses.COLOR_RED, -1)
                curses.init_pair(CP_ENEMY_2, curses.COLOR_YELLOW, -1)
                curses.init_pair(CP_ENEMY_3, curses.COLOR_MAGENTA, -1)
                curses.init_pair(CP_ENEMY_4, curses.COLOR_CYAN, -1)
                curses.init_pair(CP_HUD_LABEL, curses.COLOR_CYAN, -1)
                curses.init_pair(CP_HUD_VALUE, curses.COLOR_WHITE, -1)
                curses.init_pair(CP_CRASH, curses.COLOR_WHITE, curses.COLOR_RED)
                curses.init_pair(CP_TITLE, curses.COLOR_YELLOW, -1)
                curses.init_pair(CP_GRASS, curses.COLOR_GREEN, -1)
        except Exception:
            pass

    def reset_game_state(self) -> None:
        """Reset all variables for a fresh game session."""
        self.state = "START_SCREEN"  # START_SCREEN, PLAYING, PAUSED, CRASHING, GAME_OVER
        self.score = 0
        self.distance = 0.0
        self.enemies_passed = 0
        self.lives = 3
        self.speed_kmh = 60.0
        self.level = 1

        self.road_scroll_offset = 0.0
        self.enemies: List[Enemy] = []
        self.scenery_dots: List[Tuple[int, int, str]] = []

        # Road boundaries in terminal coords
        self.update_dimensions()

        # Place player in middle lane near bottom
        self.player_x = float(self.road_left + 1 + LANE_WIDTH + (LANE_WIDTH - CAR_WIDTH) // 2)
        self.player_y = float(self.road_bottom - CAR_HEIGHT - 1)

        self.crash_timer = 0.0
        self.spawn_timer = 0.0
        self.last_frame_time = time.monotonic()

    def update_dimensions(self) -> None:
        """Recalculate layout coordinates based on terminal size."""
        self.term_height, self.term_width = self.stdscr.getmaxyx()

        # Road layout
        self.road_height = max(16, self.term_height - 6)
        self.road_top = 2
        self.road_bottom = self.road_top + self.road_height
        self.road_left = max(2, (self.term_width - ROAD_WIDTH) // 2 - 6)
        self.road_right = self.road_left + ROAD_WIDTH

        # HUD Side Panel
        self.hud_left = self.road_right + 3

    def get_lane_x(self, lane_index: int) -> int:
        """Calculate X coordinate for a given lane (0, 1, or 2)."""
        lane_inner_x = self.road_left + 1 + (lane_index * (LANE_WIDTH + 1))
        # Center car in the lane
        return lane_inner_x + max(0, (LANE_WIDTH - CAR_WIDTH) // 2)

    def spawn_enemy(self) -> None:
        """Spawn an enemy vehicle safely without blocking all lanes."""
        # Check active enemies near the top (y < 7)
        top_enemies = [e for e in self.enemies if e.y < 7]
        occupied_lanes = set()
        for e in top_enemies:
            # Determine which lane the enemy roughly occupies
            for l in range(ROAD_LANES):
                lx = self.get_lane_x(l)
                if abs(e.x - lx) < 4:
                    occupied_lanes.add(l)

        # Anti-wall guarantee: Always leave at least one lane open
        free_lanes = [l for l in range(ROAD_LANES) if l not in occupied_lanes]
        if not free_lanes:
            return  # Skip spawning this frame to prevent an impossible road block

        target_lane = random.choice(free_lanes)
        spawn_x = float(self.get_lane_x(target_lane))
        spawn_y = float(self.road_top - CAR_HEIGHT)

        # Vary speed slightly for realism
        speed_factor = random.uniform(0.85, 1.15)
        sprite_type = random.randint(0, len(ENEMY_SPRITES) - 1)

        self.enemies.append(
            Enemy(
                x=spawn_x,
                y=spawn_y,
                speed=speed_factor,
                sprite_type=sprite_type,
            )
        )

    def check_collision(self, enemy: Enemy) -> bool:
        """Bounding box collision check between player and enemy."""
        px1 = self.player_x + 1
        px2 = self.player_x + CAR_WIDTH - 1
        py1 = self.player_y
        py2 = self.player_y + CAR_HEIGHT - 0.2

        ex1 = enemy.x + 1
        ex2 = enemy.x + CAR_WIDTH - 1
        ey1 = enemy.y
        ey2 = enemy.y + CAR_HEIGHT - 0.2

        # Check for overlap
        if px1 < ex2 and px2 > ex1 and py1 < ey2 and py2 > ey1:
            return True
        return False

    def handle_input(self) -> bool:
        """Read and process user input. Returns False if user wants to quit."""
        try:
            key = self.stdscr.getch()
        except Exception:
            key = -1

        if key == -1:
            return True

        # Quit keys
        if key in (ord("q"), ord("Q"), 27):  # 27 = Escape
            return False

        # Start Screen input
        if self.state == "START_SCREEN":
            if key in (ord(" "), ord("\n"), ord("\r"), curses.KEY_ENTER, ord("r"), ord("R")):
                self.state = "PLAYING"
            return True

        # Game Over input
        if self.state == "GAME_OVER":
            if key in (ord("r"), ord("R"), ord(" "), ord("\n"), curses.KEY_ENTER):
                self.reset_game_state()
                self.state = "PLAYING"
            return True

        # Pause toggle
        if key in (ord("p"), ord("P")):
            if self.state == "PLAYING":
                self.state = "PAUSED"
            elif self.state == "PAUSED":
                self.state = "PLAYING"
            return True

        # Steering (Only during active gameplay)
        if self.state == "PLAYING":
            # Left
            if key in (curses.KEY_LEFT, ord("a"), ord("A"), ord("h"), ord("H")):
                min_x = self.road_left + 1
                self.player_x = max(min_x, self.player_x - 3)
            # Right
            elif key in (curses.KEY_RIGHT, ord("d"), ord("D"), ord("l"), ord("L")):
                max_x = self.road_right - CAR_WIDTH - 1
                self.player_x = min(max_x, self.player_x + 3)

        return True

    def update(self, dt: float) -> None:
        """Update game physics, enemies, and score."""
        if self.state != "PLAYING" and self.state != "CRASHING":
            return

        # Handle crash recovery timer
        if self.state == "CRASHING":
            self.crash_timer -= dt
            if self.crash_timer <= 0:
                if self.lives <= 0:
                    self.state = "GAME_OVER"
                    if self.score > self.high_score:
                        self.high_score = self.score
                        HighScoreManager.save(self.high_score)
                else:
                    # Respawn player in middle lane
                    self.player_x = float(self.get_lane_x(1))
                    # Clear nearby enemies to give player breathing room
                    self.enemies = [e for e in self.enemies if e.y > self.road_top + 10 or e.y < self.road_top]
                    self.state = "PLAYING"
            return

        # Smooth speed ramp-up based on score & distance
        self.speed_kmh = 60.0 + min(160.0, self.distance * 0.15 + self.enemies_passed * 8.0)

        # Simulation speed factor
        sim_speed = (self.speed_kmh / 60.0) * 12.0 * dt

        # Update distance, score & level
        self.distance += sim_speed * 1.5
        self.score = int(self.distance) + (self.enemies_passed * 50)
        self.level = 1 + int(self.score / 500)
        if self.score > self.high_score:
            self.high_score = self.score

        # Road scroll animation
        self.road_scroll_offset = (self.road_scroll_offset + sim_speed) % 4

        # Spawn enemies
        self.spawn_timer += dt
        spawn_interval = max(0.9, 2.2 - (self.level * 0.18))
        if self.spawn_timer >= spawn_interval:
            self.spawn_timer = 0.0
            self.spawn_enemy()

        # Update enemies
        surviving_enemies = []
        for enemy in self.enemies:
            # Move enemy downwards relative to player speed
            enemy.y += (sim_speed * 0.75 * enemy.speed)

            # Check if player passed this enemy
            if not enemy.passed and enemy.y > (self.player_y + CAR_HEIGHT):
                enemy.passed = True
                self.enemies_passed += 1

            # Check collision
            if self.check_collision(enemy):
                self.lives -= 1
                self.state = "CRASHING"
                self.crash_timer = 0.9  # Brief crash animation freeze
                return

            # Keep enemy if still on or near screen
            if enemy.y < self.road_bottom + 4:
                surviving_enemies.append(enemy)

        self.enemies = surviving_enemies

    def safe_addstr(self, y: int, x: int, text: str, attr: int = 0) -> None:
        """Safely render text within window bounds without throwing curses errors."""
        if 0 <= y < self.term_height and 0 <= x < self.term_width:
            available_width = self.term_width - x
            if available_width > 0:
                try:
                    self.stdscr.addstr(y, x, text[:available_width], attr)
                except curses.error:
                    pass

    def cp(self, pair_id: int, attr: int = 0) -> int:
        """Safely retrieve curses color pair attribute or fallback to attr in headless mode."""
        if not curses:
            return attr
        try:
            return curses.color_pair(pair_id) | attr
        except Exception:
            return attr

    def draw_road(self) -> None:
        """Render the road borders, asphalt, and scrolling dashed lane dividers."""
        offset = int(self.road_scroll_offset)

        for y in range(self.road_top, self.road_bottom):
            # Left & Right grass / shoulders
            if self.road_left > 0:
                self.safe_addstr(y, self.road_left - 1, "|", self.cp(CP_GRASS))
            if self.road_right < self.term_width:
                self.safe_addstr(y, self.road_right, "|", self.cp(CP_GRASS))

            # Road Left Border
            self.safe_addstr(y, self.road_left, "║", self.cp(CP_ROAD_BORDER, curses.A_BOLD if curses else 0))

            # Road asphalt fill
            self.safe_addstr(y, self.road_left + 1, " " * (ROAD_WIDTH - 2), self.cp(CP_DEFAULT))

            # Road Right Border
            self.safe_addstr(y, self.road_right - 1, "║", self.cp(CP_ROAD_BORDER, curses.A_BOLD if curses else 0))

            # Lane Dividers (Dashed lines scrolling down)
            # Pattern repeats every 4 characters
            is_dash = ((y + offset) % 4) < 2
            char = "│" if is_dash else " "
            for lane in range(1, ROAD_LANES):
                div_x = self.road_left + (lane * (LANE_WIDTH + 1))
                if is_dash:
                    self.safe_addstr(y, div_x, char, self.cp(CP_ROAD_LANE, curses.A_BOLD if curses else 0))

    def draw_player(self) -> None:
        """Render the player car or the crash effect."""
        px = int(self.player_x)
        py = int(self.player_y)

        if self.state == "CRASHING":
            # Flashing explosion sprite
            for i, line in enumerate(CRASH_SPRITE):
                self.safe_addstr(py + i, px, line, self.cp(CP_CRASH, curses.A_BOLD if curses else 0))
        else:
            for i, line in enumerate(PLAYER_SPRITE):
                self.safe_addstr(py + i, px, line, self.cp(CP_PLAYER, curses.A_BOLD if curses else 0))

    def draw_enemies(self) -> None:
        """Render all active enemy vehicles."""
        for enemy in self.enemies:
            ex = int(enemy.x)
            ey = int(enemy.y)
            sprite = enemy.sprite
            for i, line in enumerate(sprite):
                row = ey + i
                if self.road_top <= row < self.road_bottom:
                    self.safe_addstr(row, ex, line, self.cp(enemy.color_pair, curses.A_BOLD if curses else 0))

    def draw_hud(self) -> None:
        """Render the dashboard / status panel."""
        # Top banner
        title = " ═══ TERMINAL RACING ═══ "
        title_x = max(2, (self.term_width - len(title)) // 2)
        self.safe_addstr(0, title_x, title, self.cp(CP_TITLE, curses.A_BOLD if curses else 0))

        # Right Side HUD Panel
        hx = self.hud_left
        hy = self.road_top + 1

        # Border for HUD
        hud_w = 20
        self.safe_addstr(hy - 1, hx, "╔" + "═" * (hud_w - 2) + "╗", self.cp(CP_HUD_LABEL))
        self.safe_addstr(hy + 0, hx, "║  DASHBOARD        ║", self.cp(CP_TITLE, curses.A_BOLD if curses else 0))
        self.safe_addstr(hy + 1, hx, "╠" + "═" * (hud_w - 2) + "╣", self.cp(CP_HUD_LABEL))

        # Score
        self.safe_addstr(hy + 2, hx, f"║ Score: {self.score:<10} ║", self.cp(CP_HUD_VALUE))

        # High Score
        self.safe_addstr(hy + 3, hx, f"║ Best:  {self.high_score:<10} ║", self.cp(CP_HUD_VALUE))

        # Lives (Hearts or [X] fallback)
        lives_display = "♥ " * self.lives + "· " * (3 - self.lives)
        self.safe_addstr(hy + 4, hx, f"║ Lives: {lives_display:<10} ║", self.cp(CP_ENEMY_1, curses.A_BOLD if curses else 0))

        # Speed
        self.safe_addstr(hy + 5, hx, f"║ Speed: {int(self.speed_kmh)} km/h{' ' * max(0, 5 - len(str(int(self.speed_kmh))))} ║", self.cp(CP_HUD_VALUE))

        # Level
        self.safe_addstr(hy + 6, hx, f"║ Level: {self.level:<10} ║", self.cp(CP_HUD_VALUE))

        # Passed
        self.safe_addstr(hy + 7, hx, f"║ Passed: {self.enemies_passed:<9} ║", self.cp(CP_HUD_VALUE))

        self.safe_addstr(hy + 8, hx, "╚" + "═" * (hud_w - 2) + "╝", self.cp(CP_HUD_LABEL))

        # Controls reference at bottom
        footer = "[A/D or ←/→] Steer   [P] Pause   [Q] Quit"
        self.safe_addstr(self.term_height - 2, max(2, (self.term_width - len(footer)) // 2), footer, self.cp(CP_DEFAULT, curses.A_DIM if curses else 0))

    def draw_start_screen(self) -> None:
        """Render the start menu."""
        center_y = self.term_height // 2 - 6
        center_x = max(2, (self.term_width - 46) // 2)

        logo = [
            r" _____ _____ ____  __  __ ___ _   _    _    _     ",
            r"|_   _| ____|  _ \|  \/  |_ _| \ | |  / \  | |    ",
            r"  | | |  _| | |_) | |\/| || ||  \| | / _ \ | |    ",
            r"  | | | |___|  _ <| |  | || || |\  |/ ___ \| |___ ",
            r"  |_| |_____|_| \_\_|  |_|___|_| \_/_/   \_\_____|",
            r"     ____      _    ____ ___ _   _  ____          ",
            r"    |  _ \    / \  / ___|_ _| \ | |/ ___|         ",
            r"    | |_) |  / _ \| |    | ||  \| | |  _          ",
            r"    |  _ <  / ___ \ |___ | || |\  | |_| |         ",
            r"    |_| \_\/_/   \_\____|___|_| \_|\____|         ",
        ]

        for i, line in enumerate(logo):
            self.safe_addstr(center_y + i, center_x, line, self.cp(CP_TITLE, curses.A_BOLD if curses else 0))

        box_y = center_y + len(logo) + 2
        box_w = 44
        bx = max(2, (self.term_width - box_w) // 2)

        self.safe_addstr(box_y, bx, "╔" + "═" * (box_w - 2) + "╗", self.cp(CP_ROAD_BORDER))
        self.safe_addstr(box_y + 1, bx, "║          DODGE TRAFFIC & SURVIVE!        ║", self.cp(CP_DEFAULT, curses.A_BOLD if curses else 0))
        self.safe_addstr(box_y + 2, bx, "╠" + "═" * (box_w - 2) + "╣", self.cp(CP_ROAD_BORDER))
        self.safe_addstr(box_y + 3, bx, "║  Controls:                               ║", self.cp(CP_HUD_LABEL))
        self.safe_addstr(box_y + 4, bx, "║   • [A / D] or [← / →] : Steer Car       ║", self.cp(CP_DEFAULT))
        self.safe_addstr(box_y + 5, bx, "║   • [P]                : Pause Game      ║", self.cp(CP_DEFAULT))
        self.safe_addstr(box_y + 6, bx, "║   • [Q]                : Quit            ║", self.cp(CP_DEFAULT))
        self.safe_addstr(box_y + 7, bx, "╠" + "═" * (box_w - 2) + "╣", self.cp(CP_ROAD_BORDER))
        self.safe_addstr(box_y + 8, bx, f"║  Best Record: {self.high_score:<26} ║", self.cp(CP_HUD_VALUE, curses.A_BOLD if curses else 0))
        self.safe_addstr(box_y + 9, bx, "╚" + "═" * (box_w - 2) + "╝", self.cp(CP_ROAD_BORDER))

        prompt = ">>> PRESS SPACE OR ENTER TO START <<<"
        self.safe_addstr(box_y + 11, max(2, (self.term_width - len(prompt)) // 2), prompt, self.cp(CP_PLAYER, curses.A_BOLD if curses else 0))

    def draw_pause_overlay(self) -> None:
        """Render pause pop-up."""
        box_w = 26
        box_h = 5
        by = self.term_height // 2 - 2
        bx = max(2, (self.term_width - box_w) // 2)

        self.safe_addstr(by + 0, bx, "╔" + "═" * (box_w - 2) + "╗", self.cp(CP_TITLE, curses.A_BOLD if curses else 0))
        self.safe_addstr(by + 1, bx, "║       PAUSED       ║", self.cp(CP_TITLE, curses.A_BOLD if curses else 0))
        self.safe_addstr(by + 2, bx, "║ Press [P] to resume║", self.cp(CP_DEFAULT))
        self.safe_addstr(by + 3, bx, "║ Press [Q] to quit  ║", self.cp(CP_DEFAULT))
        self.safe_addstr(by + 4, bx, "╚" + "═" * (box_w - 2) + "╝", self.cp(CP_TITLE, curses.A_BOLD if curses else 0))

    def draw_game_over_screen(self) -> None:
        """Render Game Over summary modal."""
        box_w = 34
        box_h = 9
        by = self.term_height // 2 - 4
        bx = max(2, (self.term_width - box_w) // 2)

        self.safe_addstr(by + 0, bx, "╔" + "═" * (box_w - 2) + "╗", self.cp(CP_ENEMY_1, curses.A_BOLD if curses else 0))
        self.safe_addstr(by + 1, bx, "║          GAME OVER!          ║", self.cp(CP_ENEMY_1, curses.A_BOLD if curses else 0))
        self.safe_addstr(by + 2, bx, "╠" + "═" * (box_w - 2) + "╣", self.cp(CP_ENEMY_1))
        self.safe_addstr(by + 3, bx, f"║  Final Score: {self.score:<14} ║", self.cp(CP_HUD_VALUE, curses.A_BOLD if curses else 0))
        self.safe_addstr(by + 4, bx, f"║  Best Score:  {self.high_score:<14} ║", self.cp(CP_TITLE, curses.A_BOLD if curses else 0))
        self.safe_addstr(by + 5, bx, f"║  Cars Passed: {self.enemies_passed:<14} ║", self.cp(CP_HUD_VALUE))
        self.safe_addstr(by + 6, bx, "╠" + "═" * (box_w - 2) + "╣", self.cp(CP_ENEMY_1))
        self.safe_addstr(by + 7, bx, "║  [R] Play Again   [Q] Quit   ║", self.cp(CP_DEFAULT, curses.A_BOLD if curses else 0))
        self.safe_addstr(by + 8, bx, "╚" + "═" * (box_w - 2) + "╝", self.cp(CP_ENEMY_1))

    def render(self) -> None:
        """Draw the complete game frame."""
        self.stdscr.erase()
        self.update_dimensions()

        # Terminal size check
        if self.term_height < MIN_ROWS or self.term_width < MIN_COLS:
            msg1 = "Terminal window is too small!"
            msg2 = f"Current size: {self.term_width}x{self.term_height}"
            msg3 = f"Required: at least {MIN_COLS}x{MIN_ROWS}"
            msg4 = "Please resize your terminal window."
            cy = max(0, self.term_height // 2 - 2)
            self.safe_addstr(cy + 0, max(0, (self.term_width - len(msg1)) // 2), msg1, curses.A_BOLD if curses else 0)
            self.safe_addstr(cy + 1, max(0, (self.term_width - len(msg2)) // 2), msg2)
            self.safe_addstr(cy + 2, max(0, (self.term_width - len(msg3)) // 2), msg3)
            self.safe_addstr(cy + 3, max(0, (self.term_width - len(msg4)) // 2), msg4)
            self.stdscr.refresh()
            return

        if self.state == "START_SCREEN":
            self.draw_start_screen()
        else:
            # Draw racing environment
            self.draw_road()
            self.draw_enemies()
            self.draw_player()
            self.draw_hud()

            if self.state == "PAUSED":
                self.draw_pause_overlay()
            elif self.state == "GAME_OVER":
                self.draw_game_over_screen()

        self.stdscr.refresh()

    def ai_steer(self) -> None:
        """Autonomous AI driver: assesses upcoming traffic threats and steers towards safest lane."""
        if self.state != "PLAYING":
            return

        # Find current lane index (0, 1, or 2)
        current_lane = 0
        min_dist = float("inf")
        for l in range(ROAD_LANES):
            lx = self.get_lane_x(l)
            if abs(self.player_x - lx) < min_dist:
                min_dist = abs(self.player_x - lx)
                current_lane = l

        # Assess danger in each lane
        lane_danger = [0.0] * ROAD_LANES
        for e in self.enemies:
            # Threat window: enemy is above player and within 14 lines
            vert_dist = self.player_y - e.y
            if 0 < vert_dist < 14:
                weight = (14.0 - vert_dist)
                for l in range(ROAD_LANES):
                    lx = self.get_lane_x(l)
                    if abs(e.x - lx) < 4:
                        lane_danger[l] += weight

        # Pick safest lane
        best_lane = current_lane
        lowest_danger = lane_danger[current_lane]
        for l in range(ROAD_LANES):
            if lane_danger[l] < lowest_danger - 1.0:
                lowest_danger = lane_danger[l]
                best_lane = l

        # Steer toward best lane
        target_x = float(self.get_lane_x(best_lane))
        if self.player_x < target_x:
            self.player_x = min(target_x, self.player_x + 3)
        elif self.player_x > target_x:
            self.player_x = max(target_x, self.player_x - 3)

    def run(self, auto_pilot: bool = False) -> None:
        """Main game loop."""
        running = True
        while running:
            current_time = time.monotonic()
            dt = current_time - self.last_frame_time
            self.last_frame_time = current_time

            # Clamp dt in case of system pauses
            dt = min(dt, 0.1)

            # Input handling or autopilot
            if auto_pilot:
                if self.state == "START_SCREEN":
                    self.state = "PLAYING"
                elif self.state == "GAME_OVER":
                    self.reset_game_state()
                    self.state = "PLAYING"
                self.ai_steer()
            else:
                running = self.handle_input()
                if not running:
                    break

            # Simulation update
            self.update(dt)

            # Render frame
            self.render()

            # Framerate limiter
            elapsed = time.monotonic() - current_time
            sleep_time = (1.0 / TARGET_FPS) - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)


def simulate_game(frames: int = 50) -> None:
    """Run simulated game session and print formatted ASCII gameplay frames."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    text_screen = TextBufferStdscr(height=24, width=60)
    game = TerminalRacingGame(text_screen)
    game.state = "PLAYING"

    print("\n" + "=" * 62)
    print("       >>>  TERMINAL RACING - AUTONOMOUS SIMULATION RUN  <<<")
    print("=" * 62 + "\n")

    snapshots = [1, 15, 30, 45, frames]

    for frame in range(1, frames + 1):
        dt = 1.0 / TARGET_FPS
        game.ai_steer()
        game.update(dt)
        game.render()

        if frame in snapshots or frame == frames:
            print(f"--- [ FRAME {frame}/{frames} | Score: {game.score} | Speed: {int(game.speed_kmh)} km/h | Lives: {game.lives} ] ---")
            print(text_screen.render_to_string())
            print("\n" + "-" * 60 + "\n")
            time.sleep(0.05)


def main():
    """Application entrypoint with clean curses initialization and terminal cleanup."""
    if "--simulate" in sys.argv or "--sim" in sys.argv:
        frames = 50
        for arg in sys.argv:
            if arg.isdigit():
                frames = int(arg)
        simulate_game(frames=frames)
        return

    auto_pilot = "--demo" in sys.argv or "--auto" in sys.argv

    if curses is None:
        print(
            "\n[Notice] The 'curses' library is required for interactive mode.\n"
            "You can run the interactive game via Docker:\n\n"
            "    docker build -t terminal-racing .\n"
            "    docker run -it --rm terminal-racing\n\n"
            "Or run the terminal simulation:\n\n"
            "    python game.py --simulate 50\n",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        curses.wrapper(lambda stdscr: TerminalRacingGame(stdscr).run(auto_pilot=auto_pilot))
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"\nTerminal Racing encountered an error: {e}", file=sys.stderr)
    finally:
        # Extra guarantee that cursor is restored
        sys.stdout.write("\033[?25h\033[0m")
        sys.stdout.flush()
        print("\nThanks for playing Terminal Racing! 🏎️💨\n")


if __name__ == "__main__":
    main()
