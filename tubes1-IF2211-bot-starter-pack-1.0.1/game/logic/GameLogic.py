from typing import Optional
from game.logic.base import BaseLogic
from game.models import GameObject, Board, Position
from ..util import get_direction

class GameLogic(BaseLogic):
    def __init__(self) -> None:
        self.directions = [(1, 0), (0, 1), (-1, 0), (0, -1)]

    def next_move(self, board_bot: GameObject, board: Board):
        self.bot = board_bot
        self.board = board
        self.position = board_bot.position
        self.diamonds = board.diamonds
        self.bots = [b for b in board.bots if b.id != board_bot.id]

        # Pulang ke base jika sudah penuh atau waktu hampir habis
        if self.bot.properties.diamonds >= 5 or self.bot.properties.milliseconds_left < 5000:
            return self.move_towards(self.bot.properties.base)

        # Pilih diamond terbaik
        target = self.select_best_diamond()
        return self.move_towards(target)

    def select_best_diamond(self) -> Position:
        def score(d: GameObject) -> float:
            distance = self.manhattan(self.position, d.position)
            value = d.properties.points
            safety = self.estimate_safety(d.position)
            return (value * safety) / (distance if distance != 0 else 1)
        return max(self.diamonds, key=score).position

    def estimate_safety(self, position: Position) -> float:
        radius = 4
        threat = sum(
            1 for enemy in self.bots
            if self.manhattan(enemy.position, position) <= radius and
               enemy.properties.diamonds >= self.bot.properties.diamonds
        )
        return 1 / (1 + threat)

    def move_towards(self, target: Position):
        dx, dy = get_direction(
            self.position.x, self.position.y, target.x, target.y
        )
        return dx, dy

    def manhattan(self, p1: Position, p2: Position) -> int:
        return abs(p1.x - p2.x) + abs(p1.y - p2.y)
