import pyray as rl

from engine.math_extensions import v2
from engine.framework import Scene
from engine.prefabs.includes import FontManager
from engine.prefabs.services import TextureService, SoundService


class TitleScreen(Scene):
    def __init__(self):
        super().__init__()
        self.font = None
        self.background_texture = None
        self.title = "N Game Runner"
        self.start_sound = None
        self.music_playing = False

    def init_services(self):
        self.add_service(TextureService)
        self.add_service(SoundService)

    def init(self):
        font_manager = self.game.get_manager(FontManager)
        self.font = font_manager.get_font("Tiny5")
        texture_service = self.get_service(TextureService)
        self.background_texture = texture_service.get_texture("assets/startscreen.png")
        sound_service = self.get_service(SoundService)
        self.start_sound = sound_service.get_sound("assets/sounds/title.mp3")
        rl.play_sound(self.start_sound)
        self.music_playing = True

    def update(self, delta_time):
        if self.music_playing and not rl.is_sound_playing(self.start_sound):
            rl.play_sound(self.start_sound)
        
        if rl.is_key_pressed(rl.KEY_ENTER) or rl.is_gamepad_button_pressed(0, rl.GAMEPAD_BUTTON_MIDDLE_RIGHT):
            if self.music_playing:
                rl.stop_sound(self.start_sound)
                self.music_playing = False
            self.game.go_to_scene_next()

    def draw(self):
        width = rl.get_screen_width()
        height = rl.get_screen_height()
        
        # Use larger sizes for retro pixel font
        title_size = 128
        subtitle_size = 48
        
        title_text_size = rl.measure_text_ex(self.font, self.title, title_size, 2)
        subtitle = "Press Start or Enter to Start the Game"
        subtitle_text_size = rl.measure_text_ex(self.font, subtitle, subtitle_size, 2)

        # Draw background image scaled to screen size
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
            rl.clear_background(rl.SKYBLUE)
        
        # Calculate positions
        title_x = (width - title_text_size.x) / 2
        title_y = (height - title_text_size.y) / 2 - 100
        subtitle_x = (width - subtitle_text_size.x) / 2
        subtitle_y = (height - subtitle_text_size.y) / 2 + 100
        
        offset = 4
        for dx, dy in [(0, offset), (offset, 0), (0, -offset), (-offset, 0), 
                       (offset, offset), (-offset, -offset), (offset, -offset), (-offset, offset)]:
            rl.draw_text_ex(
                self.font,
                self.title,
                v2(title_x + dx, title_y + dy),
                title_size,
                2,
                rl.Color(20, 50, 20, 255),  # Dark green outline
            )
        rl.draw_text_ex(
            self.font,
            self.title,
            v2(title_x, title_y),
            title_size,
            2,
            rl.Color(255, 255, 100, 255),  # Bright yellow
        )
        
        offset = 2
        for dx, dy in [(0, offset), (offset, 0), (0, -offset), (-offset, 0)]:
            rl.draw_text_ex(
                self.font,
                subtitle,
                v2(subtitle_x + dx, subtitle_y + dy),
                subtitle_size,
                2,
                rl.Color(20, 50, 20, 255),  # Dark green outline
            )
        # Main subtitle text in white
        rl.draw_text_ex(
            self.font,
            subtitle,
            v2(subtitle_x, subtitle_y),
            subtitle_size,
            2,
            rl.WHITE,
        )
