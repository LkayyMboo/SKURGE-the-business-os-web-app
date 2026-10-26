"""
startup_service.py

Coordinates SKURGE's startup/boot sequence.

Currently performs only a short, fixed delay to establish the SKURGE
product identity before the main application appears. No real
initialization work exists yet.

DEFAULT_BOOT_DURATION_SECONDS is the ONE place this duration is
configured — do not hardcode a startup delay anywhere else.
"""

from kivy.clock import Clock

DEFAULT_BOOT_DURATION_SECONDS = 4.0


class StartupService:
    """Runs SKURGE's startup sequence and reports completion."""

    @staticmethod
    def run_startup(on_complete, duration: float = DEFAULT_BOOT_DURATION_SECONDS) -> None:
        Clock.schedule_once(lambda _dt: on_complete(), duration)
