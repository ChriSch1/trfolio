"""
theme.py - Theme Definitions & Active Theme Resolver

Two themes:
  - neon   : Vibrant neon-on-dark (original TRFolio look)
  - minimal: Professional blue-gray dark, Bloomberg-inspired

Usage:
    from src.dashboard.theme import get_active_theme
    THEME = get_active_theme()
"""
import streamlit as st
from typing import Literal

ThemeName = Literal["neon", "minimal"]

# ---------------------------------------------------------------------------
# Theme: Neon Dark (original)
# ---------------------------------------------------------------------------

THEME_NEON: dict = {
    # Surfaces
    "bg_dark":          "#0d0d1a",
    "bg_card":          "#12122a",
    "bg_sidebar":       "#0a0a18",
    # Accent (primary) & glow
    "primary":          "#6366f1",
    "primary_light":    "rgba(99,102,241,0.15)",
    "primary_alpha":    "rgba(99,102,241,0.25)",
    "accent":           "#6366f1",
    "accent_alpha":     "rgba(99,102,241,0.20)",
    "glow":             "rgba(99,102,241,0.35)",
    "shadow_card":      "0 0 18px rgba(99,102,241,0.25)",
    # Semantic
    "success":          "#10b981",
    "success_alpha":    "rgba(16,185,129,0.25)",
    "danger":           "#ef4444",
    "danger_alpha":     "rgba(239,68,68,0.25)",
    "warning":          "#f59e0b",
    # Waterfall fills
    "wf_gain":          "#1e7a52",
    "wf_loss":          "#9b2c2c",
    "wf_total":         "#3d5a78",
    # Text
    "text_primary":     "#e2e8f0",
    "text_secondary":   "#94a3b8",
    "text_muted":       "#475569",
    # Borders
    "border":           "rgba(99,102,241,0.2)",
    "border_strong":    "rgba(99,102,241,0.45)",
    # Chart
    "chart_bg":         "rgba(0,0,0,0)",
    "chart_grid":       "rgba(99,102,241,0.12)",
    # Decorative palette
    "palette": [
        "#5a5fcf",
        "#7c3aed",
        "#2563eb",
        "#0891b2",
        "#059669",
    ],
    "palette_alpha": [
        "rgba(90,95,207,0.55)",
        "rgba(124,58,237,0.55)",
        "rgba(37,99,235,0.55)",
        "rgba(8,145,178,0.55)",
        "rgba(5,150,105,0.55)",
    ],
}

# ---------------------------------------------------------------------------
# Theme: Minimal Dark  -  Bloomberg-inspired professional dark
# ---------------------------------------------------------------------------

THEME_MINIMAL: dict = {
    # Surfaces
    "bg_dark":          "#0f1117",
    "bg_card":          "#161b27",
    "bg_sidebar":       "#0c0e14",
    # Primary (interactive)
    "primary":          "#7aa2f7",
    "primary_light":    "rgba(122,162,247,0.10)",
    "primary_alpha":    "rgba(122,162,247,0.18)",
    # Accent - warm amber for KPI stripes & progress bars
    "accent":           "#c9a96e",
    "accent_alpha":     "rgba(201,169,110,0.18)",
    "glow":             "rgba(0,0,0,0)",
    "shadow_card":      "0 1px 3px rgba(0,0,0,0.40)",
    # Semantic
    "success":          "#4ade80",
    "success_alpha":    "rgba(74,222,128,0.18)",
    "danger":           "#f87171",
    "danger_alpha":     "rgba(248,113,113,0.18)",
    "warning":          "#facc15",
    # Waterfall fills
    "wf_gain":          "#2d6a4f",
    "wf_loss":          "#7a2c2c",
    "wf_total":         "#4a6080",
    # Text
    "text_primary":     "#dde3ed",
    "text_secondary":   "#7c8899",
    "text_muted":       "#3d4554",
    # Borders
    "border":           "rgba(255,255,255,0.07)",
    "border_strong":    "rgba(255,255,255,0.13)",
    # Chart
    "chart_bg":         "rgba(0,0,0,0)",
    "chart_grid":       "rgba(255,255,255,0.05)",
    # Decorative palette
    "palette": [
        "#4e7fcc",
        "#c4705a",
        "#5a9e7c",
        "#8b6fbf",
        "#b8924a",
    ],
    "palette_alpha": [
        "rgba(78,127,204,0.22)",
        "rgba(196,112,90,0.22)",
        "rgba(90,158,124,0.22)",
        "rgba(139,111,191,0.22)",
        "rgba(184,146,74,0.22)",
    ],
}

# ---------------------------------------------------------------------------
# Session-state helpers
# ---------------------------------------------------------------------------

_SESSION_KEY   = "trfolio_theme"
_DEFAULT_THEME: ThemeName = "minimal"


def get_active_theme() -> dict:
    """Return the currently selected theme dict.

    Reads ``st.session_state[_SESSION_KEY]``.  Falls back to neon on first load.
    """
    name: ThemeName = st.session_state.get(_SESSION_KEY, _DEFAULT_THEME)
    return THEME_NEON if name == "neon" else THEME_MINIMAL


def set_theme(name: ThemeName) -> None:
    """Persist a theme choice to session state."""
    st.session_state[_SESSION_KEY] = name


def get_theme_name() -> ThemeName:
    """Return the name of the currently active theme."""
    return st.session_state.get(_SESSION_KEY, _DEFAULT_THEME)


def is_minimal() -> bool:
    """Convenience check - True when the minimal theme is active."""
    return get_theme_name() == "minimal"
