"""
components/income_deep_dive.py - Income & Tax Analysis
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import calendar

from src.dashboard.theme import get_active_theme, is_minimal

_MONTH_ORDER = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December',
]

_TOP_PAYERS_MAX_NAME_LEN = 18


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hex_to_rgba(hex_color: str, alpha: float = 1.0) -> str:
    """Convert a 6-digit hex color string to an rgba() string Plotly accepts."""
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f'rgba({r},{g},{b},{alpha})'


def _truncate_name(name: str, max_len: int = _TOP_PAYERS_MAX_NAME_LEN) -> str:
    """Truncate a display name to max_len characters, appending an ellipsis."""
    return name[:max_len] + '\u2026' if len(name) > max_len else name


def _kpi(THEME: dict, label: str, value: str, color: str | None = None,
         margin_bottom: str = '16px', font_size: str = '24px') -> str:
    c      = color or THEME['text_primary']
    shadow = f"0 0 14px {THEME['glow']}" if not is_minimal() else THEME['shadow_card']
    stripe = (f"border-left:3px solid {THEME['accent']};border-radius:0 8px 8px 0;"
              if is_minimal() else 'border-radius:8px;')
    return (
        f'<div style="background:{THEME["bg_card"]};padding:12px 14px;{stripe}'
        f'border:1px solid {THEME["border"]};box-shadow:{shadow};margin-bottom:{margin_bottom};">'
        f'<div style="color:{THEME["text_secondary"]};font-size:10px;text-transform:uppercase;'
        f'letter-spacing:0.07em;margin-bottom:5px;">{label}</div>'
        f'<div style="color:{c};font-size:{font_size};font-weight:700;">{value}</div></div>'
    )


def _kpi_delta(THEME: dict, label: str, value: str, delta_pct: float | None,
               color: str | None = None, margin_bottom: str = '8px') -> str:
    """KPI card with an optional YoY delta badge (↑/↓ x.x%, green/red)."""
    c      = color or THEME['text_primary']
    shadow = f"0 0 14px {THEME['glow']}" if not is_minimal() else THEME['shadow_card']
    stripe = (f"border-left:3px solid {THEME['accent']};border-radius:0 8px 8px 0;"
              if is_minimal() else 'border-radius:8px;')

    if delta_pct is not None:
        d_color = THEME['success'] if delta_pct >= 0 else THEME['danger']
        arrow   = '\u2191' if delta_pct >= 0 else '\u2193'
        delta_html = (
            f'<span style="color:{d_color};font-size:10px;font-weight:600;'
            f'margin-left:6px;">{arrow} {abs(delta_pct):.1f}% YoY</span>'
        )
    else:
        delta_html = ''

    return (
        f'<div style="background:{THEME["bg_card"]};padding:12px 14px;{stripe}'
        f'border:1px solid {THEME["border"]};box-shadow:{shadow};margin-bottom:{margin_bottom};">'
        f'<div style="color:{THEME["text_secondary"]};font-size:10px;text-transform:uppercase;'
        f'letter-spacing:0.07em;margin-bottom:5px;">{label}</div>'
        f'<div style="display:flex;align-items:baseline;">'
        f'<div style="color:{c};font-size:20px;font-weight:700;">{value}</div>'
        f'{delta_html}</div></div>'
    )


def _chart_layout(THEME: dict, height: int, margin: dict) -> dict:
    return dict(
        height=height, margin=margin,
        paper_bgcolor=THEME['chart_bg'], plot_bgcolor=THEME['chart_bg'],
        font=dict(size=11, color=THEME['text_secondary'], family='Inter, sans-serif'),
    )


def _subtab_css(THEME: dict) -> str:
    if is_minimal():
        ab = THEME['accent'];  ac = THEME['accent'];  bg = THEME['bg_card']
        hov = 'rgba(255,255,255,0.04)'; inact = THEME['text_secondary']
    else:
        ab = THEME['primary']; ac = THEME['primary']; bg = THEME['primary_alpha']
        hov = THEME['primary_light'];   inact = THEME['text_secondary']
    return f"""
    <style>
    .stTabs [data-baseweb="tab-list"] {{
        gap:0;border-bottom:1px solid {THEME['border']};padding-bottom:0;margin-bottom:8px;
    }}
    .stTabs [data-baseweb="tab"] {{
        background:transparent;border:none;border-bottom:2px solid transparent;
        border-radius:0;padding:6px 18px;font-size:12px;font-weight:500;
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


def _build_waterfall_fig(THEME: dict, labels: list, values: list, colors: list,
                         height: int = 380) -> go.Figure:
    """Build a waterfall chart using stacked go.Bar traces for full per-bar color control.

    go.Waterfall does not support marker.color overrides, so we simulate it:
    - An invisible 'base' bar holds the running offset
    - A visible 'delta' bar sits on top with the correct color
    """
    bases, deltas = [], []
    running = 0.0
    for val in values:
        bases.append(running)
        deltas.append(val)
        running += val

    fig = go.Figure()

    # Invisible spacer
    fig.add_trace(go.Bar(
        x=labels, y=bases,
        marker_color='rgba(0,0,0,0)',
        hoverinfo='skip',
        showlegend=False,
    ))

    # Visible bars — one trace per bar so each gets its own color
    for i, (lbl, delta, color) in enumerate(zip(labels, deltas, colors)):
        sign_label = f'\u20ac{abs(delta):,.0f}'
        fig.add_trace(go.Bar(
            x=[lbl], y=[delta],
            base=[bases[i]],
            marker_color=color,
            marker_line=dict(color=THEME['border'], width=0.5),
            text=[sign_label],
            textposition='auto',  # was 'outside'
            textfont=dict(color=THEME['text_primary'], size=11),
            hovertemplate=f'<b>{lbl}</b><br>\u20ac{delta:,.2f}<extra></extra>',
            showlegend=False,
        ))

    fig.update_layout(
        **_chart_layout(THEME, height=height, margin=dict(t=8, b=0, l=0, r=0)),
        barmode='stack',
        showlegend=False,
        yaxis=dict(title='Amount (\u20ac)', showgrid=True, gridcolor=THEME['chart_grid'],
                   color=THEME['text_secondary']),
        xaxis=dict(color=THEME['text_secondary']),
    )
    return fig


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def render_income_deep_dive(
    interest_data: pd.DataFrame,
    transactions: pd.DataFrame,
    trades: pd.DataFrame = pd.DataFrame()
) -> None:
    THEME = get_active_theme()
    st.markdown(_subtab_css(THEME), unsafe_allow_html=True)

    dividends_df = transactions[transactions['event_type'] == 'dividend'].copy()
    interest_df  = transactions[transactions['event_type'] == 'interest'].copy()

    total_div_net    = dividends_df['net_cash_flow'].sum() if not dividends_df.empty else 0.0
    total_int_net    = interest_df['net_cash_flow'].sum()  if not interest_df.empty  else 0.0
    total_income_net = total_div_net + total_int_net

    tab_overview, tab_details, tab_tax = st.tabs(['Summary', 'Dividends', 'Taxes'])

    with tab_overview:
        st.caption('Overview')
        _render_overview(total_income_net, dividends_df, interest_data, trades)

    with tab_details:
        st.caption('Dividend Details')
        _render_details(dividends_df)

    with tab_tax:
        st.caption('Tax Report')
        _render_taxes(transactions, trades)


# ---------------------------------------------------------------------------
# Sub-tab: Overview
# ---------------------------------------------------------------------------

def _yoy_monthly_avg(events: list[dict]) -> tuple[float | None, float | None]:
    """Return (current_year_monthly_avg, prior_year_monthly_avg) from a list of
    {'date': pd.Timestamp, 'amount': float} dicts. Returns (None, None) if
    insufficient data for a comparison."""
    if not events:
        return None, None
    df = pd.DataFrame(events)
    df['date'] = pd.to_datetime(df['date'])
    df['year'] = df['date'].dt.year
    current_yr = df['year'].max()
    prior_yr   = current_yr - 1
    cur  = df[df['year'] == current_yr]['amount'].sum()
    prev = df[df['year'] == prior_yr]['amount'].sum()
    cur_months  = df[df['year'] == current_yr]['date'].dt.month.nunique()
    prev_months = df[df['year'] == prior_yr]['date'].dt.month.nunique()
    if prev_months == 0:
        return cur / max(cur_months, 1), None
    return cur / max(cur_months, 1), prev / prev_months


def _delta_pct(current: float | None, prior: float | None) -> float | None:
    if current is None or prior is None or prior == 0:
        return None
    return (current - prior) / abs(prior) * 100


def _render_overview(total_income, dividends_df, interest_data, trades):
    THEME = get_active_theme()
    col_kpi, col_charts = st.columns([1, 2])

    income_color  = THEME['accent']     if is_minimal() else THEME['palette'][3]
    income2_color = THEME['palette'][1] if is_minimal() else THEME['palette'][2]
    income3_color = THEME['palette'][4] if len(THEME['palette']) > 4 else THEME['palette'][0]
    income4_color = THEME['palette'][0]

    # ---- Aggregate values ------------------------------------------------ #
    div_sum        = dividends_df['net_cash_flow'].sum() if not dividends_df.empty else 0.0
    int_sum        = interest_data['net_interest'].sum() if not interest_data.empty else 0.0
    realized_gains = trades['realized_gain'].sum() if not trades.empty else 0.0

    total_all      = div_sum + int_sum + realized_gains   # Div + Int + Trades
    total_div_int  = div_sum + int_sum                    # Div + Int only
    total_div_tr   = div_sum + realized_gains             # Div + Trades (cash generative)

    # Monthly avg (all) over full data span
    if not dividends_df.empty or not interest_data.empty:
        all_dates = (
            pd.concat([dividends_df['date'], interest_data['month']])
            if not interest_data.empty else dividends_df['date']
        )
        months_span = max(1, (all_dates.max() - all_dates.min()).days / 30.44) if not all_dates.empty else 1
    else:
        months_span = 1
    monthly_avg_all = total_all / months_span

    # YoY monthly avg — all income (Div + Int + Trades)
    all_events: list[dict] = []
    if not dividends_df.empty:
        all_events += [{'date': r['date'], 'amount': r['net_cash_flow']}
                       for _, r in dividends_df.iterrows()]
    if not interest_data.empty:
        all_events += [{'date': r['month'], 'amount': r['net_interest']}
                       for _, r in interest_data.iterrows()]
    if not trades.empty:
        all_events += [{'date': r['sell_date'], 'amount': r['realized_gain']}
                       for _, r in trades.iterrows()]

    cur_all, prev_all = _yoy_monthly_avg(all_events)
    delta_all         = _delta_pct(cur_all, prev_all)

    # YoY monthly avg — Div + Int only
    di_events: list[dict] = []
    if not dividends_df.empty:
        di_events += [{'date': r['date'], 'amount': r['net_cash_flow']}
                      for _, r in dividends_df.iterrows()]
    if not interest_data.empty:
        di_events += [{'date': r['month'], 'amount': r['net_interest']}
                      for _, r in interest_data.iterrows()]

    cur_di, prev_di = _yoy_monthly_avg(di_events)
    delta_di        = _delta_pct(cur_di, prev_di)

    with col_kpi:
        # 2-column sub-grid for 6 KPI cards (3 rows × 2 cols)
        g1, g2 = st.columns(2)

        # Row 1: Total Income (all) | Monthly Avg (all)   <-- switched
        with g1:
            st.markdown(
                _kpi_delta(THEME, 'Total Income \u00b7 All', f'\u20ac{total_all:,.0f}',
                           None, income_color),
                unsafe_allow_html=True,
            )
        with g2:
            st.markdown(
                _kpi_delta(THEME, 'Monthly Avg \u00b7 All', f'\u20ac{monthly_avg_all:,.0f}',
                           None, income_color),
                unsafe_allow_html=True,
            )

        # Row 2: Div + Trades | Monthly YoY (all)   <-- switched
        with g1:
            st.markdown(
                _kpi_delta(THEME, 'Div + Trades', f'\u20ac{total_div_tr:,.0f}',
                           None, income4_color),
                unsafe_allow_html=True,
            )
        with g2:
            cur_all_fmt = f'\u20ac{cur_all:,.0f}' if cur_all is not None else 'n/a'
            st.markdown(
                _kpi_delta(THEME, 'Monthly \u00b7 YoY (All)', cur_all_fmt,
                           delta_all, income3_color),
                unsafe_allow_html=True,
            )

        # Row 3: Total Income (Div+Int) | Monthly YoY (Div+Int)   <-- switched
        with g1:
            st.markdown(
                _kpi_delta(THEME, 'Total Income \u00b7 Div+Int', f'\u20ac{total_div_int:,.0f}',
                           None, income2_color),
                unsafe_allow_html=True,
            )
        with g2:
            cur_di_fmt = f'\u20ac{cur_di:,.0f}' if cur_di is not None else 'n/a'
            st.markdown(
                _kpi_delta(THEME, 'Monthly \u00b7 YoY (Div+Int)', cur_di_fmt,
                           delta_di, income2_color),
                unsafe_allow_html=True,
            )

        # Donut chart — Div vs Int split
        if div_sum + int_sum > 0:
            fig_donut = go.Figure(data=[go.Pie(
                labels=['Dividends', 'Interest'],
                values=[div_sum, int_sum],
                hole=0.6,
                marker=dict(
                    colors=[income_color, income2_color],
                    line=dict(color=THEME['bg_card'], width=3),
                ),
                textinfo='percent+label',
                textfont=dict(color=THEME['text_primary'], size=11),
                pull=[0.04, 0.04],
            )])
            fig_donut.update_layout(
                **_chart_layout(THEME, height=200, margin=dict(t=10, b=10, l=0, r=0)),
                showlegend=False,
            )
            st.plotly_chart(fig_donut, use_container_width=True, config={'displayModeBar': False})

    with col_charts:
        _render_income_charts(dividends_df, interest_data)


@st.fragment
def _render_income_charts(dividends_df, interest_data):
    THEME = get_active_theme()
    income_color  = THEME['accent']     if is_minimal() else THEME['palette'][3]
    income2_color = THEME['palette'][1] if is_minimal() else THEME['palette'][2]

    col_title, col_toggle = st.columns([1, 1])
    with col_title:
        st.subheader('Income Trends')
    with col_toggle:
        chart_view = st.radio(
            'View', ['Monthly', 'Year-over-Year'],
            horizontal=True, label_visibility='collapsed',
            key='income_chart_toggle',
        )

    if chart_view == 'Monthly':
        chart_data = []
        if not dividends_df.empty:
            div_monthly = dividends_df.groupby(dividends_df['date'].dt.to_period('M'))['net_cash_flow'].sum()
            for period, val in div_monthly.items():
                chart_data.append({'Month': str(period), 'Amount': val, 'Type': 'Dividends'})
        if not interest_data.empty:
            for _, row in interest_data.iterrows():
                m_str = row['month'].strftime('%Y-%m') if isinstance(row['month'], pd.Timestamp) else str(row['month'])[:7]
                chart_data.append({'Month': m_str, 'Amount': row['net_interest'], 'Type': 'Interest'})

        if chart_data:
            df_chart = pd.DataFrame(chart_data).sort_values('Month')
            fig_trend = px.bar(
                df_chart, x='Month', y='Amount', color='Type', barmode='stack',
                color_discrete_map={
                    'Dividends': income_color,
                    'Interest':  income2_color,
                },
            )
            fig_trend.update_traces(marker_line_color=THEME['bg_card'], marker_line_width=0.8)
            fig_trend.update_layout(
                **_chart_layout(THEME, height=430, margin=dict(t=8, b=0, l=0, r=0)),
                yaxis=dict(showgrid=True, gridcolor=THEME['chart_grid'],
                           title='Amount (\u20ac)', color=THEME['text_secondary']),
                xaxis=dict(showgrid=False, title='', color=THEME['text_secondary']),
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1,
                            font=dict(color=THEME['text_primary'])),
            )
            st.plotly_chart(fig_trend, use_container_width=True, config={'displayModeBar': False})
        else:
            st.info('No income data available for monthly view.')

    else:  # Year-over-Year
        income_events = []
        if not dividends_df.empty:
            for _, row in dividends_df.iterrows():
                income_events.append({'date': row['date'], 'amount': row['net_cash_flow']})
        if not interest_data.empty:
            for _, row in interest_data.iterrows():
                income_events.append({'date': row['month'], 'amount': row['net_interest']})

        if income_events:
            df_inc = pd.DataFrame(income_events)
            df_inc['date']      = pd.to_datetime(df_inc['date'])
            df_inc['year']      = df_inc['date'].dt.year.astype(str)
            df_inc['month_num'] = df_inc['date'].dt.month
            df_grouped = df_inc.groupby(['year', 'month_num'])['amount'].sum().reset_index()
            df_grouped['cumulative'] = df_grouped.groupby('year')['amount'].cumsum()
            month_map = {i: calendar.month_abbr[i] for i in range(1, 13)}
            df_grouped['month_name'] = df_grouped['month_num'].map(month_map)

            years   = sorted(df_grouped['year'].unique())
            fig_cum = go.Figure()
            for i, yr in enumerate(years):
                yr_data = df_grouped[df_grouped['year'] == yr].sort_values('month_num')
                color   = THEME['palette'][i % len(THEME['palette'])]
                fig_cum.add_trace(go.Scatter(
                    x=yr_data['month_name'], y=yr_data['cumulative'],
                    mode='lines+markers', name=yr,
                    line=dict(color=color, width=2),
                    marker=dict(size=6, color=color, line=dict(color=THEME['border'], width=1)),
                ))
            fig_cum.update_xaxes(categoryorder='array', categoryarray=list(month_map.values()))
            fig_cum.update_layout(
                **_chart_layout(THEME, height=430, margin=dict(t=8, b=0, l=0, r=0)),
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1,
                            font=dict(color=THEME['text_primary'])),
                yaxis=dict(showgrid=True, gridcolor=THEME['chart_grid'],
                           title='Cumulative Income (\u20ac)', color=THEME['text_secondary']),
                xaxis=dict(showgrid=False, title='', color=THEME['text_secondary']),
            )
            st.plotly_chart(fig_cum, use_container_width=True, config={'displayModeBar': False})
        else:
            st.info('Not enough data for year-over-year comparison.')


