#!/usr/bin/env python3
"""Vestaboard Local API MCP Server"""

import os
import json
import datetime
import time
import threading
import requests
from mcp.server.fastmcp import FastMCP
from vestaboard import Formatter

VESTABOARD_HOST = os.environ.get("VESTABOARD_HOST", "http://192.168.68.64:7000")
VESTABOARD_API_KEY = os.environ.get("VESTABOARD_API_KEY", "")
HEADERS = {"X-Vestaboard-Local-Api-Key": VESTABOARD_API_KEY}

# Vestaboard character encoding
CHAR_MAP = {
    " ": 0,
    "A": 1,  "B": 2,  "C": 3,  "D": 4,  "E": 5,  "F": 6,  "G": 7,
    "H": 8,  "I": 9,  "J": 10, "K": 11, "L": 12, "M": 13, "N": 14,
    "O": 15, "P": 16, "Q": 17, "R": 18, "S": 19, "T": 20, "U": 21,
    "V": 22, "W": 23, "X": 24, "Y": 25, "Z": 26,
    "1": 27, "2": 28, "3": 29, "4": 30, "5": 31,
    "6": 32, "7": 33, "8": 34, "9": 35, "0": 36,
    "!": 37, "@": 38, "#": 39, "$": 40, "(": 41, ")": 42, "-": 44,
    "+": 46, "&": 47, "=": 48, ";": 49, ":": 50, "'": 52, '"': 53,
    "%": 54, ",": 55, ".": 56, "/": 59, "?": 60, "°": 62,
}

COLOR_MAP = {
    "red": 63, "orange": 64, "yellow": 65, "green": 66,
    "blue": 67, "violet": 68, "white": 69, "black": 70,
}

ROWS = 6
COLS = 22

DAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
          "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

# ---------------------------------------------------------------------------
# Color code aliases
# ---------------------------------------------------------------------------
_n, _R, _O, _Y, _G, _B, _V, _W, _K = 0, 63, 64, 65, 66, 67, 68, 69, 70

