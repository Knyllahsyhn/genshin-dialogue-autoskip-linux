# Genshin Dialogue Autoskip (Linux)

Dialogue auto-skipper for Genshin Impact running under Wine (XWayland) -
works with Steam/HoYoPlay and Lutris setups.
Linux port of [1hubert/genshin-dialogue-autoskip](https://github.com/1hubert/genshin-dialogue-autoskip).

Reads checkpoint pixels directly from the Genshin window (X11) and presses
the interaction key (F) through a virtual uinput keyboard. When answer
options appear, the first option is confirmed automatically (can be turned
off, see Configuration). UI uses user-friendly rich terminal output.

## Requirements

### System Requirements

 - OS: Linux (tested on CachyOS w/ 7.1.3-2 kernel)
 - Display: Genshin running through XWayland, native Wayland not tested 
 - Privileges: user in `input` group

### Software Requirements

 - Python 3.11+
 - uv package manager
 - Genshin Impact installed via Steam/Lutris (wine) and running


## One-time setup (permissions)

```bash
# 1. Add your user to the input group (read hotkeys)
sudo usermod -aG input $USER

# 2. udev rule for /dev/uinput (create the virtual keyboard)
sudo tee /etc/udev/rules.d/99-uinput.rules <<'EOF'
KERNEL=="uinput", GROUP="input", MODE="0660", OPTIONS+="static_node=uinput"
EOF

# 3. Load the uinput module (now and on every boot)
sudo modprobe uinput
echo uinput | sudo tee /etc/modules-load.d/uinput.conf

# 4. Reload the rules
sudo udevadm control --reload-rules && sudo udevadm trigger

# 5. Log in again so the group membership takes effect!
```

## Installation

```bash
uv sync
```

## Configuration (optional)

All tunables live in a `.env` file next to the project root:

```bash
cp .env.example .env
```

| Key | Default | Meaning |
| --- | --- | --- |
| `NOTIFICATIONS` | `true` | Desktop notifications on start/pause/quit |
| `AUTO_CONFIRM` | `true` | Auto-confirm the first answer option; `false` waits for you |
| `PLAYING_ICON_COLOR` | `236,229,216` | RGB of the dialogue autoplay icon |
| `COLOR_TOLERANCE` | `10` | Allowed per-channel color deviation |
| `PATCH_RADIUS` | `3` | Half-size of the pixel box sampled per checkpoint (3 → 7x7) |
| `MATCH_FRACTION` | `0.34` | Fraction of the box that must match for a checkpoint to trigger |
| `CHECKPOINT_*` | see `.env.example` | Checkpoint coordinates in 1080p reference space |

Every key is optional. Environment variables with the same names override
the file. Invalid values abort startup with a message naming the key.

## Usage

1. Start Genshin (windowed/borderless/fullscreen, 16:9 only for now).
2. **First run - calibration** (once, and again after Genshin updates that
   change the UI):
   - Bring the game into a dialogue scene (talk to an NPC).
   - `uv run python -m genshin_autoskip.calibrate`
   - Check the output: `playing_icon` must show `[OK]` while the dialogue
     is running. `calibration.png` marks the checkpoints with red circles.
   - Repeat with answer options visible: one of the `dialogue_icon_*`
     checkpoints must show `[OK]`.
   - If the colors are off, adjust `PLAYING_ICON_COLOR` / `CHECKPOINT_*`
     in your `.env` file (see Configuration above).
3. **Test run without key presses:**
   `uv run genshin-autoskip --dry-run` → press F8, start a dialogue,
   the terminal must log "Would now: …".
4. **Live:** `uv run genshin-autoskip`
   - `F8` start, `F9` pause, `F12` quit.

## Notes

- Pixel bots formally violate the HoYoverse ToS - use at your own risk.
  The tool only reads screen pixels and sends key presses; it never touches
  game memory or game files.
- Roughly every 30 s there is a 4% chance of a "human-like break" (3-8 s) -
  intentional, not a bug.
- The tool only presses keys while the dialogue autoplay icon is visible;
  loading screens are guarded by a checkpoint pixel.

## TODO
- Test/include native Wayland support for Genshin running with PROTON_WAYLAND enabled. 
- Support for ultrawide resolutions. 

## Development

```bash
uv run pytest          # unit tests (run without the game/X/uinput)
```

## License
This project is licensed under the terms specified in the [LICENSE](LICENSE) file.
