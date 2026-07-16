# Genshin Dialogue Autoskip (Linux)

Dialog-Autoskipper für Genshin Impact unter Wine/Lutris (XWayland).
Linux-Port von [1hubert/genshin-dialogue-autoskip](https://github.com/1hubert/genshin-dialogue-autoskip).

Liest Prüfpixel direkt aus dem Genshin-Fenster (X11) und drückt die
Interaktionstaste (F) über eine virtuelle uinput-Tastatur. Bei
Antwortoptionen wird automatisch die erste Option bestätigt.

## Einmaliges Setup (Berechtigungen)

```bash
# 1. User in die input-Gruppe (Hotkeys lesen)
sudo usermod -aG input $USER

# 2. udev-Regel für /dev/uinput (virtuelle Tastatur erstellen)
sudo tee /etc/udev/rules.d/99-uinput.rules <<'EOF'
KERNEL=="uinput", GROUP="input", MODE="0660", OPTIONS+="static_node=uinput"
EOF

# 3. uinput-Modul laden (jetzt und bei jedem Boot)
sudo modprobe uinput
echo uinput | sudo tee /etc/modules-load.d/uinput.conf

# 4. Regeln neu laden
sudo udevadm control --reload-rules && sudo udevadm trigger

# 5. Neu einloggen, damit die Gruppenmitgliedschaft greift!
```

## Installation

```bash
uv sync
```

## Nutzung

1. Genshin starten (Fenster- oder Borderless-Modus, 16:9).
2. **Erstinbetriebnahme — Kalibrierung** (einmalig, und nach
   Genshin-Updates mit UI-Änderungen):
   - Spiel in eine Dialogszene bringen (NPC ansprechen).
   - `uv run python -m genshin_autoskip.calibrate`
   - Ausgabe prüfen: `playing_icon` muss `[OK]` sein, solange der Dialog
     läuft. `calibration.png` zeigt die Prüfpunkte als rote Kreise.
   - Danach mit sichtbaren Antwortoptionen wiederholen: `dialogue_icon_*`
     muss `[OK]` zeigen.
   - Weichen Farben ab: Werte in `genshin_autoskip/detector.py`
     (`PLAYING_ICON_COLOR`, `CHECKPOINTS`) anpassen.
3. **Probelauf ohne Tastendrücke:**
   `uv run genshin-autoskip --dry-run` → F8 drücken, Dialog starten,
   Terminal muss „Würde jetzt: …" loggen.
4. **Scharf:** `uv run genshin-autoskip`
   - `F8` Start, `F9` Pause, `F12` Beenden.

## Hinweise

- Pixel-Bots verstoßen formal gegen die HoYoverse-ToS — Nutzung auf
  eigenes Risiko. Das Tool liest nur Bildschirm-Pixel und sendet
  Tastendrücke; es greift weder auf Spielspeicher noch -dateien zu.
- Alle ~30 s besteht eine 4-%-Chance auf eine „Menschenpause" (3–8 s) —
  gewollt, kein Bug.
- Das Tool drückt nur, wenn das Dialog-Autoplay-Icon sichtbar ist;
  Ladebildschirme sind per Prüfpixel abgesichert.

## Entwicklung

```bash
uv run pytest          # Unit-Tests (laufen ohne Spiel/X/uinput)
```
