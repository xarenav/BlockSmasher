"""
BLOCK SMASHER - Python/Pygame Final Edition
Optimized for 1024x768 Resolution
Complete with Login System and Real Leaderboard
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

# Initialize Pygame
pygame.init()

# Screen Configuration - 1024x768
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
CANVAS_WIDTH = 650
CANVAS_HEIGHT = 500
FPS = 60

# Exact Color Palette
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

# Glass morphism RGBA
GLASS_BG = (20, 25, 40, 100)
GLASS_BORDER = (64, 224, 208, 40)

# Game States
class GameState(Enum):
    LOGIN = 0
    REGISTER = 1
    MAIN_MENU = 2
    MAPS_SCREEN = 3
    GAME_SCREEN = 4
    SETTINGS_SCREEN = 5
    LEADERBOARD_SCREEN = 6

class MapsTab(Enum):
    CURATED = 1
    PROCEDURAL = 2

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
    """Manages user data and leaderboard persistence"""
    
    def __init__(self):
        self.users_file = 'users.json'
        self.leaderboard_file = 'leaderboard.json'
        self.users: Dict[str, User] = {}
        self.leaderboard: List[LeaderboardEntry] = []
        self.load_data()
    
    def hash_password(self, password: str) -> str:
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def load_data(self):
        """Load users and leaderboard from JSON files"""
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
        """Save users and leaderboard to JSON files"""
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
        """Register a new user"""
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
        """Authenticate user"""
        if username not in self.users:
            return False, "Username not found"
        
        password_hash = self.hash_password(password)
        if self.users[username].password_hash != password_hash:
            return False, "Incorrect password"
        
        return True, "Login successful!"
    
    def add_score(self, username: str, score: int, level: int):
        """Add score to leaderboard"""
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
        """Get top N scores"""
        return self.leaderboard[:limit]

class BlockSmasher:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("BLOCK SMASHER")
        self.clock = pygame.time.Clock()
        self.running = True
        
        # Load Fonts - Smaller for 1024x768
        self.font_title = pygame.font.SysFont('Arial', 64, bold=True)
        self.font_large = pygame.font.SysFont('Arial', 42, bold=True)
        self.font_medium = pygame.font.SysFont('Arial', 28, bold=True)
        self.font_small = pygame.font.SysFont('Arial', 20, bold=False)
        self.font_tiny = pygame.font.SysFont('Arial', 16, bold=False)
        
        # Data Manager
        self.data_manager = DataManager()
        
        # Login/Auth State
        self.state = GameState.LOGIN
        self.current_user: Optional[str] = None
        self.username_input = ""
        self.password_input = ""
        self.input_active = "username"
        self.error_message = ""
        self.success_message = ""
        
        # Game State
        self.maps_tab = MapsTab.CURATED
        self.settings = Settings()
        
        # Game Variables
        self.current_level = 1
        self.score = 0
        self.lives = 3
        self.paddle_x = CANVAS_WIDTH // 2 - 60
        self.paddle_width = 100
        self.paddle_height = 12
        self.ball_x = CANVAS_WIDTH // 2
        self.ball_y = CANVAS_HEIGHT - 80
        self.ball_vx = 0
        self.ball_vy = 0
        self.ball_radius = 7
        self.ball_launched = False
        self.blocks: List[Block] = []
        self.particles: List[Particle] = []
        self.unlocked_levels = [1]
        
        # Animation Variables
        self.time = 0
        self.menu_blocks = self.create_floating_blocks()
        self.game_over_type = None
        self.fps_counter = 0
        
        # Mouse State
        self.mouse_x, self.mouse_y = pygame.mouse.get_pos()
        self.mouse_clicked = False
    
    def create_floating_blocks(self):
        """Create floating decorative blocks for menu"""
        return [
            {'x': SCREEN_WIDTH * 0.75, 'y': SCREEN_HEIGHT * 0.15, 'size': 55, 'offset': 0},
            {'x': SCREEN_WIDTH * 0.82, 'y': SCREEN_HEIGHT * 0.45, 'size': 45, 'offset': 1},
            {'x': SCREEN_WIDTH * 0.70, 'y': SCREEN_HEIGHT * 0.70, 'size': 70, 'offset': 2},
            {'x': SCREEN_WIDTH * 0.62, 'y': SCREEN_HEIGHT * 0.28, 'size': 52, 'offset': 1.5},
        ]
    
    def seeded_random(self, seed: int):
        """Seeded RNG for procedural levels"""
        state = seed
        def rand():
            nonlocal state
            state = (state * 1664525 + 1013904223) % 4294967296
            return state / 4294967296
        return rand
    
    def generate_blocks_for_level(self, level: int) -> List[Block]:
        """Generate blocks based on level - scaled for smaller canvas"""
        blocks = []
        
        if level == 1:
            rows, cols = 4, 6
            block_width, block_height = 50, 20
            gap_x, gap_y = 4, 4
            start_x, start_y = 40, 40
            colors = [COLOR_CYAN, COLOR_PURPLE, COLOR_ORANGE, COLOR_PINK]
            
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
            
            level_difficulty = (level - 100) % 12
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
        """Helper to generate block clusters"""
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
    
    def start_level(self, level: int):
        """Initialize level"""
        self.current_level = level
        self.lives = 3
        self.score = 0
        self.ball_launched = False
        self.paddle_x = CANVAS_WIDTH // 2 - 50
        self.ball_x = CANVAS_WIDTH // 2
        self.ball_y = CANVAS_HEIGHT - 80
        self.ball_vx = 0
        self.ball_vy = 0
        self.blocks = self.generate_blocks_for_level(level)
        self.particles = []
        self.game_over_type = None
        self.state = GameState.GAME_SCREEN
    
    def create_particles(self, x: float, y: float, count: int, color: Tuple[int, int, int]):
        """Create particle explosion"""
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
        """Update game physics"""
        if self.game_over_type:
            return
        
        # Move paddle
        canvas_x = (SCREEN_WIDTH - CANVAS_WIDTH) // 2
        adjusted_mouse_x = self.mouse_x - canvas_x
        
        if 0 <= adjusted_mouse_x <= CANVAS_WIDTH:
            self.paddle_x = adjusted_mouse_x - self.paddle_width // 2
            self.paddle_x = max(0, min(self.paddle_x, CANVAS_WIDTH - self.paddle_width))
        
        # Ball follows paddle if not launched
        if not self.ball_launched:
            self.ball_x = self.paddle_x + self.paddle_width // 2
            self.ball_y = CANVAS_HEIGHT - 80
        else:
            # Update ball
            self.ball_x += self.ball_vx
            self.ball_y += self.ball_vy
            
            # Wall collision
            if self.ball_x - self.ball_radius <= 0 or self.ball_x + self.ball_radius >= CANVAS_WIDTH:
                self.ball_vx = -self.ball_vx
                self.ball_x = max(self.ball_radius, min(self.ball_x, CANVAS_WIDTH - self.ball_radius))
                self.create_particles(self.ball_x, self.ball_y, 6, COLOR_CYAN)
            
            if self.ball_y - self.ball_radius <= 0:
                self.ball_vy = -self.ball_vy
                self.ball_y = self.ball_radius
                self.create_particles(self.ball_x, self.ball_y, 6, COLOR_CYAN)
            
            # Paddle collision
            paddle_y = CANVAS_HEIGHT - 35
            if (self.paddle_x <= self.ball_x <= self.paddle_x + self.paddle_width and
                paddle_y - self.ball_radius <= self.ball_y <= paddle_y + self.paddle_height):
                hit_pos = (self.ball_x - (self.paddle_x + self.paddle_width / 2)) / (self.paddle_width / 2)
                self.ball_vx = hit_pos * 4.5
                self.ball_vy = -abs(self.ball_vy)
                self.ball_y = paddle_y - self.ball_radius
                self.create_particles(self.ball_x, self.ball_y, 10, COLOR_PURPLE)
            
            # Block collision
            for block in self.blocks:
                if not block.alive:
                    continue
                if (block.x - self.ball_radius <= self.ball_x <= block.x + block.width + self.ball_radius and
                    block.y - self.ball_radius <= self.ball_y <= block.y + block.height + self.ball_radius):
                    block.alive = False
                    self.ball_vy = -self.ball_vy
                    self.score += 100
                    self.create_particles(block.x + block.width / 2, block.y + block.height / 2, 15, block.color)
                    break
            
            # Ball fell
            if self.ball_y > CANVAS_HEIGHT:
                self.lives -= 1
                if self.lives <= 0:
                    self.game_over_type = 'defeat'
                    if self.current_user and self.score > 0:
                        self.data_manager.add_score(self.current_user, self.score, self.current_level)
                else:
                    self.ball_launched = False
                    self.ball_vx = 0
                    self.ball_vy = 0
        
        # Update particles
        for particle in self.particles[:]:
            particle.x += particle.vx
            particle.y += particle.vy
            particle.vy += 0.25
            particle.life -= 0.015
            if particle.life <= 0:
                self.particles.remove(particle)
        
        # Victory check
        if all(not block.alive for block in self.blocks) and not self.game_over_type:
            self.game_over_type = 'victory'
            if self.current_user and self.score > 0:
                self.data_manager.add_score(self.current_user, self.score, self.current_level)
            
            if self.current_level + 1 not in self.unlocked_levels and self.current_level < 100:
                self.unlocked_levels.append(self.current_level + 1)
    
    def draw_glow_text(self, text: str, font, color: Tuple[int, int, int], x: int, y: int, center=False):
        """Draw text with glow effect"""
        # Glow layers
        for offset in [(1, 1), (-1, 1), (1, -1), (-1, -1)]:
            glow_surf = font.render(text, True, (*color[:3], 80) if len(color) == 3 else color)
            rect = glow_surf.get_rect(center=(x + offset[0], y + offset[1])) if center else glow_surf.get_rect(topleft=(x + offset[0], y + offset[1]))
            self.screen.blit(glow_surf, rect)
        
        # Main text
        text_surf = font.render(text, True, color)
        rect = text_surf.get_rect(center=(x, y)) if center else text_surf.get_rect(topleft=(x, y))
        self.screen.blit(text_surf, rect)
        return rect
    
    def draw_glass_rect(self, x: int, y: int, width: int, height: int, 
                       border_color: Tuple[int, int, int], glow: bool = False, radius: int = 10):
        """Draw glass morphism rectangle"""
        # Background
        s = pygame.Surface((width, height), pygame.SRCALPHA)
        s.fill(GLASS_BG)
        self.screen.blit(s, (x, y))
        
        # Glow
        if glow:
            for i in range(2):
                glow_rect = pygame.Rect(x - i*2, y - i*2, width + i*4, height + i*4)
                s_glow = pygame.Surface((width + i*4, height + i*4), pygame.SRCALPHA)
                pygame.draw.rect(s_glow, (*border_color, 25 - i*10), (0, 0, width + i*4, height + i*4), border_radius=radius+i*2)
                self.screen.blit(s_glow, (x - i*2, y - i*2))
        
        # Border
        pygame.draw.rect(self.screen, border_color, (x, y, width, height), 2, border_radius=radius)
    
    def draw_button(self, text: str, x: int, y: int, width: int, height: int,
                   color: Tuple[int, int, int], icon: str = None) -> bool:
        """Draw glass button and return if hovered"""
        rect = pygame.Rect(x, y, width, height)
        is_hover = rect.collidepoint(self.mouse_x, self.mouse_y)
        
        self.draw_glass_rect(x, y, width, height, color, is_hover)
        
        # Icon
        icon_x = x + 15
        if icon:
            icon_surf = self.font_small.render(icon, True, color)
            self.screen.blit(icon_surf, (icon_x, y + height // 2 - 10))
            icon_x += 32
        
        # Text
        text_surf = self.font_medium.render(text, True, color)
        text_rect = text_surf.get_rect(midleft=(icon_x, y + height // 2))
        self.screen.blit(text_surf, text_rect)
        
        return is_hover
    
    def draw_login_screen(self):
        """Draw login screen"""
        self.screen.fill(BG_DARK)
        
        # Background gradient effect
        for y in range(0, SCREEN_HEIGHT, 4):
            for x in range(0, SCREEN_WIDTH, 6):
                dist = math.sqrt((x - SCREEN_WIDTH//2)**2 + (y - SCREEN_HEIGHT//2)**2)
                glow = max(0, 25 - dist / 18)
                r = BG_DARK[0] + int(glow * 0.5)
                g = BG_DARK[1] + int(glow * 1.2)
                b = BG_DARK[2] + int(glow * 1.0)
                pygame.draw.rect(self.screen, (r, g, b), (x, y, 6, 4))
        
        # Title
        self.draw_glow_text("BLOCK SMASHER", self.font_title, COLOR_CYAN, SCREEN_WIDTH // 2, 100, center=True)
        
        subtitle = self.font_small.render("Login to Continue", True, COLOR_FOREGROUND)
        subtitle_rect = subtitle.get_rect(center=(SCREEN_WIDTH // 2, 165))
        self.screen.blit(subtitle, subtitle_rect)
        
        # Login card
        card_width, card_height = 420, 340
        card_x = SCREEN_WIDTH // 2 - card_width // 2
        card_y = SCREEN_HEIGHT // 2 - card_height // 2 + 10
        
        self.draw_glass_rect(card_x, card_y, card_width, card_height, COLOR_CYAN, True)
        
        # Username input
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
        
        # Password input
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
        
        # Buttons
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
        
        # Click handlers
        if self.mouse_clicked:
            if login_hover:
                success, message = self.data_manager.login_user(self.username_input, self.password_input)
                if success:
                    self.current_user = self.username_input
                    self.state = GameState.MAIN_MENU
                    self.username_input = ""
                    self.password_input = ""
                else:
                    self.error_message = message
            elif register_hover:
                self.state = GameState.REGISTER
                self.error_message = ""
            else:
                if pygame.Rect(input_x, username_y, input_width, input_height).collidepoint(self.mouse_x, self.mouse_y):
                    self.input_active = "username"
                elif pygame.Rect(input_x, password_y, input_width, input_height).collidepoint(self.mouse_x, self.mouse_y):
                    self.input_active = "password"
        
        # Error/Success messages
        if self.error_message:
            error_surf = self.font_small.render(self.error_message, True, COLOR_ERROR)
            error_rect = error_surf.get_rect(center=(SCREEN_WIDTH // 2, card_y + card_height + 25))
            self.screen.blit(error_surf, error_rect)
        
        if self.success_message:
            success_surf = self.font_small.render(self.success_message, True, COLOR_SUCCESS)
            success_rect = success_surf.get_rect(center=(SCREEN_WIDTH // 2, card_y + card_height + 25))
            self.screen.blit(success_surf, success_rect)
    
    def draw_register_screen(self):
        """Draw registration screen"""
        self.screen.fill(BG_DARK)
        
        # Background gradient
        for y in range(0, SCREEN_HEIGHT, 4):
            for x in range(0, SCREEN_WIDTH, 6):
                dist = math.sqrt((x - SCREEN_WIDTH//2)**2 + (y - SCREEN_HEIGHT//2)**2)
                glow = max(0, 25 - dist / 18)
                r = BG_DARK[0] + int(glow * 0.5)
                g = BG_DARK[1] + int(glow * 1.2)
                b = BG_DARK[2] + int(glow * 1.0)
                pygame.draw.rect(self.screen, (r, g, b), (x, y, 6, 4))
        
        # Title
        self.draw_glow_text("BLOCK SMASHER", self.font_title, COLOR_PURPLE, SCREEN_WIDTH // 2, 100, center=True)
        
        subtitle = self.font_small.render("Create New Account", True, COLOR_FOREGROUND)
        subtitle_rect = subtitle.get_rect(center=(SCREEN_WIDTH // 2, 165))
        self.screen.blit(subtitle, subtitle_rect)
        
        # Register card
        card_width, card_height = 420, 380
        card_x = SCREEN_WIDTH // 2 - card_width // 2
        card_y = SCREEN_HEIGHT // 2 - card_height // 2 + 10
        
        self.draw_glass_rect(card_x, card_y, card_width, card_height, COLOR_PURPLE, True)
        
        # Username input
        input_width = 360
        input_height = 42
        input_x = card_x + (card_width - input_width) // 2
        
        username_y = card_y + 65
        username_active = self.input_active == "username"
        self.draw_glass_rect(input_x, username_y, input_width, input_height,
                           COLOR_PURPLE if username_active else COLOR_BORDER, username_active)
        
        username_label = self.font_small.render("Username (min 3 chars):", True, COLOR_FOREGROUND)
        self.screen.blit(username_label, (input_x, username_y - 25))
        
        username_display = self.username_input if self.username_input else "Enter username..."
        username_text = self.font_small.render(username_display, True,
                                               COLOR_FOREGROUND if self.username_input else (*COLOR_FOREGROUND, 100))
        self.screen.blit(username_text, (input_x + 12, username_y + 11))
        
        # Password input
        password_y = card_y + 160
        password_active = self.input_active == "password"
        self.draw_glass_rect(input_x, password_y, input_width, input_height,
                           COLOR_PURPLE if password_active else COLOR_BORDER, password_active)
        
        password_label = self.font_small.render("Password (min 4 chars):", True, COLOR_FOREGROUND)
        self.screen.blit(password_label, (input_x, password_y - 25))
        
        password_display = "*" * len(self.password_input) if self.password_input else "Enter password..."
        password_text = self.font_small.render(password_display, True,
                                               COLOR_FOREGROUND if self.password_input else (*COLOR_FOREGROUND, 100))
        self.screen.blit(password_text, (input_x + 12, password_y + 11))
        
        # Buttons
        create_btn_y = card_y + 265
        create_btn_rect = pygame.Rect(input_x, create_btn_y, 170, 48)
        back_btn_rect = pygame.Rect(input_x + 190, create_btn_y, 170, 48)
        
        create_hover = create_btn_rect.collidepoint(self.mouse_x, self.mouse_y)
        back_hover = back_btn_rect.collidepoint(self.mouse_x, self.mouse_y)
        
        self.draw_glass_rect(create_btn_rect.x, create_btn_rect.y, create_btn_rect.width, create_btn_rect.height,
                           COLOR_PURPLE, create_hover)
        self.draw_glass_rect(back_btn_rect.x, back_btn_rect.y, back_btn_rect.width, back_btn_rect.height,
                           COLOR_CYAN, back_hover)
        
        create_text = self.font_medium.render("CREATE", True, COLOR_PURPLE)
        back_text = self.font_medium.render("BACK", True, COLOR_CYAN)
        
        create_text_rect = create_text.get_rect(center=create_btn_rect.center)
        back_text_rect = back_text.get_rect(center=back_btn_rect.center)
        
        self.screen.blit(create_text, create_text_rect)
        self.screen.blit(back_text, back_text_rect)
        
        # Click handlers
        if self.mouse_clicked:
            if create_hover:
                success, message = self.data_manager.register_user(self.username_input, self.password_input)
                if success:
                    self.success_message = message
                    self.error_message = ""
                    self.current_user = self.username_input
                    self.username_input = ""
                    self.password_input = ""
                    pygame.time.wait(500)
                    self.state = GameState.MAIN_MENU
                else:
                    self.error_message = message
                    self.success_message = ""
            elif back_hover:
                self.state = GameState.LOGIN
                self.error_message = ""
                self.success_message = ""
                self.username_input = ""
                self.password_input = ""
            else:
                if pygame.Rect(input_x, username_y, input_width, input_height).collidepoint(self.mouse_x, self.mouse_y):
                    self.input_active = "username"
                elif pygame.Rect(input_x, password_y, input_width, input_height).collidepoint(self.mouse_x, self.mouse_y):
                    self.input_active = "password"
        
        # Error/Success messages
        if self.error_message:
            error_surf = self.font_small.render(self.error_message, True, COLOR_ERROR)
            error_rect = error_surf.get_rect(center=(SCREEN_WIDTH // 2, card_y + card_height + 25))
            self.screen.blit(error_surf, error_rect)
        
        if self.success_message:
            success_surf = self.font_small.render(self.success_message, True, COLOR_SUCCESS)
            success_rect = success_surf.get_rect(center=(SCREEN_WIDTH // 2, card_y + card_height + 25))
            self.screen.blit(success_surf, success_rect)
    
    def draw_main_menu(self):
        """Draw main menu"""
        # Background gradient
        for y in range(SCREEN_HEIGHT):
            for x in range(0, SCREEN_WIDTH, 3):
                dist_tl = math.sqrt((x - SCREEN_WIDTH*0.2)**2 + (y - SCREEN_HEIGHT*0.2)**2)
                dist_br = math.sqrt((x - SCREEN_WIDTH*0.8)**2 + (y - SCREEN_HEIGHT*0.8)**2)
                
                glow_tl = max(0, 35 - dist_tl / 12)
                glow_br = max(0, 35 - dist_br / 12)
                
                r = BG_DARK[0] + int(glow_tl * 0.3 + glow_br * 0.15)
                g = BG_DARK[1] + int(glow_tl * 0.8 + glow_br * 0.4)
                b = BG_DARK[2] + int(glow_tl * 0.8 + glow_br * 0.1)
                
                pygame.draw.line(self.screen, (r, g, b), (x, y), (x+3, y))
        
        # Floating blocks
        for block in self.menu_blocks:
            float_y = math.sin(self.time * 0.5 + block['offset']) * 12
            size = block['size']
            x, y = int(block['x']), int(block['y'] + float_y)
            
            s = pygame.Surface((size, size), pygame.SRCALPHA)
            s.fill((*COLOR_PURPLE, 60))
            self.screen.blit(s, (x, y))
            pygame.draw.rect(self.screen, COLOR_PURPLE, (x, y, size, size), 2, border_radius=7)
            
            for i in range(2):
                glow_size = size + i*5
                glow_surf = pygame.Surface((glow_size, glow_size), pygame.SRCALPHA)
                pygame.draw.rect(glow_surf, (*COLOR_PURPLE, 18-i*8), (0, 0, glow_size, glow_size), border_radius=9)
                self.screen.blit(glow_surf, (x-i*2.5, y-i*2.5))
        
        # Title
        title_x, title_y = 75, 130
        self.draw_glow_text("BLOCK", self.font_title, COLOR_CYAN, title_x, title_y)
        self.draw_glow_text("SMASHER", self.font_title, COLOR_ORANGE, title_x, title_y + 75)
        
        # Gradient line
        line_y = title_y + 165
        for i in range(180):
            t = i / 180
            if t < 0.33:
                color = COLOR_CYAN
            elif t < 0.66:
                color = COLOR_PURPLE
            else:
                color = COLOR_ORANGE
            pygame.draw.line(self.screen, color, (title_x + i, line_y), (title_x + i, line_y + 3))
        
        # Welcome message
        welcome_text = self.font_small.render(f"Welcome, {self.current_user}!", True, COLOR_FOREGROUND)
        self.screen.blit(welcome_text, (title_x, title_y - 40))
        
        # Menu buttons
        button_x, button_y = 75, 360
        button_spacing = 55
        
        buttons = [
            ("▶", "PLAY", GameState.MAPS_SCREEN),
            ("◆", "MAPS", GameState.MAPS_SCREEN),
            ("★", "LEADERBOARD", GameState.LEADERBOARD_SCREEN),
            ("⚙", "SETTINGS", GameState.SETTINGS_SCREEN),
            ("⎋", "LOGOUT", GameState.LOGIN),
        ]
        
        for i, (icon, text, next_state) in enumerate(buttons):
            y = button_y + i * button_spacing
            hover = self.draw_button(text, button_x, y, 280, 42, COLOR_CYAN, icon)
            
            if hover and self.mouse_clicked:
                if next_state == GameState.LOGIN:
                    self.current_user = None
                    self.username_input = ""
                    self.password_input = ""
                self.state = next_state
        
        # Info card
        info_y = button_y + len(buttons) * button_spacing + 15
        self.draw_glass_rect(button_x, info_y, 280, 58, COLOR_CYAN)
        premium_text = self.font_small.render("PREMIUM EDITION", True, (*COLOR_FOREGROUND, 150))
        version_text = self.font_tiny.render("Version 1.0.0", True, (*COLOR_FOREGROUND, 100))
        self.screen.blit(premium_text, (button_x + 12, info_y + 10))
        self.screen.blit(version_text, (button_x + 12, info_y + 35))
    
    def draw_maps_screen(self):
        """Draw maps selection screen"""
        self.screen.fill(BG_DARK)
        
        self.draw_glow_text("SELECT MAP", self.font_large, COLOR_CYAN, 40, 25)
        
        # Back button
        back_rect = pygame.Rect(40, 80, 120, 38)
        back_hover = back_rect.collidepoint(self.mouse_x, self.mouse_y)
        self.draw_glass_rect(40, 80, 120, 38, COLOR_CYAN, back_hover)
        back_text = self.font_small.render("← BACK", True, COLOR_CYAN)
        self.screen.blit(back_text, (55, 89))
        
        if back_hover and self.mouse_clicked:
            self.state = GameState.MAIN_MENU
        
        # Tab buttons
        curated_rect = pygame.Rect(190, 80, 170, 38)
        procedural_rect = pygame.Rect(380, 80, 190, 38)
        
        curated_hover = curated_rect.collidepoint(self.mouse_x, self.mouse_y)
        procedural_hover = procedural_rect.collidepoint(self.mouse_x, self.mouse_y)
        
        self.draw_glass_rect(190, 80, 170, 38, COLOR_CYAN,
                           curated_hover or self.maps_tab == MapsTab.CURATED)
        self.draw_glass_rect(380, 80, 190, 38, COLOR_PURPLE,
                           procedural_hover or self.maps_tab == MapsTab.PROCEDURAL)
        
        curated_text = self.font_small.render("CURATED", True, COLOR_CYAN)
        procedural_text = self.font_small.render("PROCEDURAL", True, COLOR_PURPLE)
        self.screen.blit(curated_text, (220, 89))
        self.screen.blit(procedural_text, (405, 89))
        
        if curated_hover and self.mouse_clicked:
            self.maps_tab = MapsTab.CURATED
        if procedural_hover and self.mouse_clicked:
            self.maps_tab = MapsTab.PROCEDURAL
        
        # Draw maps
        if self.maps_tab == MapsTab.CURATED:
            self.draw_curated_maps()
        else:
            self.draw_procedural_maps()
    
    def draw_curated_maps(self):
        """Draw curated map cards"""
        maps = [
            (1, "First Steps", "Easy", 24),
            (2, "Circular Formation", "Medium", 8),
            (3, "Pyramid Power", "Medium", 36),
            (4, "Checkerboard", "Hard", 32),
            (5, "The Fortress", "Hard", 64),
            (6, "Explosive Chaos", "Extreme", 80),
        ]
        
        start_x, start_y = 40, 155
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
            
            # Level number
            level_text = self.font_large.render(str(level_id), True, color)
            self.screen.blit(level_text, (x + 15, y + 12))
            
            # Name
            name_text = self.font_medium.render(name, True, COLOR_FOREGROUND if not locked else (150, 150, 150))
            self.screen.blit(name_text, (x + 70, y + 16))
            
            # Details
            details_text = self.font_small.render(f"{difficulty} | {blocks} blocks", True, COLOR_PURPLE if not locked else (120, 120, 120))
            self.screen.blit(details_text, (x + 70, y + 55))
            
            # Lock icon
            if locked:
                lock_text = self.font_large.render("🔒", True, (150, 150, 150))
                lock_rect = lock_text.get_rect(center=(x + card_width // 2, y + card_height // 2))
                self.screen.blit(lock_text, lock_rect)
            
            # Click handler
            if is_hover and self.mouse_clicked:
                self.start_level(level_id)
    
    def draw_procedural_maps(self):
        """Draw procedural map cards"""
        start_x, start_y = 40, 155
        card_width, card_height = 235, 100
        spacing = 18
        
        for i in range(12):
            level_id = 101 + i
            row, col = i // 4, i % 4
            x = start_x + col * (card_width + spacing)
            y = start_y + row * (card_height + spacing)
            
            card_rect = pygame.Rect(x, y, card_width, card_height)
            is_hover = card_rect.collidepoint(self.mouse_x, self.mouse_y)
            
            self.draw_glass_rect(x, y, card_width, card_height, COLOR_PURPLE, is_hover)
            
            # Icon and number
            shuffle_text = self.font_large.render("🔀", True, COLOR_CYAN)
            self.screen.blit(shuffle_text, (x + 12, y + 10))
            
            num_text = self.font_large.render(str(i + 1), True, COLOR_PURPLE)
            self.screen.blit(num_text, (x + 65, y + 12))
            
            # Name
            name_text = self.font_small.render(f"Random Level #{i + 1}", True, COLOR_FOREGROUND)
            self.screen.blit(name_text, (x + 12, y + 52))
            
            # Difficulty
            difficulties = ['Easy', 'Medium', 'Hard', 'Expert']
            difficulty = difficulties[(i // 3) % 4]
            diff_text = self.font_tiny.render(difficulty, True, COLOR_PURPLE)
            self.screen.blit(diff_text, (x + 12, y + 75))
            
            # Click
            if is_hover and self.mouse_clicked:
                self.start_level(level_id)
    
    def draw_game_screen(self):
        """Draw gameplay screen"""
        self.screen.fill(BG_DARK)
        
        # Canvas
        canvas_x = (SCREEN_WIDTH - CANVAS_WIDTH) // 2
        canvas_y = (SCREEN_HEIGHT - CANVAS_HEIGHT) // 2 + 20
        
        # Canvas border with glow
        for i in range(2):
            glow_rect = pygame.Rect(canvas_x - 2 - i*2, canvas_y - 2 - i*2, CANVAS_WIDTH + 4 + i*4, CANVAS_HEIGHT + 4 + i*4)
            pygame.draw.rect(self.screen, (*COLOR_CYAN, 50 - i*20), glow_rect, 2)
        
        # Canvas background
        canvas_surface = pygame.Surface((CANVAS_WIDTH, CANVAS_HEIGHT))
        canvas_surface.fill((15, 20, 35))
        self.screen.blit(canvas_surface, (canvas_x, canvas_y))
        
        # Draw blocks
        for block in self.blocks:
            if block.alive:
                bx, by = canvas_x + int(block.x), canvas_y + int(block.y)
                pygame.draw.rect(self.screen, block.color, (bx, by, int(block.width), int(block.height)), border_radius=3)
                
                # Block glow
                s = pygame.Surface((int(block.width) + 3, int(block.height) + 3), pygame.SRCALPHA)
                pygame.draw.rect(s, (*block.color, 70), (0, 0, int(block.width) + 3, int(block.height) + 3), 1, border_radius=4)
                self.screen.blit(s, (bx - 1.5, by - 1.5))
        
        # Draw paddle
        paddle_y = CANVAS_HEIGHT - 35
        px, py = canvas_x + int(self.paddle_x), canvas_y + paddle_y
        pygame.draw.rect(self.screen, COLOR_PURPLE, (px, py, self.paddle_width, self.paddle_height), border_radius=3)
        
        # Paddle glow
        for i in range(2):
            s = pygame.Surface((self.paddle_width + i*3, self.paddle_height + i*3), pygame.SRCALPHA)
            pygame.draw.rect(s, (*COLOR_PURPLE, 45 - i*15), (0, 0, self.paddle_width + i*3, self.paddle_height + i*3), 1, border_radius=5)
            self.screen.blit(s, (px - i*1.5, py - i*1.5))
        
        # Draw ball
        ball_pos = (canvas_x + int(self.ball_x), canvas_y + int(self.ball_y))
        pygame.draw.circle(self.screen, COLOR_CYAN, ball_pos, self.ball_radius)
        
        # Ball glow
        for i in range(2):
            s = pygame.Surface((self.ball_radius*2 + i*3, self.ball_radius*2 + i*3), pygame.SRCALPHA)
            pygame.draw.circle(s, (*COLOR_CYAN, 70 - i*22), (self.ball_radius + i*1.5, self.ball_radius + i*1.5), self.ball_radius + i*1.5, 1)
            self.screen.blit(s, (ball_pos[0] - self.ball_radius - i*1.5, ball_pos[1] - self.ball_radius - i*1.5))
        
        # Draw particles
        for particle in self.particles:
            if particle.life > 0:
                alpha = int((particle.life / particle.max_life) * 255)
                pos = (canvas_x + int(particle.x), canvas_y + int(particle.y))
                size = max(1, int(particle.size * (particle.life / particle.max_life)))
                s = pygame.Surface((size*2, size*2), pygame.SRCALPHA)
                pygame.draw.circle(s, (*particle.color, min(255, alpha)), (size, size), size)
                self.screen.blit(s, (pos[0] - size, pos[1] - size))
        
        # HUD
        level_text = f"Random Level #{self.current_level - 99}" if self.current_level >= 100 else f"Level {self.current_level}"
        hud = self.font_small.render(f"{level_text} | Score: {self.score} | Lives: {self.lives}", True, COLOR_FOREGROUND)
        self.screen.blit(hud, (40, 20))
        
        # FPS
        if self.settings.show_fps:
            fps_text = self.font_small.render(f"FPS: {self.fps_counter}", True, COLOR_ORANGE)
            self.screen.blit(fps_text, (SCREEN_WIDTH - 100, 20))
        
        # Launch hint
        if not self.ball_launched:
            hint = self.font_small.render("SPACE or CLICK to launch", True, COLOR_CYAN)
            hint_rect = hint.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 35))
            self.screen.blit(hint, hint_rect)
        
        # Game over overlay
        if self.game_over_type:
            self.draw_game_over_overlay()
        
        # Back/Pause button
        pause_rect = pygame.Rect(40, 60, 55, 38)
        pause_hover = pause_rect.collidepoint(self.mouse_x, self.mouse_y)
        self.draw_glass_rect(40, 60, 55, 38, COLOR_ORANGE, pause_hover)
        pause_text = self.font_medium.render("⏸", True, COLOR_ORANGE)
        self.screen.blit(pause_text, (52, 65))
        
        if pause_hover and self.mouse_clicked:
            self.state = GameState.MAPS_SCREEN
    
    def draw_game_over_overlay(self):
        """Draw victory/defeat overlay"""
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, (0, 0))
        
        if self.game_over_type == 'victory':
            self.draw_glow_text("VICTORY!", self.font_title, COLOR_CYAN, SCREEN_WIDTH // 2, 200, center=True)
            stars = self.font_large.render("★ ★ ★", True, COLOR_YELLOW)
            stars_rect = stars.get_rect(center=(SCREEN_WIDTH // 2, 280))
            self.screen.blit(stars, stars_rect)
        else:
            self.draw_glow_text("GAME OVER", self.font_title, COLOR_ORANGE, SCREEN_WIDTH // 2, 200, center=True)
        
        # Score
        score_text = self.font_medium.render(f"Final Score: {self.score}", True, COLOR_FOREGROUND)
        score_rect = score_text.get_rect(center=(SCREEN_WIDTH // 2, 350))
        self.screen.blit(score_text, score_rect)
        
        # Saved message
        saved_text = self.font_small.render("Score saved to leaderboard!", True, COLOR_SUCCESS)
        saved_rect = saved_text.get_rect(center=(SCREEN_WIDTH // 2, 390))
        self.screen.blit(saved_text, saved_rect)
        
        # Buttons
        retry_rect = pygame.Rect(SCREEN_WIDTH // 2 - 190, 440, 175, 55)
        menu_rect = pygame.Rect(SCREEN_WIDTH // 2 + 15, 440, 175, 55)
        
        retry_hover = retry_rect.collidepoint(self.mouse_x, self.mouse_y)
        menu_hover = menu_rect.collidepoint(self.mouse_x, self.mouse_y)
        
        self.draw_glass_rect(retry_rect.x, retry_rect.y, retry_rect.width, retry_rect.height, COLOR_PURPLE, retry_hover)
        self.draw_glass_rect(menu_rect.x, menu_rect.y, menu_rect.width, menu_rect.height, COLOR_CYAN, menu_hover)
        
        retry_text = self.font_medium.render("RETRY", True, COLOR_PURPLE)
        menu_text = self.font_medium.render("MENU", True, COLOR_CYAN)
        retry_text_rect = retry_text.get_rect(center=retry_rect.center)
        menu_text_rect = menu_text.get_rect(center=menu_rect.center)
        self.screen.blit(retry_text, retry_text_rect)
        self.screen.blit(menu_text, menu_text_rect)
        
        if retry_hover and self.mouse_clicked:
            self.start_level(self.current_level)
        if menu_hover and self.mouse_clicked:
            self.state = GameState.MAPS_SCREEN
    
    def draw_settings_screen(self):
        """Draw settings screen"""
        self.screen.fill(BG_DARK)
        
        self.draw_glow_text("SETTINGS", self.font_large, COLOR_CYAN, 40, 25)
        
        # Back button
        back_rect = pygame.Rect(40, 80, 120, 38)
        back_hover = back_rect.collidepoint(self.mouse_x, self.mouse_y)
        self.draw_glass_rect(40, 80, 120, 38, COLOR_CYAN, back_hover)
        back_text = self.font_small.render("← BACK", True, COLOR_CYAN)
        self.screen.blit(back_text, (55, 89))
        
        if back_hover and self.mouse_clicked:
            self.state = GameState.MAIN_MENU
        
        # Settings
        y = 170
        spacing = 70
        
        settings_items = [
            f"Particle Effects: {'ON' if self.settings.particle_effects else 'OFF'}",
            f"Screen Shake: {'ON' if self.settings.screen_shake else 'OFF'}",
            f"Show FPS: {'ON' if self.settings.show_fps else 'OFF'}",
            f"Quality: {self.settings.quality.upper()}",
            f"Difficulty: {self.settings.difficulty.upper()}",
        ]
        
        for i, item in enumerate(settings_items):
            item_y = y + i * spacing
            item_rect = pygame.Rect(SCREEN_WIDTH // 2 - 230, item_y, 460, 56)
            item_hover = item_rect.collidepoint(self.mouse_x, self.mouse_y)
            
            self.draw_glass_rect(item_rect.x, item_rect.y, item_rect.width, item_rect.height, COLOR_PURPLE, item_hover)
            
            item_text = self.font_medium.render(item, True, COLOR_FOREGROUND)
            item_text_rect = item_text.get_rect(center=item_rect.center)
            self.screen.blit(item_text, item_text_rect)
            
            # Toggle particle effects
            if i == 0 and item_hover and self.mouse_clicked:
                self.settings.particle_effects = not self.settings.particle_effects
            # Toggle show FPS
            elif i == 2 and item_hover and self.mouse_clicked:
                self.settings.show_fps = not self.settings.show_fps
    
    def draw_leaderboard_screen(self):
        """Draw leaderboard screen with real data"""
        self.screen.fill(BG_DARK)
        
        self.draw_glow_text("LEADERBOARD", self.font_large, COLOR_CYAN, 40, 25)
        
        # Back button
        back_rect = pygame.Rect(40, 80, 120, 38)
        back_hover = back_rect.collidepoint(self.mouse_x, self.mouse_y)
        self.draw_glass_rect(40, 80, 120, 38, COLOR_CYAN, back_hover)
        back_text = self.font_small.render("← BACK", True, COLOR_CYAN)
        self.screen.blit(back_text, (55, 89))
        
        if back_hover and self.mouse_clicked:
            self.state = GameState.MAIN_MENU
        
        # Get top scores
        top_scores = self.data_manager.get_top_scores(10)
        
        if not top_scores:
            # No scores yet
            no_scores_text = self.font_medium.render("No scores yet. Play to get on the leaderboard!", True, COLOR_FOREGROUND)
            no_scores_rect = no_scores_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            self.screen.blit(no_scores_text, no_scores_rect)
            return
        
        # Top 3 podium
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
        
        # Rest of leaderboard
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
    
    def handle_text_input(self, event):
        """Handle text input for login/register"""
        if event.key == pygame.K_BACKSPACE:
            if self.input_active == "username":
                self.username_input = self.username_input[:-1]
            elif self.input_active == "password":
                self.password_input = self.password_input[:-1]
        elif event.key == pygame.K_TAB:
            self.input_active = "password" if self.input_active == "username" else "username"
        elif event.key == pygame.K_RETURN:
            # Try to login/register
            if self.state == GameState.LOGIN:
                success, message = self.data_manager.login_user(self.username_input, self.password_input)
                if success:
                    self.current_user = self.username_input
                    self.state = GameState.MAIN_MENU
                    self.username_input = ""
                    self.password_input = ""
                else:
                    self.error_message = message
            elif self.state == GameState.REGISTER:
                success, message = self.data_manager.register_user(self.username_input, self.password_input)
                if success:
                    self.success_message = message
                    self.error_message = ""
                    self.current_user = self.username_input
                    self.username_input = ""
                    self.password_input = ""
                    pygame.time.wait(500)
                    self.state = GameState.MAIN_MENU
                else:
                    self.error_message = message
                    self.success_message = ""
        else:
            # Add character
            if event.unicode.isprintable() and len(event.unicode) == 1:
                if self.input_active == "username" and len(self.username_input) < 20:
                    self.username_input += event.unicode
                elif self.input_active == "password" and len(self.password_input) < 30:
                    self.password_input += event.unicode
    
    def handle_events(self):
        """Handle pygame events"""
        self.mouse_clicked = False
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            elif event.type == pygame.MOUSEMOTION:
                self.mouse_x, self.mouse_y = event.pos
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self.mouse_clicked = True
                
                if self.state == GameState.GAME_SCREEN and not self.game_over_type:
                    if not self.ball_launched:
                        self.ball_launched = True
                        self.ball_vx = random.uniform(-2.5, 2.5)
                        self.ball_vy = -5
            
            elif event.type == pygame.KEYDOWN:
                # Handle text input for login/register screens
                if self.state in [GameState.LOGIN, GameState.REGISTER]:
                    self.handle_text_input(event)
                
                # Game controls
                elif event.key == pygame.K_SPACE:
                    if self.state == GameState.GAME_SCREEN and not self.game_over_type:
                        if not self.ball_launched:
                            self.ball_launched = True
                            self.ball_vx = random.uniform(-2.5, 2.5)
                            self.ball_vy = -5
                
                elif event.key == pygame.K_ESCAPE:
                    if self.state == GameState.GAME_SCREEN:
                        self.state = GameState.MAPS_SCREEN
                    elif self.state not in [GameState.LOGIN, GameState.REGISTER]:
                        self.state = GameState.MAIN_MENU
    
    def run(self):
        """Main game loop"""
        while self.running:
            self.time += 0.016
            self.handle_events()
            
            # Clear screen
            self.screen.fill(BG_DARK)
            
            # Draw current screen
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
            elif self.state == GameState.SETTINGS_SCREEN:
                self.draw_settings_screen()
            elif self.state == GameState.LEADERBOARD_SCREEN:
                self.draw_leaderboard_screen()
            
            # Update display
            pygame.display.flip()
            
            # Track FPS
            self.clock.tick(FPS)
            self.fps_counter = int(self.clock.get_fps())
        
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = BlockSmasher()
    game.run()
