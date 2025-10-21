# src/HistoryManager.py
import os
import json
import time # <-- AÑADIR ESTA LÍNEA

class HistoryManager:
    def __init__(self, settings_dir):
        self.history_path = os.path.join(settings_dir, 'history.json')
        self.max_history_size = 10
        self.history = self.load_history()

    def load_history(self):
        try:
            with open(self.history_path, 'r') as f:
                history = json.load(f)
                if history and isinstance(history[0], str): return []
                return history if isinstance(history, list) else []
        except (FileNotFoundError, json.JSONDecodeError, IndexError):
            return []

    def save_history(self):
        try:
            with open(self.history_path, 'w') as f: json.dump(self.history, f, indent=4)
        except Exception as e:
            print(f"Error: No se pudo guardar el historial. {e}")

    def add_entry(self, filepath):
        self.history = [entry for entry in self.history if entry.get('path') != filepath]
        new_entry = {'path': filepath, 'timestamp': time.time()}
        self.history.insert(0, new_entry)
        self.history = self.history[:self.max_history_size]
        self.save_history()

    def remove_entry(self, filepath):
        self.history = [entry for entry in self.history if entry.get('path') != filepath]
        self.save_history()
        print(f"Se eliminó '{os.path.basename(filepath)}' del historial.")

    def get_history(self):
        return self.history