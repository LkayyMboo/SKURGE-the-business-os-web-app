"""
main.py

Entry point for the Business OS frontend application.

Run this file to launch Business OS:

    python main.py

Keep this file minimal — its only job is to start the app.
All real logic lives in app/, screens/, components/, etc.
"""

from app.app import BusinessOSApp

if __name__ == "__main__":
    BusinessOSApp().run()