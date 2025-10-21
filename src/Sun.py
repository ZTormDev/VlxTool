# Sun.py
import numpy as np
import math

class Sun:
    def __init__(self, initial_angle_deg=45.0):
        self.color = np.array([1.0, 1.0, 0.9], dtype=np.float32) # Luz ligeramente amarilla
        self.direction = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        self.angle = math.radians(initial_angle_deg)
        self.update_direction()

    def update_direction(self):
        # La luz viene desde una dirección diagonal, rotando alrededor del eje Y
        self.direction[0] = math.sin(self.angle)
        self.direction[1] = -0.8 # Siempre apuntando hacia abajo
        self.direction[2] = math.cos(self.angle)
        # Normalizamos para que la longitud sea 1
        self.direction = self.direction / np.linalg.norm(self.direction)