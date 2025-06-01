import random
from typing import Optional, List, Tuple
from game.logic.base import BaseLogic
from game.models import GameObject, Board, Position
from ..util import get_direction

class GreedyByEfficiency(BaseLogic):
    def __init__(self):
        self.directions = [(1, 0), (0, 1), (-1, 0), (0, -1)]
        self.goal_position: Optional[Position] = None
        self.target_diamond: Optional[GameObject] = None
        self.danger_radius = 3  # Radius untuk mendeteksi musuh
        self.safe_distance = 2  # Jarak aman minimum dari musuh
        
    def next_move(self, board_bot: GameObject, board: Board):
        try:
            props = board_bot.properties
            current_position = board_bot.position
            
            # Prioritas 1: Menghindari musuh - periksa ancaman terdekat
            enemies = self.get_enemies(board, board_bot)
            if enemies:
                danger_move = self.avoid_enemies(current_position, enemies)
                if danger_move:
                    return danger_move
            
            # Prioritas 2: Jika membawa 4+ berlian, kembali ke base (dikurangi dari 5)
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
            
            # Prioritas 3: Jika di base dan punya berlian, bergerak menjauh dulu
            if props.base and self.is_at_position(current_position, props.base) and props.diamonds > 0:
                # Bergerak menjauh dari base untuk melanjutkan pengumpulan
                return self.move_away_from_base(current_position, props.base)
            
            # Prioritas 4: Cari dan kumpulkan berlian
            diamonds = self.get_diamonds(board)
            
            if diamonds:
                # Cari berlian terbaik dengan penilaian yang diperbaiki
                best_diamond = self.find_best_diamond(current_position, diamonds, enemies)
                if best_diamond:
                    delta_x, delta_y = get_direction(
                        current_position.x,
                        current_position.y,
                        best_diamond.position.x,
                        best_diamond.position.y,
                    )
                    return delta_x, delta_y
            
            # Prioritas 5: Jika membawa berlian dan tidak ada berlian bagus yang ditemukan, kembali ke base
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
            
            # Prioritas 6: Eksplorasi cerdas alih-alih gerakan acak
            return self.get_exploration_move(current_position, board)
            
        except Exception as e:
            # Fallback ke gerakan acak yang aman
            print(f"Error in GreedyDiamondBot: {e}")
            return self.get_safe_random_move()
    
    def get_enemies(self, board: Board, bot: GameObject) -> List[GameObject]:
        """Dapatkan semua bot musuh di papan"""
        enemies = []
        try:
            for game_object in board.game_objects:
                # Periksa apakah itu bot dan bukan bot kita
                if (hasattr(game_object, 'type') and 'Bot' in game_object.type and 
                    game_object.id != bot.id):
                    # Periksa apakah musuh dalam radius bahaya
                    distance = self.manhattan_distance(bot.position, game_object.position)
                    if distance <= self.danger_radius:
                        enemies.append(game_object)
        except:
            pass
        return enemies
    
    def avoid_enemies(self, current_pos: Position, enemies: List[GameObject]) -> Optional[Tuple[int, int]]:
        """Hitung gerakan untuk menghindari musuh"""
        if not enemies:
            return None
        
        # Cari musuh terdekat
        closest_enemy = min(enemies, 
                          key=lambda enemy: self.manhattan_distance(current_pos, enemy.position))
        
        enemy_pos = closest_enemy.position
        distance = self.manhattan_distance(current_pos, enemy_pos)
        
        # Jika terlalu dekat, bergerak menjauh segera
        if distance <= self.safe_distance:
            # Hitung arah menjauhi musuh
            if enemy_pos.x != current_pos.x:
                move_x = -1 if enemy_pos.x > current_pos.x else 1
            else:
                move_x = 0
                
            if enemy_pos.y != current_pos.y:
                move_y = -1 if enemy_pos.y > current_pos.y else 1
            else:
                move_y = 0
            
            # Prioritaskan sumbu dengan selisih jarak yang lebih besar
            if abs(enemy_pos.x - current_pos.x) > abs(enemy_pos.y - current_pos.y):
                return (move_x, 0)
            else:
                return (0, move_y)
        
        return None
    
    def get_diamonds(self, board: Board) -> List[GameObject]:
        """Dapatkan semua berlian di papan"""
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
        """Cari berlian terbaik menggunakan algoritma greedy yang diperbaiki"""
        if not diamonds:
            return None
            
        best_diamond = None
        best_score = float('inf')
        
        for diamond in diamonds:
            try:
                # Hitung jarak Manhattan
                distance = self.manhattan_distance(current_pos, diamond.position)
                
                # Dapatkan poin berlian jika tersedia
                diamond_points = 1
                if hasattr(diamond, 'properties') and hasattr(diamond.properties, 'points'):
                    diamond_points = diamond.properties.points
                
                # Periksa apakah berlian aman dari musuh
                diamond_safe = True
                for enemy in enemies:
                    enemy_to_diamond_dist = self.manhattan_distance(enemy.position, diamond.position)
                    if enemy_to_diamond_dist <= self.safe_distance:
                        diamond_safe = False
                        break
                
                # Hitung skor: semakin rendah semakin baik
                if diamond_points > 0:
                    score = distance / diamond_points
                else:
                    score = distance
                
                # Penalti untuk berlian yang tidak aman
                if not diamond_safe:
                    score *= 2  # Buat berlian tidak aman kurang menarik
                
                # Bonus untuk berlian bernilai tinggi
                if diamond_points >= 2:
                    score *= 0.7  # Buat berlian bernilai tinggi lebih menarik
                
                if score < best_score:
                    best_score = score
                    best_diamond = diamond
                    
            except Exception:
                continue
                
        return best_diamond
    
    def is_at_position(self, pos1: Position, pos2: Position) -> bool:
        """Periksa apakah dua posisi sama"""
        return pos1.x == pos2.x and pos1.y == pos2.y
    
    def move_away_from_base(self, current_pos: Position, base: Position) -> Tuple[int, int]:
        """Bergerak menjauh dari base untuk melanjutkan eksplorasi"""
        # Hitung arah menjauhi base
        if base.x != current_pos.x:
            move_x = -1 if base.x > current_pos.x else 1
        else:
            move_x = random.choice([-1, 1])
            
        if base.y != current_pos.y:
            move_y = -1 if base.y > current_pos.y else 1
        else:
            move_y = random.choice([-1, 1])
        
        # Pilih arah yang paling jauh dari base
        if abs(move_x) > abs(move_y):
            return (move_x, 0)
        else:
            return (0, move_y)
    
    def get_exploration_move(self, current_pos: Position, board: Board) -> Tuple[int, int]:
        """Dapatkan gerakan eksplorasi cerdas alih-alih acak"""
        # Coba bergerak ke area yang kurang dieksplorasi (pusat papan)
        board_center_x = board.width // 2 if hasattr(board, 'width') else 10
        board_center_y = board.height // 2 if hasattr(board, 'height') else 10
        
        # Bergerak ke pusat dengan sedikit keacakan
        if random.random() < 0.7:  # 70% kemungkinan bergerak ke pusat
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
        """Dapatkan gerakan acak"""
        return random.choice(self.directions)
    
    def manhattan_distance(self, pos1: Position, pos2: Position) -> int:
        """Hitung jarak Manhattan antara dua posisi"""
        return abs(pos1.x - pos2.x) + abs(pos1.y - pos2.y)