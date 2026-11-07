# Wizard Duel

A simple 2D local two-player fighting game built with Pygame. Two wizards face
off in a castle arena using melee attacks, blocks and spells — first to win
**2 rounds** (best of 3) takes the match.

> The wizard artwork follows the team's Claude Design canvas (see
> [`design/`](design/)) and is drawn with Pygame shapes, so no image files are needed.

## Requirements

- Python 3.9+
- [pygame](https://pypi.org/project/pygame/) (or [pygame-ce](https://pypi.org/project/pygame-ce/))

## Getting started

```bash
git clone https://github.com/KaabaCarter/Software-Engineering.git
cd Software-Engineering

python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install pygame

python wizard_duel.py
```

## How to play

1. From the main menu press **Enter** to play (or **C** to view controls).
2. On the character select screen each player picks a wizard and confirms
   with their attack key. The match starts once both players are ready.
3. Reduce your opponent's health to 0 to win the round. Win 2 rounds to win
   the match, then press **Enter** for a rematch or **M** for the menu.

## Controls

| Action      | Player 1 | Player 2    |
|-------------|----------|-------------|
| Move        | A / D    | ← / →       |
| Jump        | W        | ↑           |
| Block       | S        | ↓           |
| Attack      | F        | `,`         |
| Stun Bolt   | G        | `.`         |
| Signature spell | H    | `/`         |

Keys are set by their **position** on the keyboard, not by letter, so the
controls sit in the same place on any layout. The table shows a US (QWERTY)
keyboard; on a French AZERTY keyboard Player 1 uses **Z Q S D** + F G H and
Player 2 uses the arrows + **; : =** (Mac) or **; : !** (Windows). The game shows
the right letters for your keyboard on the Controls screen and in the key bar.

During a fight, a **key bar** along the bottom of the screen shows each
player's keys. Keys light up while held, and Strike, Stun and Fire fill up as
they recharge and glow when ready. Press **Tab** to hide or show it.

**Esc** pauses the match; while paused, **Q** quits to the menu.

## Sound

Spells, hits, blocks, knockouts, round wins and menus all have sound effects,
with a quiet music-box tune in the background. Every sound is generated in
code (`sound.py`), so there are no audio files. Press **V** on the main menu
or pause menu to turn sound on or off; the choice is remembered. On a
computer without an audio device the game simply plays silently.

## Night and Day

Press **L** on the main menu or in the pause menu to switch between **Night**
(a candlelit hall) and **Day** (the same hall in sunlight, with light panels).
The game remembers your choice in `settings.json` (not committed to git).

## Wizards

| Wizard  | Colors          | Speed | Spell power | Health |
|---------|-----------------|-------|-------------|--------|
| Ember   | Scarlet & gold  | 6     | ×1.0        | 100    |
| Sage    | Emerald & silver| 5     | ×1.25       | 100    |
| Quill   | Sapphire & bronze | 5.5   | ×1.1        | 100    |
| Bramble | Gold & black    | 4.5   | ×1.1        | 120    |

On the character select screen, use your left/right keys to browse wizards.

## Combat

| Move                  | Who      | Damage    | Cooldown | Effect |
|-----------------------|----------|-----------|----------|--------|
| Wand strike           | Everyone | 6         | 0.5 s    | Close range |
| Stun Bolt             | Everyone | 8         | 0.75 s   | Fast bolt |
| Fire Blast            | Ember    | 16        | 2 s      | Big, slow fireball |
| Vine Snare            | Sage     | 11        | 2.5 s    | Halves the target's speed for 1.5 s (not if blocked) |
| Arcane Volley         | Quill    | 3 × 5     | 2 s      | Three quick bolts in a spread |
| Shockwave             | Bramble  | 13        | 2.5 s    | Rolls along the floor; jump over it to dodge |

Every wizard has Stun Bolt plus their own **signature spell** on the second
spell key. All spell numbers are in `STUN_BOLT` and `SIGNATURE_SPELLS` at the
top of `wizard_duel.py`.

- Spell damage is multiplied by the wizard's spell power.
- Blocking reduces incoming damage to 25%, but you can't move or attack while
  blocking (and can only block on the ground).
- Spell recharge is shown on the Stun and signature-spell keys in the key bar.
- The amber strip on a health bar shows the damage just taken.
- If both wizards hit 0 health at the same time it's a Double KO and no one
  scores the round.

## Tweaking the game

All colors live in `THEMES` (one set for Night, one for Day) at the top of `scene_art.py` (wizard colors are
in `LOOKS` in `wizard_art.py`). All gameplay values live at the top of `wizard_duel.py`: screen size, gravity,
jump speed, rounds to win, health, damage, block reduction, and the
`WIZARDS`, `SPELLS` and `CONTROLS` tables.

To add a wizard:
1. Add a look to `LOOKS` in `wizard_art.py` (palette plus hat, hair and
   optional beard shapes, in the 50 × 100 hitbox coordinates).
2. Add an entry to `WIZARDS` in `wizard_duel.py` pointing at that look, with
   its `speed`, `power`, optional `health`, and a `signature` spell from
   `SIGNATURE_SPELLS` (or add a new one there).

## Project files

| Path | What it is |
|------|------------|
| `wizard_duel.py` | The game: settings, fighters, rounds, menus |
| `wizard_art.py` | Wizard artwork and poses (idle, walk, jump, block, strike, cast, hit, KO) |
| `sound.py` | Sound effects and music, generated from simple waveforms |
| `scene_art.py` | Color theme, castle hall, candles, spells, particles, keycaps and buttons |
| `design/` | Source of the Claude Design canvas (screens, style guide, pitch deck) |

## Authors

- Ani Washington
- Kaaba Carter
- Youmbo Fatima Ane
