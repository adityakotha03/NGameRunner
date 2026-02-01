from __future__ import annotations

import math
from typing import Dict, List

from Box2D import b2ContactListener, b2PolygonShape, b2Vec2
import pyray as rl

from engine.framework import GameObject, Scene
from engine.math_extensions import vec_add, vec_div, vec_mul, vec_sub, v2
from engine.prefabs.components import (AnimationController, BodyComponent, MultiComponent, SoundComponent,
                                       SpriteComponent, PlatformerMovementComponent, PlatformerMovementParams)
from engine.prefabs.game_objects import CharacterParams, StaticBox
from engine.prefabs.managers import FontManager
from engine.prefabs.services import LevelService, PhysicsService, SoundService, TextureService
import random


class BloodParticle:
    """Simple blood particle effect."""
    def __init__(self, position: rl.Vector2):
        self.position = rl.Vector2(position.x, position.y)
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(50, 150)
        self.velocity = rl.Vector2(math.cos(angle) * speed, math.sin(angle) * speed)
        self.lifetime = random.uniform(0.3, 0.6)
        self.max_lifetime = self.lifetime
        self.size = random.uniform(3, 8)
    
    def update(self, delta_time: float) -> bool:
        self.position.x += self.velocity.x * delta_time
        self.position.y += self.velocity.y * delta_time
        self.velocity.y += 300 * delta_time
        self.lifetime -= delta_time
        return self.lifetime > 0
    
    def draw(self):
        alpha = int(255 * (self.lifetime / self.max_lifetime))
        color = rl.Color(180, 0, 0, alpha)
        rl.draw_circle_v(self.position, self.size, color)


