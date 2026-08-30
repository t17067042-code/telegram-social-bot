import os


def env_int(name, default):
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


MAX_WARNS = env_int("MAX_WARNS", 3)
REP_COOLDOWN_HOURS = env_int("REP_COOLDOWN_HOURS", 24)
FLOOD_MESSAGES = env_int("FLOOD_MESSAGES", 6)
FLOOD_WINDOW_SECONDS = env_int("FLOOD_WINDOW_SECONDS", 8)
FLOOD_MUTE_MINUTES = env_int("FLOOD_MUTE_MINUTES", 2)
XP_PER_MESSAGE = env_int("XP_PER_MESSAGE", 1)