# ---------------------------------------------------------------------------
# Full-board weather icons — 6×22 grids of Vestaboard color codes
# Displayed alone (full screen) via vestaboard_show_icon or before forecast
# ---------------------------------------------------------------------------
WEATHER_ICONS = {
    # ☀️  Yellow sun on blue sky with 4-corner rays
    "sunny": [
        [_B,_B,_B,_B,_B,_Y,_B,_B,_B,_B,_Y,_B,_B,_B,_B,_Y,_B,_B,_B,_B,_B,_B],
        [_B,_B,_B,_B,_B,_B,_Y,_Y,_Y,_Y,_Y,_Y,_Y,_Y,_B,_B,_B,_B,_B,_B,_B,_B],
        [_B,_Y,_B,_B,_Y,_Y,_Y,_Y,_Y,_Y,_Y,_Y,_Y,_Y,_Y,_Y,_B,_B,_Y,_B,_B,_B],
        [_B,_B,_B,_Y,_Y,_Y,_Y,_Y,_Y,_Y,_Y,_Y,_Y,_Y,_Y,_Y,_B,_Y,_B,_B,_B,_B],
        [_B,_B,_B,_B,_B,_B,_Y,_Y,_Y,_Y,_Y,_Y,_Y,_Y,_B,_B,_B,_B,_B,_B,_B,_B],
        [_B,_B,_B,_B,_B,_Y,_B,_B,_B,_B,_Y,_B,_B,_B,_B,_Y,_B,_B,_B,_B,_B,_B],
    ],

    # 🌤️  Small sun upper-left, white cloud right
    "partly_cloudy": [
        [_B,_B,_B,_Y,_B,_B,_Y,_B,_B,_B,_W,_W,_W,_W,_W,_W,_B,_B,_B,_B,_B,_B],
        [_B,_B,_Y,_Y,_Y,_Y,_Y,_Y,_B,_W,_W,_W,_W,_W,_W,_W,_W,_B,_B,_B,_B,_B],
        [_B,_B,_Y,_Y,_Y,_Y,_Y,_Y,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_B,_B,_B,_B],
        [_B,_B,_B,_Y,_Y,_Y,_Y,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_B,_B,_B],
        [_B,_B,_B,_B,_Y,_B,_B,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_B,_B,_B,_B,_B],
        [_B,_B,_B,_B,_B,_B,_B,_B,_W,_W,_W,_W,_W,_W,_W,_W,_B,_B,_B,_B,_B,_B],
    ],

    # ☁️  White cloud layers filling the board
    "cloudy": [
        [_B,_B,_B,_B,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_B,_B,_B,_B,_B,_B],
        [_B,_B,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_B,_B,_B,_B],
        [_B,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_B,_B,_B],
        [_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_B,_B],
        [_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_B],
        [_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W],
    ],

    # 🌧️  Black cloud top half, blue rain drops bottom
    "rainy": [
        [_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K],
        [_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K],
        [_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K],
        [_n,_n,_n,_n,_n,_n,_n,_n,_n,_n,_n,_n,_n,_n,_n,_n,_n,_n,_n,_n,_n,_n],
        [_B,_n,_B,_n,_B,_n,_B,_n,_B,_n,_B,_n,_B,_n,_B,_n,_B,_n,_B,_n,_B,_n],
        [_n,_B,_n,_B,_n,_B,_n,_B,_n,_B,_n,_B,_n,_B,_n,_B,_n,_B,_n,_B,_n,_B],
    ],

    # ❄️  White snowflake crosses on blue sky
    "snowy": [
        [_B,_B,_W,_B,_B,_B,_B,_W,_B,_B,_B,_B,_W,_B,_B,_B,_B,_W,_B,_B,_B,_B],
        [_B,_W,_W,_W,_B,_B,_W,_W,_W,_B,_B,_W,_W,_W,_B,_B,_W,_W,_W,_B,_B,_B],
        [_B,_B,_W,_B,_B,_B,_B,_W,_B,_B,_B,_B,_W,_B,_B,_B,_B,_W,_B,_B,_B,_B],
        [_B,_B,_B,_B,_W,_B,_B,_B,_B,_W,_B,_B,_B,_B,_W,_B,_B,_B,_B,_W,_B,_B],
        [_B,_B,_B,_W,_W,_W,_B,_B,_W,_W,_W,_B,_B,_W,_W,_W,_B,_B,_W,_W,_W,_B],
        [_B,_B,_B,_B,_W,_B,_B,_B,_B,_W,_B,_B,_B,_B,_W,_B,_B,_B,_B,_W,_B,_B],
    ],

    # ⛈️  Black sky + orange double lightning bolts + blue rain
    "stormy": [
        [_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K],
        [_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K,_K],
        [_K,_K,_K,_K,_O,_O,_K,_K,_K,_K,_K,_K,_K,_O,_O,_K,_K,_K,_K,_K,_K,_K],
        [_K,_K,_K,_O,_O,_K,_K,_K,_K,_K,_K,_K,_O,_O,_K,_K,_K,_K,_K,_K,_K,_K],
        [_K,_K,_O,_O,_O,_K,_B,_B,_K,_K,_K,_O,_O,_O,_K,_B,_B,_K,_K,_K,_K,_K],
        [_K,_K,_O,_K,_K,_K,_B,_K,_K,_K,_K,_O,_K,_K,_K,_B,_K,_K,_K,_K,_K,_K],
    ],

    # 🌫️  Alternating white fog bands
    "foggy": [
        [_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W],
        [_n,_n,_n,_n,_n,_n,_n,_n,_n,_n,_n,_n,_n,_n,_n,_n,_n,_n,_n,_n,_n,_n],
        [_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W],
        [_n,_n,_n,_n,_n,_n,_n,_n,_n,_n,_n,_n,_n,_n,_n,_n,_n,_n,_n,_n,_n,_n],
        [_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W],
        [_n,_n,_n,_n,_n,_n,_n,_n,_n,_n,_n,_n,_n,_n,_n,_n,_n,_n,_n,_n,_n,_n],
    ],

    # 🥵  Red-orange sun — used for hot/scorching conditions
    "hot": [
        [_B,_B,_B,_B,_B,_O,_B,_B,_B,_B,_O,_B,_B,_B,_B,_O,_B,_B,_B,_B,_B,_B],
        [_B,_B,_B,_B,_B,_B,_R,_R,_R,_R,_R,_R,_R,_R,_B,_B,_B,_B,_B,_B,_B,_B],
        [_B,_O,_B,_B,_R,_R,_R,_Y,_Y,_Y,_Y,_Y,_Y,_R,_R,_R,_B,_B,_O,_B,_B,_B],
        [_B,_B,_B,_O,_R,_R,_Y,_Y,_Y,_Y,_Y,_Y,_Y,_Y,_R,_R,_O,_B,_B,_B,_B,_B],
        [_B,_B,_B,_B,_B,_B,_R,_R,_R,_R,_R,_R,_R,_R,_B,_B,_B,_B,_B,_B,_B,_B],
        [_B,_B,_B,_B,_B,_O,_B,_B,_B,_B,_O,_B,_B,_B,_B,_O,_B,_B,_B,_B,_B,_B],
    ],

    # 💨  Horizontal white streaks — windy
    "windy": [
        [_B,_B,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_B,_B,_B,_B,_B,_B],
        [_B,_B,_B,_B,_B,_B,_B,_B,_B,_B,_B,_B,_B,_B,_B,_B,_B,_B,_B,_B,_B,_B],
        [_B,_B,_B,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_B,_B,_B],
        [_B,_B,_B,_B,_B,_B,_B,_B,_B,_B,_B,_B,_B,_B,_B,_B,_B,_B,_B,_B,_B,_B],
        [_B,_B,_B,_B,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_W,_B,_B,_B,_B,_B],
        [_B,_B,_B,_B,_B,_B,_B,_B,_B,_B,_B,_B,_B,_B,_B,_B,_B,_B,_B,_B,_B,_B],
    ],
}