class NCharacter(GameObject):
    """Platformer character with attacks and one-way platform logic."""
    def __init__(self, params: CharacterParams, player_number: int = 1) -> None:
        """Create a player-controlled fighter.

        Args:
            params: Character sizing and physics parameters.
            player_number: 1-based index used to map input/skins.

        Returns:
            None
        """
        super().__init__()
        self.p = params
        self.player_number = player_number
        self.gamepad = player_number - 1
        self.width = params.width
        self.height = params.height
        self.physics: PhysicsService = None  # type: ignore[assignment]
        self.level: LevelService = None  # type: ignore[assignment]
        self.body: BodyComponent = None  # type: ignore[assignment]
        self.movement: PlatformerMovementComponent = None  # type: ignore[assignment]
        self.animation: AnimationController = None  # type: ignore[assignment]
        self.sounds: MultiComponent = None  # type: ignore[assignment]
        self.jump_sound: SoundComponent = None  # type: ignore[assignment]
        self.hit_sound: SoundComponent = None  # type: ignore[assignment]
        self.die_sound: SoundComponent = None  # type: ignore[assignment]
        self.fall_through = False
        self.fall_through_timer = 0.0
        self.fall_through_duration = 0.2
        self.attack_display_timer = 0.0
        self.attack_display_duration = 0.1
        self.attack = False
        self.has_won = False

    def init(self) -> None:
        """Initialize body, movement, sounds, and animations.

        Returns:
            None
        """
        self.physics = self.scene.get_service(PhysicsService)

        def build_body(component: BodyComponent):
            """Build body.

            Args:
                component: Parameter.

            Returns:
                Result of the operation.
            """
            world = self.physics.world
            body = world.CreateDynamicBody(position=(self.physics.convert_to_meters(self.p.position).x,
                                                     self.physics.convert_to_meters(self.p.position).y),
                                           fixedRotation=True,
                                           bullet=True)
            shape = b2PolygonShape(box=(self.physics.convert_length_to_meters(self.p.width / 2.0),
                                        self.physics.convert_length_to_meters(self.p.height / 2.0)))
            body.CreateFixture(shape=shape, density=self.p.density, friction=self.p.friction,
                               restitution=self.p.restitution)
            component.body = body

        self.body = self.add_component(BodyComponent(build=build_body))

        movement_params = PlatformerMovementParams()
        movement_params.width = self.p.width
        movement_params.height = self.p.height
        self.movement = self.add_component(PlatformerMovementComponent(movement_params))

        self.level = self.scene.get_service(LevelService)

        self.sounds = self.add_component(MultiComponent())
        self.jump_sound = self.sounds.add_component("jump", SoundComponent, "assets/sounds/jump.wav")
        self.jump_sound.set_volume(0.1)
        self.hit_sound = self.sounds.add_component("hit", SoundComponent, "assets/sounds/hit.wav")
        self.die_sound = self.sounds.add_component("die", SoundComponent, "assets/sounds/die.wav")
        self.boom_sound = self.sounds.add_component("boom", SoundComponent, "assets/sounds/vineboom.mp3")
        self.win_sound = self.sounds.add_component("win", SoundComponent, "assets/sounds/win.wav")

        self.animation = self.add_component(AnimationController(self.body))
        if self.player_number == 1:
            self.animation.add_animation_from_files("run",
                                                   ["assets/sunnyland/fox/run-1.png",
                                                    "assets/sunnyland/fox/run-2.png",
                                                    "assets/sunnyland/fox/run-3.png",
                                                    "assets/sunnyland/fox/run-4.png",
                                                    "assets/sunnyland/fox/run-5.png",
                                                    "assets/sunnyland/fox/run-6.png"],
                                                   10.0)
            self.animation.add_animation_from_files("idle",
                                                   ["assets/sunnyland/fox/idle-1.png",
                                                    "assets/sunnyland/fox/idle-2.png",
                                                    "assets/sunnyland/fox/idle-3.png",
                                                    "assets/sunnyland/fox/idle-4.png"],
                                                   5.0)
            self.animation.origin.y += 4
        elif self.player_number == 2:
            self.animation.add_animation_from_files("run",
                                                   ["assets/sunnyland/bunny/run-1.png",
                                                    "assets/sunnyland/bunny/run-2.png",
                                                    "assets/sunnyland/bunny/run-3.png",
                                                    "assets/sunnyland/bunny/run-4.png",
                                                    "assets/sunnyland/bunny/run-5.png",
                                                    "assets/sunnyland/bunny/run-6.png"],
                                                   10.0)
            self.animation.add_animation_from_files("idle",
                                                   ["assets/sunnyland/bunny/idle-1.png",
                                                    "assets/sunnyland/bunny/idle-2.png",
                                                    "assets/sunnyland/bunny/idle-3.png",
                                                    "assets/sunnyland/bunny/idle-4.png"],
                                                   10.0)
            self.animation.origin.y += 8
        elif self.player_number == 3:
            self.animation.add_animation_from_files("run",
                                                   ["assets/sunnyland/squirrel/run-1.png",
                                                    "assets/sunnyland/squirrel/run-2.png",
                                                    "assets/sunnyland/squirrel/run-3.png",
                                                    "assets/sunnyland/squirrel/run-4.png",
                                                    "assets/sunnyland/squirrel/run-5.png",
                                                    "assets/sunnyland/squirrel/run-6.png"],
                                                   10.0)
            self.animation.add_animation_from_files("idle",
                                                   ["assets/sunnyland/squirrel/idle-1.png",
                                                    "assets/sunnyland/squirrel/idle-2.png",
                                                    "assets/sunnyland/squirrel/idle-3.png",
                                                    "assets/sunnyland/squirrel/idle-4.png",
                                                    "assets/sunnyland/squirrel/idle-5.png",
                                                    "assets/sunnyland/squirrel/idle-6.png",
                                                    "assets/sunnyland/squirrel/idle-7.png",
                                                    "assets/sunnyland/squirrel/idle-8.png"],
                                                   8.0)
            self.animation.origin.y += 7
        elif self.player_number == 4:
            self.animation.add_animation_from_files("run",
                                                   ["assets/sunnyland/imp/run-1.png",
                                                    "assets/sunnyland/imp/run-2.png",
                                                    "assets/sunnyland/imp/run-3.png",
                                                    "assets/sunnyland/imp/run-4.png",
                                                    "assets/sunnyland/imp/run-5.png",
                                                    "assets/sunnyland/imp/run-6.png",
                                                    "assets/sunnyland/imp/run-7.png",
                                                    "assets/sunnyland/imp/run-8.png"],
                                                   10.0)
            self.animation.add_animation_from_files("idle",
                                                   ["assets/sunnyland/imp/idle-1.png",
                                                    "assets/sunnyland/imp/idle-2.png",
                                                    "assets/sunnyland/imp/idle-3.png",
                                                    "assets/sunnyland/imp/idle-4.png"],
                                                   10.0)
            self.animation.origin.y += 10

    def update(self, delta_time: float) -> None:
        """Handle input, jumping, attacks, and respawn logic.

        Args:
            delta_time: Seconds since last frame.

        Returns:
            None
        """
        self.jump_sound.set_volume(0.4)
        deadzone = 0.1
        jump_pressed = rl.is_key_pressed(rl.KEY_W) or rl.is_gamepad_button_pressed(self.gamepad, rl.GAMEPAD_BUTTON_RIGHT_FACE_DOWN)
        jump_held = rl.is_key_down(rl.KEY_W) or rl.is_gamepad_button_down(self.gamepad, rl.GAMEPAD_BUTTON_RIGHT_FACE_DOWN)

        move_x = rl.get_gamepad_axis_movement(self.gamepad, rl.GAMEPAD_AXIS_LEFT_X)
        if abs(move_x) < deadzone:
            move_x = 0.0
        if rl.is_key_down(rl.KEY_D) or rl.is_gamepad_button_down(self.gamepad, rl.GAMEPAD_BUTTON_LEFT_FACE_RIGHT):
            move_x = 1.0
        elif rl.is_key_down(rl.KEY_A) or rl.is_gamepad_button_down(self.gamepad, rl.GAMEPAD_BUTTON_LEFT_FACE_LEFT):
            move_x = -1.0

        self.movement.set_input(move_x, jump_pressed, jump_held)

        if self.movement.grounded and jump_pressed:
            self.jump_sound.play()

        if abs(self.movement.move_x) > 0.1:
            self.animation.play("run")
            self.animation.flip_x = self.movement.move_x < 0.0
        else:
            self.animation.play("idle")

        if not self.movement.grounded:
            if self.player_number != 3:
                if self.body.get_velocity_meters().y < 0.0:
                    self.animation.play("jump")
                else:
                    self.animation.play("fall")
            else:
                self.animation.play("jump")

        move_y = rl.get_gamepad_axis_movement(self.gamepad, rl.GAMEPAD_AXIS_LEFT_Y)
        if rl.is_key_pressed(rl.KEY_S) or rl.is_gamepad_button_pressed(self.gamepad, rl.GAMEPAD_BUTTON_LEFT_FACE_DOWN) or move_y > 0.5:
            self.fall_through = True
            self.fall_through_timer = self.fall_through_duration

        if self.fall_through_timer > 0.0:
            self.fall_through_timer = max(0.0, self.fall_through_timer - delta_time)
            if self.fall_through_timer == 0.0:
                self.fall_through = False

        if rl.is_key_pressed(rl.KEY_SPACE) or rl.is_gamepad_button_pressed(self.gamepad, rl.GAMEPAD_BUTTON_RIGHT_FACE_RIGHT):
            self.hit_sound.play()
            self.hit_sound.set_volume(2.0)
            self.attack = True
            self.attack_display_timer = self.attack_display_duration
            position = self.body.get_position_pixels()
            position.x += (self.width / 2.0 + 8.0) * (-1.0 if self.animation.flip_x else 1.0)
            bodies = self.physics.circle_overlap(position, 8.0, self.body.body)
            for other_body in bodies:
                if other_body == self.body.body:
                    continue
                impulse = b2Vec2(-10.0 if self.animation.flip_x else 10.0, -10.0)
                other_body.ApplyLinearImpulse(impulse=impulse, point=other_body.worldCenter, wake=True)
                # self.hit_sound.play()

        if self.attack_display_timer > 0.0:
            self.attack_display_timer = max(0.0, self.attack_display_timer - delta_time)
            if self.attack_display_timer == 0.0:
                self.attack = False

        if not self.has_won:
            for contact_body in self.body.get_contacts():
                other = contact_body.userData
                if other and other.has_tag("goal"):
                    self.has_won = True
                    self.win_sound.play()
                    scene = self.scene
                    if hasattr(scene, 'add_winner'):
                        scene.add_winner(self.player_number)
                    self.is_active = False
                    self.body.set_position(v2(-1000.0, -1000.0))
                    self.body.set_velocity(v2(0.0, 0.0))
                    self.body.disable()
                    break

        for contact_body in self.body.get_contacts():
            other = contact_body.userData
            if other and other.has_tag("bomb"):
                self.boom_sound.play()
                scene = self.scene
                if hasattr(scene, 'spawn_blood_particles'):
                    scene.spawn_blood_particles(self.body.get_position_pixels())
                self.body.set_position(self.p.position)
                self.body.set_velocity(v2(0.0, 0.0))
                break

        position = self.body.get_position_pixels()
        level_width = self.level.get_size().x
        
        if position.x <= 0.0:
            velocity = self.body.get_velocity_pixels()
            self.body.set_position(v2(level_width, position.y))
            self.body.set_velocity(velocity)
        elif position.x >= level_width:
            velocity = self.body.get_velocity_pixels()
            self.body.set_position(v2(0.0, position.y))
            self.body.set_velocity(velocity)
        
        if position.y > self.level.get_size().y + 200.0:
            self.body.set_position(self.p.position)
            self.body.set_velocity(v2(0.0, 0.0))
            self.die_sound.play()

    def draw(self) -> None:
        """Draw attack indicator (animations are drawn by controller).

        Returns:
            None
        """
        if self.attack:
            position = self.body.get_position_pixels()
            position.x += (self.width / 2.0 + 8.0) * (-1.0 if self.animation.flip_x else 1.0)
            rl.draw_circle_v(position, 8.0, rl.Color(230, 41, 55, 128))

    def pre_solve(self, body_a, body_b, contact, platforms: List[StaticBox]) -> bool:
        """Custom pre-solve for one-way platforms.

        Args:
            body_a: First body in the contact.
            body_b: Second body in the contact.
            contact: Box2D contact instance.
            platforms: List of one-way platform StaticBox objects.

        Returns:
            True to enable contact, False to disable it.
        """
        normal = contact.worldManifold.normal
        other = None
        sign = 0.0
        if body_a == self.body.body:
            sign = 1.0
            other = body_b
        elif body_b == self.body.body:
            sign = -1.0
            other = body_a
        if sign * normal.y < 0.5:
            return False
        if self.fall_through:
            for platform in platforms:
                if other == platform.body:
                    return False
        return True