# ---------------------------------------------------------------------------
# Sub-tab: Dividends
# ---------------------------------------------------------------------------

def _render_details(dividends_df: pd.DataFrame):
    THEME = get_active_theme()
    if dividends_df.empty:
        st.info('No dividend data.')
        return

    st.subheader('Dividend Calendar')
    heatmap_data = dividends_df.copy()
    heatmap_data['month_name'] = heatmap_data['date'].dt.month_name()
    heatmap_data['year']       = heatmap_data['date'].dt.year
    heatmap_agg = heatmap_data.groupby(['year', 'month_name'])['net_cash_flow'].sum().reset_index()

    years_sorted = sorted(heatmap_agg['year'].unique())
    pivot_raw = heatmap_agg.pivot(index='year', columns='month_name', values='net_cash_flow').reindex(
        index=years_sorted, columns=_MONTH_ORDER
    ).fillna(0)
    pivot_log = np.log1p(pivot_raw)

    hover_text = [
        [f'<b>{col} {row}</b><br>\u20ac{pivot_raw.loc[row, col]:,.2f}' for col in pivot_raw.columns]
        for row in pivot_raw.index
    ]

    primary_hex = THEME['accent'] if is_minimal() else THEME['primary']
    colorscale = [
        [0.0, THEME['bg_card']],
        [0.3, _hex_to_rgba(primary_hex, 0.35)],
        [1.0, _hex_to_rgba(primary_hex, 1.0)],
    ]

    fig_heatmap = go.Figure(go.Heatmap(
        z=pivot_log.values,
        x=list(pivot_log.columns),
        y=[str(y) for y in pivot_log.index],
        text=hover_text,
        hovertemplate='%{text}<extra></extra>',
        colorscale=colorscale,
        showscale=False,
        xgap=2, ygap=2,
    ))
    fig_heatmap.update_layout(
        **_chart_layout(THEME, height=200, margin=dict(t=10, b=0, l=0, r=0)),
        xaxis=dict(title='', color=THEME['text_secondary'], side='bottom'),
        yaxis=dict(title='', color=THEME['text_secondary']),
    )
    st.plotly_chart(fig_heatmap, use_container_width=True, config={'displayModeBar': False})

    st.markdown('---')
    col_bars, col_scatter, col_table = st.columns([1.3, 1, 1.2])

    with col_bars:
        st.subheader('Top Payers')
        top_payers = (
            dividends_df.groupby('name')['net_cash_flow']
            .sum()
            .nlargest(8)
            .reset_index()
        )
        top_payers['name'] = top_payers['name'].apply(_truncate_name)

        n = len(top_payers)
        bar_alphas = [
            _hex_to_rgba(THEME['accent'], 0.27) if is_minimal()
            else THEME['palette_alpha'][i % len(THEME['palette_alpha'])]
            for i in range(n)
        ]
        bar_colors = [
            THEME['accent'] if is_minimal() else THEME['palette'][i % len(THEME['palette'])]
            for i in range(n)
        ]
        fig_bar = go.Figure(go.Bar(
            x=top_payers['net_cash_flow'], y=top_payers['name'],
            orientation='h',
            text=['\u20ac' + f'{v:,.0f}' for v in top_payers['net_cash_flow']],
            textposition='auto',  # was 'outside'
            textfont=dict(color=THEME['text_primary'], size=11),
            marker=dict(
                color=bar_alphas,
                line=dict(color=bar_colors, width=1.5),
            ),
            cliponaxis=False,  # allow text to overflow axes
        ))
        fig_bar.update_layout(
            **_chart_layout(THEME, height=400, margin=dict(t=0, b=0, l=10, r=10)),  # reduced right margin
            showlegend=False,
            yaxis=dict(
                title='', categoryorder='total ascending',
                color=THEME['text_primary'], tickfont=dict(size=11),
                automargin=True,
            ),
            xaxis=dict(title='Total \u20ac', color=THEME['text_secondary'],
                       showgrid=True, gridcolor=THEME['chart_grid']),
        )
        st.plotly_chart(fig_bar, use_container_width=True, config={'displayModeBar': False})

    with col_scatter:
        st.subheader('Quality Matrix')
        quality_data = dividends_df.groupby('name').agg(
            total_payout=('net_cash_flow', 'sum'),
            payout_count=('net_cash_flow', 'count'),
            days_span=('date', lambda x: (x.max() - x.min()).days),
        ).reset_index()
        quality_data['annual_frequency'] = quality_data.apply(
            lambda r: (r['payout_count'] / max(r['days_span'], 1)) * 365
            if r['days_span'] > 0 else r['payout_count'],
            axis=1,
        )

        max_payout = max(quality_data['total_payout'].max(), 1)
        min_payout = quality_data['total_payout'].min()

        p = THEME['palette']
        fig_scatter = go.Figure()
        for idx, (_, row) in enumerate(quality_data.iterrows()):
            norm_payout  = (row['total_payout'] - min_payout) / max(max_payout - min_payout, 1)
            size         = max(10, min(44, norm_payout * 44 + 10))
            fill_color   = THEME['palette_alpha'][idx % len(THEME['palette_alpha'])]
            border_color = p[idx % len(p)]
            fig_scatter.add_trace(go.Scatter(
                x=[row['total_payout']], y=[row['annual_frequency']],
                mode='markers',
                marker=dict(size=size, color=fill_color,
                            line=dict(color=border_color, width=1.5)),
                name=row['name'],
                hovertemplate=(
                    f"<b>{row['name']}</b><br>"
                    'Total: \u20ac%{x:,.0f}<br>'
                    'Payouts/Year: %{y:.1f}<extra></extra>'
                ),
                showlegend=False,
            ))
        fig_scatter.update_layout(
            **_chart_layout(THEME, height=400, margin=dict(t=0, b=0, l=0, r=0)),
            xaxis=dict(title='Total Payout (\u20ac)', showgrid=True,
                       gridcolor=THEME['chart_grid'], color=THEME['text_secondary']),
            yaxis=dict(title='Payouts/Year', showgrid=True,
                       gridcolor=THEME['chart_grid'], color=THEME['text_secondary']),
            hovermode='closest',
        )
        st.plotly_chart(fig_scatter, use_container_width=True, config={'displayModeBar': False})

    with col_table:
        st.subheader('Recent Payouts')
        recent = dividends_df[['date', 'name', 'net_cash_flow']].copy()
        recent.columns = ['Date', 'Asset', 'Amount']
        recent = recent.sort_values('Date', ascending=False).head(20)
        max_amount = recent['Amount'].max() if not recent.empty else 1

        def _style_amount(val):
            if not isinstance(val, (int, float)):
                return ''
            norm = val / max_amount if max_amount > 0 else 0
            if is_minimal():
                return f'color:{THEME["accent"]};font-weight:bold'
            opacity = round(0.35 + 0.65 * norm, 2)
            return f'color:rgba(122,162,247,{opacity});font-weight:bold'

        st.dataframe(
            recent.style
            .format({'Date': lambda t: t.strftime('%Y-%m-%d'), 'Amount': '\u20ac{:,.2f}'})
            .applymap(_style_amount, subset=['Amount']),
            use_container_width=True, height=400, hide_index=True,
        )


