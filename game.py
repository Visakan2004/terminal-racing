#!/usr/bin/env python3
"""
🏎️ TERMINAL RACING - Enhanced Arcade Edition
=============================================
High-performance ASCII arcade racing game for Linux & Docker terminals.
Featuring rich color effects, multiple car chassis, dynamic nitro boost,
tire skid trails, near-miss combos, weather/day-night cycles, and headlamp beams.

Controls:
  - Steer: [Left / A] or [Right / D]
  - Nitro Turbo Boost: [Up / W / Shift]
  - Switch Car: [C]
  - Pause: [P]
  - Restart: [R]
  - Quit: [Q / Esc]
"""

try:
    import curses
except ImportError:
    try:
        import windows_curses as curses
    except ImportError:
        curses = None

import math
import os
import random
import sys
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# -----------------------------------------------------------------------------
# Configuration & Constants
# -----------------------------------------------------------------------------
TARGET_FPS = 30
FRAME_DELAY_MS = int(1000 / TARGET_FPS)

MIN_ROWS = 24
MIN_COLS = 58

ROAD_WIDTH = 31          # Asphalt width
ROAD_LANES = 3           # 3 lanes
LANE_WIDTH = 9           # Width per lane
CAR_WIDTH = 5            # ASCII car width
CAR_HEIGHT = 3           # Standard ASCII car height

HIGH_SCORE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "highscore.txt")

# -----------------------------------------------------------------------------
# Player Car Models (Selectable with [C])
# -----------------------------------------------------------------------------
PLAYER_CARS = [
    {
        "name": "HYPER TURBO GT",
        "desc": "Aerodynamic speedster with dual rear diffusers",
        "sprites": {
            "straight": [
                r" /▲\ ",
                r"|█▓█|",
                r"db=db",
            ],
            "left": [
                r"/▲\  ",
                r"\\█▓\\",
                r"db=db",
            ],
            "right": [
                r"  /▲\\",
                r"//█▓//",
                r"db=db",
            ],
        },
        "color_pair": 4, # CP_PLAYER
        "flame_color": 14, # CP_NITRO
    },
    {
        "name": "CYBERPUNK RACER",
        "desc": "Neon-infused night runner with energy coils",
        "sprites": {
            "straight": [
                r" /══\ ",
                r"|⚡P⚡|",
                r"d---b",
            ],
            "left": [
                r"/══\  ",
                r"\\⚡P\\",
                r"d---b",
            ],
            "right": [
                r"  /══\\",
                r"//P⚡//",
                r"d---b",
            ],
        },
        "color_pair": 17, # CP_CYBER
        "flame_color": 16, # CP_SPARK
    },
    {
        "name": "STREET DRIFT SPEC",
        "desc": "Widebody tuner with high-downforce wing",
        "sprites": {
            "straight": [
                r" /──\ ",
                r"|[GT]|",
                r"d═══b",
            ],
            "left": [
                r"/──\  ",
                r"\\GT\\",
                r"d═══b",
            ],
            "right": [
                r"  /──\\",
                r"//GT//",
                r"d═══b",
            ],
        },
        "color_pair": 18, # CP_GOLD
        "flame_color": 14,
    },
    {
        "name": "POLICE INTERCEPTOR",
        "desc": "Twin-turbo pursuit cruiser with flashing lights",
        "sprites": {
            "straight": [
                r" .[!]. ",
                r"|911|",
                r"d---b",
            ],
            "left": [
                r" .[!]. ",
                r"\\911\\",
                r"d---b",
            ],
            "right": [
                r" .[!]. ",
                r"//911//",
                r"d---b",
            ],
        },
        "color_pair": 19, # CP_POLICE
        "flame_color": 14,
    },
]

# Legacy default sprite reference
PLAYER_SPRITE = PLAYER_CARS[0]["sprites"]["straight"]

# -----------------------------------------------------------------------------
# Enemy Car Models & Sprites
# -----------------------------------------------------------------------------
ENEMY_SPRITES = [
    # 0: Sport Sedan
    [
        r" .-. ",
        r"|[1]|",
        r"'-=-'",
    ],
    # 1: Red Rival Racer
    [
        r" /V\ ",
        r"|{X}|",
        r"d---b",
    ],
    # 2: Big-Rig Cargo Van
    [
        r"|===|",
        r"| TR|",
        r"|===|",
    ],
    # 3: City Taxi
    [
        r" .T. ",
        r"|TXI|",
        r"'-=-'",
    ],
    # 4: Heavy Transport Truck (Tall)
    [
        r"[═══]",
        r"|CAR|",
        r"|GO!|",
        r"[###]",
    ],
    # 5: Street Muscle Car
    [
        r" /──\ ",
        r"|{M}|",
        r"d---b",
    ],
]

