#!/usr/bin/env python3
"""Vestaboard Local API MCP Server"""

import os
import json
import requests
from mcp.server.fastmcp import FastMCP

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
    # Digits per official Vestaboard codes: 1-9 = 27-35, 0 = 36
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


def text_to_board(text: str) -> list[list[int]]:
    """Convert multi-line text into a 6x22 character code grid, centered."""
    lines = text.upper().splitlines()
    # Truncate to 6 lines
    lines = lines[:ROWS]
    board = []
    for line in lines:
        codes = [CHAR_MAP.get(c, 0) for c in line[:COLS]]
        # Center the line
        pad = COLS - len(codes)
        left = pad // 2
        right = pad - left
        board.append([0] * left + codes + [0] * right)
    # Pad to 6 rows
    while len(board) < ROWS:
        board.append([0] * COLS)
    # Vertically center: move content rows to middle
    content_rows = [r for r in board if any(c != 0 for c in r)]
    empty_row = [0] * COLS
    n_content = len(content_rows)
    top_pad = (ROWS - n_content) // 2
    result = [empty_row[:] for _ in range(top_pad)]
    result.extend(content_rows)
    while len(result) < ROWS:
        result.append(empty_row[:])
    return result


mcp = FastMCP("vestaboard")


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
    # Decode back to readable text
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
    resp = requests.post(
        f"{VESTABOARD_HOST}/local-api/message",
        headers={**HEADERS, "Content-Type": "application/json"},
        json=board,
        timeout=10,
    )
    if resp.ok:
        return "Board cleared."
    return f"Error {resp.status_code}: {resp.text}"


@mcp.tool()
def vestaboard_send_raw(rows: list) -> str:
    """Send a raw character code grid to the Vestaboard.
    rows: a 6x22 list of lists with integer character codes.
    Codes: 0=blank, 1-26=A-Z, 27-35=1-9, 36=0, 62=degree,
           63=red, 64=orange, 65=yellow, 66=green, 67=blue,
           68=violet, 69=white, 70=black"""
    if len(rows) != ROWS or any(len(r) != COLS for r in rows):
        return f"Invalid dimensions: need {ROWS}x{COLS} grid, got {len(rows)} rows"
    resp = requests.post(
        f"{VESTABOARD_HOST}/local-api/message",
        headers={**HEADERS, "Content-Type": "application/json"},
        json=rows,
        timeout=10,
    )
    if resp.ok:
        return "Raw message sent successfully."
    return f"Error {resp.status_code}: {resp.text}"


if __name__ == "__main__":
    mcp.run()
