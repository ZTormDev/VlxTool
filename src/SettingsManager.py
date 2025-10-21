# src/SettingsManager.py
import os
import json
class SettingsManager:
    def __init__(self):
        app_data_path = os.getenv('LOCALAPPDATA', os.path.expanduser("~"))
        self.settings_dir = os.path.join(app_data_path, 'VlxTool')
        self.settings_path = os.path.join(self.settings_dir, 'Settings.json')

    def load_settings(self):
        try:
            with open(self.settings_path, 'r') as f:
                settings = json.load(f)
                if 'hpp_path' in settings and os.path.exists(settings['hpp_path']):
                    return settings
                print("Info: Saved .hpp path is no longer valid.")
                return None
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def save_settings(self, settings_dict):
        try:
            os.makedirs(self.settings_dir, exist_ok=True)
            with open(self.settings_path, 'w') as f:
                json.dump(settings_dict, f, indent=4)
            print(f"Settings saved to {self.settings_path}")
        except Exception as e:
            print(f"Error: Could not save settings. {e}")