class Goal(GameObject):
    """Goal/finish line that players can reach to win."""
    def __init__(self, position: rl.Vector2, size: rl.Vector2) -> None:
        """Create a goal trigger area.

        Args:
            position: Center position in pixels.
            size: Width and height in pixels.

        Returns:
            None
        """
        super().__init__()
        self.position = position
        self.size = size
        self.physics: PhysicsService = None  # type: ignore[assignment]
        self.body: BodyComponent = None  # type: ignore[assignment]
        self.sprite: SpriteComponent = None  # type: ignore[assignment]

    def init(self) -> None:
        """Initialize goal body as a sensor and add door sprite.

        Returns:
            None
        """
        self.physics = self.scene.get_service(PhysicsService)

        def build_body(component: BodyComponent):
            """Build body.

            Args:
                component: Parameter.

            Returns:
                Result of the operation.
            """
            world = self.physics.world
            body = world.CreateStaticBody(position=(self.physics.convert_to_meters(self.position).x,
                                                    self.physics.convert_to_meters(self.position).y))
            body.userData = self
            shape = b2PolygonShape(box=(self.physics.convert_length_to_meters(self.size.x / 2.0),
                                        self.physics.convert_length_to_meters(self.size.y / 2.0)))
            fixture = body.CreateFixture(shape=shape, density=0.0)
            fixture.sensor = True
            component.body = body

        self.body = self.add_component(BodyComponent(build=build_body))
        self.sprite = self.add_component(SpriteComponent("assets/ngamerunnerdoor.png", self.body))
        self.sprite.scale = 2.0


