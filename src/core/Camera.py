# camera.py
import pyrr
import numpy as np
import math

class Camera:
    def __init__(self, position, target):
        # Orbit-style camera (targeted)
        self.position = np.array(position, dtype=np.float32)
        self.target = np.array(target, dtype=np.float32)

        # World-up is constant
        self.world_up = np.array([0, 1, 0], dtype=np.float32)

        # Spherical coordinates around the target
        dir_vec = self.position - self.target
        # normalize direction to derive yaw/pitch, but set a fixed default distance
        norm = np.linalg.norm(dir_vec)
        if norm > 0.0:
            dir_norm = dir_vec / norm
        else:
            dir_norm = np.array([0.0, 0.0, 1.0], dtype=np.float32)
        # derive yaw/pitch from normalized direction vector
        nx, ny, nz = dir_norm
        # default distance (units): set to 32 as requested
        self.distance = 32.0
        # yaw: azimuth around Y, pitch: elevation
        # Use fixed defaults so the camera doesn't start looking straight down
        self.yaw = 0.0
        self.pitch = 0.0

        # sensitivities and limits
        self.orbit_sensitivity = 0.2
        self.zoom_sensitivity = 1.0
        self.pan_sensitivity = 0.002
        self.min_distance = 1.0
        self.max_distance = 128.0

        # keyboard movement speed (used for panning with WASD/space/ctrl)
        self.speed = 5.0

        # computed vectors
        self.front = np.array([0, 0, -1], dtype=np.float32)
        self.up = np.array([0, 1, 0], dtype=np.float32)
        self.right = np.array([1, 0, 0], dtype=np.float32)

        # initialize camera position from spherical coords
        self.update_position_from_spherical()

    def get_view_matrix(self):
        return pyrr.matrix44.create_look_at(self.position, self.target, self.up)

    def update_vectors(self):
        # Recompute front/right/up based on current position and target
        self.front = self.target - self.position
        norm = np.linalg.norm(self.front)
        if norm != 0:
            self.front = self.front / norm
        else:
            self.front = np.array([0, 0, -1], dtype=np.float32)

        self.right = np.cross(self.front, self.world_up)
        rnorm = np.linalg.norm(self.right)
        if rnorm != 0:
            self.right = self.right / rnorm
        else:
            self.right = np.array([1, 0, 0], dtype=np.float32)

        self.up = np.cross(self.right, self.front)
        unorm = np.linalg.norm(self.up)
        if unorm != 0:
            self.up = self.up / unorm
        else:
            self.up = self.world_up

    def update_position_from_spherical(self):
        # Convert spherical coordinates (yaw, pitch, distance) to Cartesian position
        yaw_r = math.radians(self.yaw)
        pitch_r = math.radians(self.pitch)
        x = math.cos(yaw_r) * math.cos(pitch_r)
        y = math.sin(pitch_r)
        z = math.sin(yaw_r) * math.cos(pitch_r)
        dir_vec = np.array([x, y, z], dtype=np.float32)
        self.position = self.target + dir_vec * self.distance
        self.update_vectors()

    def process_keyboard(self, direction, delta_time, is_sprinting=False):
        """
        Procesa el movimiento de la cámara.
        Acepta un booleano 'is_sprinting' para triplicar la velocidad.
        """
        sprint_multiplier = 5.0 if is_sprinting else 1.0
        velocity = self.speed * sprint_multiplier * delta_time
        
        # keep keyboard movement but move both target and position (pan in world)
        move = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        if direction == "FORWARD":
            move += self.front * velocity
        if direction == "BACKWARD":
            move -= self.front * velocity
        if direction == "LEFT":
            move -= self.right * velocity
        if direction == "RIGHT":
            move += self.right * velocity
        if direction == "UP":
            move += self.world_up * velocity
        if direction == "DOWN":
            move -= self.world_up * velocity

        self.position += move
        self.target += move
        self.update_vectors()

    def process_mouse_movement(self, x_offset, y_offset, constrain_pitch=True):
        # legacy raw movement: orbit
        self.orbit(x_offset, y_offset)

    # --- New orbit-style controls ---
    def orbit(self, x_offset, y_offset):
        self.yaw += x_offset * self.orbit_sensitivity
        self.pitch += y_offset * self.orbit_sensitivity
        if self.pitch > 89.0: self.pitch = 89.0
        if self.pitch < -89.0: self.pitch = -89.0
        self.update_position_from_spherical()

    def zoom(self, scroll_amount):
        # scroll_amount is typically positive when scrolling up, negative when down
        # use exponential zoom for smoothness
        factor = math.pow(0.9, scroll_amount * self.zoom_sensitivity)
        self.distance *= factor
        self.distance = max(self.min_distance, min(self.max_distance, self.distance))
        self.update_position_from_spherical()

    def pan(self, x_offset, y_offset):
        # Move target and position sideways/up based on cursor deltas
        right_move = -x_offset * self.pan_sensitivity * self.distance
        up_move = y_offset * self.pan_sensitivity * self.distance
        move = self.right * right_move + self.up * up_move
        self.target += move
        self.position += move
        self.update_vectors()