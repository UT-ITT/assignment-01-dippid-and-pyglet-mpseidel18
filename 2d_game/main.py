import pyglet
from pyglet.window import key
import random
import os
import numpy as np
from DIPPID import SensorUDP


WINDOW_WIDTH = 900
WINDOW_HEIGHT = 600
PLAYER_SIZE = 40
PLAYER_SPEED = 300  # pixels per second
PLAYER_SPRITE_SCALE_FACTOR = 4.0 # the sprite was very small
PROJECTILE_SPRITE_SCALE_FACTOR = 2.0 # the sprite was very small
PROJECTILE_SPEED = 260
PROJECTILE_SPAWN_INTERVAL = 0.8
BUFFER_SIZE = 500
PORT = 5700
GYRO_SCALE = 10.0
GYRO_DEADZONE = 0.08 # makes it easier to control by ignoring small gyro values around 0
REST_TILT_X = 7.3 # default resting position of the device when held in hand, used for calibrating gyro input to make controls more intuitive
REST_TILT_Z = 6.4 # default resting position of the device when held in hand, used for calibrating gyro input to make controls more intuitive

class DodgeGameWindow(pyglet.window.Window):
    def __init__(self):
        super().__init__(WINDOW_WIDTH, WINDOW_HEIGHT, caption="Gyro Dodge - Starter")
        self.set_minimum_size(640, 480)
        self.state = "start"
        self.player_x = WINDOW_WIDTH // 2
        self.player_y = WINDOW_HEIGHT // 2

        self.projectiles = []
        self.projectile_spawn_timer = 0.0
        self.score_seconds = 0.0
        self.is_game_over = False

        # DIPPID initialization and state
        self.buffer_size = BUFFER_SIZE

        self.x_data = np.zeros(self.buffer_size)
        self.y_data = np.zeros(self.buffer_size)
        self.z_data = np.zeros(self.buffer_size)

        self.sensor = SensorUDP(PORT)
        self.sensor_connected = True

        pyglet.clock.schedule_interval(self.update, 1 / 120)

        # png support via resource loader
        assets_dir = os.path.join(os.path.dirname(__file__), "assets")
        pyglet.resource.path = [assets_dir]
        pyglet.resource.reindex()
        self.player_image = pyglet.resource.image("player_sprite.png")
        self.projectile_image = pyglet.resource.image("meteor.png")
        self.background_image = pyglet.resource.image("background.png")

        self.player_image.anchor_x = self.player_image.width // 2
        self.player_image.anchor_y = self.player_image.height // 2
        self.projectile_image.anchor_x = self.projectile_image.width // 2
        self.projectile_image.anchor_y = self.projectile_image.height // 2

        self.bg_image = self.background_image
        self.bg_sprite = pyglet.sprite.Sprite(self.bg_image, x=0, y=0)
        self.player_sprite = pyglet.sprite.Sprite(self.player_image, x=self.player_x, y=self.player_y)

    def shutdown_sensor(self):
        if not self.sensor_connected:
            return
        try:
            self.sensor.disconnect()
        except ValueError:
            pass
        self.sensor_connected = False

    def on_close(self):
        self.shutdown_sensor()
        pyglet.clock.unschedule(self.update)
        super().on_close()

    def on_draw(self):
        self.clear()

        if self.state == "start":
            self.draw_start_frame()
        else:
            self.draw_game()

    def draw_start_frame(self):
        title = pyglet.text.Label(
            "[Exercise 2] Gyro Dodge",
            font_name="Arial",
            font_size=48,
            x=self.width // 2,
            y=self.height // 2 + 80,
            anchor_x="center",
            anchor_y="center",
            color=(255, 255, 255, 255),
        )

        subtitle = pyglet.text.Label(
            "Press ENTER to start",
            font_name="Arial",
            font_size=22,
            x=self.width // 2,
            y=self.height // 2,
            anchor_x="center",
            anchor_y="center",
            color=(200, 200, 200, 255),
        )

        controls = pyglet.text.Label(
            "Tilt phone to move",
            font_name="Arial",
            font_size=18,
            x=self.width // 2,
            y=self.height // 2 - 50,
            anchor_x="center",
            anchor_y="center",
            color=(160, 220, 255, 255),
        )

            # checking for gravity data
        gravity_checklabel = pyglet.text.Label(
            "Make sure your device is sending gravity data to DIPPID on port 5700",
            font_name="Arial",
            font_size=14,
            x=self.width // 2,
            y=self.height // 2 - 80,
            anchor_x="center",
            anchor_y="center",
            color=(160, 220, 255, 255),
        )

        # helpful label for debugging to show current gravity data on the start screen
        gravity_data = self.sensor.get_value("gravity")
        # checking if gravity data is available and has the expected keys before trying to display it
        if gravity_data and all(k in gravity_data for k in ("x", "y", "z")):
            gravity_text = (
                f"Current gravity data: "
                f"x={float(gravity_data['x']):.2f}, "
                f"y={float(gravity_data['y']):.2f}, "
                f"z={float(gravity_data['z']):.2f}"
            )
        else:
            gravity_text = "Current gravity data: waiting for data..."

        gravity_data_label = pyglet.text.Label(
            gravity_text,
            font_name="Arial",
            font_size=14,
            x=self.width // 2,
            y=self.height // 2 - 110,
            anchor_x="center",
            anchor_y="center",
            color=(200, 200, 200, 255),
        )

        title.draw()
        subtitle.draw()
        controls.draw()
        gravity_checklabel.draw()
        gravity_data_label.draw()

    def draw_game(self):
        # draw background first
        self.bg_sprite.scale_x = self.width / self.bg_image.width
        self.bg_sprite.scale_y = self.height / self.bg_image.height
        self.bg_sprite.draw()

        self.draw_projectiles()

        self.player_sprite.x = self.player_x
        self.player_sprite.y = self.player_y
        player_base = min(self.player_image.width, self.player_image.height)
        self.player_sprite.scale = (PLAYER_SIZE * PLAYER_SPRITE_SCALE_FACTOR) / player_base # scale the sprite 
        self.player_sprite.draw()

        hud = pyglet.text.Label(
            f"Tilt phone to move | ESC to return to start | Survival: {self.score_seconds:0.1f}s",
            font_name="Arial",
            font_size=14,
            x=15,
            y=self.height - 25,
            anchor_x="left",
            anchor_y="center",
            color=(230, 230, 230, 255),
        )
        hud.draw()

        if self.is_game_over:
            game_over_label = pyglet.text.Label(
                "GAME OVER (placeholder) - Press R to restart",
                font_name="Arial",
                font_size=20,
                x=self.width // 2,
                y=self.height // 2,
                anchor_x="center",
                anchor_y="center",
                color=(255, 120, 120, 255),
            )
            game_over_label.draw()

    def on_key_press(self, symbol, modifiers):
        if self.state == "start":
            if symbol == key.ENTER:
                self.state = "playing"
            return

        if symbol == key.ESCAPE:
            self.state = "start"
            return

        if symbol == key.R and self.is_game_over:
            self.reset_round()
            return

    def on_key_release(self, symbol, modifiers):
        return

    def update(self, dt):
        if self.state != "playing":
            return

        if self.is_game_over:
            return

        self.score_seconds += dt

        self.update_player_movement(dt)
        self.update_projectiles(dt)

        if self.check_collisions():
            self.is_game_over = True

    def update_player_movement(self, dt):
        gyro_x, gyro_y, gyro_z = self.read_gravity_input()

        # tilt forward (negative x, away from user) should move up, tilt right (positive y) should move right
        # vice versa for tilting the other way, and tilting back (positive x) should move down

        move_x = 0.0
        move_y = 0.0

        # using x and z for tilt
        pitch_tilt = (gyro_x - gyro_z) * 0.5

        move_x += pitch_tilt
        move_y += gyro_y

        # linear speed scaling: stronger tilt means faster movement
        tilt_strength = (move_x * move_x + move_y * move_y) ** 0.5
        speed_factor = min(1.5, tilt_strength)
        if tilt_strength > 0.0:
            move_x /= tilt_strength
            move_y /= tilt_strength

        self.player_x += move_y * PLAYER_SPEED * speed_factor * dt # swap x/y from gyro to match expected movement directions
        self.player_y += -(move_x * PLAYER_SPEED * speed_factor * dt) # invert x from gyro so tilting right (positive y) moves right, and tilting forward (negative x) moves up

        half = PLAYER_SIZE // 2
        self.player_x = max(half, min(self.width - half, self.player_x))
        self.player_y = max(half, min(self.height - half, self.player_y))

    def read_gravity_input(self):
        if not self.sensor.has_capability("gravity"):
            return 0.0, 0.0, 0.0

        data = self.sensor.get_value("gravity")
        if not data:
            return 0.0, 0.0, 0.0

        try:
            raw_x = float(data["x"])
            raw_y = float(data["y"])
            raw_z = float(data["z"])
            print(f"Raw gravity data: x={raw_x:.2f}, y={raw_y:.2f}, z={raw_z:.2f}")
        except (KeyError, TypeError, ValueError):
            print("Invalid gravity data received:", data)
            return 0.0, 0.0, 0.0

        centered_x = raw_x - REST_TILT_X
        centered_z = raw_z - REST_TILT_Z

        self.x_data = np.roll(self.x_data, -1)
        self.y_data = np.roll(self.y_data, -1)
        self.z_data = np.roll(self.z_data, -1)

        # new data
        self.x_data[-1] = centered_x
        self.y_data[-1] = raw_y
        self.z_data[-1] = centered_z

        # normalize
        tilt_x = self.x_data[-1] / GYRO_SCALE
        tilt_y = self.y_data[-1] / GYRO_SCALE
        tilt_z = self.z_data[-1] / GYRO_SCALE

        # Apply deadzone
        if abs(tilt_x) < GYRO_DEADZONE:
            tilt_x = 0.0
        if abs(tilt_y) < GYRO_DEADZONE:
            tilt_y = 0.0
        if abs(tilt_z) < GYRO_DEADZONE:
            tilt_z = 0.0

        return tilt_x, tilt_y, tilt_z

    def update_projectiles(self, dt):
        # update existing projectiles
        self.projectile_spawn_timer -= dt

        while self.projectile_spawn_timer <= 0:
            self.spawn_projectile()
            self.projectile_spawn_timer += PROJECTILE_SPAWN_INTERVAL

        for _projectile in self.projectiles:
            _projectile["x"] += _projectile["vx"] * dt
            _projectile["y"] += _projectile["vy"] * dt

        margin = 80
        self.projectiles = [
            _projectile
            for _projectile in self.projectiles
            if -margin <= _projectile["x"] <= self.width + margin
            and -margin <= _projectile["y"] <= self.height + margin
        ]

    def spawn_projectile(self):
        # spawn at random position outside of the screen and aim towards the player with some random offset
        radius = random.randint(10, 18)
        side = random.choice(("left", "right", "top", "bottom"))

        if side == "left":
            start_x = -radius
            start_y = random.uniform(0, self.height)
        elif side == "right":
            start_x = self.width + radius
            start_y = random.uniform(0, self.height)
        elif side == "top":
            start_x = random.uniform(0, self.width)
            start_y = self.height + radius
        else:
            start_x = random.uniform(0, self.width)
            start_y = -radius

        # aim at the current player position with a small random offset.
        target_x = self.player_x + random.uniform(-100, 100)
        target_y = self.player_y + random.uniform(-100, 100)

        dir_x = target_x - start_x
        dir_y = target_y - start_y
        length = (dir_x * dir_x + dir_y * dir_y) ** 0.5 or 1.0

        self.projectiles.append(
            {
                "x": start_x,
                "y": start_y,
                "vx": (dir_x / length) * PROJECTILE_SPEED,
                "vy": (dir_y / length) * PROJECTILE_SPEED,
                "radius": radius,
            }
        )

    def draw_projectiles(self):
        # display projectiles as scaled sprites based on their radius
        for _projectile in self.projectiles:
            projectile_sprite = pyglet.sprite.Sprite(
                self.projectile_image,
                x=_projectile["x"],
                y=_projectile["y"],
            )
            diameter = _projectile["radius"] * 2
            projectile_base = min(self.projectile_image.width, self.projectile_image.height)
            projectile_sprite.scale = (diameter * PROJECTILE_SPRITE_SCALE_FACTOR) / projectile_base
            projectile_sprite.draw()

    def check_collisions(self):
        # check for collision
        left = self.player_x - PLAYER_SIZE // 2
        right = self.player_x + PLAYER_SIZE // 2
        top = self.player_y + PLAYER_SIZE // 2
        bottom = self.player_y - PLAYER_SIZE // 2

        for _projectile in self.projectiles:
            proj_x = _projectile["x"]
            proj_y = _projectile["y"]
            radius = _projectile["radius"]

            closest_x = max(left, min(proj_x, right))
            closest_y = max(bottom, min(proj_y, top))

            dx = proj_x - closest_x
            dy = proj_y - closest_y

            # collision occurs if the distance from the projectile to the closest point
            if dx * dx + dy * dy <= radius * radius:
                return True

    def reset_round(self):
        # reset player position and clear projectiles for a new round
        self.player_x = self.width // 2
        self.player_y = self.height // 2
        self.projectiles.clear()
        self.projectile_spawn_timer = 0.0
        self.score_seconds = 0.0
        self.is_game_over = False


if __name__ == "__main__":
    window = DodgeGameWindow()
    try:
        pyglet.app.run() # Starting the game
    finally:
        window.shutdown_sensor() # Disconnect sensor when game window is closed
