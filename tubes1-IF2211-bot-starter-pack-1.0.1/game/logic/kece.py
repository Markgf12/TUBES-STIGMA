import random
from typing import Optional, List, Tuple

from game.logic.base import BaseLogic
from game.models import GameObject, Board, Position
from ..util import get_direction


class GreedyDiamondBot(BaseLogic):
    def _init_(self):
        self.directions = [(1, 0), (0, 1), (-1, 0), (0, -1)]
        self.goal_position: Optional[Position] = None
        self.target_diamond: Optional[GameObject] = None
        self.danger_radius = 3  # Radius to detect enemies
        self.safe_distance = 2  # Minimum safe distance from enemies
        
    def next_move(self, board_bot: GameObject, board: Board):
        try:
            props = board_bot.properties
            current_position = board_bot.position
            
            # Priority 1: Avoid enemies - check for nearby threats
            enemies = self.get_enemies(board, board_bot)
            if enemies:
                danger_move = self.avoid_enemies(current_position, enemies)
                if danger_move:
                    return danger_move
            
            # Priority 2: If carrying 4+ diamonds, return to base (reduced from 5)
            if props.diamonds >= 4:
                base = props.base
                if base and not self.is_at_position(current_position, base):
                    delta_x, delta_y = get_direction(
                        current_position.x,
                        current_position.y,
                        base.x,
                        base.y,
                    )
                    return delta_x, delta_y
            
            # Priority 3: If at base and have diamonds, move away first
            if props.base and self.is_at_position(current_position, props.base) and props.diamonds > 0:
                # Move away from base to continue collecting
                return self.move_away_from_base(current_position, props.base)
            
            # Priority 4: Find and collect diamonds
            diamonds = self.get_diamonds(board)
            
            if diamonds:
                # Find best diamond with improved scoring
                best_diamond = self.find_best_diamond(current_position, diamonds, enemies)
                if best_diamond:
                    delta_x, delta_y = get_direction(
                        current_position.x,
                        current_position.y,
                        best_diamond.position.x,
                        best_diamond.position.y,
                    )
                    return delta_x, delta_y
            
            # Priority 5: If carrying any diamonds and no good diamonds found, return to base
            if props.diamonds > 0:
                base = props.base
                if base and not self.is_at_position(current_position, base):
                    delta_x, delta_y = get_direction(
                        current_position.x,
                        current_position.y,
                        base.x,
                        base.y,
                    )
                    return delta_x, delta_y
            
            # Priority 6: Intelligent exploration instead of random
            return self.get_exploration_move(current_position, board)
            
        except Exception as e:
            # Fallback to safe random movement
            print(f"Error in GreedyDiamondBot: {e}")
            return self.get_safe_random_move()
    
    def get_enemies(self, board: Board, bot: GameObject) -> List[GameObject]:
        """Get all enemy bots on the board"""
        enemies = []
        try:
            for game_object in board.game_objects:
                # Check if it's a bot and not our bot
                if (hasattr(game_object, 'type') and 'Bot' in game_object.type and 
                    game_object.id != bot.id):
                    # Check if enemy is within danger radius
                    distance = self.manhattan_distance(bot.position, game_object.position)
                    if distance <= self.danger_radius:
                        enemies.append(game_object)
        except:
            pass
        return enemies
    
    def avoid_enemies(self, current_pos: Position, enemies: List[GameObject]) -> Optional[Tuple[int, int]]:
        """Calculate move to avoid enemies"""
        if not enemies:
            return None
        
        # Find the closest enemy
        closest_enemy = min(enemies, 
                          key=lambda enemy: self.manhattan_distance(current_pos, enemy.position))
        
        enemy_pos = closest_enemy.position
        distance = self.manhattan_distance(current_pos, enemy_pos)
        
        # If too close, move away immediately
        if distance <= self.safe_distance:
            # Calculate direction away from enemy
            if enemy_pos.x != current_pos.x:
                move_x = -1 if enemy_pos.x > current_pos.x else 1
            else:
                move_x = 0
                
            if enemy_pos.y != current_pos.y:
                move_y = -1 if enemy_pos.y > current_pos.y else 1
            else:
                move_y = 0
            
            # Prioritize the axis with larger distance difference
            if abs(enemy_pos.x - current_pos.x) > abs(enemy_pos.y - current_pos.y):
                return (move_x, 0)
            else:
                return (0, move_y)
        
        return None
    
    def get_diamonds(self, board: Board) -> List[GameObject]:
        """Get all diamonds on the board"""
        diamonds = []
        try:
            for game_object in board.game_objects:
                if hasattr(game_object, 'type') and game_object.type == "DiamondGameObject":
                    diamonds.append(game_object)
                elif "Diamond" in str(type(game_object)):
                    diamonds.append(game_object)
        except:
            pass
        return diamonds
    
    def find_best_diamond(self, current_pos: Position, diamonds: List[GameObject], 
                         enemies: List[GameObject]) -> Optional[GameObject]:
        """Find the best diamond using improved greedy algorithm"""
        if not diamonds:
            return None
            
        best_diamond = None
        best_score = float('inf')
        
        for diamond in diamonds:
            try:
                # Calculate Manhattan distance
                distance = self.manhattan_distance(current_pos, diamond.position)
                
                # Get diamond points if available
                diamond_points = 1
                if hasattr(diamond, 'properties') and hasattr(diamond.properties, 'points'):
                    diamond_points = diamond.properties.points
                
                # Check if diamond is safe from enemies
                diamond_safe = True
                for enemy in enemies:
                    enemy_to_diamond_dist = self.manhattan_distance(enemy.position, diamond.position)
                    if enemy_to_diamond_dist <= self.safe_distance:
                        diamond_safe = False
                        break
                
                # Calculate score: lower is better
                if diamond_points > 0:
                    score = distance / diamond_points
                else:
                    score = distance
                
                # Penalty for unsafe diamonds
                if not diamond_safe:
                    score *= 2  # Make unsafe diamonds less attractive
                
                # Bonus for high-value diamonds
                if diamond_points >= 2:
                    score *= 0.7  # Make high-value diamonds more attractive
                
                if score < best_score:
                    best_score = score
                    best_diamond = diamond
                    
            except Exception:
                continue
                
        return best_diamond
    
    def is_at_position(self, pos1: Position, pos2: Position) -> bool:
        """Check if two positions are the same"""
        return pos1.x == pos2.x and pos1.y == pos2.y
    
    def move_away_from_base(self, current_pos: Position, base: Position) -> Tuple[int, int]:
        """Move away from base to continue exploration"""
        # Calculate direction away from base
        if base.x != current_pos.x:
            move_x = -1 if base.x > current_pos.x else 1
        else:
            move_x = random.choice([-1, 1])
            
        if base.y != current_pos.y:
            move_y = -1 if base.y > current_pos.y else 1
        else:
            move_y = random.choice([-1, 1])
        
        # Choose the direction that moves furthest from base
        if abs(move_x) > abs(move_y):
            return (move_x, 0)
        else:
            return (0, move_y)
    
    def get_exploration_move(self, current_pos: Position, board: Board) -> Tuple[int, int]:
        """Get intelligent exploration move instead of random"""
        # Try to move towards less explored areas (center of the board)
        board_center_x = board.width // 2 if hasattr(board, 'width') else 10
        board_center_y = board.height // 2 if hasattr(board, 'height') else 10
        
        # Move towards center with some randomness
        if random.random() < 0.7:  # 70% chance to move towards center
            delta_x, delta_y = get_direction(
                current_pos.x,
                current_pos.y,
                board_center_x,
                board_center_y,
            )
            return delta_x, delta_y
        else:
            return self.get_safe_random_move()
    
    def get_safe_random_move(self) -> Tuple[int, int]:
        """Get a random move"""
        return random.choice(self.directions)
    
    def manhattan_distance(self, pos1: Position, pos2: Position) -> int:
        """Calculate Manhattan distance between two positions"""
        return abs(pos1.x - pos2.x) + abs(pos1.y - pos2.y)