#!/usr/bin/env python3
"""
Vestaboard text->character-code encoder + grid builder.

Authoritative character codes from the official Vestaboard docs
(https://docs.vestaboard.com/docs/charactercodes/), cross-verified
empirically on the physical board.

Usage as a library:
    from vesta_encode import build_weather_grid, text_to_codes, render_grid
    grid = build_weather_grid(now_f=57, hi_f=67, lo_f=48, condition="Light Rain")
    # grid is a 6x22 list of lists of ints, ready for vestaboard_send_raw

Usage as a CLI (prints JSON 6x22 grid to stdout):
    python3 vesta_encode.py --now 57 --hi 67 --lo 48 --condition "Light Rain"
"""
import argparse
import json
import sys

# --- Authoritative character code map (verified) ---
CHAR_CODES = {
    " ": 0,
    "A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6, "G": 7, "H": 8,
    "I": 9, "J": 10, "K": 11, "L": 12, "M": 13, "N": 14, "O": 15, "P": 16,
    "Q": 17, "R": 18, "S": 19, "T": 20, "U": 21, "V": 22, "W": 23, "X": 24,
    "Y": 25, "Z": 26,
    "1": 27, "2": 28, "3": 29, "4": 30, "5": 31, "6": 32, "7": 33, "8": 34,
    "9": 35, "0": 36,
    "!": 37, "@": 38, "#": 39, "$": 40, "(": 41, ")": 42, "-": 44, "+": 46,
    "&": 47, "=": 48, ";": 49, ":": 50, "'": 52, '"': 53, "%": 54, ",": 55,
    ".": 56, "/": 59, "?": 60,
    "\u00b0": 62,  # degree symbol
}

# Colors
RED, ORANGE, YELLOW, GREEN, BLUE, VIOLET, WHITE, BLACK, FILLED = (
    63, 64, 65, 66, 67, 68, 69, 70, 71
)

COLS = 22
ROWS = 6
DEGREE = 62


def text_to_codes(text):
    """Convert a string to a list of Vestaboard character codes.
    Unknown characters become blank (0). Case-insensitive (uppercased)."""
    out = []
    for ch in text.upper():
        out.append(CHAR_CODES.get(ch, 0))
    return out


def pad_row(codes, width=COLS, fill=0):
    """Pad/truncate a list of codes to exactly `width`."""
    codes = list(codes)
    if len(codes) > width:
        return codes[:width]
    return codes + [fill] * (width - len(codes))


def center_row(codes, width=COLS, fill=0):
    """Center a list of codes within `width`."""
    codes = list(codes)
    if len(codes) >= width:
        return codes[:width]
    total = width - len(codes)
    left = total // 2
    right = total - left
    return [fill] * left + codes + [fill] * right


def place(row, codes, start):
    """Place `codes` into `row` (a list) starting at column `start`, in place."""
    for i, c in enumerate(codes):
        idx = start + i
        if 0 <= idx < len(row):
            row[idx] = c
    return row


def _icon_for(condition):
    """Return (icon_func, strip_color) for a condition string.
    icon_func(row2, row3) draws a small color glyph on the right side
    (cols ~14-18) of rows 2 and 3."""
    c = condition.lower()

    def sunny(r2, r3):
        place(r2, [YELLOW, YELLOW, YELLOW], 15)
        place(r3, [YELLOW, YELLOW, YELLOW], 15)

    def rain(r2, r3):
        place(r2, [WHITE, WHITE, WHITE, WHITE], 14)  # cloud
        r3[14] = BLUE; r3[16] = BLUE; r3[18] = BLUE   # raindrops

    def cloudy(r2, r3):
        place(r2, [WHITE, WHITE, WHITE, WHITE, WHITE], 14)
        place(r3, [WHITE, WHITE, WHITE], 15)

    def snow(r2, r3):
        place(r2, [WHITE, WHITE, WHITE, WHITE], 14)
        r3[14] = WHITE; r3[16] = WHITE; r3[18] = WHITE

    def storm(r2, r3):
        place(r2, [WHITE, WHITE, WHITE, WHITE], 14)
        place(r3, [VIOLET, VIOLET], 15)

    def fog(r2, r3):
        place(r2, [WHITE, WHITE, WHITE, WHITE, WHITE], 14)
        place(r3, [WHITE, WHITE, WHITE, WHITE, WHITE], 14)

    # keyword matching, order matters (most specific first)
    if any(k in c for k in ("thunder", "storm", "lightning")):
        return storm, VIOLET
    if "snow" in c or "sleet" in c or "blizzard" in c:
        return snow, WHITE
    if any(k in c for k in ("rain", "drizzle", "shower")):
        return rain, BLUE
    if any(k in c for k in ("fog", "mist", "haze")):
        return fog, WHITE
    if any(k in c for k in ("sunny", "clear", "sun")):
        return sunny, YELLOW
    # default: cloudy
    return cloudy, WHITE


