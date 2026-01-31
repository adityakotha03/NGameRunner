from __future__ import annotations

import math
from typing import List

from Box2D import b2ContactListener, b2PolygonShape, b2Vec2
import pyray as rl

from engine.framework import GameObject, Scene
from engine.math_extensions import vec_add, vec_div, vec_mul, vec_sub, v2
from engine.prefabs.components import (AnimationController, BodyComponent, MultiComponent, SoundComponent,
                                       PlatformerMovementComponent, PlatformerMovementParams)
from engine.prefabs.game_objects import CharacterParams, StaticBox
from engine.prefabs.managers import FontManager
from engine.prefabs.services import LevelService, PhysicsService, SoundService, TextureService


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
        self.hit_sound = self.sounds.add_component("hit", SoundComponent, "assets/sounds/hit.wav")
        self.die_sound = self.sounds.add_component("die", SoundComponent, "assets/sounds/die.wav")

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
                self.hit_sound.play()

        if self.attack_display_timer > 0.0:
            self.attack_display_timer = max(0.0, self.attack_display_timer - delta_time)
            if self.attack_display_timer == 0.0:
                self.attack = False

        if self.body.get_position_pixels().y > self.level.get_size().y + 200.0:
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


class NContactListener(b2ContactListener):
    """Routes Box2D PreSolve callbacks to the owning character."""
    def __init__(self, scene: "NScene") -> None:
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
                # enabled = character.pre_solve(body_a, body_b, contact, self.scene.platforms)
                contact.enabled = True
                return


class NScene(Scene):
    """Platformer scene with fighting characters and simple rendering."""
    def __init__(self) -> None:
        """Initialize scene storage for services, actors, and render targets.

        Returns:
            None
        """
        super().__init__()
        self.platforms: List[StaticBox] = []
        self.characters: List[NCharacter] = []
        self.level: LevelService = None  # type: ignore[assignment]
        self.physics: PhysicsService = None  # type: ignore[assignment]
        self.renderer: rl.RenderTexture = None  # type: ignore[assignment]

    def init_services(self) -> None:
        """Register services required by the scene.

        Returns:
            None
        """
        self.add_service(TextureService)
        self.add_service(SoundService)
        self.physics = self.add_service(PhysicsService)
        collision_names = ["walls"]
        self.level = self.add_service(LevelService, "assets/levels/fighting.ldtk", "Stage", collision_names)

    def init(self) -> None:
        """Create platforms, players, and render target.

        Returns:
            None
        """
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

        self.level.set_layer_visibility("Background", False)
        self.renderer = rl.load_render_texture(int(self.level.get_size().x), int(self.level.get_size().y))

    def update(self, delta_time: float) -> None:
        """Update logic and scene transitions.

        Args:
            delta_time: Seconds since last frame.

        Returns:
            None
        """
        # Trigger scene change on Enter key or gamepad start button
        if rl.is_key_pressed(rl.KEY_ENTER) or rl.is_gamepad_button_pressed(0, rl.GAMEPAD_BUTTON_MIDDLE_RIGHT):
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
        rl.end_texture_mode()

        rl.draw_texture_pro(self.renderer.texture,
                       rl.Rectangle(0.0, 0.0, float(self.renderer.texture.width), -float(self.renderer.texture.height)),
                       rl.Rectangle(0.0, 0.0, float(rl.get_screen_width()), float(rl.get_screen_height())),
                       v2(0.0, 0.0),
                       0.0,
                       rl.Color(255, 255, 255, 255))