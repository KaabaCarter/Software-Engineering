"""
Wizard Duel - sound effects and music, generated in code (no audio files).

Every sound is built from simple waveforms when the game starts. If the
computer has no audio device, sound is silently turned off.
"""
import array
import math
import random
import threading
import pygame

RATE = 22050
enabled = True       # the player's on/off choice
available = False    # whether the mixer started
SOUNDS = {}
VOLUMES = {}
music = None
music_channel = None
_music_samples = None      # filled by a background thread, turned into a Sound by poll()


def init_mixer():
    """Call before pygame.init() so the mixer uses our format."""
    pygame.mixer.pre_init(RATE, -16, 1, 512)


def _env(i, n, attack=0.005, release=None):
    """Envelope: short fade-in, then exponential decay (or linear release)."""
    t = i / RATE
    a = min(1.0, t / attack) if attack else 1.0
    if release is None:
        return a
    return a * math.exp(-t / release)


def _make(samples, volume=1.0):
    peak = max(1e-6, max(abs(s) for s in samples))
    scale = 32000 * volume / max(1.0, peak)
    data = array.array("h", (int(s * scale) for s in samples))
    channels = pygame.mixer.get_init()[2]
    if channels == 2:                       # some systems force stereo
        stereo = array.array("h")
        for s in data:
            stereo.append(s)
            stereo.append(s)
        data = stereo
    return pygame.mixer.Sound(buffer=data.tobytes())


def _tone(freq_start, freq_end, dur, decay, harmonics=(1.0,), noise=0.0):
    n = int(RATE * dur)
    out, phase = [], 0.0
    for i in range(n):
        f = freq_start + (freq_end - freq_start) * i / n
        phase += 2 * math.pi * f / RATE
        s = sum(h * math.sin(phase * (k + 1)) for k, h in enumerate(harmonics))
        if noise:
            s += noise * random.uniform(-1, 1)
        out.append(s * _env(i, n, release=decay))
    return out


def _noise(dur, decay, smooth=0.5, sweep=None):
    """Filtered noise. smooth near 1 = darker (more low-pass)."""
    n = int(RATE * dur)
    out, y = [], 0.0
    for i in range(n):
        k = smooth if sweep is None else smooth + (sweep - smooth) * i / n
        y = k * y + (1 - k) * random.uniform(-1, 1)
        out.append(y * _env(i, n, attack=0.01, release=decay))
    return out


def _mix(*parts):
    n = max(len(p) for p in parts)
    return [sum(p[i] for p in parts if i < len(p)) for i in range(n)]


def _seq(notes, gap):
    """Play tones one after another, `gap` seconds apart (they may overlap)."""
    out = []
    for k, part in enumerate(notes):
        start = int(k * gap * RATE)
        if len(out) < start + len(part):
            out.extend([0.0] * (start + len(part) - len(out)))
        for i, s in enumerate(part):
            out[start + i] += s
    return out


