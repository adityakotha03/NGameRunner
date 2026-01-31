import pyray as rl

from engine.framework import Game
from engine.prefabs.managers import FontManager, WindowManager
from samples.collecting_game import CollectingScene
from samples.fighting_game import FightingScene
from samples.zombie_game import ZombieScene
from samples.title_screen import TitleScreen
from samples.n_game import NScene

game = Game()


def update() -> None:
    delta_time = rl.get_frame_time()
    game.update(delta_time)


def main() -> int:
    game.add_manager(WindowManager, 1440, 1440, "Game Jam Kit")
    font_manager = game.add_manager(FontManager)
    game.init()

    font_manager.load_font("Roboto", "assets/fonts/Roboto.ttf", 64)
    font_manager.load_font("Tiny5", "assets/fonts/Tiny5.ttf", 64)
    font_manager.set_texture_filter("Roboto", 4)

    game.add_scene("title", TitleScreen)
    # game.add_scene("fighting", FightingScene)
    # game.add_scene("collecting", CollectingScene)
    # game.add_scene("zombie", ZombieScene)
    game.add_scene("n", NScene)

    while not rl.window_should_close():
        update()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
