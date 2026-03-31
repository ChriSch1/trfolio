"""
sidebar.py - Sidebar Navigation, Filters & Theme Toggle

Renders:
  - Theme selector (Neon / Minimal Dark)
  - Year filter
"""
import streamlit as st
import pandas as pd

from src.dashboard.theme import get_active_theme, get_theme_name, set_theme


def render_sidebar(df: pd.DataFrame) -> str:
    """
    Render sidebar with theme toggle and year filter.

    Returns:
        selected_year (str): Year as string or "All Time"
    """
    THEME = get_active_theme()

    # ------------------------------------------------------------------ #
    # Sidebar base styling                                                 #
    # ------------------------------------------------------------------ #
    st.sidebar.markdown(
        f"""
        <style>
        [data-testid="stSidebar"] {{
            background-color: {THEME['bg_sidebar']};
            border-right: 1px solid {THEME['border']};
        }}
        div[data-testid="stSidebar"] .stRadio > label {{
            font-size: 0.78rem;
            color: {THEME['text_secondary']};
        }}
        div[data-testid="stSidebar"] .stRadio [data-testid="stMarkdownContainer"] p {{
            font-size: 0.78rem;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ------------------------------------------------------------------ #
    # Theme selector                                                       #
    # ------------------------------------------------------------------ #
    st.sidebar.markdown(
        f"<div style='color:{THEME['text_muted']};font-size:0.7rem;"
        f"letter-spacing:0.08em;text-transform:uppercase;"
        f"margin-bottom:4px;'>Appearance</div>",
        unsafe_allow_html=True,
    )

    theme_options = {
        "\u2746 Neon":         "neon",
        "\u25cc Minimal Dark": "minimal",
    }
    current_label = {
        "neon":    "\u2746 Neon",
        "minimal": "\u25cc Minimal Dark",
    }[get_theme_name()]

    selected_label = st.sidebar.radio(
        label="Theme",
        options=list(theme_options.keys()),
        index=list(theme_options.keys()).index(current_label),
        label_visibility="collapsed",
        key="_theme_radio",
    )
    new_theme = theme_options[selected_label]
    if new_theme != get_theme_name():
        set_theme(new_theme)
        st.rerun()

    st.sidebar.markdown(
        f"<hr style='border:none;border-top:1px solid {THEME['border']};"
        f"margin:12px 0;'>",
        unsafe_allow_html=True,
    )

    # ------------------------------------------------------------------ #
    # Year filter                                                          #
    # ------------------------------------------------------------------ #
    st.sidebar.markdown(
        f"<div style='color:{THEME['text_muted']};font-size:0.7rem;"
        f"letter-spacing:0.08em;text-transform:uppercase;"
        f"margin-bottom:4px;'>Filters</div>",
        unsafe_allow_html=True,
    )

    available_years = sorted(df["date"].dt.year.unique().tolist())
    selected_year = st.sidebar.selectbox(
        "\U0001f4c5 Select Year",
        options=available_years + ["All Time"],
        index=len(available_years),
    )

    return selected_year