class Bomb(GameObject):
    """Explosive bomb that makes players respawn when touched."""
    def __init__(self, position: rl.Vector2, size: rl.Vector2) -> None:
        """Create a bomb trigger area.

        Args:
            position: Center position in pixels.
            size: Width and height in pixels.

        Returns:
            None
        """
        super().__init__()
        self.position = position
        self.size = size
        self.physics: PhysicsService = None  # type: ignore[assignment]
        self.body: BodyComponent = None  # type: ignore[assignment]
        self.sprite: SpriteComponent = None  # type: ignore[assignment]

    def init(self) -> None:
        """Initialize bomb body as a sensor and add explosive sprite.

        Returns:
            None
        """
        self.physics = self.scene.get_service(PhysicsService)

        def build_body(component: BodyComponent):
            """Build body.

            Args:
                component: Parameter.

            Returns:
                Result of the operation.
            """
            world = self.physics.world
            body = world.CreateStaticBody(position=(self.physics.convert_to_meters(self.position).x,
                                                    self.physics.convert_to_meters(self.position).y))
            body.userData = self
            shape = b2PolygonShape(box=(self.physics.convert_length_to_meters(self.size.x / 2.0),
                                        self.physics.convert_length_to_meters(self.size.y / 2.0)))
            fixture = body.CreateFixture(shape=shape, density=0.0)
            fixture.sensor = True
            component.body = body

        self.body = self.add_component(BodyComponent(build=build_body))
        self.sprite = self.add_component(SpriteComponent("assets/ngamerunnerexplosive.png", self.body))
        self.sprite.scale = 0.5