# ---------------------------------------------------------------------------
# Small icons — 6×8 grids for icon+text side-by-side layout
# Layout: cols 0-7 = icon, col 8 = blank, cols 9-21 = text (13 chars)
# ---------------------------------------------------------------------------
SMALL_WEATHER_ICONS = {
    "sunny": [
        [_B,_Y,_B,_B,_Y,_B,_B,_B],
        [_B,_B,_Y,_Y,_Y,_Y,_B,_B],
        [_Y,_Y,_Y,_Y,_Y,_Y,_Y,_B],
        [_B,_Y,_Y,_Y,_Y,_Y,_Y,_B],
        [_B,_B,_Y,_Y,_Y,_Y,_B,_B],
        [_B,_Y,_B,_B,_Y,_B,_B,_B],
    ],
    "partly_cloudy": [
        [_Y,_Y,_B,_W,_W,_W,_B,_B],
        [_Y,_Y,_Y,_W,_W,_W,_W,_B],
        [_Y,_Y,_W,_W,_W,_W,_W,_W],
        [_B,_W,_W,_W,_W,_W,_W,_W],
        [_B,_W,_W,_W,_W,_W,_W,_B],
        [_B,_B,_W,_W,_W,_W,_B,_B],
    ],
    "cloudy": [
        [_B,_W,_W,_W,_W,_B,_B,_B],
        [_W,_W,_W,_W,_W,_W,_W,_B],
        [_W,_W,_W,_W,_W,_W,_W,_W],
        [_W,_W,_W,_W,_W,_W,_W,_W],
        [_W,_W,_W,_W,_W,_W,_W,_B],
        [_B,_W,_W,_W,_W,_B,_B,_B],
    ],
    "rainy": [
        [_K,_K,_K,_K,_K,_K,_K,_K],
        [_K,_K,_K,_K,_K,_K,_K,_K],
        [_K,_K,_K,_K,_K,_K,_K,_K],
        [_n,_n,_n,_n,_n,_n,_n,_n],
        [_B,_n,_B,_n,_B,_n,_B,_n],
        [_n,_B,_n,_B,_n,_B,_n,_B],
    ],
    "snowy": [
        [_B,_W,_B,_B,_W,_B,_B,_B],
        [_W,_W,_W,_B,_W,_W,_W,_B],
        [_B,_W,_B,_B,_B,_W,_B,_B],
        [_B,_B,_B,_W,_B,_B,_B,_W],
        [_B,_B,_W,_W,_W,_B,_W,_W],
        [_B,_B,_B,_W,_B,_B,_B,_W],
    ],
    "stormy": [
        [_K,_K,_K,_K,_K,_K,_K,_K],
        [_K,_K,_K,_K,_K,_K,_K,_K],
        [_K,_K,_O,_O,_K,_K,_K,_K],
        [_K,_O,_O,_K,_B,_K,_K,_K],
        [_O,_O,_O,_K,_B,_K,_K,_K],
        [_O,_K,_K,_K,_B,_K,_K,_K],
    ],
    "foggy": [
        [_W,_W,_W,_W,_W,_W,_W,_W],
        [_n,_n,_n,_n,_n,_n,_n,_n],
        [_W,_W,_W,_W,_W,_W,_W,_W],
        [_n,_n,_n,_n,_n,_n,_n,_n],
        [_W,_W,_W,_W,_W,_W,_W,_W],
        [_n,_n,_n,_n,_n,_n,_n,_n],
    ],
    "hot": [
        [_B,_O,_B,_B,_O,_B,_B,_B],
        [_B,_B,_R,_R,_R,_R,_B,_B],
        [_O,_R,_R,_Y,_Y,_R,_R,_B],
        [_B,_R,_Y,_Y,_Y,_Y,_R,_O],
        [_B,_B,_R,_R,_R,_R,_B,_B],
        [_B,_O,_B,_B,_O,_B,_B,_B],
    ],
    "windy": [
        [_B,_W,_W,_W,_W,_W,_W,_W],
        [_B,_B,_B,_B,_B,_B,_B,_B],
        [_B,_B,_W,_W,_W,_W,_W,_W],
        [_B,_B,_B,_B,_B,_B,_B,_B],
        [_B,_B,_B,_W,_W,_W,_W,_W],
        [_B,_B,_B,_B,_B,_B,_B,_B],
    ],
}

