# app/state.py
import logging
from typing import Optional

class AppState:
    def __init__(self):
        self.ready = False
        self.failure_reason = None
        self.startup_time = None

app_state = AppState()