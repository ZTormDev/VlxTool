# Sun.py
import numpy as np
import math

class Sun:
    def __init__(self, initial_angle_deg=0.0):
        self.color = np.array([1.0, 1.0, 0.9], dtype=np.float32) # Luz ligeramente amarilla
        self.direction = np.array([-1.0, -1.0, -1.0], dtype=np.float32)
        self.angle = math.radians(initial_angle_deg)