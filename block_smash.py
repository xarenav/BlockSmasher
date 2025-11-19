"""
BLOCK SMASHER v33
A block-breaking game with powerups and procedurally generated levels
Optimized for 1024x768 resolution

v33 Changes:
- Removed shield powerup completely (caused paddle stuck issues)
- Rebalanced powerup weights (Sticky Paddle and Extra Life increased to 10% each)
- 6 powerup types remain: Multiball, Paddle Expand, Fireball, Laser, Extra Life, Sticky Paddle
"""

import pygame
import random
import math
import sys
import json
import os
import hashlib
from dataclasses import dataclass, asdict
from typing import List, Tuple, Optional, Dict
from enum import Enum
from datetime import datetime

pygame.init()

SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
CANVAS_WIDTH = 650
CANVAS_HEIGHT = 500
FPS = 60

BG_DARK = (10, 14, 26)
BG_CARD = (18, 23, 40)
COLOR_CYAN = (64, 224, 208)
COLOR_PURPLE = (147, 112, 219)
COLOR_ORANGE = (255, 140, 0)
COLOR_PINK = (236, 72, 153)
COLOR_YELLOW = (234, 179, 8)
COLOR_FOREGROUND = (230, 237, 243)
COLOR_BORDER = (45, 50, 65)
COLOR_ERROR = (220, 38, 38)
COLOR_SUCCESS = (34, 197, 94)

GLASS_BG = (20, 25, 40, 100)
GLASS_BORDER = (64, 224, 208, 40)

class GameState(Enum):
    LOGIN = 0
    REGISTER = 1
    MAIN_MENU = 2
    MAPS_SCREEN = 3
    GAME_SCREEN = 4
    SETTINGS_SCREEN = 5
    LEADERBOARD_SCREEN = 6
    PAUSED = 7

class MapsTab(Enum):
    CURATED = 1
    PROCEDURAL = 2

class PowerupType(Enum):
    MULTIBALL = 1
    PADDLE_EXPAND = 2
    FIREBALL = 3
    LASER = 4
    EXTRA_LIFE = 5
    STICKY_PADDLE = 6

@dataclass
class Block:
    x: float
    y: float
    width: float
    height: float
    alive: bool
    color: Tuple[int, int, int]

@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    max_life: float
    size: float
    color: Tuple[int, int, int]

@dataclass
class Powerup:
    x: float
    y: float
    vy: float
    width: float
    height: float
    type: PowerupType
    alive: bool

@dataclass
class Ball:
    x: float
    y: float
    vx: float
    vy: float
    radius: float
    is_fireball: bool = False
    is_stuck: bool = False

@dataclass
class Laser:
    x: float
    y: float
    vy: float
    width: float
    height: float
    alive: bool

@dataclass
class Settings:
    master_volume: float = 75
    music_volume: float = 65
    sfx_volume: float = 80
    difficulty: str = 'medium'
    quality: str = 'high'
    particle_effects: bool = True
    screen_shake: bool = True
    show_fps: bool = False

@dataclass
class LeaderboardEntry:
    username: str
    score: int
    level: int
    timestamp: str

@dataclass
class User:
    username: str
    password_hash: str
    high_score: int = 0
    levels_completed: List[int] = None
    
    def __post_init__(self):
        if self.levels_completed is None:
            self.levels_completed = []

class DataManager:
    
    def __init__(self):
        self.users_file = 'users.json'
        self.leaderboard_file = 'leaderboard.json'
        self.users: Dict[str, User] = {}
        self.leaderboard: List[LeaderboardEntry] = []
        self.load_data()
    
    def hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()
    
    def load_data(self):
        if os.path.exists(self.users_file):
            try:
                with open(self.users_file, 'r') as f:
                    users_data = json.load(f)
                    for username, user_data in users_data.items():
                        self.users[username] = User(**user_data)
            except Exception as e:
                print(f"Error loading users: {e}")
        
        if os.path.exists(self.leaderboard_file):
            try:
                with open(self.leaderboard_file, 'r') as f:
                    leaderboard_data = json.load(f)
                    self.leaderboard = [LeaderboardEntry(**entry) for entry in leaderboard_data]
                    self.leaderboard.sort(key=lambda x: x.score, reverse=True)
            except Exception as e:
                print(f"Error loading leaderboard: {e}")
    
    def save_data(self):
        try:
            users_data = {username: asdict(user) for username, user in self.users.items()}
            with open(self.users_file, 'w') as f:
                json.dump(users_data, f, indent=2)
        except Exception as e:
            print(f"Error saving users: {e}")
        
        try:
            leaderboard_data = [asdict(entry) for entry in self.leaderboard]
            with open(self.leaderboard_file, 'w') as f:
                json.dump(leaderboard_data, f, indent=2)
        except Exception as e:
            print(f"Error saving leaderboard: {e}")
    
    def register_user(self, username: str, password: str) -> Tuple[bool, str]:
        if not username or len(username) < 3:
            return False, "Username must be at least 3 characters"
        
        if not password or len(password) < 4:
            return False, "Password must be at least 4 characters"
        
        if username in self.users:
            return False, "Username already exists"
        
        password_hash = self.hash_password(password)
        self.users[username] = User(username=username, password_hash=password_hash)
        self.save_data()
        return True, "Registration successful!"
    
    def login_user(self, username: str, password: str) -> Tuple[bool, str]:
        if username not in self.users:
            return False, "Username not found"
        
        password_hash = self.hash_password(password)
        if self.users[username].password_hash != password_hash:
            return False, "Incorrect password"
        
        return True, "Login successful!"
    
    def add_score(self, username: str, score: int, level: int):
        entry = LeaderboardEntry(
            username=username,
            score=score,
            level=level,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M")
        )
        self.leaderboard.append(entry)
        self.leaderboard.sort(key=lambda x: x.score, reverse=True)
        self.leaderboard = self.leaderboard[:100]
        
        if username in self.users:
            if score > self.users[username].high_score:
                self.users[username].high_score = score
        
        self.save_data()
    
    def get_top_scores(self, limit: int = 10) -> List[LeaderboardEntry]:
        return self.leaderboard[:limit]
    
    def get_user_unlocked_levels(self, username: str) -> List[int]:
        """Get unlocked levels for a user. Always includes level 1."""
        if username in self.users:
            unlocked = self.users[username].levels_completed.copy() if self.users[username].levels_completed else []
            # Always ensure level 1 is unlocked
            if 1 not in unlocked:
                unlocked.insert(0, 1)
            return unlocked
        return [1]
    
    def update_user_unlocked_levels(self, username: str, unlocked_levels: List[int]):
        """Save unlocked levels to user profile."""
        if username in self.users:
            self.users[username].levels_completed = unlocked_levels.copy()
            self.save_data()

