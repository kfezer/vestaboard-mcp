# Vestaboard MCP

A small [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server for controlling a [Vestaboard](https://www.vestaboard.com/) split-flap display over its **Local API**, plus a helper for building rich text/graphic layouts (e.g. a daily weather board).

It exposes simple tools an LLM agent (Claude, Hermes, etc.) can call to read, write, clear, and draw on the board.

## Features

- **`vestaboard_send_text`** — send centered multi-line text (auto-laid out into the 6×22 grid).
- **`vestaboard_send_raw`** — send a raw 6×22 grid of character codes (full control over letters, digits, punctuation, and color chips).
- **`vestaboard_read`** — read the board's current contents (returns a decoded text approximation).
- **`vestaboard_clear`** — blank the board.
- **`vesta_encode.py`** — standalone helper that converts text → correct Vestaboard character codes and builds a weather layout with a little color "icon" (sun / cloud / rain / snow / storm). Use it directly or from a scheduled job.

## Requirements

- A Vestaboard with the **Local API enabled** and an Local API key. See Vestaboard's [Local API docs](https://docs.vestaboard.com/docs/local-api/introduction).
- Python 3.10+
- The board reachable on your network (host + port).

## Install

```bash
git clone https://github.com/kfezer/vestaboard-mcp.git
cd vestaboard-mcp
pip install -r requirements.txt
```

## Configuration

Copy the example env file and fill in your board's host and Local API key:

```bash
cp .env.example .env
```

```ini
# .env
VESTABOARD_HOST=http://192.168.x.x:7000     # your board's local IP + port
VESTABOARD_API_KEY=your_local_api_key_here
```

The server reads these from the environment (`VESTABOARD_HOST`, `VESTABOARD_API_KEY`).

## Running

### As a standalone MCP server (stdio)

```bash
python3 vestaboard_mcp.py
```

### Registering with an MCP host

Add it to your MCP host's server config. Example (`mcp_servers` block, as used by Hermes / Claude-style configs):

```yaml
mcp_servers:
  vestaboard:
    command: python3
    args:
      - /absolute/path/to/vestaboard-mcp/vestaboard_mcp.py
    env:
      VESTABOARD_HOST: http://192.168.x.x:7000
      VESTABOARD_API_KEY: your_local_api_key_here
    enabled: true
```

Or the Claude Desktop style (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "vestaboard": {
      "command": "python3",
      "args": ["/absolute/path/to/vestaboard-mcp/vestaboard_mcp.py"],
      "env": {
        "VESTABOARD_HOST": "http://192.168.x.x:7000",
        "VESTABOARD_API_KEY": "your_local_api_key_here"
      }
    }
  }
}
```

## Character codes

The board is a **6 rows × 22 columns** grid. Each cell is an integer character code.

| Code(s) | Meaning |
|---------|---------|
| `0`     | Blank   |
| `1`–`26` | `A`–`Z` |
| `27`–`35` | `1`–`9` |
| `36`    | `0`     |
| `37`–`60` | Punctuation (`!@#$()-+&=;:'"%,./?`) |
| `62`    | `°` (degree) |
| `63`–`70` | Color chips: 63 red, 64 orange, 65 yellow, 66 green, 67 blue, 68 violet, 69 white, 70 black |
| `71`    | Filled (all-on) |

> **Note:** digits are `1`–`9` = `27`–`35` and `0` = `36` (zero comes *after* nine), and the degree symbol is `62`. These match the [official Vestaboard character codes](https://docs.vestaboard.com/docs/characterCodes/). Using the wrong table makes digits render as punctuation.

The `vesta_encode.py` helper already encodes against this verified table, so prefer it over hand-building grids.

## Weather board helper

`vesta_encode.py` builds a ready-to-send 6×22 grid for a weather display, including a small color "icon" chosen from the condition text.

```bash
python3 vesta_encode.py --now 57 --hi 67 --lo 48 --condition "Light Rain" --preview
```

`--preview` prints an ASCII rendering to stderr:

```
|   SEATTLE WEATHER    |
|                      |
|  NOW 57°F    WWWW    |
|  LIGHT RAIN  B B B   |
| HI 67°  LOW 48°      |
|BBBBBBBBBBBBBBBBBBBBBB|
```

The JSON 6×22 grid is printed to stdout — pipe it straight into `vestaboard_send_raw`.

### Icons by condition

| Condition keywords | Icon | Strip color |
|--------------------|------|-------------|
| sunny / clear / sun | yellow block | yellow |
| rain / drizzle / shower | white cloud + blue drops | blue |
| cloudy / overcast | white cloud | white |
| snow / sleet / blizzard | white cloud + white flakes | white |
| thunder / storm / lightning | white cloud + violet bolt | violet |
| fog / mist / haze | white block | white |

### Example: daily weather cron

Fetch the forecast and push it to the board on a schedule (e.g. weekday mornings):

```bash
# 7:30am Mon–Fri
30 7 * * 1-5  /path/to/update_weather.sh
```

```bash
#!/bin/bash
# update_weather.sh — fetch Seattle weather and draw it on the board
cd "$(dirname "$0")"
read NOW HI LO COND < <(curl -s 'https://wttr.in/Seattle?format=j1' | python3 -c '
import sys, json
d = json.load(sys.stdin)
c = d["current_condition"][0]; t = d["weather"][0]
print(c["temp_F"], t["maxtempF"], t["mintempF"], c["weatherDesc"][0]["value"])
')
GRID=$(python3 vesta_encode.py --now "$NOW" --hi "$HI" --lo "$LO" --condition "$COND")
curl -s -X POST "$VESTABOARD_HOST/local-api/message" \
  -H "X-Vestaboard-Local-Api-Key: $VESTABOARD_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$GRID"
```

## API notes

- Messages are sent via `POST {VESTABOARD_HOST}/local-api/message` with header `X-Vestaboard-Local-Api-Key`.
- The current board is read via `GET {VESTABOARD_HOST}/local-api/message`.
- `vestaboard_read`'s decode is a best-effort text approximation; for exact verification, judge by what's physically on the board.

## License

MIT