# Aliases for common condition string variations
_ICON_MAP = {
    "sunny": "sunny",
    "clear": "sunny",
    "hot": "hot",
    "scorching": "hot",
    "partly cloudy": "partly_cloudy",
    "mostly clear": "partly_cloudy",
    "partly sunny": "partly_cloudy",
    "patchy rain": "partly_cloudy",
    "cloudy": "cloudy",
    "overcast": "cloudy",
    "mostly cloudy": "cloudy",
    "broken clouds": "cloudy",
    "light rain": "rainy",
    "light drizzle": "rainy",
    "drizzle": "rainy",
    "rain": "rainy",
    "heavy rain": "rainy",
    "showers": "rainy",
    "patchy light rain": "rainy",
    "light snow": "snowy",
    "snow": "snowy",
    "heavy snow": "snowy",
    "blizzard": "snowy",
    "blowing snow": "snowy",
    "freezing drizzle": "snowy",
    "sleet": "snowy",
    "thunderstorm": "stormy",
    "thunder": "stormy",
    "storm": "stormy",
    "tstorm": "stormy",
    "fog": "foggy",
    "mist": "foggy",
    "haze": "foggy",
    "smoke": "foggy",
    "windy": "windy",
    "breezy": "windy",
    "gale": "windy",
}

# Icon panel dimensions for side-by-side layout
_ICON_COLS = 8
_TEXT_COLS = 13  # 22 - 8 icon - 1 separator


def get_weather_icon(condition: str) -> list | None:
    """Return a 6×22 full-board icon for a weather condition, or None."""
    lower = condition.lower()
    for key, icon_name in _ICON_MAP.items():
        if key in lower:
            return WEATHER_ICONS[icon_name]
    return None


def get_small_icon(condition: str) -> list | None:
    """Return a 6×8 small icon for a weather condition, or None."""
    lower = condition.lower()
    for key, icon_name in _ICON_MAP.items():
        if key in lower:
            return SMALL_WEATHER_ICONS[icon_name]
    return None


def compose_icon_text(icon_small: list, text_lines: list) -> list:
    """Combine a 6×8 icon with left-aligned text into a 6×22 board.

    Layout: [8 cols icon] [1 col blank] [13 cols text]
    """
    board = []
    for i in range(ROWS):
        icon_row = list(icon_small[i]) if i < len(icon_small) else [0] * _ICON_COLS
        sep = [0]
        if i < len(text_lines):
            line = str(text_lines[i]).upper()[:_TEXT_COLS]
            codes = [CHAR_MAP.get(c, 0) for c in line]
            text_row = codes + [0] * (_TEXT_COLS - len(codes))
        else:
            text_row = [0] * _TEXT_COLS
        board.append(icon_row + sep + text_row)
    return board