# ---------------------------------------------------------------------------
# Sub-tab: Taxes
# ---------------------------------------------------------------------------

def _render_taxes(transactions: pd.DataFrame, trades: pd.DataFrame):
    THEME = get_active_theme()
    if transactions.empty:
        st.info('No transaction data available for tax analysis.')
        return

    years_in_tx     = set(transactions['date'].dt.year.unique())   if not transactions.empty else set()
    years_in_trades = set(trades['sell_date'].dt.year.unique())     if not trades.empty       else set()
    all_years       = sorted(list(years_in_tx.union(years_in_trades)), reverse=True)
    selected_tax_year = None

    if len(all_years) > 1:
        col_warn, col_select = st.columns([2, 1])
        with col_warn:
            st.info(f'\u2139\ufe0f Tax reports are annual. Defaulting to **{all_years[0]}**.')
        with col_select:
            selected_tax_year = st.selectbox('Select Tax Year', all_years, index=0, key='tax_year_select')
        transactions = transactions[transactions['date'].dt.year == selected_tax_year]
        if not trades.empty:
            trades = trades[trades['sell_date'].dt.year == selected_tax_year]
    elif len(all_years) == 1:
        selected_tax_year = all_years[0]
        st.caption(f'Tax Report for **{selected_tax_year}**')

    default_allowance = 1000 if (selected_tax_year and selected_tax_year >= 2023) else 801
    col_input, col_kpi_metrics = st.columns([1, 3])
    with col_input:
        allowance = st.number_input(
            'Allowance / Freibetrag (\u20ac)', value=default_allowance, step=100,
            key=f'allowance_input_{selected_tax_year}',
        )

    capital_tax    = transactions['capital_tax'].abs().sum()
    soli_tax       = transactions['soli_tax'].abs().sum()
    church_tax     = transactions['church_tax'].abs().sum()
    foreign_tax    = transactions['foreign_tax'].abs().sum()
    total_tax_paid = capital_tax + soli_tax + church_tax + foreign_tax

    div_gross    = transactions[transactions['event_type'] == 'dividend']['gross_amount'].sum()
    int_tx       = transactions[transactions['event_type'] == 'interest']
    int_tax      = int_tx['capital_tax'].abs() + int_tx['soli_tax'].abs() + int_tx['church_tax'].abs()
    int_gross    = int_tx['net_cash_flow'].sum() + int_tax.sum()
    trade_profit = trades['realized_gain'].sum() if not trades.empty else 0.0

    total_taxable_income = div_gross + int_gross + trade_profit
    net_profit_after_tax = total_taxable_income - total_tax_paid
    effective_taxable    = max(0, total_taxable_income)
    rate_fmt             = f'{(total_tax_paid / total_taxable_income * 100):.1f}%' if total_taxable_income > 0 else '0%'

    taxable_income_color = THEME['palette'][0] if is_minimal() else THEME['primary']
    tax_color            = THEME['danger']
    net_color            = THEME['text_primary']

    with col_kpi_metrics:
        m1, m2, m3 = st.columns(3)
        with m1:
            st.markdown(_kpi(THEME, 'Taxable Income',
                             f'\u20ac{total_taxable_income:,.2f}', taxable_income_color,
                             font_size='18px', margin_bottom='0'), unsafe_allow_html=True)
        with m2:
            st.markdown(_kpi(THEME, f'Total Tax Paid ({rate_fmt})',
                             f'\u20ac{total_tax_paid:,.2f}', tax_color,
                             font_size='18px', margin_bottom='0'), unsafe_allow_html=True)
        with m3:
            st.markdown(_kpi(THEME, 'Net After Tax',
                             f'\u20ac{net_profit_after_tax:,.2f}', net_color,
                             font_size='18px', margin_bottom='0'), unsafe_allow_html=True)

    st.markdown('---')
    col_waterfall, col_allowance = st.columns([2, 1])

    with col_waterfall:
        st.subheader(f'Tax Waterfall ({selected_tax_year})')

        income_fill   = THEME['palette'][0] if is_minimal() else THEME['primary']
        tax_red_dark  = 'rgba(180,30,30,0.85)'
        tax_red_mid   = 'rgba(200,50,50,0.70)'
        tax_red_light = 'rgba(220,80,80,0.55)'
        tax_red_faint = 'rgba(230,100,100,0.40)'
        net_fill      = THEME['wf_total']

        wf_labels = ['Taxable Income', 'Foreign Tax', 'Capital Tax', 'Soli', 'Church Tax', 'Net After Tax']
        wf_values = [
            total_taxable_income,
            -foreign_tax, -capital_tax, -soli_tax, -church_tax,
            net_profit_after_tax,
        ]
        wf_colors = [income_fill, tax_red_dark, tax_red_mid, tax_red_light, tax_red_faint, net_fill]

        bases  = [0.0]
        running = total_taxable_income
        for v in wf_values[1:-1]:
            bases.append(running)
            running += v
        bases.append(0.0)  # net total starts from zero (absolute)

        fig_wf = go.Figure()
        fig_wf.add_trace(go.Bar(
            x=wf_labels, y=bases,
            marker_color='rgba(0,0,0,0)',
            hoverinfo='skip', showlegend=False,
        ))
        for lbl, val, base, color in zip(wf_labels, wf_values, bases, wf_colors):
            fig_wf.add_trace(go.Bar(
                x=[lbl], y=[val], base=[base],
                marker_color=color,
                marker_line=dict(color=THEME['border'], width=0.5),
                text=[f'\u20ac{val:,.0f}'],
                textposition='outside',
                textfont=dict(color=THEME['text_secondary'], size=10),
                hovertemplate=f'<b>{lbl}</b><br>\u20ac{val:,.2f}<extra></extra>',
                showlegend=False,
            ))
        fig_wf.update_layout(
            **_chart_layout(THEME, height=380, margin=dict(t=8, b=0, l=0, r=0)),
            barmode='stack', showlegend=False,
            yaxis=dict(title='Amount (\u20ac)', showgrid=True, gridcolor=THEME['chart_grid'],
                       color=THEME['text_secondary']),
            xaxis=dict(color=THEME['text_secondary']),
        )
        st.plotly_chart(fig_wf, use_container_width=True, config={'displayModeBar': False})

    with col_allowance:
        st.subheader('Allowance Usage')
        remaining = allowance
        segments  = []
        for cat, gross in [('Dividends', div_gross), ('Interest', int_gross),
                           ('Capital Gains', max(0, trade_profit))]:
            used = min(max(0, gross), remaining)
            if used > 0:
                segments.append({'Category': cat, 'Amount': used})
                remaining -= used
        if remaining > 0:
            segments.append({'Category': 'Remaining', 'Amount': remaining})
        excess = max(0, effective_taxable - allowance)
        if excess > 0:
            segments.append({'Category': 'Taxable (Over)', 'Amount': excess})

        df_allowance = pd.DataFrame(segments)
        color_map = {
            'Dividends':      THEME['palette'][0],
            'Interest':       THEME['palette'][2],
            'Capital Gains':  THEME['palette'][3],
            'Remaining':      THEME['border'],
            'Taxable (Over)': THEME['danger'],
        }
        fig_allow = go.Figure()
        for cat in df_allowance['Category'].unique():
            df_cat = df_allowance[df_allowance['Category'] == cat]
            fig_allow.add_trace(go.Bar(
                x=['Allowance'], y=df_cat['Amount'], name=cat,
                marker_color=color_map.get(cat, THEME['palette'][0]),
                text=f'\u20ac{df_cat["Amount"].iloc[0]:.0f}',
                textposition='inside',
                textfont=dict(color=THEME['text_primary'], size=10),
            ))
        fig_allow.update_layout(
            **_chart_layout(THEME, height=380, margin=dict(t=8, b=0, l=0, r=0)),
            barmode='stack', showlegend=True,
            legend=dict(orientation='v', x=1.05, y=1,
                        font=dict(color=THEME['text_primary'], size=10)),
            yaxis=dict(title='Amount (\u20ac)', showgrid=False, color=THEME['text_secondary']),
            xaxis=dict(showticklabels=False),
        )
        st.plotly_chart(fig_allow, use_container_width=True, config={'displayModeBar': False})