CRASH_SPRITE = [
    r"\ * * /",
    r"*💥BOOM💥*",
    r"/ * * \\",
]

# -----------------------------------------------------------------------------
# Color Pair IDs
# -----------------------------------------------------------------------------
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
CP_NITRO = 14
CP_SKID = 15
CP_SPARK = 16
CP_CYBER = 17
CP_GOLD = 18
CP_POLICE = 19
CP_COMBO = 20
CP_HEADLIGHT = 21


@dataclass
class Particle:
    x: float
    y: float
    char: str
    color_pair: int
    life: float
    max_life: float
    vx: float = 0.0
    vy: float = 0.0


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    color_pair: int
    life: float = 1.0


@dataclass
class SkidMark:
    x: int
    y: float
    char: str = "│"
    life: float = 1.2


@dataclass
class Enemy:
    x: float
    y: float
    speed: float
    sprite_type: int
    passed: bool = False
    is_tall: bool = False

    def __post_init__(self):
        if self.sprite_type == 4:
            self.is_tall = True

    @property
    def sprite(self) -> List[str]:
        return ENEMY_SPRITES[self.sprite_type % len(ENEMY_SPRITES)]

    @property
    def height(self) -> int:
        return len(self.sprite)

    @property
    def color_pair(self) -> int:
        type_mod = self.sprite_type % 6
        if type_mod == 0:
            return CP_ENEMY_1
        elif type_mod == 1:
            return CP_ENEMY_2
        elif type_mod == 2:
            return CP_ENEMY_3
        elif type_mod == 3:
            return CP_ENEMY_4
        elif type_mod == 4:
            return CP_GOLD
        else:
            return CP_CYBER


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
        self.selected_car_index = 0
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

                # Basic palettes
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

                # Extended effect palettes
                curses.init_pair(CP_NITRO, curses.COLOR_CYAN, -1)
                curses.init_pair(CP_SKID, curses.COLOR_BLACK, -1)
                curses.init_pair(CP_SPARK, curses.COLOR_YELLOW, -1)
                curses.init_pair(CP_CYBER, curses.COLOR_MAGENTA, -1)
                curses.init_pair(CP_GOLD, curses.COLOR_YELLOW, -1)
                curses.init_pair(CP_POLICE, curses.COLOR_BLUE, -1)
                curses.init_pair(CP_COMBO, curses.COLOR_MAGENTA, -1)
                curses.init_pair(CP_HEADLIGHT, curses.COLOR_YELLOW, -1)
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
        self.target_speed_kmh = 60.0
        self.level = 1

        # Nitro turbo system
        self.nitro_fuel = 100.0
        self.is_boosting = False
        self.nitro_cooldown = 0.0

        # Combo & Near-miss system
        self.combo_count = 0
        self.combo_multiplier = 1.0
        self.combo_timer = 0.0

        # Visual steering tilt
        self.tilt_state = "straight"  # "straight", "left", "right"
        self.tilt_timer = 0.0

        # Particle effects & trails
        self.particles: List[Particle] = []
        self.floating_texts: List[FloatingText] = []
        self.skid_marks: List[SkidMark] = []
        self.rain_drops: List[Tuple[float, float, str]] = []

        # Road animation & environment
        self.road_scroll_offset = 0.0
        self.day_time = 0.0  # 0.0 to 100.0 cycle for Day -> Sunset -> Night
        self.siren_tick = 0

        self.enemies: List[Enemy] = []
        self.update_dimensions()

        # Place player in middle lane near bottom
        self.player_x = float(self.get_lane_x(1))
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
        self.road_left = max(2, (self.term_width - ROAD_WIDTH) // 2 - 7)
        self.road_right = self.road_left + ROAD_WIDTH

        # HUD Side Panel
        self.hud_left = self.road_right + 3

    def get_lane_x(self, lane_index: int) -> int:
        """Calculate X coordinate for a given lane (0, 1, or 2)."""
        lane_inner_x = self.road_left + 1 + (lane_index * (LANE_WIDTH + 1))
        return lane_inner_x + max(0, (LANE_WIDTH - CAR_WIDTH) // 2)

    def trigger_near_miss(self, enemy: Enemy) -> None:
        """Award combo points and trigger floating text effect for thrilling near-misses."""
        self.combo_count += 1
        self.combo_multiplier = min(4.0, 1.0 + (self.combo_count * 0.5))
        self.combo_timer = 2.5
        bonus = int(100 * self.combo_multiplier)
        self.score += bonus

        # Floating popup above car
        tag = "NEAR MISS!" if self.combo_count == 1 else f"COMBO x{self.combo_multiplier:.1f}!"
        self.floating_texts.append(
            FloatingText(
                x=float(self.player_x - 1),
                y=float(self.player_y - 1),
                text=f"+{bonus} {tag}",
                color_pair=CP_COMBO,
                life=1.0,
            )
        )

        # Sparks near the player chassis
        for _ in range(6):
            self.particles.append(
                Particle(
                    x=self.player_x + random.uniform(0, CAR_WIDTH),
                    y=self.player_y + random.uniform(0, CAR_HEIGHT),
                    char=random.choice(["*", "✦", "•", "+"]),
                    color_pair=CP_SPARK,
                    life=0.4,
                    max_life=0.4,
                    vx=random.uniform(-1.5, 1.5),
                    vy=random.uniform(-1.0, 1.0),
                )
            )

    def spawn_enemy(self) -> None:
        """Spawn an enemy vehicle safely without blocking all lanes."""
        top_enemies = [e for e in self.enemies if e.y < 7]
        occupied_lanes = set()
        for e in top_enemies:
            for l in range(ROAD_LANES):
                lx = self.get_lane_x(l)
                if abs(e.x - lx) < 4:
                    occupied_lanes.add(l)

        free_lanes = [l for l in range(ROAD_LANES) if l not in occupied_lanes]
        if not free_lanes:
            return  # Prevent impossible wall

        target_lane = random.choice(free_lanes)
        spawn_x = float(self.get_lane_x(target_lane))
        sprite_type = random.randint(0, len(ENEMY_SPRITES) - 1)
        spawn_y = float(self.road_top - (4 if sprite_type == 4 else CAR_HEIGHT))
        speed_factor = random.uniform(0.85, 1.15)

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
        ey2 = enemy.y + enemy.height - 0.2

        return px1 < ex2 and px2 > ex1 and py1 < ey2 and py2 > ey1

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
            if key in (ord("c"), ord("C")):
                self.selected_car_index = (self.selected_car_index + 1) % len(PLAYER_CARS)
                return True
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

        # Active gameplay controls
        if self.state == "PLAYING":
            # Switch car in game
            if key in (ord("c"), ord("C")):
                self.selected_car_index = (self.selected_car_index + 1) % len(PLAYER_CARS)
                car_name = PLAYER_CARS[self.selected_car_index]["name"]
                self.floating_texts.append(
                    FloatingText(
                        x=float(self.player_x - 3),
                        y=float(self.player_y - 1),
                        text=f"CAR: {car_name}",
                        color_pair=CP_CYBER,
                        life=1.0,
                    )
                )

            # Steer Left
            elif key in (curses.KEY_LEFT, ord("a"), ord("A"), ord("h"), ord("H")):
                min_x = self.road_left + 1
                self.player_x = max(min_x, self.player_x - 3)
                self.tilt_state = "left"
                self.tilt_timer = 0.25
                # Add drift skid mark
                self.skid_marks.append(SkidMark(x=int(self.player_x + 1), y=self.player_y + CAR_HEIGHT, char="/"))
                self.skid_marks.append(SkidMark(x=int(self.player_x + CAR_WIDTH - 2), y=self.player_y + CAR_HEIGHT, char="/"))

            # Steer Right
            elif key in (curses.KEY_RIGHT, ord("d"), ord("D"), ord("l"), ord("L")):
                max_x = self.road_right - CAR_WIDTH - 1
                self.player_x = min(max_x, self.player_x + 3)
                self.tilt_state = "right"
                self.tilt_timer = 0.25
                # Add drift skid mark
                self.skid_marks.append(SkidMark(x=int(self.player_x + 1), y=self.player_y + CAR_HEIGHT, char="\\"))
                self.skid_marks.append(SkidMark(x=int(self.player_x + CAR_WIDTH - 2), y=self.player_y + CAR_HEIGHT, char="\\"))

            # Nitro Boost
            elif key in (curses.KEY_UP, ord("w"), ord("W"), ord(" "), ord("\t")):
                if self.nitro_fuel >= 15.0:
                    self.is_boosting = True
                    self.nitro_fuel = max(0.0, self.nitro_fuel - 20.0)
                    self.floating_texts.append(
                        FloatingText(
                            x=float(self.player_x),
                            y=float(self.player_y - 1),
                            text=">> NITRO BOOST! <<",
                            color_pair=CP_NITRO,
                            life=0.8,
                        )
                    )

        return True

    def update(self, dt: float) -> None:
        """Update game physics, enemies, particles, and score."""
        if self.state != "PLAYING" and self.state != "CRASHING":
            return

        self.siren_tick = (self.siren_tick + 1) % 60
        self.day_time = (self.day_time + (dt * 1.5)) % 100.0

        # Tilt recovery timer
        if self.tilt_timer > 0:
            self.tilt_timer -= dt
            if self.tilt_timer <= 0:
                self.tilt_state = "straight"

        # Handle crash explosion and recovery
        if self.state == "CRASHING":
            self.crash_timer -= dt

            # Spawn explosion debris particles
            if random.random() < 0.8:
                for _ in range(4):
                    self.particles.append(
                        Particle(
                            x=self.player_x + random.uniform(-1, CAR_WIDTH + 1),
                            y=self.player_y + random.uniform(-1, CAR_HEIGHT + 1),
                            char=random.choice(["💥", "*", "#", "@", "%", "•", "x"]),
                            color_pair=random.choice([CP_CRASH, CP_SPARK, CP_ENEMY_1]),
                            life=0.6,
                            max_life=0.6,
                            vx=random.uniform(-3.0, 3.0),
                            vy=random.uniform(-2.0, 2.0),
                        )
                    )

            if self.crash_timer <= 0:
                if self.lives <= 0:
                    self.state = "GAME_OVER"
                    if self.score > self.high_score:
                        self.high_score = self.score
                        HighScoreManager.save(self.high_score)
                else:
                    self.player_x = float(self.get_lane_x(1))
                    self.enemies = [e for e in self.enemies if e.y > self.road_top + 10 or e.y < self.road_top]
                    self.state = "PLAYING"
            return

        # Nitro mechanics
        if self.is_boosting:
            self.target_speed_kmh = 160.0 + min(120.0, self.distance * 0.15)
            self.nitro_fuel = max(0.0, self.nitro_fuel - (dt * 25.0))
            if self.nitro_fuel <= 0:
                self.is_boosting = False
        else:
            self.target_speed_kmh = 60.0 + min(160.0, self.distance * 0.15 + self.enemies_passed * 8.0)
            self.nitro_fuel = min(100.0, self.nitro_fuel + (dt * 12.0))

        # Smooth speed interpolation
        self.speed_kmh += (self.target_speed_kmh - self.speed_kmh) * min(1.0, dt * 4.0)

        # Simulation speed factor
        sim_speed = (self.speed_kmh / 60.0) * 12.0 * dt

        # Distance & Score
        self.distance += sim_speed * 1.5
        base_score = int(self.distance) + (self.enemies_passed * 50)
        self.score = base_score + (self.combo_count * 25)
        self.level = 1 + int(self.score / 500)
        if self.score > self.high_score:
            self.high_score = self.score

        # Combo timer decay
        if self.combo_timer > 0:
            self.combo_timer -= dt
            if self.combo_timer <= 0:
                self.combo_count = 0
                self.combo_multiplier = 1.0

        # Road scroll animation
        self.road_scroll_offset = (self.road_scroll_offset + sim_speed) % 4

        # Spawn exhaust flame particles behind tires
        flame_color = PLAYER_CARS[self.selected_car_index]["flame_color"]
        if self.is_boosting or random.random() < 0.6:
            flame_char = random.choice(["🔥", "^", "*", "!", ":", "▲"]) if self.is_boosting else random.choice(["^", "·", ":", "."])
            # Left wheel flame
            self.particles.append(
                Particle(
                    x=self.player_x + 0.5,
                    y=self.player_y + CAR_HEIGHT + random.uniform(0.1, 0.4),
                    char=flame_char,
                    color_pair=flame_color if self.is_boosting else CP_DEFAULT,
                    life=0.25 if self.is_boosting else 0.15,
                    max_life=0.25,
                    vy=random.uniform(0.5, 1.5),
                )
            )
            # Right wheel flame
            self.particles.append(
                Particle(
                    x=self.player_x + CAR_WIDTH - 1.5,
                    y=self.player_y + CAR_HEIGHT + random.uniform(0.1, 0.4),
                    char=flame_char,
                    color_pair=flame_color if self.is_boosting else CP_DEFAULT,
                    life=0.25 if self.is_boosting else 0.15,
                    max_life=0.25,
                    vy=random.uniform(0.5, 1.5),
                )
            )

        # Update and cull particles
        live_particles = []
        for p in self.particles:
            p.life -= dt
            p.x += p.vx * dt * 10
            p.y += (p.vy + sim_speed * 0.5) * dt * 5
            if p.life > 0 and self.road_top <= p.y < self.road_bottom + 2:
                live_particles.append(p)
        self.particles = live_particles

        # Update floating texts
        live_texts = []
        for ft in self.floating_texts:
            ft.life -= dt
            ft.y -= dt * 1.5
            if ft.life > 0:
                live_texts.append(ft)
        self.floating_texts = live_texts

        # Update skid marks
        live_skids = []
        for sk in self.skid_marks:
            sk.life -= dt
            sk.y += (sim_speed * 0.7)
            if sk.life > 0 and sk.y < self.road_bottom:
                live_skids.append(sk)
        self.skid_marks = live_skids

        # Spawn enemies
        self.spawn_timer += dt
        spawn_interval = max(0.8, 2.0 - (self.level * 0.15))
        if self.spawn_timer >= spawn_interval:
            self.spawn_timer = 0.0
            self.spawn_enemy()

        # Update enemies & collision
        surviving_enemies = []
        for enemy in self.enemies:
            enemy.y += (sim_speed * 0.75 * enemy.speed)

            # Check if player overtook this enemy
            if not enemy.passed and enemy.y > (self.player_y + CAR_HEIGHT):
                enemy.passed = True
                self.enemies_passed += 1

                # Check near-miss condition (close horizontal distance)
                if abs(self.player_x - enemy.x) <= (CAR_WIDTH + 2):
                    self.trigger_near_miss(enemy)

            # Check collision
            if self.check_collision(enemy):
                self.lives -= 1
                self.state = "CRASHING"
                self.crash_timer = 1.0
                self.combo_count = 0
                self.combo_multiplier = 1.0
                return

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
        """Render the road borders, asphalt, headlight illumination, and scrolling lane dividers."""
        offset = int(self.road_scroll_offset)
        is_night = self.day_time > 60.0

        for y in range(self.road_top, self.road_bottom):
            # Left & Right roadside scenery
            if self.road_left > 0:
                scenery_char = "♣" if ((y + offset) % 6 == 0) else "|"
                self.safe_addstr(y, self.road_left - 1, scenery_char, self.cp(CP_GRASS))
            if self.road_right < self.term_width:
                scenery_char = "♦" if ((y + offset + 2) % 6 == 0) else "|"
                self.safe_addstr(y, self.road_right, scenery_char, self.cp(CP_GRASS))

            # Road Left Border
            self.safe_addstr(y, self.road_left, "║", self.cp(CP_ROAD_BORDER, curses.A_BOLD if curses else 0))

            # Road asphalt fill (with speed streaks if high speed or night lighting)
            asphalt_char = " "
            if self.is_boosting and ((y + offset) % 5 == 0):
                asphalt_char = "·"
            self.safe_addstr(y, self.road_left + 1, asphalt_char * (ROAD_WIDTH - 2), self.cp(CP_DEFAULT))

            # Road Right Border
            self.safe_addstr(y, self.road_right - 1, "║", self.cp(CP_ROAD_BORDER, curses.A_BOLD if curses else 0))

            # Lane Dividers
            is_dash = ((y + offset) % 4) < 2
            char = "│" if is_dash else " "
            for lane in range(1, ROAD_LANES):
                div_x = self.road_left + (lane * (LANE_WIDTH + 1))
                if is_dash:
                    self.safe_addstr(y, div_x, char, self.cp(CP_ROAD_LANE, curses.A_BOLD if curses else 0))

        # Render Skid Marks
        for sk in self.skid_marks:
            sy = int(sk.y)
            if self.road_top <= sy < self.road_bottom and self.road_left < sk.x < self.road_right - 1:
                self.safe_addstr(sy, sk.x, sk.char, self.cp(CP_DEFAULT, curses.A_DIM if curses else 0))

        # Headlight Beams projecting ahead of player car
        if self.state == "PLAYING":
            px = int(self.player_x)
            py = int(self.player_y)
            for dist in range(1, 6):
                beam_y = py - dist
                if self.road_top <= beam_y < self.road_bottom:
                    beam_left = max(self.road_left + 1, px - dist // 2)
                    beam_right = min(self.road_right - 2, px + CAR_WIDTH + dist // 2)
                    self.safe_addstr(beam_y, beam_left, "\\", self.cp(CP_HEADLIGHT, curses.A_DIM if curses else 0))
                    self.safe_addstr(beam_y, beam_right - 1, "/", self.cp(CP_HEADLIGHT, curses.A_DIM if curses else 0))

    def draw_player(self) -> None:
        """Render the player car with dynamic tilt and particle effects."""
        px = int(self.player_x)
        py = int(self.player_y)
        car_info = PLAYER_CARS[self.selected_car_index]

        if self.state == "CRASHING":
            for i, line in enumerate(CRASH_SPRITE):
                self.safe_addstr(py + i, px - 1, line, self.cp(CP_CRASH, curses.A_BOLD if curses else 0))
        else:
            sprite = car_info["sprites"].get(self.tilt_state, car_info["sprites"]["straight"])
            for i, line in enumerate(sprite):
                color = car_info["color_pair"]
                # If police car, alternate flashing light
                if self.selected_car_index == 3 and i == 0:
                    color = CP_ENEMY_1 if (self.siren_tick % 10 < 5) else CP_POLICE
                self.safe_addstr(py + i, px, line, self.cp(color, curses.A_BOLD if curses else 0))

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

    def draw_particles_and_popups(self) -> None:
        """Render all active particles and floating combo texts."""
        # Particles
        for p in self.particles:
            py = int(p.y)
            px = int(p.x)
            if self.road_top <= py < self.road_bottom and 0 <= px < self.term_width:
                self.safe_addstr(py, px, p.char, self.cp(p.color_pair, curses.A_BOLD if curses else 0))

        # Floating Popups
        for ft in self.floating_texts:
            fy = int(ft.y)
            fx = int(ft.x)
            if 0 <= fy < self.term_height:
                self.safe_addstr(fy, fx, ft.text, self.cp(ft.color_pair, curses.A_BOLD if curses else 0))

    def draw_hud(self) -> None:
        """Render the dashboard, tachometer, nitro meter, and combo status."""
        title = " ═══ 🏎️ TERMINAL RACING ARCADE ═══ "
        title_x = max(2, (self.term_width - len(title)) // 2)
        self.safe_addstr(0, title_x, title, self.cp(CP_TITLE, curses.A_BOLD if curses else 0))

        hx = self.hud_left
        hy = self.road_top + 1
        hud_w = 23

        # Border for HUD
        self.safe_addstr(hy - 1, hx, "╔" + "═" * (hud_w - 2) + "╗", self.cp(CP_HUD_LABEL))
        self.safe_addstr(hy + 0, hx, "║  DASHBOARD & GAUGES ║", self.cp(CP_TITLE, curses.A_BOLD if curses else 0))
        self.safe_addstr(hy + 1, hx, "╠" + "═" * (hud_w - 2) + "╣", self.cp(CP_HUD_LABEL))

        # Score & High Score
        self.safe_addstr(hy + 2, hx, f"║ Score : {self.score:<11} ║", self.cp(CP_HUD_VALUE))
        self.safe_addstr(hy + 3, hx, f"║ Best  : {self.high_score:<11} ║", self.cp(CP_GOLD, curses.A_BOLD if curses else 0))

        # Lives
        lives_display = "♥ " * self.lives + "· " * (3 - self.lives)
        self.safe_addstr(hy + 4, hx, f"║ Lives : {lives_display:<11} ║", self.cp(CP_ENEMY_1, curses.A_BOLD if curses else 0))

        # Speedometer with color alert
        speed_int = int(self.speed_kmh)
        speed_color = CP_ENEMY_1 if speed_int >= 180 else (CP_GOLD if speed_int >= 120 else CP_HUD_VALUE)
        self.safe_addstr(hy + 5, hx, f"║ Speed : {speed_int:>3} km/h{' ' * 5} ║", self.cp(speed_color, curses.A_BOLD if curses else 0))

        # Nitro Gauge Bar
        nitro_bars = int((self.nitro_fuel / 100.0) * 8)
        nitro_bar_str = "█" * nitro_bars + "░" * (8 - nitro_bars)
        nitro_label = "⚡ BOOST!" if self.is_boosting else f"[{nitro_bar_str}]"
        self.safe_addstr(hy + 6, hx, f"║ Nitro : {nitro_label:<11} ║", self.cp(CP_NITRO, curses.A_BOLD if curses else 0))

        # Combo Multiplier
        combo_str = f"x{self.combo_multiplier:.1f} 🔥" if self.combo_count > 0 else "---"
        self.safe_addstr(hy + 7, hx, f"║ Combo : {combo_str:<11} ║", self.cp(CP_COMBO, curses.A_BOLD if curses else 0))

        # Active Car Model
        car_short = PLAYER_CARS[self.selected_car_index]["name"][:11]
        self.safe_addstr(hy + 8, hx, f"║ Car   : {car_short:<11} ║", self.cp(CP_CYBER))

        # Level & Passed
        self.safe_addstr(hy + 9, hx, f"║ Lvl/Pass: {self.level}/{self.enemies_passed:<8} ║", self.cp(CP_HUD_VALUE))

        self.safe_addstr(hy + 10, hx, "╚" + "═" * (hud_w - 2) + "╝", self.cp(CP_HUD_LABEL))

        # Controls reference at bottom
        footer = "[A/D / ←/→] Steer  [W / ↑] Nitro  [C] Car  [P] Pause  [Q] Quit"
        self.safe_addstr(self.term_height - 2, max(2, (self.term_width - len(footer)) // 2), footer, self.cp(CP_DEFAULT, curses.A_DIM if curses else 0))

    def draw_start_screen(self) -> None:
        """Render the start menu with car preview and controls."""
        center_y = max(1, self.term_height // 2 - 8)
        center_x = max(2, (self.term_width - 48) // 2)

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

        box_y = center_y + len(logo) + 1
        box_w = 48
        bx = max(2, (self.term_width - box_w) // 2)

        car_info = PLAYER_CARS[self.selected_car_index]
        self.safe_addstr(box_y, bx, "╔" + "═" * (box_w - 2) + "╗", self.cp(CP_ROAD_BORDER))
        self.safe_addstr(box_y + 1, bx, "║          🔥 ARCADE TURBO EDITION 🔥           ║", self.cp(CP_TITLE, curses.A_BOLD if curses else 0))
        self.safe_addstr(box_y + 2, bx, "╠" + "═" * (box_w - 2) + "╣", self.cp(CP_ROAD_BORDER))
        self.safe_addstr(box_y + 3, bx, f"║  Selected Car [Press C to switch]:           ║", self.cp(CP_HUD_LABEL))
        self.safe_addstr(box_y + 4, bx, f"║   ▶ {car_info['name']:<40} ║", self.cp(car_info["color_pair"], curses.A_BOLD if curses else 0))
        self.safe_addstr(box_y + 5, bx, "║  Controls:                                   ║", self.cp(CP_HUD_LABEL))
        self.safe_addstr(box_y + 6, bx, "║   • [A / D] or [← / →] : Steer & Drift       ║", self.cp(CP_DEFAULT))
        self.safe_addstr(box_y + 7, bx, "║   • [W / ↑] or [Shift] : Nitro Turbo Boost   ║", self.cp(CP_NITRO))
        self.safe_addstr(box_y + 8, bx, "║   • [C]                : Change Car Chassis  ║", self.cp(CP_DEFAULT))
        self.safe_addstr(box_y + 9, bx, "║   • [P]                : Pause / Resume      ║", self.cp(CP_DEFAULT))
        self.safe_addstr(box_y + 10, bx, "║   • [Q]                : Quit Game           ║", self.cp(CP_DEFAULT))
        self.safe_addstr(box_y + 11, bx, "╠" + "═" * (box_w - 2) + "╣", self.cp(CP_ROAD_BORDER))
        self.safe_addstr(box_y + 12, bx, f"║  High Score Record: {self.high_score:<24} ║", self.cp(CP_GOLD, curses.A_BOLD if curses else 0))
        self.safe_addstr(box_y + 13, bx, "╚" + "═" * (box_w - 2) + "╝", self.cp(CP_ROAD_BORDER))

        prompt = ">>> PRESS SPACE OR ENTER TO RACE <<<"
        self.safe_addstr(box_y + 15, max(2, (self.term_width - len(prompt)) // 2), prompt, self.cp(CP_PLAYER, curses.A_BOLD if curses else 0))

    def draw_pause_overlay(self) -> None:
        """Render pause pop-up."""
        box_w = 26
        by = self.term_height // 2 - 2
        bx = max(2, (self.term_width - box_w) // 2)

        self.safe_addstr(by + 0, bx, "╔" + "═" * (box_w - 2) + "╗", self.cp(CP_TITLE, curses.A_BOLD if curses else 0))
        self.safe_addstr(by + 1, bx, "║       PAUSED       ║", self.cp(CP_TITLE, curses.A_BOLD if curses else 0))
        self.safe_addstr(by + 2, bx, "║ Press [P] to resume║", self.cp(CP_DEFAULT))
        self.safe_addstr(by + 3, bx, "║ Press [Q] to quit  ║", self.cp(CP_DEFAULT))
        self.safe_addstr(by + 4, bx, "╚" + "═" * (box_w - 2) + "╝", self.cp(CP_TITLE, curses.A_BOLD if curses else 0))

    def draw_game_over_screen(self) -> None:
        """Render Game Over summary modal."""
        box_w = 36
        by = self.term_height // 2 - 5
        bx = max(2, (self.term_width - box_w) // 2)

        self.safe_addstr(by + 0, bx, "╔" + "═" * (box_w - 2) + "╗", self.cp(CP_ENEMY_1, curses.A_BOLD if curses else 0))
        self.safe_addstr(by + 1, bx, "║            GAME OVER!            ║", self.cp(CP_ENEMY_1, curses.A_BOLD if curses else 0))
        self.safe_addstr(by + 2, bx, "╠" + "═" * (box_w - 2) + "╣", self.cp(CP_ENEMY_1))
        self.safe_addstr(by + 3, bx, f"║  Final Score  : {self.score:<16} ║", self.cp(CP_HUD_VALUE, curses.A_BOLD if curses else 0))
        self.safe_addstr(by + 4, bx, f"║  Best Record  : {self.high_score:<16} ║", self.cp(CP_GOLD, curses.A_BOLD if curses else 0))
        self.safe_addstr(by + 5, bx, f"║  Cars Passed  : {self.enemies_passed:<16} ║", self.cp(CP_HUD_VALUE))
        self.safe_addstr(by + 6, bx, f"║  Top Speed    : {int(self.speed_kmh)} km/h{' ' * 9} ║", self.cp(CP_NITRO))
        self.safe_addstr(by + 7, bx, "╠" + "═" * (box_w - 2) + "╣", self.cp(CP_ENEMY_1))
        self.safe_addstr(by + 8, bx, "║    [R] Race Again   [Q] Quit     ║", self.cp(CP_DEFAULT, curses.A_BOLD if curses else 0))
        self.safe_addstr(by + 9, bx, "╚" + "═" * (box_w - 2) + "╝", self.cp(CP_ENEMY_1))

    def render(self) -> None:
        """Draw the complete game frame."""
        self.stdscr.erase()
        self.update_dimensions()

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
            self.draw_road()
            self.draw_enemies()
            self.draw_player()
            self.draw_particles_and_popups()
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

        current_lane = 0
        min_dist = float("inf")
        for l in range(ROAD_LANES):
            lx = self.get_lane_x(l)
            if abs(self.player_x - lx) < min_dist:
                min_dist = abs(self.player_x - lx)
                current_lane = l

        lane_danger = [0.0] * ROAD_LANES
        for e in self.enemies:
            vert_dist = self.player_y - e.y
            if 0 < vert_dist < 14:
                weight = (14.0 - vert_dist)
                for l in range(ROAD_LANES):
                    lx = self.get_lane_x(l)
                    if abs(e.x - lx) < 4:
                        lane_danger[l] += weight

        best_lane = current_lane
        lowest_danger = lane_danger[current_lane]
        for l in range(ROAD_LANES):
            if lane_danger[l] < lowest_danger - 1.0:
                lowest_danger = lane_danger[l]
                best_lane = l

        target_x = float(self.get_lane_x(best_lane))
        if self.player_x < target_x:
            self.player_x = min(target_x, self.player_x + 3)
            self.tilt_state = "right"
            self.tilt_timer = 0.2
        elif self.player_x > target_x:
            self.player_x = max(target_x, self.player_x - 3)
            self.tilt_state = "left"
            self.tilt_timer = 0.2

    def run(self, auto_pilot: bool = False) -> None:
        """Main game loop."""
        running = True
        while running:
            current_time = time.monotonic()
            dt = current_time - self.last_frame_time
            self.last_frame_time = current_time
            dt = min(dt, 0.1)

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

            self.update(dt)
            self.render()

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
            print(f"--- [ FRAME {frame}/{frames} | Score: {game.score} | Speed: {int(game.speed_kmh)} km/h | Nitro: {int(game.nitro_fuel)}% ] ---")
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
        sys.stdout.write("\033[?25h\033[0m")
        sys.stdout.flush()
        print("\nThanks for playing Terminal Racing! 🏎️💨\n")


if __name__ == "__main__":
    main()
