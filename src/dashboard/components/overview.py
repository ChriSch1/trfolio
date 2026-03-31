"""
components/overview.py - Overview Tab
Theme-aware (Neon / Minimal Dark)
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from src.dashboard.theme import get_active_theme, is_minimal
from src.dashboard.calculations import (
    calculate_stock_returns,
    calculate_crypto_returns,
)


# ---------------------------------------------------------------------------
# Shared CSS helpers
# ---------------------------------------------------------------------------

def _subtab_css(THEME: dict) -> str:
    """Elegant pill-style sub-tab CSS, theme-aware."""
    if is_minimal():
        active_bg   = THEME["bg_card"]
        active_border = THEME["accent"]
        active_color  = THEME["accent"]
        hover_bg    = "rgba(255,255,255,0.04)"
        inactive_color = THEME["text_secondary"]
    else:
        active_bg   = THEME["primary_alpha"]
        active_border = THEME["primary"]
        active_color  = THEME["primary"]
        hover_bg    = THEME["primary_light"]
        inactive_color = THEME["text_secondary"]
    return f"""
    <style>
    .stTabs [data-baseweb="tab-list"] {{
        gap: 0px;
        border-bottom: 1px solid {THEME['border']};
        padding-bottom: 0;
        margin-bottom: 16px;
    }}
    .stTabs [data-baseweb="tab"] {{
        background: transparent;
        border: none;
        border-bottom: 2px solid transparent;
        border-radius: 0;
        padding: 8px 20px;
        font-size: 12px;
        font-weight: 500;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: {inactive_color};
        transition: color 0.2s ease, border-color 0.2s ease, background 0.2s ease;
    }}
    .stTabs [data-baseweb="tab"]:hover {{
        background: {hover_bg};
        color: {active_color};
        border-bottom-color: {active_border};
    }}
    .stTabs [aria-selected="true"] {{
        background: {active_bg} !important;
        border-bottom: 2px solid {active_border} !important;
        color: {active_color} !important;
        box-shadow: none !important;
    }}
    </style>
    """


def _kpi_card(THEME: dict, label: str, value: str, sub: str,
             value_color: str | None = None,
             accent_override: str | None = None) -> str:
    """Unified KPI card. Minimal: left accent stripe. Neon: glow shadow."""
    v_color = value_color or THEME["text_primary"]
    if is_minimal():
        stripe = accent_override or THEME["accent"]
        border_left = f"border-left: 3px solid {stripe};"
        border_radius = "border-radius: 0 8px 8px 0;"
        shadow = THEME["shadow_card"]
    else:
        border_left = ""
        border_radius = "border-radius: 8px;"
        glow_color = accent_override or THEME["glow"]
        shadow = f"0 0 18px {glow_color}"
    return (
        f'<div style="background:{THEME["bg_card"]};'
        f'padding:16px 14px;'
        f'{border_radius}'
        f'border:1px solid {THEME["border"]};'
        f'{border_left}'
        f'box-shadow:{shadow};'
        f'min-height:88px;">'
        f'<div style="color:{THEME["text_secondary"]};font-size:10px;'
        f'text-transform:uppercase;letter-spacing:0.08em;margin-bottom:6px;">{label}</div>'
        f'<div style="color:{v_color};font-size:22px;'
        f'font-weight:700;letter-spacing:-0.02em;line-height:1.2;">{value}</div>'
        f'<div style="color:{THEME["text_muted"]};font-size:10px;margin-top:5px;">{sub}</div>'
        f'</div>'
    )


def _chart_layout(THEME: dict, height: int, margin: dict) -> dict:
    return dict(
        height=height,
        margin=margin,
        paper_bgcolor=THEME["chart_bg"],
        plot_bgcolor=THEME["chart_bg"],
        font=dict(size=11, color=THEME["text_secondary"], family="Inter, sans-serif"),
    )


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------

def render_overview(
    stocks_holdings: pd.DataFrame,
    crypto_holdings: pd.DataFrame,
    etf_holdings: pd.DataFrame,
    interest_data: pd.DataFrame,
    all_holdings: pd.DataFrame,
    transactions: pd.DataFrame,
    trades: pd.DataFrame,
) -> None:
    THEME = get_active_theme()

    total_invested_etf = transactions[
        transactions["event_type"] == "etf_saving_plan"
    ]["net_cash_flow"].abs().sum()

    total_dividends = transactions[
        transactions["event_type"] == "dividend"
    ]["net_cash_flow"].sum()

    total_interest   = interest_data["net_interest"].sum() if not interest_data.empty else 0
    total_income     = total_dividends + total_interest
    realized_gains   = trades["realized_gain"].sum() if not trades.empty else 0.0
    stock_returns    = calculate_stock_returns(all_holdings, trades)

    total_stocks_value = stocks_holdings["market_value"].sum() if not stocks_holdings.empty else 0
    total_crypto_value = crypto_holdings["market_value"].sum() if not crypto_holdings.empty else 0
    total_etf_value    = etf_holdings["market_value"].sum()    if not etf_holdings.empty    else 0
    total_portfolio_value = total_stocks_value + total_crypto_value + total_etf_value
    unrealized_gains      = all_holdings["unrealized_pnl"].sum() if not all_holdings.empty else 0

    crypto_invested = crypto_holdings["total_cost"].abs().sum() if not crypto_holdings.empty else 0
    total_invested  = stock_returns["invested_current"] + total_invested_etf + crypto_invested
    unrealized_pct  = (unrealized_gains / total_invested * 100) if total_invested > 0 else 0

    total_all_gains = (
        stock_returns["unrealized"] + realized_gains
        + (total_etf_value    - total_invested_etf)
        + (total_crypto_value - crypto_invested)
        + total_income
    )
    total_return_pct = (total_all_gains / total_invested * 100) if total_invested > 0 else 0

    if not transactions.empty:
        months_in_period = max(
            (transactions["date"].max() - transactions["date"].min()).days / 30.44, 1
        )
    else:
        months_in_period = 1

    monthly_dividends      = total_dividends / months_in_period
    monthly_interest       = total_interest  / months_in_period
    monthly_passive_income = monthly_dividends + monthly_interest
    monthly_realized       = realized_gains   / months_in_period
    total_monthly_income   = monthly_passive_income + monthly_realized

    # ---- KPI row -------------------------------------------------------- #
    unrealized_color   = THEME["success"] if unrealized_gains >= 0 else THEME["danger"]
    total_return_color = THEME["success"] if total_all_gains  >= 0 else THEME["danger"]

    col1, col2, col3, col4, col5 = st.columns(5)
    cards = [
        (col1, "Portfolio Value",  f"\u20ac{total_portfolio_value:,.0f}",
         f"Invested \u20ac{total_invested:,.0f}",          None,               None),
        (col2, "Unrealized P&L",   f"\u20ac{unrealized_gains:+,.0f}",
         f"{unrealized_pct:+.1f}%",                       unrealized_color,   THEME["palette"][0]),
        (col3, "Total Return",     f"{total_return_pct:+.1f}%",
         f"\u20ac{total_all_gains:+,.0f} all-time",        total_return_color, THEME["palette"][2]),
        (col4, "Monthly Income",   f"\u20ac{monthly_passive_income:,.0f}",
         f"Div \u20ac{monthly_dividends:.0f} \u00b7 Int \u20ac{monthly_interest:.0f}",
         None, THEME["palette"][3]),
        (col5, "Total Monthly",    f"\u20ac{total_monthly_income:,.0f}",
         f"Incl. trades \u20ac{monthly_realized:,.0f}",    None,               THEME["palette"][4]),
    ]
    for col, lbl, val, sub, v_color, accent in cards:
        with col:
            st.markdown(_kpi_card(THEME, lbl, val, sub, v_color, accent), unsafe_allow_html=True)

    st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)

    # ---- Main 2-column layout ------------------------------------------- #
    col_main, col_side = st.columns([1.8, 1])

    with col_main:
        st.markdown(
            f"<p style='font-size:11px;font-weight:600;color:{THEME['text_secondary']};"
            f"text-transform:uppercase;letter-spacing:0.08em;margin-bottom:6px;'>"
            f"Portfolio Composition</p>",
            unsafe_allow_html=True,
        )

        wf_data = [
            ("Invested",   total_invested,  "absolute"),
            ("Unrealized", unrealized_gains, "relative"),
            ("Realized",   realized_gains,   "relative"),
            ("Income",     total_income,     "relative"),
            ("Total",      0,                "total"),
        ]
        wf_labels = [
            f"\u20ac{abs(d[1]):,.0f}" if d[2] != "total" else f"\u20ac{total_portfolio_value:,.0f}"
            for d in wf_data
        ]
        wf_y_max = total_portfolio_value * 1.18 if total_portfolio_value > 0 else 1

        fig_wf = go.Figure()
        fig_wf.add_trace(go.Waterfall(
            x=[d[0] for d in wf_data],
            y=[d[1] for d in wf_data],
            measure=[d[2] for d in wf_data],
            text=wf_labels,
            textposition="outside",
            textfont=dict(size=10, color=THEME["text_secondary"]),
            increasing=dict(marker=dict(color=THEME["wf_gain"],  line=dict(width=0))),
            decreasing=dict(marker=dict(color=THEME["wf_loss"],  line=dict(width=0))),
            totals=dict(marker=dict(color=THEME["wf_total"],     line=dict(width=0))),
            connector=dict(line=dict(color=THEME["border"], width=1, dash="dot")),
            hovertemplate="<b>%{x}</b><br>\u20ac%{y:,.0f}<extra></extra>",
        ))
        fig_wf.update_layout(
            **_chart_layout(THEME, height=310, margin=dict(l=0, r=0, t=48, b=10)),
            showlegend=False,
            xaxis=dict(showgrid=False, title=None, color=THEME["text_secondary"]),
            yaxis=dict(
                showgrid=True, gridcolor=THEME["chart_grid"],
                title=None, zeroline=True, zerolinecolor=THEME["border"],
                color=THEME["text_secondary"], range=[0, wf_y_max],
            ),
            waterfallgap=0.25,
        )
        st.plotly_chart(fig_wf, use_container_width=True, config={"displayModeBar": False})

        # ---- Performance bars ---------------------------------------- #
        st.markdown(
            f"<p style='font-size:11px;font-weight:600;color:{THEME['text_secondary']};"
            f"text-transform:uppercase;letter-spacing:0.08em;margin-bottom:6px;'>"
            f"Performance by Asset Class</p>",
            unsafe_allow_html=True,
        )

        etf_return = (
            (total_etf_value - total_invested_etf) / total_invested_etf * 100
            if total_invested_etf > 0 else 0
        )
        crypto_ret = calculate_crypto_returns(crypto_holdings)

        perf_df = pd.DataFrame({
            "Asset":  ["Stocks", "ETFs", "Crypto"],
            "Return": [stock_returns["unrealized_pct"], etf_return, crypto_ret["unrealized_pct"]],
            "Value":  [total_stocks_value, total_etf_value, total_crypto_value],
        })
        perf_df = perf_df[perf_df["Value"] > 0]

        if not perf_df.empty:
            bar_fills = [
                THEME["wf_gain"] if r >= 0 else THEME["wf_loss"]
                for r in perf_df["Return"]
            ]
            fig_perf = go.Figure()
            fig_perf.add_trace(go.Bar(
                y=perf_df["Asset"],
                x=perf_df["Return"],
                orientation="h",
                marker=dict(color=bar_fills, line=dict(width=0)),
                text=[f"{r:+.1f}%" for r in perf_df["Return"]],
                textposition="auto",
                textfont=dict(size=11, color=THEME["text_primary"], weight="bold"),
                hovertemplate=(
                    "<b>%{y}</b><br>Return: %{x:+.1f}%<br>"
                    "Value: \u20ac%{customdata:,.0f}<extra></extra>"
                ),
                customdata=perf_df["Value"],
            ))
            fig_perf.update_layout(
                **_chart_layout(THEME, height=190, margin=dict(l=60, r=40, t=10, b=10)),
                showlegend=False,
                xaxis=dict(
                    showgrid=True, gridcolor=THEME["chart_grid"],
                    zeroline=True, zerolinecolor=THEME["border_strong"], zerolinewidth=1.5,
                    title=None, color=THEME["text_secondary"], ticksuffix="%",
                ),
                yaxis=dict(showgrid=False, title=None, color=THEME["text_primary"]),
            )
            st.plotly_chart(fig_perf, use_container_width=True, config={"displayModeBar": False})

    # ---- Side column ----------------------------------------------------- #
    with col_side:
        st.markdown(
            f"<p style='font-size:11px;font-weight:600;color:{THEME['text_secondary']};"
            f"text-transform:uppercase;letter-spacing:0.08em;margin-bottom:6px;'>"
            f"Allocation</p>",
            unsafe_allow_html=True,
        )

        alloc_df = pd.DataFrame({
            "Category": ["Stocks", "ETFs", "Crypto"],
            "Value":    [total_stocks_value, total_etf_value, total_crypto_value],
        })
        alloc_df = alloc_df[alloc_df["Value"] > 0].reset_index(drop=True)

        donut_fills = [
            {"Stocks": THEME["wf_total"],   "ETFs": THEME["palette"][1],
             "Crypto": THEME["palette"][2]}.get(cat, THEME["palette"][0])
            for cat in alloc_df["Category"]
        ]

        fig_donut = go.Figure()
        fig_donut.add_trace(go.Pie(
            labels=alloc_df["Category"],
            values=alloc_df["Value"],
            hole=0.68,
            marker=dict(colors=donut_fills, line=dict(color=THEME["bg_card"], width=3)),
            textinfo="percent",
            textposition="outside",
            textfont=dict(size=10, color=THEME["text_secondary"]),
            hovertemplate="<b>%{label}</b><br>\u20ac%{value:,.0f}<br>%{percent}<extra></extra>",
        ))
        fig_donut.update_layout(
            **_chart_layout(THEME, height=270, margin=dict(l=10, r=10, t=10, b=10)),
            showlegend=True,
            legend=dict(
                orientation="v", yanchor="middle", y=0.5,
                xanchor="left",  x=0,
                font=dict(size=10, color=THEME["text_primary"]),
            ),
        )
        st.plotly_chart(fig_donut, use_container_width=True, config={"displayModeBar": False})

        # ---- Top Holdings -------------------------------------------- #
        st.markdown(
            f"<p style='font-size:11px;font-weight:600;color:{THEME['text_secondary']};"
            f"text-transform:uppercase;letter-spacing:0.08em;margin:12px 0 6px;'>"
            f"Top Holdings</p>",
            unsafe_allow_html=True,
        )

        if not stocks_holdings.empty and total_stocks_value > 0:
            top_h = (
                stocks_holdings
                .nlargest(5, "market_value")[["ticker", "market_value"]]
                .rename(columns={"ticker": "Symbol", "market_value": "Value"})
                .copy()
            )
            top_h["Pct"]   = (top_h["Value"] / total_stocks_value * 100).round(1)
            top_h["v_fmt"] = top_h["Value"].apply(lambda x: f"\u20ac{x:,.0f}")

            for _, row in top_h.iterrows():
                pct   = row["Pct"]
                sym   = row["Symbol"]
                v_fmt = row["v_fmt"]
                if is_minimal():
                    fill_bg   = f"background:{THEME['accent_alpha']};"
                    pct_color = THEME["accent"]
                else:
                    fill_bg   = (
                        f"background:linear-gradient(90deg,{THEME['primary_light']},"
                        f"{THEME['primary_alpha']});"
                        f"box-shadow:0 0 12px {THEME['glow']};"
                    )
                    pct_color = THEME["primary"]
                st.markdown(
                    f"""
                    <div style="position:relative;padding:9px 12px;margin:5px 0;
                               background:{THEME['bg_card']};border-radius:6px;
                               border:1px solid {THEME['border']};
                               box-shadow:{THEME['shadow_card']};overflow:hidden;font-size:11px;">
                        <div style="position:absolute;left:0;top:0;height:100%;width:{pct}%;
                                    {fill_bg}border-radius:6px 0 0 6px;z-index:0;"></div>
                        <div style="position:relative;z-index:1;
                                    display:flex;justify-content:space-between;align-items:center;">
                            <span style="font-weight:600;color:{THEME['text_primary']};
                                         letter-spacing:0.01em;">{sym}</span>
                            <span style="color:{THEME['text_secondary']};">{
                                v_fmt}&nbsp;<span style="color:{pct_color};font-weight:600;"
                                >{pct}%</span></span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.info("No stock holdings")

    # ---- Income Breakdown ----------------------------------------------- #
    st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
    st.markdown(
        f"<p style='font-size:11px;font-weight:600;color:{THEME['text_secondary']};"
        f"text-transform:uppercase;letter-spacing:0.08em;margin-bottom:10px;'>"
        f"Income Breakdown</p>",
        unsafe_allow_html=True,
    )

    col_inc1, col_inc2 = st.columns(2)
    income_items = [
        ("Dividends", f"\u20ac{total_dividends:,.0f}",
         f"Monthly avg \u20ac{monthly_dividends:.0f}"),
        ("Interest",  f"\u20ac{total_interest:,.0f}",
         f"Monthly avg \u20ac{monthly_interest:.0f}"),
        ("Realized",  f"\u20ac{realized_gains:,.0f}",
         f"Monthly avg \u20ac{monthly_realized:.0f}"),
    ]

    with col_inc1:
        sub1, sub2, sub3 = st.columns(3)
        for col_widget, (lbl, val, sub_txt), palette_color in zip(
            [sub1, sub2, sub3], income_items, THEME["palette"]
        ):
            with col_widget:
                st.markdown(
                    _kpi_card(THEME, lbl, val, sub_txt, accent_override=palette_color),
                    unsafe_allow_html=True,
                )

    with col_inc2:
        inc_df = pd.DataFrame({
            "Source": [i[0] for i in income_items],
            "Amount": [total_dividends, total_interest, realized_gains],
        })
        inc_df = inc_df[inc_df["Amount"] > 0]

        if not inc_df.empty:
            fig_inc = go.Figure()
            fig_inc.add_trace(go.Bar(
                x=inc_df["Source"],
                y=inc_df["Amount"],
                marker=dict(
                    color=THEME["palette"][:len(inc_df)],
                    line=dict(width=0),
                    opacity=0.80,
                ),
                text=[f"\u20ac{v:,.0f}" for v in inc_df["Amount"]],
                textposition="inside",
                textfont=dict(size=11, color="white", weight="bold"),
                hovertemplate="<b>%{x}</b><br>\u20ac%{y:,.0f}<extra></extra>",
            ))
            fig_inc.update_layout(
                **_chart_layout(THEME, height=165, margin=dict(l=0, r=0, t=10, b=10)),
                showlegend=False,
                xaxis=dict(showgrid=False, title=None, color=THEME["text_secondary"]),
                yaxis=dict(
                    showgrid=True, gridcolor=THEME["chart_grid"],
                    title=None, color=THEME["text_secondary"],
                ),
            )
            st.plotly_chart(fig_inc, use_container_width=True, config={"displayModeBar": False})
