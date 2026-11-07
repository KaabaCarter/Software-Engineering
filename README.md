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
| Fire Blast  | H        | `/`         |

**Esc** pauses the match; while paused, **Q** quits to the menu.

## Wizards

| Wizard  | Colors          | Speed | Spell power | Health |
|---------|-----------------|-------|-------------|--------|
| Ember   | Scarlet & gold  | 6     | ×1.0        | 100    |
| Sage    | Emerald & silver| 5     | ×1.25       | 100    |
| Quill   | Blue & bronze   | 5.5   | ×1.1        | 100    |
| Bramble | Yellow & black  | 4.5   | ×1.1        | 120    |

On the character select screen, use your left/right keys to browse wizards.

## Combat

| Move       | Damage | Cooldown |
|------------|--------|----------|
| Attack     | 6      | 0.5 s    |
| Stun Bolt  | 8      | 0.75 s   |
| Fire Blast | 15     | 2.5 s    |

- Spell damage is multiplied by the wizard's spell power.
- Blocking reduces incoming damage to 25%, but you can't move or attack while
  blocking (and can only block on the ground).
- Spell cooldowns are shown as colored bars under each health bar.
- If both wizards hit 0 health at the same time it's a Double KO and no one
  scores the round.

## Tweaking the game

All tuning values live at the top of `wizard_duel.py`: screen size, gravity,
jump speed, rounds to win, health, damage, block reduction, and the
`WIZARDS`, `SPELLS` and `CONTROLS` tables.

To add a wizard:
1. Add a look to `LOOKS` in `wizard_art.py` (palette plus hat, hair and
   optional beard shapes, in the 50 × 100 hitbox coordinates).
2. Add an entry to `WIZARDS` in `wizard_duel.py` pointing at that look, with
   its `speed`, `power` and optional `health`.

## Project files

| Path | What it is |
|------|------------|
| `wizard_duel.py` | The game: settings, fighters, rounds, menus |
| `wizard_art.py` | Wizard artwork and poses (idle, walk, jump, block, strike, cast, hit, KO) |
| `design/` | Source of the Claude Design canvas (screens, style guide, pitch deck) |

## Authors

- Ani Washington
- Kaaba Carter
- Youmbo Fatima Ane