def text_to_board(text: str) -> list:
    """Convert multi-line text into a 6×22 character code grid, centered."""
    lines = text.upper().splitlines()[:ROWS]
    board = []
    for line in lines:
        codes = [CHAR_MAP.get(c, 0) for c in line[:COLS]]
        pad = COLS - len(codes)
        left = pad // 2
        board.append([0] * left + codes + [0] * (pad - left))
    while len(board) < ROWS:
        board.append([0] * COLS)
    content_rows = [r for r in board if any(c != 0 for c in r)]
    empty_row = [0] * COLS
    top_pad = (ROWS - len(content_rows)) // 2
    result = [empty_row[:] for _ in range(top_pad)]
    result.extend(content_rows)
    while len(result) < ROWS:
        result.append(empty_row[:])
    return result


def _post_board(board: list) -> str:
    resp = requests.post(
        f"{VESTABOARD_HOST}/local-api/message",
        headers={**HEADERS, "Content-Type": "application/json"},
        json=board,
        timeout=10,
    )
    if resp.ok:
        return "ok"
    return f"Error {resp.status_code}: {resp.text}"


def _shorten_condition(desc: str, max_len: int = 9) -> str:
    """Abbreviate common weather descriptions to fit the board."""
    abbr = {
        "partly cloudy": "PT CLOUDY",
        "mostly cloudy": "MT CLOUDY",
        "overcast": "OVERCAST",
        "light rain": "LT RAIN",
        "heavy rain": "HVY RAIN",
        "light snow": "LT SNOW",
        "heavy snow": "HVY SNOW",
        "thunderstorm": "TSTORM",
        "patchy rain": "PTCHY RAIN",
        "blowing snow": "BLWG SNOW",
        "freezing drizzle": "FRZG DRZ",
        "light drizzle": "LT DRZL",
    }
    lower = desc.lower()
    for key, short in abbr.items():
        if key in lower:
            return short
    return desc.upper()[:max_len]


def _cycle_screens(screens: list, delay: int) -> None:
    """Post a sequence of screens with a delay between each (background thread)."""
    for i, screen in enumerate(screens):
        _post_board(screen)
        if i < len(screens) - 1:
            time.sleep(delay)


mcp = FastMCP("vestaboard")


