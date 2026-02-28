"""
Entry point for running nanobot as a module: python -m nanobot

Starts the Flask server with channel support.
"""

from nanobot.server.app import run_server

if __name__ == "__main__":
    run_server()