class NContactListener(b2ContactListener):
    """Routes Box2D PreSolve callbacks to the owning character."""
    def __init__(self, scene: "NScene3") -> None:
        """Capture the scene so contacts can be filtered.

        Args:
            scene: Scene containing fighters and one-way platforms.

        Returns:
            None
        """
        super().__init__()
        self.scene = scene

    def PreSolve(self, contact, old_manifold):
        """Dispatch pre-solve handling to the matching character.

        Args:
            contact: Box2D contact.
            old_manifold: Previous contact manifold.

        Returns:
            None
        """
        body_a = contact.fixtureA.body
        body_b = contact.fixtureB.body
        for character in self.scene.characters:
            if body_a == character.body.body or body_b == character.body.body:
                contact.enabled = True
                return


class NScene3(Scene):
    """Platformer scene with fighting characters and simple rendering."""
    def __init__(self) -> None:
        """Initialize scene storage for services, actors, and render targets.

        Returns:
            None
        """
        super().__init__()
        self.platforms: List[StaticBox] = []
        self.characters: List[NCharacter] = []
        self.bombs: List[Bomb] = []
        self.level: LevelService = None  # type: ignore[assignment]
        self.physics: PhysicsService = None  # type: ignore[assignment]
        self.renderer: rl.RenderTexture = None  # type: ignore[assignment]
        self.font_manager: FontManager = None  # type: ignore[assignment]
        self.winners: List[int] = []
        self.winner_times: Dict[int, float] = {}
        self.winner_display_duration = 3.0
        self.goal: Goal = None  # type: ignore[assignment]
        self.time_limit = 120.0
        self.elapsed_time = 0.0
        self.player_completion_times: Dict[int, float] = {}
        self.clock_sound = None  # type: ignore[assignment]
        self.clock_playing = False
        self.background_music = None  # type: ignore[assignment]
        self.music_playing = False
        self.blood_particles: List[BloodParticle] = []

    def init_services(self) -> None:
        """Register services required by the scene.

        Returns:
            None
        """
        self.add_service(TextureService)
        self.add_service(SoundService)
        self.physics = self.add_service(PhysicsService)
        collision_names = ["walls"]
        self.level = self.add_service(LevelService, "assets/levels/ngamerunnerlevel3.ldtk", "Stamps", collision_names)
        self.font_manager = self.game.get_manager(FontManager)

    def init(self) -> None:
        """Create platforms, players, and render target.

        Returns:
            None
        """
        self.platforms = []
        self.characters = []
        self.bombs = []
        self.winners = []
        self.winner_times = {}
        self.elapsed_time = 0.0
        self.player_completion_times = {}
        self.clock_playing = False
        self.music_playing = False
        self.blood_particles = []
        
        platform_entities = self.level.get_entities_by_name("One_way_platform")
        for platform_entity in platform_entities:
            position = self.level.convert_to_pixels(platform_entity.getPosition())
            size = self.level.convert_to_pixels(platform_entity.getSize())
            platform = self.add_game_object(StaticBox.from_vectors(vec_add(position, vec_div(size, 2.0)), size))
            platform.is_visible = False
            platform.add_tag("platform")
            self.platforms.append(platform)

        if self.physics.world:
            self.physics.world.contactListener = NContactListener(self)

        player_entities = self.level.get_entities_by_name("Start")
        for i, player_entity in enumerate(player_entities[:4]):
            params = CharacterParams()
            params.position = self.level.convert_to_pixels(player_entity.getPosition())
            params.width = 16
            params.height = 24
            character = self.add_game_object(NCharacter(params, i + 1))
            character.add_tag("character")
            self.characters.append(character)

        goal_entities = self.level.get_entities_by_name("Goal")
        if goal_entities:
            goal_entity = goal_entities[0]
            position = self.level.convert_to_pixels(goal_entity.getPosition())
            size = self.level.convert_to_pixels(goal_entity.getSize())
            self.goal = self.add_game_object(Goal(vec_add(position, vec_div(size, 2.0)), size))
            self.goal.add_tag("goal")

        bomb_entities = self.level.get_entities_by_name("Bomb")
        for bomb_entity in bomb_entities:
            position = self.level.convert_to_pixels(bomb_entity.getPosition())
            size = self.level.convert_to_pixels(bomb_entity.getSize())
            bomb = self.add_game_object(Bomb(vec_add(position, vec_div(size, 2.0)), size))
            bomb.add_tag("bomb")
            self.bombs.append(bomb)

        self.level.set_layer_visibility("Background", False)
        self.renderer = rl.load_render_texture(int(self.level.get_size().x), int(self.level.get_size().y))
        
        sound_service = self.get_service(SoundService)
        self.clock_sound = sound_service.get_sound("assets/sounds/tick.mp3")
        self.background_music = sound_service.get_sound("assets/sounds/level3.mp3")
        rl.play_sound(self.background_music)
        self.music_playing = True

    def add_winner(self, player_number: int) -> None:
        """Add a player to the winners list.

        Args:
            player_number: Player number that reached the goal.

        Returns:
            None
        """
        if player_number not in self.winners:
            self.winners.append(player_number)
            self.winner_times[player_number] = 0.0
            self.player_completion_times[player_number] = self.elapsed_time
            if not hasattr(self.game, 'player_times_level3'):
                self.game.player_times_level3 = {}
            self.game.player_times_level3[player_number] = self.elapsed_time
    
    def spawn_blood_particles(self, position: rl.Vector2) -> None:
        for _ in range(15):
            self.blood_particles.append(BloodParticle(position))

    def update(self, delta_time: float) -> None:
        """Update logic and scene transitions.

        Args:
            delta_time: Seconds since last frame.

        Returns:
            None
        """
        self.elapsed_time += delta_time
        
        self.blood_particles = [p for p in self.blood_particles if p.update(delta_time)]
        
        remaining_time = self.time_limit - self.elapsed_time
        
        if remaining_time <= 20.0 and remaining_time > 0.0:
            if self.music_playing:
                rl.stop_sound(self.background_music)
                self.music_playing = False
            if not self.clock_playing:
                rl.play_sound(self.clock_sound)
                self.clock_playing = True
            elif not rl.is_sound_playing(self.clock_sound):
                rl.play_sound(self.clock_sound)
        else:
            if self.music_playing and not rl.is_sound_playing(self.background_music):
                rl.play_sound(self.background_music)
            if self.clock_playing:
                rl.stop_sound(self.clock_sound)
                self.clock_playing = False
        
        for player_num in list(self.winner_times.keys()):
            self.winner_times[player_num] += delta_time
            if self.winner_times[player_num] > self.winner_display_duration:
                del self.winner_times[player_num]
        
        all_finished = len(self.player_completion_times) == len(self.characters)
        if all_finished and len(self.characters) > 0:
            if all(time > self.winner_display_duration for time in self.winner_times.values()) or not self.winner_times:
                if self.clock_playing:
                    rl.stop_sound(self.clock_sound)
                    self.clock_playing = False
                if self.music_playing:
                    rl.stop_sound(self.background_music)
                    self.music_playing = False
                self.game.go_to_scene_next()
                return
        
        if self.elapsed_time >= self.time_limit:
            if self.clock_playing:
                rl.stop_sound(self.clock_sound)
                self.clock_playing = False
            if self.music_playing:
                rl.stop_sound(self.background_music)
                self.music_playing = False
            if not hasattr(self.game, 'player_times_level3'):
                self.game.player_times_level3 = {}
            for i, char in enumerate(self.characters):
                player_num = i + 1
                if player_num not in self.player_completion_times:
                    self.game.player_times_level3[player_num] = -1.0
            self.game.go_to_scene_next()
        
        if rl.is_key_pressed(rl.KEY_ENTER) or rl.is_gamepad_button_pressed(0, rl.GAMEPAD_BUTTON_MIDDLE_RIGHT):
            if self.clock_playing:
                rl.stop_sound(self.clock_sound)
                self.clock_playing = False
            if self.music_playing:
                rl.stop_sound(self.background_music)
                self.music_playing = False
            self.game.go_to_scene_next()

    def draw_scene(self) -> None:
        """Render the world to a texture and draw it fullscreen.

        Returns:
            None
        """
        rl.begin_texture_mode(self.renderer)
        rl.clear_background(rl.MAGENTA)
        self.level.draw_layer("Background")
        super().draw_scene()
        for particle in self.blood_particles:
            particle.draw()
        rl.end_texture_mode()

        rl.draw_texture_pro(self.renderer.texture,
                       rl.Rectangle(0.0, 0.0, float(self.renderer.texture.width), -float(self.renderer.texture.height)),
                       rl.Rectangle(0.0, 0.0, float(rl.get_screen_width()), float(rl.get_screen_height())),
                       v2(0.0, 0.0),
                       0.0,
                       rl.Color(255, 255, 255, 255))

        if self.winner_times:
            player_colors = [
                rl.Color(230, 41, 55, 255),
                rl.Color(0, 121, 241, 255),
                rl.Color(253, 249, 0, 255),
                rl.Color(0, 228, 48, 255)
            ]
            
            font = self.font_manager.get_font("Tiny5")
            text_size = 96
            y_offset = 50.0
            
            for player_num in self.winner_times.keys():
                color = player_colors[player_num - 1] if player_num - 1 < len(player_colors) else rl.WHITE
                text = f"Player {player_num} Won!"
                
                measured = rl.measure_text_ex(font, text, text_size, 2)
                text_x = float(rl.get_screen_width()) / 2.0 - measured.x / 2.0
                
                outline_offset = 3
                for dx, dy in [(0, outline_offset), (outline_offset, 0), (0, -outline_offset), (-outline_offset, 0),
                               (outline_offset, outline_offset), (-outline_offset, -outline_offset), 
                               (outline_offset, -outline_offset), (-outline_offset, outline_offset)]:
                    rl.draw_text_ex(font, text, v2(text_x + dx, y_offset + dy), text_size, 2, rl.BLACK)
                
                rl.draw_text_ex(font, text, v2(text_x, y_offset), text_size, 2, color)
                y_offset += 110.0
        
        remaining_time = max(0.0, self.time_limit - self.elapsed_time)
        minutes = int(remaining_time // 60)
        seconds = int(remaining_time % 60)
        timer_text = f"Time: {minutes}:{seconds:02d}"
        
        timer_font = self.font_manager.get_font("Tiny5")
        timer_size = 64
        timer_measured = rl.measure_text_ex(timer_font, timer_text, timer_size, 2)
        timer_x = float(rl.get_screen_width()) / 2.0 - timer_measured.x / 2.0
        timer_y = 20.0
        
        timer_color = rl.RED if remaining_time < 20.0 else rl.WHITE
        for dx, dy in [(0, 2), (2, 0), (0, -2), (-2, 0)]:
            rl.draw_text_ex(timer_font, timer_text, v2(timer_x + dx, timer_y + dy), timer_size, 2, rl.BLACK)
        rl.draw_text_ex(timer_font, timer_text, v2(timer_x, timer_y), timer_size, 2, timer_color)