class BlockSmasher:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("BLOCK SMASHER v33")
        self.clock = pygame.time.Clock()
        self.running = True
        
        self.font_title = pygame.font.SysFont('Rajdhani', 64, bold=True)
        self.font_large = pygame.font.SysFont('Rajdhani', 42, bold=True)
        self.font_medium = pygame.font.SysFont('Rajdhani', 28, bold=True)
        self.font_small = pygame.font.SysFont('Rajdhani', 20, bold=False)
        self.font_tiny = pygame.font.SysFont('Rajdhani', 16, bold=False)
        
        self.data_manager = DataManager()
        
        self.state = GameState.LOGIN
        self.current_user: Optional[str] = None
        self.username_input = ""
        self.password_input = ""
        self.input_active = "username"
        self.error_message = ""
        self.success_message = ""
        
        self.maps_tab = MapsTab.CURATED
        self.settings = Settings()
        
        self.reset_game_state()
        
        self.time = 0
        self.menu_blocks = self.create_floating_blocks()
        self.fps_counter = 0
        
        self.mouse_x, self.mouse_y = pygame.mouse.get_pos()
        self.mouse_clicked = False
    
    def reset_game_state(self):
        self.current_level = 1
        self.score = 0
        self.lives = 3
        self.paddle_x = CANVAS_WIDTH // 2 - 60
        self.paddle_width = 100
        self.paddle_base_width = 100
        self.paddle_height = 12
        self.balls: List[Ball] = [Ball(CANVAS_WIDTH // 2, CANVAS_HEIGHT - 80, 0, 0, 7)]
        self.ball_launched = False
        self.blocks: List[Block] = []
        self.particles: List[Particle] = []
        self.powerups: List[Powerup] = []
        self.lasers: List[Laser] = []
        self.unlocked_levels = [1]
        self.game_over_type = None
        
        # Powerup states
        self.active_powerups: Dict[PowerupType, float] = {}
        self.laser_active = False
        self.sticky_paddle_active = False
        self.laser_cooldown = 0
    
    def create_floating_blocks(self):
        return [
            {'x': SCREEN_WIDTH * 0.75, 'y': SCREEN_HEIGHT * 0.15, 'size': 55, 'offset': 0},
            {'x': SCREEN_WIDTH * 0.82, 'y': SCREEN_HEIGHT * 0.45, 'size': 45, 'offset': 1},
            {'x': SCREEN_WIDTH * 0.70, 'y': SCREEN_HEIGHT * 0.70, 'size': 70, 'offset': 2},
            {'x': SCREEN_WIDTH * 0.62, 'y': SCREEN_HEIGHT * 0.28, 'size': 52, 'offset': 1.5},
        ]
    
    def seeded_random(self, seed: int):
        state = seed
        def rand():
            nonlocal state
            state = (state * 1664525 + 1013904223) % 4294967296
            return state / 4294967296
        return rand
    
    def generate_blocks_for_level(self, level: int) -> List[Block]:
        blocks = []
        
        if level == 1:
            rows, cols = 3, 4
            block_width, block_height = 55, 22
            gap_x, gap_y = 8, 8
            total_width = cols * block_width + (cols - 1) * gap_x
            total_height = rows * block_height + (rows - 1) * gap_y
            start_x = (CANVAS_WIDTH - total_width) // 2
            start_y = 80
            colors = [COLOR_CYAN, COLOR_PURPLE, COLOR_ORANGE]
            
            for row in range(rows):
                for col in range(cols):
                    x = start_x + col * (block_width + gap_x)
                    y = start_y + row * (block_height + gap_y)
                    blocks.append(Block(x, y, block_width, block_height, True, colors[row % len(colors)]))
        
        elif level == 2:
            center_x, center_y = CANVAS_WIDTH // 2, 150
            radius = 80
            num_blocks = 8
            block_width, block_height = 50, 20
            colors = [COLOR_CYAN, COLOR_PURPLE, COLOR_ORANGE]
            
            for i in range(num_blocks):
                angle = (i / num_blocks) * 2 * math.pi
                x = center_x + math.cos(angle) * radius - block_width // 2
                y = center_y + math.sin(angle) * radius - block_height // 2
                blocks.append(Block(x, y, block_width, block_height, True, colors[i % 3]))
        
        elif level == 3:
            block_width, block_height = 45, 18
            colors = [COLOR_ORANGE, COLOR_CYAN, COLOR_PURPLE, COLOR_PINK]
            start_y = 50
            rows = 6
            
            for row in range(rows):
                blocks_in_row = 6 - row
                start_x = (CANVAS_WIDTH - (blocks_in_row * (block_width + 6))) // 2
                for col in range(blocks_in_row):
                    x = start_x + col * (block_width + 6)
                    y = start_y + row * (block_height + 6)
                    blocks.append(Block(x, y, block_width, block_height, True, colors[row % len(colors)]))
        
        elif level == 4:
            block_width, block_height = 50, 18
            rows, cols = 4, 8
            start_x = (CANVAS_WIDTH - (cols * (block_width + 5))) // 2
            start_y = 60
            
            for row in range(rows):
                for col in range(cols):
                    if (row + col) % 2 == 0:
                        x = start_x + col * (block_width + 5)
                        y = start_y + row * (block_height + 5)
                        color = COLOR_PURPLE if row % 2 == 0 else COLOR_CYAN
                        blocks.append(Block(x, y, block_width, block_height, True, color))
        
        elif level == 5:
            block_width, block_height = 40, 15
            colors = [COLOR_ORANGE, COLOR_CYAN, COLOR_PURPLE, COLOR_PINK]
            
            for i in range(12):
                blocks.append(Block(70 + i * 42, 60, block_width, block_height, True, colors[0]))
            for i in range(10):
                blocks.append(Block(112 + i * 42, 85, block_width, block_height, True, colors[1]))
            for i in range(8):
                blocks.append(Block(154 + i * 42, 110, block_width, block_height, True, colors[2]))
            for i in range(6):
                blocks.append(Block(196 + i * 42, 135, block_width, block_height, True, colors[3]))
        
        elif level == 6:
            random_gen = self.seeded_random(12345)
            colors = [COLOR_ORANGE, COLOR_CYAN, COLOR_PURPLE, COLOR_PINK, COLOR_YELLOW]
            margin = 40
            max_y = 350
            num_clusters = 10
            patterns = ['tight', 'scattered', 'line', 'arc']
            
            for c in range(num_clusters):
                cluster_x = margin + random_gen() * (CANVAS_WIDTH - margin * 2 - 120)
                cluster_y = margin + random_gen() * (max_y - margin - 80)
                pattern = patterns[int(random_gen() * len(patterns))]
                block_count = 5 + int(random_gen() * 4)
                color = colors[int(random_gen() * len(colors))]
                block_width = 30 + random_gen() * 12
                block_height = 15 + random_gen() * 6
                
                self._generate_cluster(blocks, pattern, cluster_x, cluster_y, block_count, 
                                     block_width, block_height, color, random_gen, margin, max_y)
        
        elif level >= 100:
            random_gen = self.seeded_random(level)
            colors = [COLOR_ORANGE, COLOR_CYAN, COLOR_PURPLE, COLOR_PINK, COLOR_YELLOW]
            margin = 40
            max_y = 350
            
            level_difficulty = (level - 100) % 6
            num_clusters = 6 + level_difficulty // 2
            patterns = ['tight', 'scattered', 'line', 'arc', 'spiral']
            
            for c in range(num_clusters):
                cluster_x = margin + random_gen() * (CANVAS_WIDTH - margin * 2 - 120)
                cluster_y = margin + random_gen() * (max_y - margin - 80)
                pattern = patterns[int(random_gen() * len(patterns))]
                block_count = 4 + int(random_gen() * 6)
                color = colors[int(random_gen() * len(colors))]
                block_width = 28 + random_gen() * 16
                block_height = 15 + random_gen() * 8
                
                self._generate_cluster(blocks, pattern, cluster_x, cluster_y, block_count,
                                     block_width, block_height, color, random_gen, margin, max_y)
        
        return blocks
    
    def _generate_cluster(self, blocks, pattern, cx, cy, count, bw, bh, color, rand_fn, margin, max_y):
        if pattern == 'tight':
            rows, cols = 2, (count + 1) // 2
            gap = 3 + rand_fn() * 3
            for i in range(count):
                row, col = i // cols, i % cols
                x, y = cx + col * (bw + gap), cy + row * (bh + gap)
                if margin <= x <= CANVAS_WIDTH - margin - bw and margin <= y <= max_y - bh:
                    blocks.append(Block(x, y, bw, bh, True, color))
        
        elif pattern == 'scattered':
            radius = 20 + rand_fn() * 28
            for i in range(count):
                angle = (i / count) * 2 * math.pi + rand_fn() * 0.6
                r = radius * (0.6 + rand_fn() * 0.7)
                x, y = cx + math.cos(angle) * r, cy + math.sin(angle) * r
                if margin <= x <= CANVAS_WIDTH - margin - bw and margin <= y <= max_y - bh:
                    blocks.append(Block(x, y, bw, bh, True, color))
        
        elif pattern == 'line':
            angle = rand_fn() * math.pi / 3 - math.pi / 6
            spacing = bw + 2 + rand_fn() * 5
            for i in range(count):
                x = cx + i * spacing * math.cos(angle)
                y = cy + i * spacing * math.sin(angle) + math.sin(i * 0.9) * 10
                if margin <= x <= CANVAS_WIDTH - margin - bw and margin <= y <= max_y - bh:
                    blocks.append(Block(x, y, bw, bh, True, color))
        
        elif pattern == 'arc':
            arc_radius = 30 + rand_fn() * 40
            start_angle = rand_fn() * math.pi
            arc_length = math.pi * 0.5 + rand_fn() * math.pi * 0.5
            for i in range(count):
                t = i / (count - 1) if count > 1 else 0
                angle = start_angle + t * arc_length
                x, y = cx + math.cos(angle) * arc_radius, cy + math.sin(angle) * arc_radius
                if margin <= x <= CANVAS_WIDTH - margin - bw and margin <= y <= max_y - bh:
                    blocks.append(Block(x, y, bw, bh, True, color))
        
        elif pattern == 'spiral':
            spiral_tightness = 2.5 + rand_fn() * 3
            for i in range(count):
                angle = (i / count) * math.pi * 2 * 1.5
                radius = 8 + (i / count) * spiral_tightness * 12
                x, y = cx + math.cos(angle) * radius, cy + math.sin(angle) * radius
                if margin <= x <= CANVAS_WIDTH - margin - bw and margin <= y <= max_y - bh:
                    blocks.append(Block(x, y, bw, bh, True, color))
    
    def spawn_powerup(self, x: float, y: float):
        # 40% chance to spawn a powerup
        if random.random() > 0.40:
            return
        
        # Weighted random selection for powerup type
        weights = {
            PowerupType.PADDLE_EXPAND: 30,
            PowerupType.MULTIBALL: 25,
            PowerupType.FIREBALL: 15,
            PowerupType.LASER: 10,
            PowerupType.STICKY_PADDLE: 10,
            PowerupType.EXTRA_LIFE: 10
        }
        
        types = list(weights.keys())
        probabilities = list(weights.values())
        total = sum(probabilities)
        rand_val = random.random() * total
        
        cumulative = 0
        selected_type = types[0]
        for ptype, weight in zip(types, probabilities):
            cumulative += weight
            if rand_val <= cumulative:
                selected_type = ptype
                break
        
        powerup = Powerup(
            x=x - 15,  # Center the powerup (width/2)
            y=y,
            vy=2.0,
            width=30,
            height=30,
            type=selected_type,
            alive=True
        )
        self.powerups.append(powerup)
    
    def activate_powerup(self, powerup_type: PowerupType):
        if powerup_type == PowerupType.MULTIBALL:
            # Duplicate all balls
            new_balls = []
            for ball in self.balls:
                if not ball.is_stuck:
                    angle1 = math.atan2(ball.vy, ball.vx) + 0.3
                    angle2 = math.atan2(ball.vy, ball.vx) - 0.3
                    speed = math.sqrt(ball.vx**2 + ball.vy**2)
                    new_balls.append(Ball(ball.x, ball.y, math.cos(angle1) * speed, 
                                         math.sin(angle1) * speed, ball.radius, ball.is_fireball))
                    new_balls.append(Ball(ball.x, ball.y, math.cos(angle2) * speed, 
                                         math.sin(angle2) * speed, ball.radius, ball.is_fireball))
            self.balls.extend(new_balls)
            self.score += 500
        
        elif powerup_type == PowerupType.PADDLE_EXPAND:
            self.active_powerups[PowerupType.PADDLE_EXPAND] = 10.0
            self.paddle_width = self.paddle_base_width * 1.5
            self.score += 200
        
        elif powerup_type == PowerupType.FIREBALL:
            self.active_powerups[PowerupType.FIREBALL] = 8.0
            for ball in self.balls:
                ball.is_fireball = True
            self.score += 300
        
        elif powerup_type == PowerupType.LASER:
            self.active_powerups[PowerupType.LASER] = 12.0
            self.laser_active = True
            self.score += 250
        
        elif powerup_type == PowerupType.EXTRA_LIFE:
            self.lives += 1
            self.score += 1000
        
        elif powerup_type == PowerupType.STICKY_PADDLE:
            self.active_powerups[PowerupType.STICKY_PADDLE] = 10.0
            self.sticky_paddle_active = True
            self.score += 150
    
    def update_powerups(self, dt: float):
        # Update falling powerups
        for powerup in self.powerups[:]:
            if not powerup.alive:
                continue
            
            powerup.y += powerup.vy
            
            # Check collision with paddle
            paddle_y = CANVAS_HEIGHT - 35
            if (self.paddle_x <= powerup.x + powerup.width / 2 <= self.paddle_x + self.paddle_width and
                paddle_y <= powerup.y + powerup.height <= paddle_y + self.paddle_height + 10):
                powerup.alive = False
                self.activate_powerup(powerup.type)
                self.create_particles(powerup.x + powerup.width / 2, powerup.y + powerup.height / 2, 20, COLOR_YELLOW)
            
            # Remove if off screen
            if powerup.y > CANVAS_HEIGHT:
                powerup.alive = False
        
        self.powerups = [p for p in self.powerups if p.alive]
        
        # Update active powerup timers
        expired_powerups = []
        for ptype, time_left in self.active_powerups.items():
            self.active_powerups[ptype] = time_left - dt
            if self.active_powerups[ptype] <= 0:
                expired_powerups.append(ptype)
        
        # Deactivate expired powerups
        for ptype in expired_powerups:
            del self.active_powerups[ptype]
            
            if ptype == PowerupType.PADDLE_EXPAND:
                self.paddle_width = self.paddle_base_width
            elif ptype == PowerupType.FIREBALL:
                for ball in self.balls:
                    ball.is_fireball = False
            elif ptype == PowerupType.LASER:
                self.laser_active = False
            elif ptype == PowerupType.STICKY_PADDLE:
                self.sticky_paddle_active = False
    
    def start_level(self, level: int):
        self.current_level = level
        self.lives = 3
        self.score = 0
        self.ball_launched = False
        self.paddle_x = CANVAS_WIDTH // 2 - 50
        self.paddle_width = self.paddle_base_width
        self.balls = [Ball(CANVAS_WIDTH // 2, CANVAS_HEIGHT - 80, 0, 0, 7)]
        self.blocks = self.generate_blocks_for_level(level)
        self.particles = []
        self.powerups = []
        self.lasers = []
        self.active_powerups = {}
        self.laser_active = False
        self.sticky_paddle_active = False
        self.laser_cooldown = 0
        self.game_over_type = None
        self.state = GameState.GAME_SCREEN
    
    def create_particles(self, x: float, y: float, count: int, color: Tuple[int, int, int]):
        if not self.settings.particle_effects:
            return
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(1.5, 4)
            self.particles.append(Particle(
                x, y,
                math.cos(angle) * speed,
                math.sin(angle) * speed,
                1.0, 1.0, random.uniform(1.5, 3.5),
                color
            ))
    
    def update_game(self):
        if self.game_over_type:
            return
        
        dt = 1.0 / FPS
        
        # Update powerups
        self.update_powerups(dt)
        
        # Update laser cooldown
        if self.laser_cooldown > 0:
            self.laser_cooldown -= dt
        
        canvas_x = (SCREEN_WIDTH - CANVAS_WIDTH) // 2
        adjusted_mouse_x = self.mouse_x - canvas_x
        
        # Update paddle position
        if 0 <= adjusted_mouse_x <= CANVAS_WIDTH:
            self.paddle_x = adjusted_mouse_x - self.paddle_width // 2
            self.paddle_x = max(0, min(self.paddle_x, CANVAS_WIDTH - self.paddle_width))
        
        # Update balls
        for ball in self.balls[:]:
            if not self.ball_launched:
                ball.x = self.paddle_x + self.paddle_width // 2
                ball.y = CANVAS_HEIGHT - 80
                ball.is_stuck = False
            elif ball.is_stuck:
                # Ball is stuck to paddle
                ball.x = self.paddle_x + self.paddle_width // 2
                ball.y = CANVAS_HEIGHT - 35 - ball.radius - 2
            else:
                ball.x += ball.vx
                ball.y += ball.vy
                
                # Wall collisions
                if ball.x - ball.radius <= 0 or ball.x + ball.radius >= CANVAS_WIDTH:
                    ball.vx = -ball.vx
                    ball.x = max(ball.radius, min(ball.x, CANVAS_WIDTH - ball.radius))
                    self.create_particles(ball.x, ball.y, 6, COLOR_CYAN)
                
                # Ceiling collision
                if ball.y - ball.radius <= 0:
                    ball.vy = -ball.vy
                    ball.y = ball.radius
                    self.create_particles(ball.x, ball.y, 6, COLOR_CYAN)
                
                # Paddle collision
                paddle_y = CANVAS_HEIGHT - 35
                if (self.paddle_x <= ball.x <= self.paddle_x + self.paddle_width and
                    paddle_y - ball.radius <= ball.y <= paddle_y + self.paddle_height):
                    
                    if self.sticky_paddle_active:
                        ball.is_stuck = True
                        ball.vx = 0
                        ball.vy = 0
                    else:
                        hit_pos = (ball.x - (self.paddle_x + self.paddle_width / 2)) / (self.paddle_width / 2)
                        ball.vx = hit_pos * 4.5
                        ball.vy = -abs(ball.vy)
                        ball.y = paddle_y - ball.radius
                    
                    self.create_particles(ball.x, ball.y, 10, COLOR_PURPLE)
                
                # Block collisions
                for block in self.blocks:
                    if not block.alive:
                        continue
                    if (block.x - ball.radius <= ball.x <= block.x + block.width + ball.radius and
                        block.y - ball.radius <= ball.y <= block.y + block.height + ball.radius):
                        block.alive = False
                        
                        if not ball.is_fireball:
                            ball.vy = -ball.vy
                        
                        self.score += 100
                        # Fixed: Powerup spawns at block center position
                        self.spawn_powerup(block.x + block.width / 2, block.y + block.height / 2)
                        self.create_particles(block.x + block.width / 2, block.y + block.height / 2, 15, block.color)
                        
                        if ball.is_fireball:
                            continue
                        else:
                            break
                
                # Ball fell off screen
                if ball.y > CANVAS_HEIGHT:
                    if len(self.balls) > 1:
                        self.balls.remove(ball)
                    else:
                        self.lives -= 1
                        if self.lives <= 0:
                            self.game_over_type = 'defeat'
                            if self.current_user and self.score > 0:
                                self.data_manager.add_score(self.current_user, self.score, self.current_level)
                        else:
                            self.ball_launched = False
                            ball.x = CANVAS_WIDTH // 2
                            ball.y = CANVAS_HEIGHT - 80
                            ball.vx = 0
                            ball.vy = 0
                            ball.is_stuck = False
                            ball.is_fireball = False
        
        # Update lasers
        for laser in self.lasers[:]:
            laser.y += laser.vy
            
            # Check laser-block collision
            for block in self.blocks:
                if not block.alive:
                    continue
                if (block.x <= laser.x + laser.width / 2 <= block.x + block.width and
                    block.y <= laser.y <= block.y + block.height):
                    block.alive = False
                    laser.alive = False
                    self.score += 100
                    # Fixed: Powerup spawns at block center position
                    self.spawn_powerup(block.x + block.width / 2, block.y + block.height / 2)
                    self.create_particles(block.x + block.width / 2, block.y + block.height / 2, 15, block.color)
                    break
            
            if laser.y < 0:
                laser.alive = False
        
        self.lasers = [l for l in self.lasers if l.alive]
        
        # Update particles
        for particle in self.particles[:]:
            particle.x += particle.vx
            particle.y += particle.vy
            particle.vy += 0.25
            particle.life -= 0.015
            if particle.life <= 0:
                self.particles.remove(particle)
        
        # Check victory
        if all(not block.alive for block in self.blocks) and not self.game_over_type:
            self.game_over_type = 'victory'
            if self.current_user and self.score > 0:
                self.data_manager.add_score(self.current_user, self.score, self.current_level)
            
            # Unlock next level (only for curated levels 1-6)
            if self.current_level + 1 not in self.unlocked_levels and self.current_level < 100:
                self.unlocked_levels.append(self.current_level + 1)
                # Save unlocked levels to user profile
                if self.current_user:
                    self.data_manager.update_user_unlocked_levels(self.current_user, self.unlocked_levels)
    
    def draw_glow_text(self, text: str, font, color: Tuple[int, int, int], x: int, y: int, center=False):
        for offset in [(1, 1), (-1, 1), (1, -1), (-1, -1)]:
            glow_surf = font.render(text, True, (*color[:3], 80) if len(color) == 3 else color)
            rect = glow_surf.get_rect(center=(x + offset[0], y + offset[1])) if center else glow_surf.get_rect(topleft=(x + offset[0], y + offset[1]))
            self.screen.blit(glow_surf, rect)
        
        text_surf = font.render(text, True, color)
        rect = text_surf.get_rect(center=(x, y)) if center else text_surf.get_rect(topleft=(x, y))
        self.screen.blit(text_surf, rect)
        return rect
    
    def draw_glass_rect(self, x: int, y: int, width: int, height: int, 
                       border_color: Tuple[int, int, int], glow: bool = False, radius: int = 10):
        s = pygame.Surface((width, height), pygame.SRCALPHA)
        s.fill(GLASS_BG)
        self.screen.blit(s, (x, y))
        
        if glow:
            for i in range(2):
                glow_rect = pygame.Rect(x - i*2, y - i*2, width + i*4, height + i*4)
                s_glow = pygame.Surface((width + i*4, height + i*4), pygame.SRCALPHA)
                pygame.draw.rect(s_glow, (*border_color, 25 - i*10), (0, 0, width + i*4, height + i*4), border_radius=radius+i*2)
                self.screen.blit(s_glow, (x - i*2, y - i*2))
        
        pygame.draw.rect(self.screen, border_color, (x, y, width, height), 2, border_radius=radius)
    
    def draw_button(self, text: str, x: int, y: int, width: int, height: int,
                   color: Tuple[int, int, int]) -> bool:
        rect = pygame.Rect(x, y, width, height)
        is_hover = rect.collidepoint(self.mouse_x, self.mouse_y)
        
        self.draw_glass_rect(x, y, width, height, color, is_hover)
        
        text_surf = self.font_medium.render(text, True, color)
        text_rect = text_surf.get_rect(center=(x + width // 2, y + height // 2))
        self.screen.blit(text_surf, text_rect)
        
        return is_hover
    
    def draw_powerup(self, powerup: Powerup, offset_x: int, offset_y: int):
        # Fixed: Now receives both offset_x and offset_y for proper canvas positioning
        x = offset_x + powerup.x
        y = offset_y + powerup.y
        
        # Draw powerup icon based on type
        colors = {
            PowerupType.MULTIBALL: COLOR_CYAN,
            PowerupType.PADDLE_EXPAND: COLOR_PURPLE,
            PowerupType.FIREBALL: COLOR_ORANGE,
            PowerupType.LASER: COLOR_YELLOW,
            PowerupType.EXTRA_LIFE: COLOR_PINK,
            PowerupType.STICKY_PADDLE: (100, 200, 255)
        }
        
        color = colors.get(powerup.type, COLOR_FOREGROUND)
        
        # Glow effect
        s = pygame.Surface((powerup.width + 10, powerup.height + 10), pygame.SRCALPHA)
        pygame.draw.circle(s, (*color, 60), (powerup.width // 2 + 5, powerup.height // 2 + 5), powerup.width // 2 + 5)
        self.screen.blit(s, (x - 5, y - 5))
        
        # Main powerup box
        pygame.draw.rect(self.screen, color, (x, y, powerup.width, powerup.height), border_radius=5)
        pygame.draw.rect(self.screen, (*color, 180), (x, y, powerup.width, powerup.height), 2, border_radius=5)
        
        # Draw icon/letter
        icons = {
            PowerupType.MULTIBALL: "M",
            PowerupType.PADDLE_EXPAND: "P",
            PowerupType.FIREBALL: "F",
            PowerupType.LASER: "L",
            PowerupType.EXTRA_LIFE: "+",
            PowerupType.STICKY_PADDLE: "ST"
        }
        
        icon_text = self.font_small.render(icons.get(powerup.type, "?"), True, BG_DARK)
        icon_rect = icon_text.get_rect(center=(x + powerup.width // 2, y + powerup.height // 2))
        self.screen.blit(icon_text, icon_rect)
    
    def draw_login_screen(self):
        self.screen.fill(BG_DARK)
        
        for y in range(0, SCREEN_HEIGHT, 4):
            for x in range(0, SCREEN_WIDTH, 6):
                dist = math.sqrt((x - SCREEN_WIDTH//2)**2 + (y - SCREEN_HEIGHT//2)**2)
                glow = max(0, 25 - dist / 18)
                r = BG_DARK[0] + int(glow * 0.5)
                g = BG_DARK[1] + int(glow * 1.2)
                b = BG_DARK[2] + int(glow * 1.0)
                pygame.draw.rect(self.screen, (r, g, b), (x, y, 6, 4))
        
        self.draw_glow_text("BLOCK SMASHER", self.font_title, COLOR_CYAN, SCREEN_WIDTH // 2, 100, center=True)
        
        subtitle = self.font_small.render("Login to Continue", True, COLOR_FOREGROUND)
        subtitle_rect = subtitle.get_rect(center=(SCREEN_WIDTH // 2, 165))
        self.screen.blit(subtitle, subtitle_rect)
        
        card_width, card_height = 420, 340
        card_x = SCREEN_WIDTH // 2 - card_width // 2
        card_y = SCREEN_HEIGHT // 2 - card_height // 2 + 10
        
        self.draw_glass_rect(card_x, card_y, card_width, card_height, COLOR_CYAN, True)
        
        input_width = 360
        input_height = 42
        input_x = card_x + (card_width - input_width) // 2
        
        username_y = card_y + 65
        username_active = self.input_active == "username"
        self.draw_glass_rect(input_x, username_y, input_width, input_height, 
                           COLOR_CYAN if username_active else COLOR_BORDER, username_active)
        
        username_label = self.font_small.render("Username:", True, COLOR_FOREGROUND)
        self.screen.blit(username_label, (input_x, username_y - 25))
        
        username_display = self.username_input if self.username_input else "Enter username..."
        username_text = self.font_small.render(username_display, True, 
                                               COLOR_FOREGROUND if self.username_input else (*COLOR_FOREGROUND, 100))
        self.screen.blit(username_text, (input_x + 12, username_y + 11))
        
        password_y = card_y + 150
        password_active = self.input_active == "password"
        self.draw_glass_rect(input_x, password_y, input_width, input_height,
                           COLOR_CYAN if password_active else COLOR_BORDER, password_active)
        
        password_label = self.font_small.render("Password:", True, COLOR_FOREGROUND)
        self.screen.blit(password_label, (input_x, password_y - 25))
        
        password_display = "*" * len(self.password_input) if self.password_input else "Enter password..."
        password_text = self.font_small.render(password_display, True,
                                               COLOR_FOREGROUND if self.password_input else (*COLOR_FOREGROUND, 100))
        self.screen.blit(password_text, (input_x + 12, password_y + 11))
        
        login_btn_y = card_y + 235
        login_btn_rect = pygame.Rect(input_x, login_btn_y, 170, 48)
        register_btn_rect = pygame.Rect(input_x + 190, login_btn_y, 170, 48)
        
        login_hover = login_btn_rect.collidepoint(self.mouse_x, self.mouse_y)
        register_hover = register_btn_rect.collidepoint(self.mouse_x, self.mouse_y)
        
        self.draw_glass_rect(login_btn_rect.x, login_btn_rect.y, login_btn_rect.width, login_btn_rect.height,
                           COLOR_CYAN, login_hover)
        self.draw_glass_rect(register_btn_rect.x, register_btn_rect.y, register_btn_rect.width, register_btn_rect.height,
                           COLOR_PURPLE, register_hover)
        
        login_text = self.font_medium.render("LOGIN", True, COLOR_CYAN)
        register_text = self.font_medium.render("REGISTER", True, COLOR_PURPLE)
        
        login_text_rect = login_text.get_rect(center=login_btn_rect.center)
        register_text_rect = register_text.get_rect(center=register_btn_rect.center)
        
        self.screen.blit(login_text, login_text_rect)
        self.screen.blit(register_text, register_text_rect)
        
        if self.mouse_clicked:
            if login_hover:
                success, message = self.data_manager.login_user(self.username_input, self.password_input)
                if success:
                    self.current_user = self.username_input
                    # Load user's unlocked levels
                    self.unlocked_levels = self.data_manager.get_user_unlocked_levels(self.username_input)
                    self.state = GameState.MAIN_MENU
                    self.username_input = ""
                    self.password_input = ""
                else:
                    self.error_message = message
            elif register_hover:
                self.state = GameState.REGISTER
                self.error_message = ""
            else:
                if username_y <= self.mouse_y <= username_y + input_height:
                    self.input_active = "username"
                elif password_y <= self.mouse_y <= password_y + input_height:
                    self.input_active = "password"
        
        if self.error_message:
            error_text = self.font_small.render(self.error_message, True, COLOR_ERROR)
            error_rect = error_text.get_rect(center=(SCREEN_WIDTH // 2, card_y + card_height + 25))
            self.screen.blit(error_text, error_rect)
    
    def draw_register_screen(self):
        self.screen.fill(BG_DARK)
        
        for y in range(0, SCREEN_HEIGHT, 4):
            for x in range(0, SCREEN_WIDTH, 6):
                dist = math.sqrt((x - SCREEN_WIDTH//2)**2 + (y - SCREEN_HEIGHT//2)**2)
                glow = max(0, 25 - dist / 18)
                r = BG_DARK[0] + int(glow * 0.5)
                g = BG_DARK[1] + int(glow * 1.2)
                b = BG_DARK[2] + int(glow * 1.0)
                pygame.draw.rect(self.screen, (r, g, b), (x, y, 6, 4))
        
        self.draw_glow_text("CREATE ACCOUNT", self.font_title, COLOR_PURPLE, SCREEN_WIDTH // 2, 100, center=True)
        
        subtitle = self.font_small.render("Join the Competition", True, COLOR_FOREGROUND)
        subtitle_rect = subtitle.get_rect(center=(SCREEN_WIDTH // 2, 165))
        self.screen.blit(subtitle, subtitle_rect)
        
        card_width, card_height = 420, 340
        card_x = SCREEN_WIDTH // 2 - card_width // 2
        card_y = SCREEN_HEIGHT // 2 - card_height // 2 + 10
        
        self.draw_glass_rect(card_x, card_y, card_width, card_height, COLOR_PURPLE, True)
        
        input_width = 360
        input_height = 42
        input_x = card_x + (card_width - input_width) // 2
        
        username_y = card_y + 65
        username_active = self.input_active == "username"
        self.draw_glass_rect(input_x, username_y, input_width, input_height, 
                           COLOR_PURPLE if username_active else COLOR_BORDER, username_active)
        
        username_label = self.font_small.render("Username (min 3 chars):", True, COLOR_FOREGROUND)
        self.screen.blit(username_label, (input_x, username_y - 25))
        
        username_display = self.username_input if self.username_input else "Choose username..."
        username_text = self.font_small.render(username_display, True, 
                                               COLOR_FOREGROUND if self.username_input else (*COLOR_FOREGROUND, 100))
        self.screen.blit(username_text, (input_x + 12, username_y + 11))
        
        password_y = card_y + 150
        password_active = self.input_active == "password"
        self.draw_glass_rect(input_x, password_y, input_width, input_height,
                           COLOR_PURPLE if password_active else COLOR_BORDER, password_active)
        
        password_label = self.font_small.render("Password (min 4 chars):", True, COLOR_FOREGROUND)
        self.screen.blit(password_label, (input_x, password_y - 25))
        
        password_display = "*" * len(self.password_input) if self.password_input else "Choose password..."
        password_text = self.font_small.render(password_display, True,
                                               COLOR_FOREGROUND if self.password_input else (*COLOR_FOREGROUND, 100))
        self.screen.blit(password_text, (input_x + 12, password_y + 11))
        
        register_btn_y = card_y + 235
        register_btn_rect = pygame.Rect(input_x, register_btn_y, 170, 48)
        back_btn_rect = pygame.Rect(input_x + 190, register_btn_y, 170, 48)
        
        register_hover = register_btn_rect.collidepoint(self.mouse_x, self.mouse_y)
        back_hover = back_btn_rect.collidepoint(self.mouse_x, self.mouse_y)
        
        self.draw_glass_rect(register_btn_rect.x, register_btn_rect.y, register_btn_rect.width, register_btn_rect.height,
                           COLOR_PURPLE, register_hover)
        self.draw_glass_rect(back_btn_rect.x, back_btn_rect.y, back_btn_rect.width, back_btn_rect.height,
                           COLOR_ORANGE, back_hover)
        
        register_text = self.font_medium.render("REGISTER", True, COLOR_PURPLE)
        back_text = self.font_medium.render("BACK", True, COLOR_ORANGE)
        
        register_text_rect = register_text.get_rect(center=register_btn_rect.center)
        back_text_rect = back_text.get_rect(center=back_btn_rect.center)
        
        self.screen.blit(register_text, register_text_rect)
        self.screen.blit(back_text, back_text_rect)
        
        if self.mouse_clicked:
            if register_hover:
                success, message = self.data_manager.register_user(self.username_input, self.password_input)
                if success:
                    self.success_message = message
                    self.username_input = ""
                    self.password_input = ""
                    self.state = GameState.LOGIN
                else:
                    self.error_message = message
            elif back_hover:
                self.state = GameState.LOGIN
                self.error_message = ""
                self.username_input = ""
                self.password_input = ""
            else:
                if username_y <= self.mouse_y <= username_y + input_height:
                    self.input_active = "username"
                elif password_y <= self.mouse_y <= password_y + input_height:
                    self.input_active = "password"
        
        if self.error_message:
            error_text = self.font_small.render(self.error_message, True, COLOR_ERROR)
            error_rect = error_text.get_rect(center=(SCREEN_WIDTH // 2, card_y + card_height + 25))
            self.screen.blit(error_text, error_rect)
    
    def draw_main_menu(self):
        self.screen.fill(BG_DARK)
        
        self.time += 0.016
        
        # Draw floating blocks on the right side
        for block in self.menu_blocks:
            float_offset = math.sin(self.time * 1.2 + block['offset']) * 12
            y = block['y'] + float_offset
            
            s = pygame.Surface((block['size'], block['size']), pygame.SRCALPHA)
            for i in range(3):
                pygame.draw.rect(s, (*COLOR_CYAN, 15 - i*5), 
                               (i*2, i*2, block['size'] - i*4, block['size'] - i*4),
                               border_radius=8)
            
            self.screen.blit(s, (block['x'], y))
            pygame.draw.rect(self.screen, COLOR_CYAN, 
                           (block['x'], y, block['size'], block['size']), 
                           2, border_radius=8)
        
        # LEFT-ALIGNED TITLE (classic layout)
        title_x = 45
        title_y = 115
        
        # "BLOCK" in cyan
        block_text = self.font_title.render("BLOCK", True, COLOR_CYAN)
        self.screen.blit(block_text, (title_x, title_y))
        
        # "SMASHER" in orange below it
        smasher_text = self.font_title.render("SMASHER", True, COLOR_ORANGE)
        self.screen.blit(smasher_text, (title_x, title_y + 65))
        
        # Decorative line under title
        pygame.draw.line(self.screen, COLOR_CYAN, (title_x, title_y + 145), (title_x + 125, title_y + 145), 3)
        
        # LEFT-ALIGNED BUTTONS (classic layout)
        button_x = 45
        button_start_y = 270
        button_width = 290
        button_height = 48
        button_spacing = 12
        
        buttons = [
            ("PLAY", button_start_y, COLOR_CYAN, GameState.MAPS_SCREEN),
            ("MAPS", button_start_y + (button_height + button_spacing), COLOR_PURPLE, GameState.MAPS_SCREEN),
            ("LEADERBOARD", button_start_y + (button_height + button_spacing) * 2, COLOR_YELLOW, GameState.LEADERBOARD_SCREEN),
        ]
        
        for text, y, color, target_state in buttons:
            rect = pygame.Rect(button_x, y, button_width, button_height)
            is_hover = rect.collidepoint(self.mouse_x, self.mouse_y)
            
            # Draw button
            self.draw_glass_rect(button_x, y, button_width, button_height, color, is_hover)
            
            # Draw text (left-aligned inside button)
            btn_text = self.font_medium.render(text, True, color)
            self.screen.blit(btn_text, (button_x + 15, y + 12))
            
            if is_hover and self.mouse_clicked:
                self.state = target_state
        
        # BOTTOM LEFT: Premium Edition text
        premium_y = SCREEN_HEIGHT - 85
        premium_text = self.font_tiny.render("PREMIUM EDITION", True, (*COLOR_FOREGROUND, 120))
        self.screen.blit(premium_text, (45, premium_y))
        
        version_text = self.font_tiny.render("Version 33.0", True, (*COLOR_FOREGROUND, 80))
        self.screen.blit(version_text, (45, premium_y + 18))
        
        # TOP RIGHT ICONS
        icon_y = 20
        icon_size = 32
        icon_spacing = 50
        
        # Settings icon
        settings_x = SCREEN_WIDTH - 140
        settings_rect = pygame.Rect(settings_x, icon_y, icon_size, icon_size)
        settings_hover = settings_rect.collidepoint(self.mouse_x, self.mouse_y)
        
        # Draw settings icon circle
        color = COLOR_CYAN if settings_hover else (*COLOR_CYAN, 150)
        pygame.draw.circle(self.screen, color, (settings_x + icon_size // 2, icon_y + icon_size // 2), icon_size // 2, 2)
        # Gear symbol (simplified)
        pygame.draw.circle(self.screen, color, (settings_x + icon_size // 2, icon_y + icon_size // 2), icon_size // 4, 2)
        
        if settings_hover and self.mouse_clicked:
            self.state = GameState.SETTINGS_SCREEN
        
        # Logout icon
        logout_x = SCREEN_WIDTH - 80
        logout_rect = pygame.Rect(logout_x, icon_y, icon_size, icon_size)
        logout_hover = logout_rect.collidepoint(self.mouse_x, self.mouse_y)
        
        # Draw logout icon circle
        color = COLOR_PINK if logout_hover else (*COLOR_PINK, 150)
        pygame.draw.circle(self.screen, color, (logout_x + icon_size // 2, icon_y + icon_size // 2), icon_size // 2, 2)
        # Exit arrow (simplified)
        arrow_points = [
            (logout_x + 10, icon_y + 16),
            (logout_x + 22, icon_y + 16),
            (logout_x + 18, icon_y + 12),
        ]
        pygame.draw.lines(self.screen, color, False, arrow_points, 2)
        
        if logout_hover and self.mouse_clicked:
            self.current_user = None
            self.username_input = ""
            self.password_input = ""
            self.unlocked_levels = [1]  # Reset to default on logout
            self.state = GameState.LOGIN
    
    def draw_maps_screen(self):
        self.screen.fill(BG_DARK)
        
        self.draw_glow_text("SELECT LEVEL", self.font_large, COLOR_CYAN, SCREEN_WIDTH // 2, 50, center=True)
        
        tab_width = 200
        tab_height = 45
        tab_y = 110
        curated_x = SCREEN_WIDTH // 2 - tab_width - 5
        procedural_x = SCREEN_WIDTH // 2 + 5
        
        curated_hover = pygame.Rect(curated_x, tab_y, tab_width, tab_height).collidepoint(self.mouse_x, self.mouse_y)
        procedural_hover = pygame.Rect(procedural_x, tab_y, tab_width, tab_height).collidepoint(self.mouse_x, self.mouse_y)
        
        self.draw_glass_rect(curated_x, tab_y, tab_width, tab_height, 
                           COLOR_CYAN if self.maps_tab == MapsTab.CURATED else COLOR_BORDER, 
                           curated_hover or self.maps_tab == MapsTab.CURATED)
        self.draw_glass_rect(procedural_x, tab_y, tab_width, tab_height,
                           COLOR_PURPLE if self.maps_tab == MapsTab.PROCEDURAL else COLOR_BORDER,
                           procedural_hover or self.maps_tab == MapsTab.PROCEDURAL)
        
        curated_text = self.font_medium.render("CURATED", True, COLOR_CYAN)
        procedural_text = self.font_medium.render("PROCEDURAL", True, COLOR_PURPLE)
        
        curated_rect = curated_text.get_rect(center=(curated_x + tab_width // 2, tab_y + tab_height // 2))
        procedural_rect = procedural_text.get_rect(center=(procedural_x + tab_width // 2, tab_y + tab_height // 2))
        
        self.screen.blit(curated_text, curated_rect)
        self.screen.blit(procedural_text, procedural_rect)
        
        if self.mouse_clicked:
            if curated_hover:
                self.maps_tab = MapsTab.CURATED
            elif procedural_hover:
                self.maps_tab = MapsTab.PROCEDURAL
        
        back_btn_hover = self.draw_button("BACK TO MENU", 40, SCREEN_HEIGHT - 80, 200, 45, COLOR_ORANGE)
        if back_btn_hover and self.mouse_clicked:
            self.state = GameState.MAIN_MENU
        
        if self.maps_tab == MapsTab.CURATED:
            self.draw_curated_maps()
        else:
            self.draw_procedural_maps()
    
    def draw_curated_maps(self):
        maps = [
            (1, "First Steps", "Easy", 12),
            (2, "Circular Formation", "Medium", 8),
            (3, "Pyramid Power", "Medium", 36),
            (4, "Checkerboard", "Hard", 32),
            (5, "The Fortress", "Hard", 64),
            (6, "Explosive Chaos", "Extreme", 80),
        ]
        
        start_x, start_y = 40, 180
        card_width, card_height = 310, 115
        spacing = 20
        
        for i, (level_id, name, difficulty, blocks) in enumerate(maps):
            row, col = i // 3, i % 3
            x = start_x + col * (card_width + spacing)
            y = start_y + row * (card_height + spacing)
            
            locked = level_id not in self.unlocked_levels
            color = (100, 100, 100) if locked else COLOR_CYAN
            
            card_rect = pygame.Rect(x, y, card_width, card_height)
            is_hover = card_rect.collidepoint(self.mouse_x, self.mouse_y) and not locked
            
            self.draw_glass_rect(x, y, card_width, card_height, color, is_hover)
            
            level_text = self.font_large.render(str(level_id), True, color)
            self.screen.blit(level_text, (x + 15, y + 12))
            
            name_text = self.font_medium.render(name, True, COLOR_FOREGROUND if not locked else (120, 120, 120))
            self.screen.blit(name_text, (x + 70, y + 16))
            
            diff_text = self.font_small.render(f"{difficulty} • {blocks} blocks", True, 
                                               COLOR_PURPLE if not locked else (100, 100, 100))
            self.screen.blit(diff_text, (x + 70, y + 55))
            
            if locked:
                lock_text = self.font_small.render("LOCKED", True, (100, 100, 100))
                self.screen.blit(lock_text, (x + 70, y + 80))
            
            if is_hover and self.mouse_clicked:
                self.start_level(level_id)
    
    def draw_procedural_maps(self):
        start_x, start_y = 40, 180
        card_width, card_height = 310, 115
        spacing = 20
        
        for i in range(6):
            level_id = 101 + i
            row, col = i // 3, i % 3
            x = start_x + col * (card_width + spacing)
            y = start_y + row * (card_height + spacing)
            
            card_rect = pygame.Rect(x, y, card_width, card_height)
            is_hover = card_rect.collidepoint(self.mouse_x, self.mouse_y)
            
            self.draw_glass_rect(x, y, card_width, card_height, COLOR_PURPLE, is_hover)
            
            num_text = self.font_large.render(str(i + 1), True, COLOR_CYAN)
            self.screen.blit(num_text, (x + 15, y + 12))
            
            name_text = self.font_medium.render(f"Random Level #{i + 1}", True, COLOR_FOREGROUND)
            self.screen.blit(name_text, (x + 70, y + 16))
            
            difficulties = ['Easy', 'Medium', 'Hard']
            difficulty = difficulties[i // 2]
            diff_text = self.font_small.render(difficulty, True, COLOR_PURPLE)
            self.screen.blit(diff_text, (x + 70, y + 55))
            
            if is_hover and self.mouse_clicked:
                self.start_level(level_id)
    
    def draw_game_screen(self):
        self.screen.fill(BG_DARK)
        
        canvas_x = (SCREEN_WIDTH - CANVAS_WIDTH) // 2
        canvas_y = (SCREEN_HEIGHT - CANVAS_HEIGHT) // 2 + 30
        
        self.draw_glass_rect(canvas_x, canvas_y, CANVAS_WIDTH, CANVAS_HEIGHT, COLOR_CYAN, True)
        
        pygame.draw.rect(self.screen, BG_CARD, (canvas_x, canvas_y, CANVAS_WIDTH, CANVAS_HEIGHT))
        
        # Draw blocks
        for block in self.blocks:
            if block.alive:
                s = pygame.Surface((block.width, block.height), pygame.SRCALPHA)
                s.fill((*block.color, 180))
                self.screen.blit(s, (canvas_x + block.x, canvas_y + block.y))
                pygame.draw.rect(self.screen, block.color, 
                               (canvas_x + block.x, canvas_y + block.y, block.width, block.height), 
                               2, border_radius=4)
        
        # Draw paddle
        paddle_y = CANVAS_HEIGHT - 35
        paddle_color = COLOR_CYAN
        if self.sticky_paddle_active:
            paddle_color = (100, 200, 255)
        
        pygame.draw.rect(self.screen, paddle_color, 
                        (canvas_x + self.paddle_x, canvas_y + paddle_y, 
                         self.paddle_width, self.paddle_height), 
                        border_radius=6)
        pygame.draw.rect(self.screen, paddle_color, 
                        (canvas_x + self.paddle_x, canvas_y + paddle_y, 
                         self.paddle_width, self.paddle_height), 
                        3, border_radius=6)
        
        # Draw balls
        for ball in self.balls:
            ball_color = COLOR_ORANGE if ball.is_fireball else COLOR_CYAN
            
            if ball.is_fireball:
                s = pygame.Surface((ball.radius*4, ball.radius*4), pygame.SRCALPHA)
                pygame.draw.circle(s, (*COLOR_ORANGE, 60), (ball.radius*2, ball.radius*2), ball.radius*2)
                self.screen.blit(s, (canvas_x + ball.x - ball.radius*2, canvas_y + ball.y - ball.radius*2))
            
            pygame.draw.circle(self.screen, ball_color, 
                             (int(canvas_x + ball.x), int(canvas_y + ball.y)), 
                             int(ball.radius))
        
        # Draw powerups - FIXED: Now passes both canvas_x and canvas_y
        for powerup in self.powerups:
            if powerup.alive:
                self.draw_powerup(powerup, canvas_x, canvas_y)
        
        # Draw lasers
        for laser in self.lasers:
            if laser.alive:
                pygame.draw.rect(self.screen, COLOR_YELLOW,
                               (canvas_x + laser.x, canvas_y + laser.y, laser.width, laser.height))
        
        # Draw particles
        for particle in self.particles:
            alpha = int(255 * (particle.life / particle.max_life))
            pos = (int(canvas_x + particle.x), int(canvas_y + particle.y))
            size = int(particle.size * (particle.life / particle.max_life))
            
            if size > 0 and alpha > 0:
                s = pygame.Surface((size*2, size*2), pygame.SRCALPHA)
                pygame.draw.circle(s, (*particle.color, min(255, alpha)), (size, size), size)
                self.screen.blit(s, (pos[0] - size, pos[1] - size))
        
        # Draw HUD
        level_text = f"Random Level #{self.current_level - 100}" if self.current_level >= 100 else f"Level {self.current_level}"
        hud = self.font_small.render(f"{level_text} | Score: {self.score} | Lives: {self.lives}", True, COLOR_FOREGROUND)
        self.screen.blit(hud, (40, 20))
        
        if self.settings.show_fps:
            fps_text = self.font_small.render(f"FPS: {self.fps_counter}", True, COLOR_ORANGE)
            self.screen.blit(fps_text, (SCREEN_WIDTH - 100, 20))
        
        # Draw active powerups indicator
        powerup_x = SCREEN_WIDTH - 160
        powerup_y = 50
        if self.active_powerups:
            indicator_text = self.font_tiny.render("ACTIVE POWERUPS:", True, COLOR_YELLOW)
            self.screen.blit(indicator_text, (powerup_x, powerup_y))
            powerup_y += 20
            
            for ptype, time_left in self.active_powerups.items():
                names = {
                    PowerupType.MULTIBALL: "Multiball",
                    PowerupType.PADDLE_EXPAND: "Expand",
                    PowerupType.FIREBALL: "Fireball",
                    PowerupType.LASER: "Laser",
                    PowerupType.STICKY_PADDLE: "Sticky"
                }
                text = self.font_tiny.render(f"{names.get(ptype, '?')}: {int(time_left)}s", True, COLOR_CYAN)
                self.screen.blit(text, (powerup_x, powerup_y))
                powerup_y += 18
        
        if not self.ball_launched:
            hint = self.font_small.render("SPACE or CLICK to launch", True, COLOR_CYAN)
            hint_rect = hint.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 35))
            self.screen.blit(hint, hint_rect)
        
        if self.game_over_type:
            self.draw_game_over_overlay()
        
        # Draw back to menu button
        menu_btn_hover = self.draw_button("MENU", 40, 60, 80, 38, COLOR_ORANGE)
        if menu_btn_hover and self.mouse_clicked:
            self.state = GameState.MAPS_SCREEN
        
        # Draw pause button
        pause_btn_x = 130
        pause_rect = pygame.Rect(pause_btn_x, 60, 80, 38)
        pause_hover = pause_rect.collidepoint(self.mouse_x, self.mouse_y)
        self.draw_glass_rect(pause_btn_x, 60, 80, 38, COLOR_PURPLE, pause_hover)
        
        # Draw pause icon (two bars)
        bar_width = 8
        bar_height = 20
        bar_gap = 8
        bar_x = pause_btn_x + (80 - bar_width * 2 - bar_gap) // 2
        bar_y = 60 + (38 - bar_height) // 2
        
        pygame.draw.rect(self.screen, COLOR_PURPLE, (bar_x, bar_y, bar_width, bar_height))
        pygame.draw.rect(self.screen, COLOR_PURPLE, (bar_x + bar_width + bar_gap, bar_y, bar_width, bar_height))
        
        if pause_hover and self.mouse_clicked:
            self.state = GameState.PAUSED
    
    def draw_paused_screen(self):
        # Draw game in background (dimmed)
        self.draw_game_screen()
        
        # Draw overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        
        self.draw_glow_text("PAUSED", self.font_title, COLOR_PURPLE, SCREEN_WIDTH // 2, 200, center=True)
        
        # Continue button
        continue_hover = self.draw_button("CONTINUE", SCREEN_WIDTH // 2 - 160, 320, 140, 50, COLOR_CYAN)
        
        # Menu button
        menu_hover = self.draw_button("MENU", SCREEN_WIDTH // 2 + 20, 320, 140, 50, COLOR_ORANGE)
        
        if self.mouse_clicked:
            if continue_hover:
                self.state = GameState.GAME_SCREEN
            elif menu_hover:
                self.state = GameState.MAPS_SCREEN
    
    def draw_game_over_overlay(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, (0, 0))
        
        if self.game_over_type == 'victory':
            self.draw_glow_text("VICTORY!", self.font_title, COLOR_CYAN, SCREEN_WIDTH // 2, 200, center=True)
            stars = self.font_large.render("COMPLETE", True, COLOR_YELLOW)
            stars_rect = stars.get_rect(center=(SCREEN_WIDTH // 2, 280))
            self.screen.blit(stars, stars_rect)
        else:
            self.draw_glow_text("GAME OVER", self.font_title, COLOR_ORANGE, SCREEN_WIDTH // 2, 200, center=True)
        
        score_text = self.font_medium.render(f"Final Score: {self.score}", True, COLOR_FOREGROUND)
        score_rect = score_text.get_rect(center=(SCREEN_WIDTH // 2, 350))
        self.screen.blit(score_text, score_rect)
        
        saved_text = self.font_small.render("Score saved to leaderboard", True, COLOR_SUCCESS)
        saved_rect = saved_text.get_rect(center=(SCREEN_WIDTH // 2, 390))
        self.screen.blit(saved_text, saved_rect)
        
        menu_btn_hover = self.draw_button("BACK TO MENU", SCREEN_WIDTH // 2 - 100, 450, 200, 50, COLOR_CYAN)
        
        if menu_btn_hover and self.mouse_clicked:
            self.state = GameState.MAPS_SCREEN
    
    def draw_settings_screen(self):
        self.screen.fill(BG_DARK)
        
        self.draw_glow_text("SETTINGS", self.font_large, COLOR_PURPLE, SCREEN_WIDTH // 2, 50, center=True)
        
        card_width, card_height = 700, 500
        card_x = SCREEN_WIDTH // 2 - card_width // 2
        card_y = 130
        
        self.draw_glass_rect(card_x, card_y, card_width, card_height, COLOR_PURPLE, True)
        
        y_offset = card_y + 40
        
        settings_list = [
            ("Master Volume", "master_volume"),
            ("Music Volume", "music_volume"),
            ("SFX Volume", "sfx_volume"),
        ]
        
        for label, attr in settings_list:
            label_text = self.font_small.render(label, True, COLOR_FOREGROUND)
            self.screen.blit(label_text, (card_x + 40, y_offset))
            
            value = getattr(self.settings, attr)
            value_text = self.font_small.render(f"{int(value)}%", True, COLOR_CYAN)
            self.screen.blit(value_text, (card_x + 600, y_offset))
            
            y_offset += 60
        
        toggles = [
            ("Particle Effects", "particle_effects"),
            ("Screen Shake", "screen_shake"),
            ("Show FPS", "show_fps"),
        ]
        
        y_offset += 20
        
        for label, attr in toggles:
            label_text = self.font_small.render(label, True, COLOR_FOREGROUND)
            self.screen.blit(label_text, (card_x + 40, y_offset))
            
            value = getattr(self.settings, attr)
            status_text = self.font_small.render("ON" if value else "OFF", 
                                                 True, COLOR_SUCCESS if value else COLOR_ERROR)
            self.screen.blit(status_text, (card_x + 600, y_offset))
            
            y_offset += 50
        
        back_btn_hover = self.draw_button("BACK TO MENU", SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT - 100, 200, 50, COLOR_ORANGE)
        
        if back_btn_hover and self.mouse_clicked:
            self.state = GameState.MAIN_MENU
    
    def draw_leaderboard_screen(self):
        self.screen.fill(BG_DARK)
        
        self.draw_glow_text("LEADERBOARD", self.font_large, COLOR_YELLOW, SCREEN_WIDTH // 2, 50, center=True)
        
        subtitle = self.font_small.render("Top Players", True, COLOR_FOREGROUND)
        subtitle_rect = subtitle.get_rect(center=(SCREEN_WIDTH // 2, 110))
        self.screen.blit(subtitle, subtitle_rect)
        
        top_scores = self.data_manager.get_top_scores(10)
        
        if not top_scores:
            no_scores_text = self.font_medium.render("No scores yet. Be the first!", True, COLOR_FOREGROUND)
            no_scores_rect = no_scores_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            self.screen.blit(no_scores_text, no_scores_rect)
        else:
            # Draw top 1 podium
            if len(top_scores) > 0:
                podium_y = 180
                self.draw_glass_rect(SCREEN_WIDTH // 2 - 120, podium_y, 240, 135, COLOR_YELLOW, True)
                
                first_text = self.font_title.render("1", True, COLOR_YELLOW)
                first_rect = first_text.get_rect(center=(SCREEN_WIDTH // 2, podium_y + 38))
                self.screen.blit(first_text, first_rect)
                
                name_text = self.font_medium.render(top_scores[0].username, True, COLOR_FOREGROUND)
                name_rect = name_text.get_rect(center=(SCREEN_WIDTH // 2, podium_y + 85))
                self.screen.blit(name_text, name_rect)
                
                score_text = self.font_small.render(f"{top_scores[0].score:,} pts | Level {top_scores[0].level}", True, COLOR_CYAN)
                score_rect = score_text.get_rect(center=(SCREEN_WIDTH // 2, podium_y + 110))
                self.screen.blit(score_text, score_rect)
            
            # Draw rest of leaderboard
            list_y = 350
            for i, entry in enumerate(top_scores[1:], start=1):
                if i >= 10:
                    break
                
                entry_y = list_y + (i - 1) * 50
                self.draw_glass_rect(SCREEN_WIDTH // 2 - 265, entry_y, 530, 44, COLOR_PURPLE)
                
                rank_text = self.font_medium.render(f"#{i + 1}", True, COLOR_CYAN)
                self.screen.blit(rank_text, (SCREEN_WIDTH // 2 - 245, entry_y + 10))
                
                name_text = self.font_medium.render(entry.username, True, COLOR_FOREGROUND)
                self.screen.blit(name_text, (SCREEN_WIDTH // 2 - 175, entry_y + 10))
                
                score_text = self.font_medium.render(f"{entry.score:,} pts", True, COLOR_ORANGE)
                score_rect = score_text.get_rect(right=SCREEN_WIDTH // 2 + 250, centery=entry_y + 22)
                self.screen.blit(score_text, score_rect)
                
                level_text = self.font_small.render(f"Lvl {entry.level}", True, (*COLOR_FOREGROUND, 150))
                level_rect = level_text.get_rect(right=SCREEN_WIDTH // 2 + 160, centery=entry_y + 22)
                self.screen.blit(level_text, level_rect)
        
        back_btn_hover = self.draw_button("BACK TO MENU", SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT - 80, 200, 50, COLOR_ORANGE)
        
        if back_btn_hover and self.mouse_clicked:
            self.state = GameState.MAIN_MENU
    
    def handle_text_input(self, event):
        if event.key == pygame.K_BACKSPACE:
            if self.input_active == "username":
                self.username_input = self.username_input[:-1]
            elif self.input_active == "password":
                self.password_input = self.password_input[:-1]
        elif event.key == pygame.K_TAB:
            self.input_active = "password" if self.input_active == "username" else "username"
        elif event.key == pygame.K_RETURN:
            if self.state == GameState.LOGIN:
                success, message = self.data_manager.login_user(self.username_input, self.password_input)
                if success:
                    self.current_user = self.username_input
                    # Load user's unlocked levels
                    self.unlocked_levels = self.data_manager.get_user_unlocked_levels(self.username_input)
                    self.state = GameState.MAIN_MENU
                    self.username_input = ""
                    self.password_input = ""
                else:
                    self.error_message = message
            elif self.state == GameState.REGISTER:
                success, message = self.data_manager.register_user(self.username_input, self.password_input)
                if success:
                    self.success_message = message
                    self.username_input = ""
                    self.password_input = ""
                    self.state = GameState.LOGIN
                else:
                    self.error_message = message
        else:
            char = event.unicode
            if char.isprintable():
                if self.input_active == "username" and len(self.username_input) < 20:
                    self.username_input += char
                elif self.input_active == "password" and len(self.password_input) < 30:
                    self.password_input += char
    
    def run(self):
        while self.running:
            self.mouse_clicked = False
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.mouse_clicked = True
                    
                    # Launch ball on click
                    if self.state == GameState.GAME_SCREEN and not self.game_over_type:
                        if not self.ball_launched:
                            self.ball_launched = True
                            for ball in self.balls:
                                if ball.vx == 0 and ball.vy == 0:
                                    ball.vx = 0  # Launch straight up
                                    ball.vy = -5
                        # Release stuck balls
                        elif self.sticky_paddle_active:
                            for ball in self.balls:
                                if ball.is_stuck:
                                    ball.is_stuck = False
                                    ball.vx = 0  # Launch straight up
                                    ball.vy = -5
                        # Fire laser
                        elif self.laser_active and self.laser_cooldown <= 0:
                            laser_x = self.paddle_x + self.paddle_width / 2 - 2
                            laser_y = CANVAS_HEIGHT - 35 - 10
                            self.lasers.append(Laser(laser_x, laser_y, -8, 4, 10, True))
                            self.laser_cooldown = 0.3
                
                elif event.type == pygame.KEYDOWN:
                    if self.state in [GameState.LOGIN, GameState.REGISTER]:
                        self.handle_text_input(event)
                    
                    elif self.state == GameState.GAME_SCREEN and not self.game_over_type:
                        if event.key == pygame.K_SPACE:
                            if not self.ball_launched:
                                self.ball_launched = True
                                for ball in self.balls:
                                    if ball.vx == 0 and ball.vy == 0:
                                        ball.vx = 0  # Launch straight up
                                        ball.vy = -5
                            elif self.sticky_paddle_active:
                                for ball in self.balls:
                                    if ball.is_stuck:
                                        ball.is_stuck = False
                                        ball.vx = 0  # Launch straight up
                                        ball.vy = -5
                        
                        elif event.key == pygame.K_ESCAPE:
                            self.state = GameState.PAUSED
                    
                    elif self.state == GameState.PAUSED:
                        if event.key == pygame.K_ESCAPE or event.key == pygame.K_SPACE:
                            self.state = GameState.GAME_SCREEN
            
            self.mouse_x, self.mouse_y = pygame.mouse.get_pos()
            
            if self.state == GameState.LOGIN:
                self.draw_login_screen()
            elif self.state == GameState.REGISTER:
                self.draw_register_screen()
            elif self.state == GameState.MAIN_MENU:
                self.draw_main_menu()
            elif self.state == GameState.MAPS_SCREEN:
                self.draw_maps_screen()
            elif self.state == GameState.GAME_SCREEN:
                self.update_game()
                self.draw_game_screen()
            elif self.state == GameState.PAUSED:
                self.draw_paused_screen()
            elif self.state == GameState.SETTINGS_SCREEN:
                self.draw_settings_screen()
            elif self.state == GameState.LEADERBOARD_SCREEN:
                self.draw_leaderboard_screen()
            
            pygame.display.flip()
            self.fps_counter = int(self.clock.get_fps())
            self.clock.tick(FPS)
        
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = BlockSmasher()
    game.run()
