import pyray as rl

from engine.math_extensions import v2
from engine.framework import Scene
from engine.prefabs.includes import FontManager
from engine.prefabs.services import TextureService, SoundService


class LeaderboardScreen(Scene):
    def __init__(self):
        super().__init__()
        self.font = None
        self.background_texture = None
        self.title = "Final Results"
        self.player_results = []
        self.background_music = None
        self.music_playing = False

    def init_services(self):
        self.add_service(TextureService)
        self.add_service(SoundService)

    def init(self):
        font_manager = self.game.get_manager(FontManager)
        self.font = font_manager.get_font("Tiny5")
        texture_service = self.get_service(TextureService)
        self.background_texture = texture_service.get_texture("assets/startscreen.png")
        
        level1_times = getattr(self.game, 'player_times_level1', {})
        level2_times = getattr(self.game, 'player_times_level2', {})
        level3_times = getattr(self.game, 'player_times_level3', {})
        all_players = set(level1_times.keys()) | set(level2_times.keys()) | set(level3_times.keys())
        
        results = []
        for player_num in all_players:
            time1 = level1_times.get(player_num, -1.0)
            time2 = level2_times.get(player_num, -1.0)
            time3 = level3_times.get(player_num, -1.0)
            
            if time1 < 0 or time2 < 0 or time3 < 0:
                total_time = -1.0
                status = "DNF"
            else:
                total_time = time1 + time2 + time3
                status = self.format_time(total_time)
            
            results.append({
                'player': player_num,
                'total_time': total_time,
                'status': status,
                'level1': self.format_time(time1) if time1 >= 0 else "DNF",
                'level2': self.format_time(time2) if time2 >= 0 else "DNF",
                'level3': self.format_time(time3) if time3 >= 0 else "DNF"
            })
        
        results.sort(key=lambda x: (x['total_time'] < 0, x['total_time'] if x['total_time'] >= 0 else float('inf')))
        self.player_results = results
        
        sound_service = self.get_service(SoundService)
        self.background_music = sound_service.get_sound("assets/sounds/end.mp3")
        rl.play_sound(self.background_music)
        self.music_playing = True

    def format_time(self, time_seconds):
        """Format time in MM:SS.ms format"""
        if time_seconds < 0:
            return "DNF"
        minutes = int(time_seconds // 60)
        seconds = time_seconds % 60
        return f"{minutes}:{seconds:05.2f}"

    def update(self, delta_time):
        if self.music_playing and not rl.is_sound_playing(self.background_music):
            rl.play_sound(self.background_music)
        
        if rl.is_key_pressed(rl.KEY_ENTER) or rl.is_gamepad_button_pressed(0, rl.GAMEPAD_BUTTON_MIDDLE_RIGHT):
            if self.music_playing:
                rl.stop_sound(self.background_music)
                self.music_playing = False
            if hasattr(self.game, 'player_times_level1'):
                delattr(self.game, 'player_times_level1')
            if hasattr(self.game, 'player_times_level2'):
                delattr(self.game, 'player_times_level2')
            if hasattr(self.game, 'player_times_level3'):
                delattr(self.game, 'player_times_level3')
            self.game.go_to_scene(0)

    def draw(self):
        width = rl.get_screen_width()
        height = rl.get_screen_height()

        if self.background_texture:
            rl.draw_texture_pro(
                self.background_texture,
                rl.Rectangle(0, 0, float(self.background_texture.width), float(self.background_texture.height)),
                rl.Rectangle(0, 0, float(width), float(height)),
                v2(0, 0),
                0,
                rl.WHITE
            )
        else:
            rl.clear_background(rl.Color(50, 150, 50, 255))
        
        rl.draw_rectangle(0, 0, width, height, rl.Color(0, 0, 0, 150))
        
        title_size = 128
        title_measured = rl.measure_text_ex(self.font, self.title, title_size, 2)
        title_x = (width - title_measured.x) / 2
        title_y = 50
        
        for dx, dy in [(0, 4), (4, 0), (0, -4), (-4, 0)]:
            rl.draw_text_ex(self.font, self.title, v2(title_x + dx, title_y + dy), title_size, 2, rl.BLACK)
        rl.draw_text_ex(self.font, self.title, v2(title_x, title_y), title_size, 2, rl.Color(255, 255, 100, 255))
        
        player_colors = [
            rl.Color(230, 41, 55, 255),
            rl.Color(0, 121, 241, 255),
            rl.Color(253, 249, 0, 255),
            rl.Color(0, 228, 48, 255)
        ]
        
        y_offset = 220
        text_size = 64
        
        for i, result in enumerate(self.player_results):
            player_num = result['player']
            color = player_colors[player_num - 1] if player_num - 1 < len(player_colors) else rl.WHITE
            
            position_text = ["1st", "2nd", "3rd", "4th"][i] if i < 4 else f"{i+1}th"
            text = f"{position_text} - Player {player_num}: {result['status']}"
            
            measured = rl.measure_text_ex(self.font, text, text_size, 2)
            text_x = (width - measured.x) / 2
            
            for dx, dy in [(0, 2), (2, 0), (0, -2), (-2, 0)]:
                rl.draw_text_ex(self.font, text, v2(text_x + dx, y_offset + dy), text_size, 2, rl.BLACK)
            rl.draw_text_ex(self.font, text, v2(text_x, y_offset), text_size, 2, color)
            
            breakdown_size = 40
            breakdown_text = f"L1: {result['level1']} | L2: {result['level2']} | L3: {result['level3']}"
            breakdown_measured = rl.measure_text_ex(self.font, breakdown_text, breakdown_size, 2)
            breakdown_x = (width - breakdown_measured.x) / 2
            
            rl.draw_text_ex(self.font, breakdown_text, v2(breakdown_x, y_offset + 70), breakdown_size, 2, rl.Color(200, 200, 200, 255))
            
            y_offset += 130
        
        instruction = "Thank you for playing!"
        instruction_size = 48
        instruction_measured = rl.measure_text_ex(self.font, instruction, instruction_size, 2)
        instruction_x = (width - instruction_measured.x) / 2
        instruction_y = height - 80
        
        for dx, dy in [(0, 2), (2, 0), (0, -2), (-2, 0)]:
            rl.draw_text_ex(self.font, instruction, v2(instruction_x + dx, instruction_y + dy), instruction_size, 2, rl.BLACK)
        rl.draw_text_ex(self.font, instruction, v2(instruction_x, instruction_y), instruction_size, 2, rl.WHITE)
