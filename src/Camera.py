# camera.py
import pyrr
import numpy as np
import math

class Camera:
    def __init__(self, position, target):
        self.position = np.array(position, dtype=np.float32)
        self.front = np.array([0, 0, -1], dtype=np.float32)
        self.up = np.array([0, 1, 0], dtype=np.float32)
        self.right = np.array([1, 0, 0], dtype=np.float32)
        self.yaw = -90.0
        self.pitch = 0.0
        self.speed = 5.0
        self.sensitivity = 0.1
        self.update_vectors()

    def get_view_matrix(self):
        return pyrr.matrix44.create_look_at(self.position, self.position + self.front, self.up)

    def update_vectors(self):
        front_x = math.cos(math.radians(self.yaw)) * math.cos(math.radians(self.pitch))
        front_y = math.sin(math.radians(self.pitch))
        front_z = math.sin(math.radians(self.yaw)) * math.cos(math.radians(self.pitch))
        self.front = np.array([front_x, front_y, front_z], dtype=np.float32)
        self.front /= np.linalg.norm(self.front)
        self.right = np.cross(self.front, np.array([0, 1, 0], dtype=np.float32))
        self.right /= np.linalg.norm(self.right)
        self.up = np.cross(self.right, self.front)
        self.up /= np.linalg.norm(self.up)

    def process_keyboard(self, direction, delta_time, is_sprinting=False):
        """
        Procesa el movimiento de la cámara.
        Acepta un booleano 'is_sprinting' para triplicar la velocidad.
        """
        sprint_multiplier = 5.0 if is_sprinting else 1.0
        velocity = self.speed * sprint_multiplier * delta_time
        
        if direction == "FORWARD":
            self.position += self.front * velocity
        if direction == "BACKWARD":
            self.position -= self.front * velocity
        if direction == "LEFT":
            self.position -= self.right * velocity
        if direction == "RIGHT":
            self.position += self.right * velocity
        if direction == "UP":
            self.position[1] += velocity # Movimiento vertical simple
        if direction == "DOWN":
            self.position[1] -= velocity # Movimiento vertical simple

    def process_mouse_movement(self, x_offset, y_offset, constrain_pitch=True):
        x_offset *= self.sensitivity
        y_offset *= self.sensitivity
        self.yaw += x_offset
        self.pitch += y_offset
        if constrain_pitch:
            if self.pitch > 89.0: self.pitch = 89.0
            if self.pitch < -89.0: self.pitch = -89.0
        self.update_vectors()