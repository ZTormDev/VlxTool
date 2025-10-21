# src/managers/ActionHistory.py
from collections import deque

class ActionHistory:
    def __init__(self, max_entries=1000):
        self.undo_stack = []
        self.redo_stack = []
        self.max_entries = max_entries

    def record(self, action):
        # action: dict describing the operation; caller must provide undo info
        self.undo_stack.append(action)
        if len(self.undo_stack) > self.max_entries:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def can_undo(self):
        return len(self.undo_stack) > 0

    def can_redo(self):
        return len(self.redo_stack) > 0

    def undo(self, world):
        if not self.can_undo():
            return False
        action = self.undo_stack.pop()
        # action types: 'set' where action contains pos, prev, new
        if action.get('type') == 'set':
            x, y, z = action['pos']
            prev = action['prev']
            world.set_voxel(x, y, z, prev)
        self.redo_stack.append(action)
        return True

    def redo(self, world):
        if not self.can_redo():
            return False
        action = self.redo_stack.pop()
        if action.get('type') == 'set':
            x, y, z = action['pos']
            new = action['new']
            world.set_voxel(x, y, z, new)
        self.undo_stack.append(action)
        return True