def build_weather_grid(now_f, hi_f, lo_f, condition):
    """Build a 6x22 weather grid. Temps are ints (Fahrenheit)."""
    now_f = int(round(float(now_f)))
    hi_f = int(round(float(hi_f)))
    lo_f = int(round(float(lo_f)))

    grid = [[0] * COLS for _ in range(ROWS)]

    # Row 0: SEATTLE WEATHER (centered)
    grid[0] = center_row(text_to_codes("SEATTLE WEATHER"))

    # Row 2: NOW <temp>°F  + icon top
    row2 = [0] * COLS
    place(row2, text_to_codes("NOW "), 2)
    nowtxt = text_to_codes(str(now_f)) + [DEGREE] + text_to_codes("F")
    place(row2, nowtxt, 6)

    # Row 3: condition text + icon bottom
    row3 = [0] * COLS
    cond = condition.upper().strip()
    place(row3, text_to_codes(cond[:11]), 2)

    # Draw icon onto rows 2 & 3
    icon_func, strip_color = _icon_for(condition)
    icon_func(row2, row3)

    grid[2] = pad_row(row2)
    grid[3] = pad_row(row3)

    # Row 4: HI <hi>°  LOW <lo>°
    row4 = [0] * COLS
    place(row4, text_to_codes("HI "), 1)
    hitxt = text_to_codes(str(hi_f)) + [DEGREE]
    place(row4, hitxt, 4)
    place(row4, text_to_codes("LOW "), 9)
    lotxt = text_to_codes(str(lo_f)) + [DEGREE]
    place(row4, lotxt, 13)
    grid[4] = pad_row(row4)

    # Row 5: full-width color strip
    grid[5] = [strip_color] * COLS

    # safety: ensure every row is exactly 22
    grid = [pad_row(r) for r in grid]
    return grid


def render_grid(grid):
    """ASCII preview of a grid for debugging (best-effort)."""
    rev = {v: k for k, v in CHAR_CODES.items()}
    color_names = {63: "R", 64: "O", 65: "Y", 66: "G", 67: "B",
                   68: "V", 69: "W", 70: "K", 71: "#"}
    lines = []
    for row in grid:
        s = ""
        for c in row:
            if c in color_names:
                s += color_names[c]
            else:
                s += rev.get(c, "?") if c != 0 else " "
        lines.append("|" + s + "|")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--now", required=True)
    ap.add_argument("--hi", required=True)
    ap.add_argument("--lo", required=True)
    ap.add_argument("--condition", required=True)
    ap.add_argument("--preview", action="store_true",
                    help="also print ASCII preview to stderr")
    args = ap.parse_args()

    grid = build_weather_grid(args.now, args.hi, args.lo, args.condition)
    # validate
    assert len(grid) == 6, "grid must have 6 rows"
    for r in grid:
        assert len(r) == 22, "each row must be 22 cols"
    if args.preview:
        sys.stderr.write(render_grid(grid) + "\n")
    print(json.dumps(grid))


if __name__ == "__main__":
    main()