@mcp.tool()
def vestaboard_weather_forecast(location: str = "Seattle", compact: bool = False) -> str:
    """Fetch the current weather forecast and display it on the Vestaboard.

    Standard mode (compact=False):
      Shows the matching weather icon for 4 seconds, then a full data screen:
        Row 1: City + date
        Row 2: Current condition + temperature
        Row 3: Feels like + humidity
        Rows 4-6: 3-day forecast (day, condition, hi/lo)

    Compact mode (compact=True):
      Shows icon (left 8 cols) alongside a condensed today summary (right 13 cols),
      all on one screen — no icon flash:
        Row 1: City name
        Row 2: Temp + condition
        Row 3: Feels like + humidity
        Row 4: Today hi/lo
        Rows 5-6: Next 2 days (day + hi/lo)

    Args:
        location: City name or location string (default: Seattle).
        compact: If True, show icon alongside condensed today view (default: False).
    """
    encoded = location.replace(" ", "+")
    url = f"https://wttr.in/{encoded}?format=j1"

    try:
        resp = requests.get(url, headers={"User-Agent": "vestaboard-mcp/1.0"}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return f"Failed to fetch weather for {location}: {e}"

    try:
        cur = data["current_condition"][0]
        area = data["nearest_area"][0]
        city = area["areaName"][0]["value"]

        temp_f = cur["temp_F"]
        temp_c = cur["temp_C"]
        feels_f = cur["FeelsLikeF"]
        humidity = cur["humidity"]
        condition_raw = cur["weatherDesc"][0]["value"]
        condition = _shorten_condition(condition_raw)

        today = datetime.date.today()
        date_str = f"{DAYS[today.weekday()]} {MONTHS[today.month-1]} {today.day}"

        weather_days = data.get("weather", [])

        if compact:
            small = get_small_icon(condition_raw) or SMALL_WEATHER_ICONS["cloudy"]

            cond_short = _shorten_condition(condition_raw, 6)
            hi_f = weather_days[0]["maxtempF"] if weather_days else "?"
            lo_f = weather_days[0]["mintempF"] if weather_days else "?"

            text_lines = [
                city.upper()[:_TEXT_COLS],
                f"{temp_f}F {cond_short}"[:_TEXT_COLS],
                f"FL{feels_f}F HM{humidity}%"[:_TEXT_COLS],
                f"HI{hi_f} LO{lo_f}F"[:_TEXT_COLS],
            ]
            for day_data in weather_days[1:3]:
                d = datetime.date.fromisoformat(day_data["date"])
                day_name = DAYS[d.weekday()]
                hi = day_data["maxtempF"]
                lo = day_data["mintempF"]
                text_lines.append(f"{day_name} H{hi} L{lo}F"[:_TEXT_COLS])

            board = compose_icon_text(small, text_lines)
            result = _post_board(board)

            if result == "ok":
                return (
                    f"Compact weather for {city} sent to Vestaboard.\n"
                    f"Current: {condition_raw}, {temp_f}°F, feels like {feels_f}°F, "
                    f"humidity {humidity}%"
                )
            return f"Fetched weather but Vestaboard error: {result}"

        else:
            header = f"{city.upper()[:10]} {date_str}"
            if len(header) > COLS:
                header = f"{city.upper()[:8]} {date_str}"

            row2 = f"{condition} {temp_f}F/{temp_c}C"
            if len(row2) > COLS:
                row2 = f"{condition} {temp_f}F"

            row3 = f"FEELS {feels_f}F  HUM {humidity}%"
            if len(row3) > COLS:
                row3 = f"FL {feels_f}F HM {humidity}%"

            forecast_rows = []
            for day_data in weather_days[:3]:
                raw_date = day_data["date"]
                d = datetime.date.fromisoformat(raw_date)
                day_name = DAYS[d.weekday()]
                hi = day_data["maxtempF"]
                lo = day_data["mintempF"]
                desc = _shorten_condition(day_data["hourly"][4]["weatherDesc"][0]["value"], 7)
                row = f"{day_name} {desc} {lo}-{hi}F"
                if len(row) > COLS:
                    row = f"{day_name} {lo}-{hi}F"
                forecast_rows.append(row)

            board_text = "\n".join([header, row2, row3] + forecast_rows)
            text_screen = text_to_board(board_text)

            icon = get_weather_icon(condition_raw)
            if icon:
                _post_board(icon)
                time.sleep(4)

            result = _post_board(text_screen)

            if result == "ok":
                icon_note = f" (showed {condition_raw.lower()} icon)" if icon else ""
                return (
                    f"Weather forecast for {city} sent to Vestaboard{icon_note}.\n"
                    f"Current: {condition_raw}, {temp_f}°F / {temp_c}°C, "
                    f"feels like {feels_f}°F, humidity {humidity}%\n"
                    f"Board text:\n{board_text}"
                )
            return f"Fetched weather but Vestaboard error: {result}"

    except (KeyError, IndexError) as e:
        return f"Unexpected weather data format: {e}"


@mcp.tool()
def vestaboard_icon_text(icon: str, text: str) -> str:
    """Display an icon on the left (8 columns) with text on the right (13 columns).

    Generic tool for any icon + text combination — not weather-specific.
    The icon occupies the left 8 columns; text fills the right 13 columns,
    left-aligned. Use \\n to break text across rows (max 6 rows × 13 chars).

    Available icon keywords: sunny, clear, cloudy, overcast, partly cloudy,
    rainy, rain, drizzle, snowy, snow, stormy, thunderstorm, foggy, mist,
    hot, windy, breezy — and common variants of each.

    Args:
        icon: Icon condition name or description (e.g. "sunny", "rainy", "stormy").
        text: Text for the right panel. Use \\n for line breaks.
    """
    small = get_small_icon(icon)
    if small is None:
        available = ", ".join(sorted(set(_ICON_MAP.keys())))
        return f"No icon found for '{icon}'. Recognized keywords: {available}"

    text_lines = text.splitlines()
    board = compose_icon_text(small, text_lines)
    result = _post_board(board)
    return "Icon+text displayed on Vestaboard." if result == "ok" else result


@mcp.tool()
def vestaboard_send_text(text: str) -> str:
    """Send a text message to the Vestaboard. Text is automatically centered.
    Use newlines to separate rows (max 6 rows, 22 chars per row).
    Example: 'Hello\\nWorld'"""
    board = text_to_board(text)
    resp = requests.post(
        f"{VESTABOARD_HOST}/local-api/message",
        headers={**HEADERS, "Content-Type": "application/json"},
        json=board,
        timeout=10,
    )
    if resp.ok:
        return f"Message sent successfully: {repr(text)}"
    return f"Error {resp.status_code}: {resp.text}"


@mcp.tool()
def vestaboard_send_long_text(text: str, delay: int = 8) -> str:
    """Send text longer than one screen — automatically splits into multiple
    6×22 screens and cycles through them with a delay between each.

    Useful for announcements, multi-line messages, or anything over 6 rows.
    Returns immediately; screens cycle in the background.

    Args:
        text: Text to display. Word-wrapped automatically at 22 chars.
        delay: Seconds between screens (default: 8).
    """
    f = Formatter()
    screens = f.createScreens(text, justify="center", align="center")

    if not screens:
        return "No content to display."

    if len(screens) == 1:
        result = _post_board(screens[0])
        return "Message sent (1 screen)." if result == "ok" else result

    thread = threading.Thread(
        target=_cycle_screens, args=(screens, delay), daemon=True
    )
    thread.start()
    return (
        f"Cycling {len(screens)} screens on Vestaboard "
        f"({delay}s between each). First screen posted."
    )


@mcp.tool()
def vestaboard_show_icon(condition: str) -> str:
    """Display a full-board weather icon by condition name (6×22, fills entire display).

    Use vestaboard_icon_text instead if you want an icon alongside text.

    Available conditions: sunny, clear, partly_cloudy, cloudy, overcast,
    rainy, light_rain, heavy_rain, snowy, light_snow, stormy, thunderstorm,
    foggy, misty, hot, windy.

    Args:
        condition: Weather condition name or description.
    """
    icon = get_weather_icon(condition)
    if icon is None:
        available = ", ".join(sorted(set(_ICON_MAP.keys())))
        return (
            f"No icon found for '{condition}'. "
            f"Recognized keywords: {available}"
        )
    result = _post_board(icon)
    return f"Icon displayed for '{condition}'." if result == "ok" else result


@mcp.tool()
def vestaboard_read() -> str:
    """Read the current message displayed on the Vestaboard.
    Returns the character code grid and a decoded text approximation."""
    resp = requests.get(
        f"{VESTABOARD_HOST}/local-api/message",
        headers=HEADERS,
        timeout=10,
    )
    if not resp.ok:
        return f"Error {resp.status_code}: {resp.text}"
    data = resp.json()
    board = data.get("message", [])
    reverse_map = {v: k for k, v in CHAR_MAP.items()}
    reverse_map.update({v: f"[{k}]" for k, v in COLOR_MAP.items()})
    lines = []
    for row in board:
        line = "".join(reverse_map.get(c, "?") if c != 0 else " " for c in row)
        lines.append(line)
    return "Current board:\n" + "\n".join(f"|{l}|" for l in lines)


@mcp.tool()
def vestaboard_clear() -> str:
    """Clear the Vestaboard display (all blank)."""
    board = [[0] * COLS for _ in range(ROWS)]
    result = _post_board(board)
    return "Board cleared." if result == "ok" else result


@mcp.tool()
def vestaboard_send_raw(rows: list) -> str:
    """Send a raw character code grid to the Vestaboard.
    rows: a 6x22 list of lists with integer character codes.
    Codes: 0=blank, 1-26=A-Z, 27-35=1-9, 36=0, 62=degree,
           63=red, 64=orange, 65=yellow, 66=green, 67=blue,
           68=violet, 69=white, 70=black"""
    if len(rows) != ROWS or any(len(r) != COLS for r in rows):
        return f"Invalid dimensions: need {ROWS}x{COLS} grid, got {len(rows)} rows"
    result = _post_board(rows)
    return "Raw message sent successfully." if result == "ok" else result


if __name__ == "__main__":
    mcp.run()