def _note(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def _pluck(freq, dur, decay=0.35):
    """Music-box style note: a sine with a bright overtone that fades fast."""
    n = int(RATE * dur)
    out = []
    for i in range(n):
        t = i / RATE
        s = math.sin(2 * math.pi * freq * t) + 0.35 * math.sin(2 * math.pi * freq * 3 * t) * math.exp(-t / 0.08)
        out.append(s * _env(i, n, attack=0.003, release=decay))
    return out


def _build_music():
    """A gentle 8-bar loop in A minor: music-box arpeggios over soft bass notes."""
    beat = 60 / 96 / 2                       # eighth notes at 96 bpm
    chords = [(57, 60, 64), (53, 57, 60), (48, 52, 55), (52, 56, 59),   # Am F C E
              (57, 60, 64), (50, 53, 57), (52, 56, 59), (57, 60, 64)]   # Am Dm E Am
    pattern = [0, 1, 2, 1, 2, 1]             # 3/4 time, six eighths per bar
    length = int(len(chords) * len(pattern) * beat * RATE)
    out = [0.0] * length
    for bar, chord in enumerate(chords):
        for step, idx in enumerate(pattern):
            start = int((bar * len(pattern) + step) * beat * RATE)
            note = _pluck(_note(chord[idx] + 12), 0.9, decay=0.3)
            for i, s in enumerate(note):
                out[(start + i) % length] += 0.5 * s
        start = int(bar * len(pattern) * beat * RATE)
        bass = _pluck(_note(chord[0] - 12), 1.6, decay=0.7)
        for i, s in enumerate(bass):
            out[(start + i) % length] += 0.6 * s
    return out


def _build_sounds():
    s = {}
    s["swing"] = _noise(0.16, 0.05, smooth=0.2, sweep=0.85)
    s["hit"] = _mix(_tone(160, 55, 0.22, 0.06, (1.0, 0.3)), _noise(0.06, 0.02, smooth=0.3))
    s["block"] = _tone(1250, 1250, 0.35, 0.09, (1.0, 0.0, 0.4, 0.0, 0.2))
    s["stun"] = _tone(700, 1700, 0.14, 0.06, (1.0, 0.25))
    s["fire"] = _mix(_noise(0.45, 0.16, smooth=0.6, sweep=0.92), _tone(110, 70, 0.4, 0.15))
    s["vines"] = _mix(_noise(0.35, 0.12, smooth=0.75),
                      _seq([_pluck(_note(n), 0.25, 0.08) for n in (62, 65)], 0.07))
    s["volley"] = _seq([_tone(1100 + 150 * k, 1500 + 150 * k, 0.07, 0.03, (1.0, 0.2)) for k in range(3)], 0.06)
    s["quake"] = _mix(_tone(70, 45, 0.6, 0.25, (1.0, 0.5, 0.25)), _noise(0.6, 0.2, smooth=0.93))
    s["ko"] = _tone(520, 130, 0.6, 0.25, (1.0, 0.3))
    s["round_win"] = _seq([_pluck(_note(n), 0.8, 0.3) for n in (72, 76, 79)], 0.12)
    s["victory"] = _seq([_pluck(_note(n), 1.0, 0.4) for n in (67, 72, 76, 79, 84)], 0.13)
    s["click"] = _tone(900, 700, 0.05, 0.02)
    s["confirm"] = _seq([_pluck(_note(n), 0.3, 0.12) for n in (76, 83)], 0.08)
    s["pause"] = _tone(600, 450, 0.12, 0.05)
    return s


# How loud each sound plays (0..1), so frequent sounds stay in the background
LEVELS = {"swing": 0.35, "hit": 0.6, "block": 0.45, "stun": 0.4, "fire": 0.6, "vines": 0.5,
          "volley": 0.4, "quake": 0.7, "ko": 0.6, "round_win": 0.6, "victory": 0.7,
          "click": 0.35, "confirm": 0.5, "pause": 0.4}
MUSIC_LEVEL = 0.25


def load():
    """Create all sounds. Safe to call when there is no audio device."""
    global available, music, music_channel
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(RATE, -16, 1, 512)
        pygame.mixer.set_num_channels(16)
        for name, samples in _build_sounds().items():
            SOUNDS[name] = _make(samples)
            SOUNDS[name].set_volume(LEVELS.get(name, 0.5))
        music_channel = pygame.mixer.Channel(0)
        pygame.mixer.set_reserved(1)             # keep channel 0 for the music
        available = True
        threading.Thread(target=_compose, daemon=True).start()   # music takes ~1 s to build
    except (pygame.error, NotImplementedError):
        available = False


def _compose():
    global _music_samples
    _music_samples = _build_music()


def poll():
    """Call once per frame: starts the music as soon as it has been built."""
    global music, _music_samples
    if available and music is None and _music_samples is not None:
        music = _make(_music_samples, 0.8)
        music.set_volume(MUSIC_LEVEL)
        _music_samples = None
        start_music()


def play(name):
    if enabled and available and name in SOUNDS:
        SOUNDS[name].play()


def start_music():
    if enabled and available and music and not music_channel.get_busy():
        music_channel.play(music, loops=-1)


def set_enabled(on):
    global enabled
    enabled = on
    if not available:
        return
    if on:
        start_music()
    else:
        pygame.mixer.stop()
