"""UI glue to initialize and teardown the project's UIManager from App."""
from src.managers.UIManager import UIManager


def init_ui(app):
    """Create and attach a UIManager to the running App instance.

    This keeps UI wiring in a single place so tests or alternate UI
    implementations can swap it out.
    """
    app.ui_manager = UIManager(app.window, app)
