"""Thin launcher for VlxTool.

This file keeps backward-compatible entrypoint behavior. The heavy lifting
is implemented in `app.app.App`.
"""
from app.app import App


def main():
    my_app = None
    try:
        my_app = App()
        my_app.run()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if my_app:
            my_app.quit()


if __name__ == "__main__":
    main()