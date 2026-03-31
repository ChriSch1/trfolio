"""
components/etf_deep_dive.py - ETF Strategy & Savings Tab
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.dashboard.theme import get_active_theme, is_minimal
from src.dashboard.calculations import calculate_etf_returns

_PNL_SCALE = [
    [0,   "rgba(185, 28, 28,  0.55)"],
    [0.5, "rgba(71,  85, 105, 0.30)"],
    [1,   "rgba(22, 163, 74,  0.55)"],
]


def _subtab_css(THEME: dict) -> str:
    if is_minimal():
        ab = THEME["accent"]; ac = THEME["accent"]; bg = THEME["bg_card"]
        hov = "rgba(255,255,255,0.04)"; inact = THEME["text_secondary"]
    else:
        ab = THEME["primary"]; ac = THEME["primary"]; bg = THEME["primary_alpha"]
        hov = THEME["primary_light"]; inact = THEME["text_secondary"]
    return f"""
    <style>
    .stTabs [data-baseweb="tab-list"] {{
        gap:0;border-bottom:1px solid {THEME['border']};padding-bottom:0;margin-bottom:16px;
    }}
    .stTabs [data-baseweb="tab"] {{
        background:transparent;border:none;border-bottom:2px solid transparent;
        border-radius:0;padding:8px 20px;font-size:12px;font-weight:500;
        letter-spacing:0.06em;text-transform:uppercase;color:{inact};
        transition:color .2s,border-color .2s,background .2s;
    }}
    .stTabs [data-baseweb="tab"]:hover {{
        background:{hov};color:{ac};border-bottom-color:{ab};
    }}
    .stTabs [aria-selected="true"] {{
        background:{bg}!important;border-bottom:2px solid {ab}!important;
        color:{ac}!important;box-shadow:none!important;
    }}
    </style>"""


def _kpi(THEME: dict, label: str, value: str, color: str | None = None,
        margin_bottom: str = "12px") -> str:
    c      = color or THEME["text_primary"]
    shadow = f"0 0 14px {THEME['glow']}" if not is_minimal() else THEME["shadow_card"]
    stripe = f"border-left:3px solid {THEME['accent']};border-radius:0 8px 8px 0;" if is_minimal() else "border-radius:8px;"
    return (
        f'<div style="background:{THEME["bg_card"]};padding:12px 14px;{stripe}'
        f'border:1px solid {THEME["border"]};box-shadow:{shadow};margin-bottom:{margin_bottom};">'
        f'<div style="color:{THEME["text_secondary"]};font-size:10px;text-transform:uppercase;'
        f'letter-spacing:0.07em;margin-bottom:5px;">{label}</div>'
        f'<div style="color:{c};font-size:20px;font-weight:700;">{value}</div></div>'
    )


def _chart_layout(THEME: dict, height: int, margin: dict) -> dict:
    return dict(
        height=height, margin=margin,
        paper_bgcolor=THEME["chart_bg"], plot_bgcolor=THEME["chart_bg"],
        font=dict(size=11, color=THEME["text_secondary"], family="Inter, sans-serif"),
    )


def render_etf_deep_dive(etf_holdings: pd.DataFrame, transactions: pd.DataFrame) -> None:
    THEME = get_active_theme()
    st.markdown(_subtab_css(THEME), unsafe_allow_html=True)

    if etf_holdings.empty:
        st.warning("No ETF holdings available.")
        return

    etf_ret = calculate_etf_returns(etf_holdings)
    returns_mapped = {
        "value":            etf_ret["value"],
        "invested_current": etf_ret["invested"],
        "unrealized":       etf_ret["unrealized"],
        "unrealized_pct":   etf_ret["unrealized_pct"],
        "total_return_pct": etf_ret["unrealized_pct"],
    }

    tab_overview, tab_holdings, tab_savings = st.tabs(["Summary", "ETFs", "Savings Plan Log"])

    with tab_overview:
        st.caption("Strategy Check")
        _render_overview(returns_mapped, etf_holdings, transactions)

    with tab_holdings:
        st.caption("Holdings")
        _render_holdings(etf_holdings)

    with tab_savings:
        st.caption("Savings Plan Log")
        _render_savings_log(transactions)


@st.fragment
def _render_allocation_chart(etf_holdings: pd.DataFrame):
    THEME = get_active_theme()
    h1, h2 = st.columns([1, 1])
    with h1:
        st.subheader("Allocation")
    with h2:
        chart_type = st.radio(
            "Chart Type", ["Pie", "Treemap"], horizontal=True,
            label_visibility="collapsed", key="etf_allocation_toggle",
        )

    n      = len(etf_holdings)
    p      = THEME["palette"]
    colors = [p[i % len(p)] for i in range(n)]

    if chart_type == "Treemap":
        fig = px.treemap(
            etf_holdings, path=[px.Constant("ETF Portfolio"), "name"],
            values="market_value", color="name", color_discrete_sequence=colors,
        )
        fig.update_traces(
            marker=dict(cornerradius=3, line=dict(color=THEME["border"], width=1)),
            textinfo="label+percent entry",
            textfont=dict(color="white", size=12, weight="bold"),
        )
    else:
        fig = px.pie(
            etf_holdings, values="market_value", names="name",
            hole=0.65, color_discrete_sequence=colors,
        )
        fig.update_traces(
            textposition="outside", textinfo="percent+label",
            textfont=dict(color=THEME["text_primary"], size=10),
            marker=dict(line=dict(color=THEME["bg_card"], width=2)),
        )

    fig.update_layout(
        **_chart_layout(THEME, height=500, margin=dict(t=10, b=0, l=0, r=0)),
        showlegend=True,
        legend=dict(
            orientation="h", yanchor="bottom", y=-0.12,
            xanchor="center", x=0.5,
            font=dict(color=THEME["text_primary"], size=9),
        ),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _render_overview(etf_ret: dict, etf_holdings: pd.DataFrame, transactions: pd.DataFrame):
    THEME = get_active_theme()
    col_status, col_charts = st.columns([2, 3])

    with col_status:
        invested = etf_ret["invested_current"]
        current  = etf_ret["value"]
        max_val  = max(invested, current) * 1.2 if invested > 0 else 100

        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=current,
            domain={"x": [0, 1], "y": [0, 1]},
            title={"text": "Active Status", "font": {"size": 16, "color": THEME["text_secondary"]}},
            delta={"reference": invested,
                   "increasing": {"color": THEME["success"]},
                   "decreasing": {"color": THEME["danger"]}},
            gauge={
                "axis":      {"visible": False, "range": [0, max_val]},
                "bar":       {"color": "rgba(0,0,0,0)"},
                "bgcolor":   "rgba(0,0,0,0)",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, invested], "color": THEME["primary_alpha"]},
                    {"range": [invested, current], "color": THEME["success_alpha"]}
                    if current >= invested
                    else {"range": [current, invested], "color": THEME["danger_alpha"]},
                ],
                "threshold": {
                    "line":      {"color": THEME["text_primary"], "width": 3},
                    "thickness": 0.75, "value": current,
                },
            },
        ))
        fig_gauge.update_layout(
            **_chart_layout(THEME, height=280, margin=dict(l=20, r=20, t=40, b=0)),
        )
        st.plotly_chart(fig_gauge, use_container_width=True, config={"displayModeBar": False})

        st.markdown("<div style='margin:8px 0 4px'></div>", unsafe_allow_html=True)
        kpi_c1, kpi_c2 = st.columns(2)

        unrealized_color = THEME["success"] if etf_ret["unrealized"] >= 0 else THEME["danger"]

        with kpi_c1:
            st.markdown(_kpi(THEME, "Invested",        f"\u20ac{etf_ret['invested_current']:,.0f}"),                       unsafe_allow_html=True)
            st.markdown(_kpi(THEME, "P&L (Unrealized)",f"\u20ac{etf_ret['unrealized']:,.0f}", unrealized_color, "0"),     unsafe_allow_html=True)

        with kpi_c2:
            st.markdown(_kpi(THEME, "Value",   f"\u20ac{etf_ret['value']:,.0f}"),                                         unsafe_allow_html=True)
            st.markdown(_kpi(THEME, "Return",  f"{etf_ret['total_return_pct']:+.1f}%", unrealized_color, "0"),            unsafe_allow_html=True)

    with col_charts:
        _render_allocation_chart(etf_holdings)


def _render_holdings(etf_holdings: pd.DataFrame):
    THEME = get_active_theme()
    col_chart, _ = st.columns([2, 1])

    with col_chart:
        st.subheader("Performance Comparison")
        sorted_h  = etf_holdings.sort_values("unrealized_pnl_pct")
        bar_fills = [
            THEME["wf_gain"] if x >= 0 else THEME["wf_loss"]
            for x in sorted_h["unrealized_pnl_pct"]
        ]
        fig_bar = go.Figure(go.Bar(
            x=sorted_h["unrealized_pnl_pct"],
            y=sorted_h["name"],
            orientation="h",
            marker=dict(color=bar_fills, line=dict(width=0)),
            text=[f"{v:+.2f}%" for v in sorted_h["unrealized_pnl_pct"]],
            textposition="outside",
            textfont=dict(color=THEME["text_primary"], size=11, weight="bold"),
        ))
        fig_bar.update_layout(
            **_chart_layout(THEME, height=350, margin=dict(t=10, b=0, l=0, r=40)),
            showlegend=False,
            yaxis=dict(title="", color=THEME["text_primary"]),
            xaxis=dict(
                title="Return %", showgrid=True, gridcolor=THEME["chart_grid"],
                zeroline=True, zerolinecolor=THEME["border_strong"],
                color=THEME["text_secondary"], ticksuffix="%",
            ),
        )
        st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})

    st.markdown("---")

    display = etf_holdings.copy()
    total   = display["market_value"].sum()
    display["Weight"] = display["market_value"] / total * 100
    display = display[["name", "ticker", "current_shares", "total_cost",
                        "market_value", "Weight", "unrealized_pnl", "unrealized_pnl_pct"]]
    display.columns = ["ETF", "Symbol", "Shares", "Invested", "Value",
                        "Weight %", "P&L (\u20ac)", "Return %"]

    def _color(val):
        if isinstance(val, (int, float)):
            if val > 0: return f"color:{THEME['success']};font-weight:bold"
            if val < 0: return f"color:{THEME['danger']};font-weight:bold"
        return ""

    st.dataframe(
        display.style
        .format({"Shares": "{:.2f}", "Invested": "\u20ac{:,.0f}", "Value": "\u20ac{:,.0f}",
                 "Weight %": "{:.1f}%", "P&L (\u20ac)": "\u20ac{:,.0f}", "Return %": "{:+.2f}%"})
        .applymap(_color, subset=["P&L (\u20ac)", "Return %"])
        .bar(subset=["Weight %"], color=THEME["primary_alpha"], vmin=0, vmax=100),
        use_container_width=True, height=400, hide_index=True,
    )


def _render_savings_log(transactions: pd.DataFrame):
    st.subheader("Execution Log")
    mask_etf   = transactions["event_type"].isin(["etf_saving_plan"])
    cols       = ["date", "name", "shares", "price", "amount", "event_type"]
    avail_cols = [c for c in cols if c in transactions.columns]
    df_log     = transactions[mask_etf][avail_cols].sort_values("date", ascending=False)
    st.dataframe(df_log, use_container_width=True, height=500, hide_index=True)
