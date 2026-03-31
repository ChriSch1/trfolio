"""
components/stocks_deep_dive.py - Stocks Deep Dive Tab
"""
import math
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.dashboard.theme import get_active_theme, is_minimal
from src.dashboard.calculations import calculate_stock_returns

_SECTOR_HUES: dict[str, tuple[int, int, int]] = {
    'Technology':             ( 99, 102, 241),
    'Consumer Cyclical':      (161, 128,  60),
    'Industrials':            ( 56,  99, 168),
    'Financial Services':     ( 22, 130,  94),
    'Healthcare':             (160,  60, 110),
    'Communication Services': ( 30, 145, 160),
    'Energy':                 (170,  80,  40),
    'Basic Materials':        ( 25, 130, 120),
    'Consumer Defensive':     (110,  60, 170),
    'Real Estate':            (160, 100,  45),
    'Utilities':              ( 90,  65, 175),
    'Unknown':                (100, 116, 139),
}
_DEFAULT_HUE  = (100, 116, 139)
_OTHERS_COLOR = 'rgba(100, 116, 139, 0.25)'

_PNL_COLORSCALE = [
    [0.0,  'rgba(220,  38,  38, 0.75)'],
    [0.35, 'rgba(185,  28,  28, 0.45)'],
    [0.5,  'rgba( 51,  65,  85, 0.30)'],
    [0.65, 'rgba(  5, 120,  85, 0.45)'],
    [1.0,  'rgba(  5, 150,  90, 0.75)'],
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sector_color(sector: str, position_idx: int, total_in_sector: int) -> str:
    r, g, b = _SECTOR_HUES.get(sector, _DEFAULT_HUE)
    opacity = 0.45 if total_in_sector <= 1 else 0.55 - (position_idx / (total_in_sector - 1)) * 0.25
    return f'rgba({r},{g},{b},{opacity:.2f})'


def _kpi(THEME: dict, label: str, value: str, color: str | None = None,
         sub: str = '', margin_bottom: str = '8px') -> str:
    """Compact KPI tile – reduced padding & font size vs overview variant."""
    c      = color or THEME['text_primary']
    shadow = f"0 0 10px {THEME['glow']}" if not is_minimal() else THEME['shadow_card']
    stripe = (f"border-left:3px solid {THEME['accent']};border-radius:0 6px 6px 0;"
              if is_minimal() else 'border-radius:6px;')
    sub_html = (
        f'<div style="color:{THEME["text_secondary"]};font-size:9px;margin-top:3px;">{sub}</div>'
        if sub else ''
    )
    return (
        f'<div style="background:{THEME["bg_card"]};padding:8px 10px;{stripe}'
        f'border:1px solid {THEME["border"]};box-shadow:{shadow};margin-bottom:{margin_bottom};">'
        f'<div style="color:{THEME["text_secondary"]};font-size:9px;text-transform:uppercase;'
        f'letter-spacing:0.07em;margin-bottom:3px;">{label}</div>'
        f'<div style="color:{c};font-size:16px;font-weight:700;">{value}</div>'
        + sub_html + '</div>'
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


def _group_small_holdings(holdings: pd.DataFrame, threshold_pct: float = 1.0) -> pd.DataFrame:
    total = holdings['market_value'].sum()
    if total == 0:
        return holdings
    holdings = holdings.copy()
    holdings['_weight'] = holdings['market_value'] / total * 100
    main  = holdings[holdings['_weight'] >= threshold_pct].drop(columns='_weight')
    small = holdings[holdings['_weight'] <  threshold_pct]
    if small.empty:
        return main
    others_value = small['market_value'].sum()
    others_row = pd.DataFrame([{
        col: ('Others' if col == 'name'
              else (others_value if col == 'market_value' else float('nan')))
        for col in holdings.columns if col != '_weight'
    }])
    return pd.concat([main, others_row], ignore_index=True)


def _filter_main_holdings(holdings: pd.DataFrame, threshold_pct: float = 1.0) -> tuple[pd.DataFrame, int]:
    total = holdings['market_value'].sum()
    if total == 0:
        return holdings, 0
    weight   = holdings['market_value'] / total * 100
    main     = holdings[weight >= threshold_pct]
    excluded = int((weight < threshold_pct).sum())
    return main, excluded


def _build_sector_color_map(data: pd.DataFrame) -> dict[str, str]:
    from collections import defaultdict
    color_map: dict[str, str] = {}
    sector_col = 'sector' if 'sector' in data.columns else None
    real = data[data['name'] != 'Others'].copy()
    real['_sector'] = real[sector_col].fillna('Unknown') if sector_col else 'Unknown'
    sector_groups: dict[str, list] = defaultdict(list)
    for _, row in real.iterrows():
        sector_groups[row['_sector']].append((row['name'], row['market_value']))
    for sec, positions in sector_groups.items():
        positions.sort(key=lambda x: x[1], reverse=True)
        total = len(positions)
        for idx, (name, _) in enumerate(positions):
            color_map[name] = _sector_color(sec, idx, total)
    if 'Others' in data['name'].values:
        color_map['Others'] = _OTHERS_COLOR
    return color_map


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def render_stocks_deep_dive(
    stocks_holdings: pd.DataFrame,
    trades: pd.DataFrame
) -> None:
    THEME = get_active_theme()
    st.markdown(_subtab_css(THEME), unsafe_allow_html=True)

    if stocks_holdings.empty:
        st.warning('No stock holdings available.')
        return

    stock_ret = calculate_stock_returns(stocks_holdings, trades)

    tab_summary, tab_holdings, tab_performance = st.tabs(['Summary', 'Holdings', 'Performance'])

    with tab_summary:
        st.caption('Overview')
        _render_summary(stock_ret, stocks_holdings)

    with tab_holdings:
        st.caption('Holdings')
        _render_holdings(stocks_holdings)

    with tab_performance:
        st.caption('Performance')
        _render_performance(stocks_holdings, trades)


@st.fragment
def _render_allocation_chart(stocks_holdings: pd.DataFrame):
    THEME = get_active_theme()
    head_c1, head_c2 = st.columns([1, 1])
    with head_c1:
        st.subheader('Allocation')
    with head_c2:
        chart_type = st.radio(
            'Chart Type', ['Pie', 'Treemap'],
            horizontal=True, label_visibility='collapsed',
            key='stock_allocation_toggle'
        )
    if stocks_holdings.empty:
        st.info('No holdings data.')
        return

    if chart_type == 'Treemap':
        fig_alloc = px.treemap(
            stocks_holdings,
            path=[px.Constant('Portfolio'), 'name'],
            values='market_value',
            color='unrealized_pnl_pct',
            color_continuous_scale=_PNL_COLORSCALE,
            color_continuous_midpoint=0,
        )
        fig_alloc.update_traces(
            marker=dict(cornerradius=3, line=dict(color=THEME['border'], width=1)),
            textinfo='label+percent entry',
            textfont=dict(color='white', size=12, weight='bold'),
        )
    else:
        pie_data  = _group_small_holdings(stocks_holdings, threshold_pct=1.0)
        pie_data  = pie_data.sort_values('market_value', ascending=False).reset_index(drop=True)
        n_slices  = len(pie_data)
        color_map = _build_sector_color_map(pie_data)
        fig_alloc = px.pie(
            pie_data, values='market_value', names='name',
            hole=0.65, color='name', color_discrete_map=color_map,
        )
        fig_alloc.update_traces(
            textposition='auto', textinfo='percent+label',
            textfont=dict(color=THEME['text_primary'], size=11),
            marker=dict(line=dict(color=THEME['border'], width=1)),
            pull=[0.03] * n_slices, rotation=90,
        )

    fig_alloc.update_layout(
        **_chart_layout(THEME, height=580, margin=dict(t=10, b=60, l=40, r=40)),
        showlegend=False,
        coloraxis_showscale=False,
    )
    st.plotly_chart(fig_alloc, use_container_width=True, config={'displayModeBar': False})


# ---------------------------------------------------------------------------
# Sub-tab: Summary
# ---------------------------------------------------------------------------

def _render_summary(stock_ret: dict, stocks_holdings: pd.DataFrame):
    THEME = get_active_theme()
    col_status, col_allocation = st.columns([2, 3])

    with col_status:
        invested = stock_ret['invested_current']
        current  = stock_ret['value']
        max_val  = max(invested, current) * 1.2 if invested > 0 else 100

        fig_gauge = go.Figure(go.Indicator(
            mode='gauge+number+delta',
            value=current,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': 'Active Status', 'font': {'size': 16, 'color': THEME['text_secondary']}},
            delta={
                'reference':  invested,
                'increasing': {'color': THEME['success']},
                'decreasing': {'color': THEME['danger']},
            },
            gauge={
                'axis':        {'visible': False, 'range': [0, max_val]},
                'bar':         {'color': 'rgba(0,0,0,0)'},
                'bgcolor':     'rgba(0,0,0,0)',
                'borderwidth': 0,
                'steps': [
                    {'range': [0, invested], 'color': THEME['primary_alpha']},
                    ({'range': [invested, current], 'color': THEME['success_alpha']}
                     if current >= invested else
                     {'range': [current, invested], 'color': THEME['danger_alpha']}),
                ],
                'threshold': {
                    'line':      {'color': THEME['text_primary'], 'width': 3},
                    'thickness': 0.75,
                    'value':     current,
                },
            },
        ))
        fig_gauge.update_layout(
            **_chart_layout(THEME, height=260, margin=dict(l=20, r=20, t=20, b=0)),
        )
        st.plotly_chart(fig_gauge, use_container_width=True, config={'displayModeBar': False})

        unrealized_color   = THEME['success'] if stock_ret['unrealized']       >= 0 else THEME['danger']
        total_return_color = THEME['success'] if stock_ret['total_return_pct'] >= 0 else THEME['danger']

        kpis = [
            ('Invested',    f"\u20ac{stock_ret['invested_current']:,.0f}", None,               ''),
            ('Value',       f"\u20ac{stock_ret['value']:,.0f}",            None,               ''),
            ('Unrealized',  f"\u20ac{stock_ret['unrealized']:,.0f}",       unrealized_color,   f"{stock_ret['unrealized_pct']:+.1f}%"),
            ('Return %',    f"{stock_ret['unrealized_pct']:+.1f}%",        unrealized_color,   ''),
            ('Realized',    f"\u20ac{stock_ret['realized_gains']:,.0f}",   None,               ''),
            ('Total Ret.',  f"{stock_ret['total_return_pct']:+.1f}%",      total_return_color, ''),
        ]
        html_boxes = ''.join(_kpi(THEME, lbl, val, c, sub, '0') for lbl, val, c, sub in kpis)
        st.markdown(
            f'<div style="display:grid;grid-template-columns:1fr 1fr;grid-auto-rows:auto;gap:6px;margin-top:6px;">'
            + html_boxes + '</div>',
            unsafe_allow_html=True,
        )

    with col_allocation:
        _render_allocation_chart(stocks_holdings)


# ---------------------------------------------------------------------------
# Lollipop chart builder
# ---------------------------------------------------------------------------

def _build_lollipop_chart(
    df: pd.DataFrame,
    x_col: str,
    x_label: str,
    tick_suffix: str,
) -> tuple[go.Figure, int]:
    THEME = get_active_theme()
    df, excluded = _filter_main_holdings(df, threshold_pct=1.0)
    df = df.sort_values(x_col).reset_index(drop=True)
    n  = len(df)
    colors      = [THEME['success'] if v >= 0 else THEME['danger']       for v in df[x_col]]
    glow_colors = [THEME['success_alpha'] if v >= 0 else THEME['danger_alpha'] for v in df[x_col]]

    fig = go.Figure()
    for i, row in df.iterrows():
        fig.add_trace(go.Scatter(
            x=[0, row[x_col]], y=[row['name'], row['name']],
            mode='lines', line=dict(color=colors[i], width=2),
            showlegend=False, hoverinfo='skip',
        ))
    fig.add_trace(go.Scatter(
        x=df[x_col], y=df['name'], mode='markers',
        marker=dict(size=18, color=glow_colors, line=dict(width=0)),
        showlegend=False, hoverinfo='skip',
    ))
    fig.add_trace(go.Scatter(
        x=df[x_col], y=df['name'], mode='markers+text',
        marker=dict(size=10, color=colors, line=dict(color=THEME['border'], width=1)),
        text=[f'{v:+.2f}{tick_suffix}' for v in df[x_col]],
        textposition=['middle right' if v >= 0 else 'middle left' for v in df[x_col]],
        textfont=dict(color=colors, size=13),
        customdata=df[['ticker', 'unrealized_pnl', 'market_value']].values,
        hovertemplate=(
            '<b>%{y}</b> (%{customdata[0]})<br>'
            + x_label + ': %{x:+.2f}' + tick_suffix + '<br>'
            'P&L: \u20ac%{customdata[1]:,.0f}<br>'
            'Value: \u20ac%{customdata[2]:,.0f}<extra></extra>'
        ),
        showlegend=False,
    ))
    fig.add_vline(x=0, line_color=THEME['border'], line_width=1, opacity=0.8)
    fig.update_layout(
        **_chart_layout(THEME, height=max(180, n * 22), margin=dict(t=0, b=6, l=10, r=80)),
        xaxis=dict(
            title=x_label, showgrid=True, gridcolor=THEME['chart_grid'],
            zeroline=False, color=THEME['text_secondary'], ticksuffix=tick_suffix,
        ),
        yaxis=dict(
            title='', tickfont=dict(color=THEME['text_primary'], size=12), showgrid=False,
        ),
        hovermode='closest',
    )
    return fig, excluded


# ---------------------------------------------------------------------------
# Sub-tab: Holdings
# ---------------------------------------------------------------------------

@st.fragment
def _render_holdings(stocks_holdings: pd.DataFrame):
    THEME = get_active_theme()
    view = st.radio(
        'View', ['Performance', 'Contribution', 'Table'],
        horizontal=True, label_visibility='collapsed',
        key='holdings_view_toggle',
    )

    if view == 'Performance':
        fig, excluded = _build_lollipop_chart(
            stocks_holdings, x_col='unrealized_pnl_pct',
            x_label='Return %', tick_suffix='%',
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        if excluded:
            st.caption(f'{excluded} position(s) < 1% portfolio weight hidden')

    elif view == 'Contribution':
        df = stocks_holdings.copy()
        total = df['market_value'].sum()
        df['weight_pct']   = df['market_value'] / total * 100
        df['contribution'] = df['unrealized_pnl_pct'] * df['weight_pct'] / 100
        fig, excluded = _build_lollipop_chart(
            df, x_col='contribution',
            x_label='Contribution to Portfolio Return', tick_suffix=' pp',
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        if excluded:
            st.caption(f'{excluded} position(s) < 1% portfolio weight hidden')

    else:
        display = stocks_holdings.copy()
        total   = display['market_value'].sum()
        display['Weight'] = display['market_value'] / total * 100
        display = display[[
            'name', 'ticker', 'current_shares', 'total_cost',
            'market_value', 'Weight', 'unrealized_pnl', 'unrealized_pnl_pct',
        ]]
        display.columns = ['Stock', 'Symbol', 'Shares', 'Invested', 'Value',
                            'Weight %', 'P&L (\u20ac)', 'Return %']

        def color_pnl(val):
            if isinstance(val, (int, float)):
                if val > 0: return f'color:{THEME["success"]};font-weight:bold'
                if val < 0: return f'color:{THEME["danger"]};font-weight:bold'
            return ''

        st.dataframe(
            display.style
            .format({'Shares': '{:.2f}', 'Invested': '\u20ac{:,.0f}', 'Value': '\u20ac{:,.0f}',
                     'Weight %': '{:.1f}%', 'P&L (\u20ac)': '\u20ac{:,.0f}', 'Return %': '{:+.2f}%'})
            .applymap(color_pnl, subset=['P&L (\u20ac)', 'Return %'])
            .bar(subset=['Weight %'], color=THEME['primary_alpha'], vmin=0, vmax=100),
            use_container_width=True, height=500, hide_index=True,
        )


# ---------------------------------------------------------------------------
# Performance helpers
# ---------------------------------------------------------------------------

def _build_yearly_pnl_chart(trades: pd.DataFrame) -> go.Figure | None:
    THEME = get_active_theme()
    required = {'sell_date', 'realized_gain'}
    if trades.empty or not required.issubset(trades.columns):
        return None
    df = trades.copy()
    df['year'] = pd.to_datetime(df['sell_date']).dt.year
    yearly = (
        df.groupby('year', as_index=False)
        .agg(realized_gain=('realized_gain', 'sum'), trade_count=('realized_gain', 'count'))
        .sort_values('year')
    )
    yearly['cumulative'] = yearly['realized_gain'].cumsum()
    yearly['color']      = yearly['realized_gain'].apply(lambda v: THEME['success'] if v >= 0 else THEME['danger'])
    yearly['bar_fill']   = yearly['realized_gain'].apply(lambda v: THEME['success_alpha'] if v >= 0 else THEME['danger_alpha'])
    year_labels = yearly['year'].astype(str).tolist()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=year_labels, y=yearly['realized_gain'],
        marker=dict(color=yearly['bar_fill'], line=dict(color=yearly['color'], width=2)),
        text=['\u20ac' + f'{v:+,.0f}' for v in yearly['realized_gain']],
        textposition='outside',
        textfont=dict(color=yearly['color'], size=12, weight='bold'),
        customdata=yearly[['trade_count', 'cumulative']].values,
        hovertemplate=(
            '<b>%{x}</b><br>Realized P&L: \u20ac%{y:+,.0f}<br>'
            'Trades closed: %{customdata[0]}<br>'
            'Cumulative: \u20ac%{customdata[1]:+,.0f}<extra></extra>'
        ),
        showlegend=False, name='Annual P&L',
    ))
    fig.add_trace(go.Scatter(
        x=year_labels, y=yearly['cumulative'],
        mode='lines+markers',
        line=dict(color=THEME['primary'], width=2, dash='dot'),
        marker=dict(size=7, color=THEME['primary'], line=dict(color=THEME['border'], width=1)),
        hovertemplate='Cumulative: \u20ac%{y:+,.0f}<extra></extra>',
        showlegend=True, name='Cumulative',
    ))
    fig.update_layout(
        **_chart_layout(THEME, height=480, margin=dict(t=10, b=10, l=10, r=10)),
        bargap=0.35,
        xaxis=dict(
            title='', type='category', showgrid=False,
            color=THEME['text_secondary'],
            tickfont=dict(size=13, color=THEME['text_primary']),
        ),
        yaxis=dict(
            title='Realized P&L (\u20ac)', showgrid=True, gridcolor=THEME['chart_grid'],
            zeroline=True, zerolinecolor=THEME['border'], zerolinewidth=1,
            color=THEME['text_secondary'],
        ),
        legend=dict(
            orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1,
            font=dict(color=THEME['text_secondary'], size=11),
        ),
    )
    return fig


def _build_done_trades_df(trades: pd.DataFrame) -> pd.DataFrame | None:
    required = {
        'sell_date', 'security_name', 'avg_buy_price',
        'shares_sold', 'sell_price', 'realized_gain',
        'realized_gain_percent', 'holding_period_days',
    }
    missing = required - set(trades.columns)
    if missing:
        st.info('Trade history structure is incomplete. Missing: ' + ', '.join(sorted(missing)))
        return None
    df = trades.copy()
    df['total_invested'] = df['avg_buy_price'] * df['shares_sold']
    df['total_realized'] = df['sell_price']    * df['shares_sold']
    display = df[[
        'sell_date', 'security_name', 'total_invested', 'total_realized',
        'realized_gain', 'realized_gain_percent', 'holding_period_days',
    ]].copy()
    display.columns = [
        'Date', 'Name', 'Total Invested (\u20ac)', 'Total Realized (\u20ac)',
        'Performance (\u20ac)', 'Performance (%)', 'Days Held',
    ]
    return display.sort_values('Date', ascending=False)


def _style_done_trades(df: pd.DataFrame) -> 'pd.io.formats.style.Styler':
    THEME = get_active_theme()

    def color_perf(val):
        if isinstance(val, (int, float)):
            if val > 0: return f'color:{THEME["success"]};font-weight:bold'
            if val < 0: return f'color:{THEME["danger"]};font-weight:bold'
        return ''

    return (
        df.style
        .format({
            'Date':                    lambda t: t.strftime('%Y-%m-%d') if hasattr(t, 'strftime') else str(t),
            'Total Invested (\u20ac)': '\u20ac{:,.2f}',
            'Total Realized (\u20ac)': '\u20ac{:,.2f}',
            'Performance (\u20ac)':    '\u20ac{:+,.2f}',
            'Performance (%)':         '{:+.2f}%',
            'Days Held':               '{:.0f}',
        })
        .applymap(color_perf, subset=['Performance (\u20ac)', 'Performance (%)'])
    )


def _render_best_worst_panel(df: pd.DataFrame) -> None:
    THEME = get_active_theme()
    best5  = df.nlargest(5,  'Performance (%)')
    worst5 = df.nsmallest(5, 'Performance (%)')
    _col_pct = 'Performance (%)'
    _col_eur = 'Performance (\u20ac)'

    st.markdown('#### Hall of Fame')
    for _, row in best5.iterrows():
        pct  = row[_col_pct]; eur = row[_col_eur]; name = row['Name']
        st.markdown(
            f'<div style="background:{THEME["bg_card"]};border:1px solid {THEME["success"]}22;'
            f'border-left:3px solid {THEME["success"]};border-radius:6px;padding:8px 10px;margin-bottom:6px;">'
            f'<div style="color:{THEME["text_primary"]};font-size:12px;font-weight:bold;">{name}</div>'
            f'<div style="color:{THEME["success"]};font-size:14px;font-weight:bold;">{pct:+.2f}%'
            f'<span style="color:{THEME["text_secondary"]};font-size:11px;"> (\u20ac{eur:+,.2f})</span></div></div>',
            unsafe_allow_html=True,
        )

    st.markdown('#### Hall of Shame')
    for _, row in worst5.iterrows():
        pct  = row[_col_pct]; eur = row[_col_eur]; name = row['Name']
        st.markdown(
            f'<div style="background:{THEME["bg_card"]};border:1px solid {THEME["danger"]}22;'
            f'border-left:3px solid {THEME["danger"]};border-radius:6px;padding:8px 10px;margin-bottom:6px;">'
            f'<div style="color:{THEME["text_primary"]};font-size:12px;font-weight:bold;">{name}</div>'
            f'<div style="color:{THEME["danger"]};font-size:14px;font-weight:bold;">{pct:+.2f}%'
            f'<span style="color:{THEME["text_secondary"]};font-size:11px;"> (\u20ac{eur:+,.2f})</span></div></div>',
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Sub-tab: Performance
# ---------------------------------------------------------------------------

@st.fragment
def _render_performance(stocks_holdings: pd.DataFrame, trades: pd.DataFrame):
    THEME = get_active_theme()
    view = st.radio(
        'View', ['Charts', 'Closed Trades'],
        horizontal=True, label_visibility='collapsed',
        key='performance_view_toggle',
    )

    if view == 'Charts':
        col_yearly, col_scatter = st.columns([1, 1])

        with col_yearly:
            st.subheader('Harvest Report')
            if trades.empty:
                st.info('No trade history available.')
            else:
                fig_yearly = _build_yearly_pnl_chart(trades)
                if fig_yearly:
                    st.plotly_chart(fig_yearly, use_container_width=True, config={'displayModeBar': False})
                else:
                    st.info('Trade data is missing required columns.')

        with col_scatter:
            st.subheader('Bubble Map')
            plot_data = stocks_holdings.copy()
            total_val = plot_data['market_value'].sum()
            plot_data['portfolio_weight'] = plot_data['market_value'] / total_val * 100
            pnl_vals  = plot_data['unrealized_pnl_pct']
            abs_max   = max(abs(pnl_vals.min()), abs(pnl_vals.max()), 1)
            plot_data['_color_norm'] = (pnl_vals / abs_max + 1) / 2

            def _point_color(norm: float) -> str:
                if norm >= 0.5:
                    t = (norm - 0.5) * 2
                    if t is None or (isinstance(t, float) and math.isnan(t)):
                        t = 0.5
                    t = max(0.0, min(1.0, float(t)))
                    r = int(75 + (239 - 75) * t)
                    g = int(85 + (68 - 85) * t)
                    b = int(99 + (68 - 99) * t)
                    return f'rgba({r},{g},{b},0.9)'
                else:
                    t = (0.5 - norm) * 2
                    if t is None or (isinstance(t, float) and math.isnan(t)):
                        t = 0.5
                    t = max(0.0, min(1.0, float(t)))
                    r = int(75 + (239 - 75) * t)
                    g = int(85 + (68 - 85) * t)
                    b = int(99 + (68 - 99) * t)
                    return f'rgba({r},{g},{b},0.9)'

            plot_data['_pt_color'] = plot_data['_color_norm'].apply(_point_color)
            fig_sc = go.Figure()
            for _, row in plot_data.iterrows():
                fig_sc.add_trace(go.Scatter(
                    x=[row['portfolio_weight']], y=[row['unrealized_pnl_pct']],
                    mode='markers+text',
                    marker=dict(
                        size=max(12, min(48, row['total_cost'] / total_val * 400)),
                        color=row['_pt_color'],
                        line=dict(color=THEME['border'], width=1),
                    ),
                    text=[row['ticker']], textposition='top center',
                    textfont=dict(color=THEME['text_primary'], size=10, weight='bold'),
                    name=row['name'],
                    hovertemplate=(
                        f"<b>{row['name']}</b><br>"
                        'Weight: %{x:.1f}%<br>Return: %{y:+.2f}%<extra></extra>'
                    ),
                    showlegend=False,
                ))
            fig_sc.add_hline(y=0, line_dash='dash', line_color=THEME['border'], opacity=0.6)
            fig_sc.update_layout(
                **_chart_layout(THEME, height=480, margin=dict(t=8, b=0, l=0, r=0)),
                xaxis=dict(title='Portfolio Weight (%)', showgrid=True,
                           gridcolor=THEME['chart_grid'], color=THEME['text_secondary']),
                yaxis=dict(title='Return (%)', showgrid=True,
                           gridcolor=THEME['chart_grid'], color=THEME['text_secondary']),
                hovermode='closest',
            )
            st.plotly_chart(fig_sc, use_container_width=True, config={'displayModeBar': False})

    else:  # Closed Trades
        if trades.empty:
            st.info('No trade history available.')
            return
        done_df = _build_done_trades_df(trades)
        if done_df is None:
            return
        n_trades = len(done_df)
        table_h  = max(420, min(n_trades * 42 + 60, 10 * 56 + 120))
        col_table, col_highlights = st.columns([2, 1])
        with col_table:
            st.caption(str(n_trades) + ' closed trade(s) \u00b7 sorted by date')
            st.dataframe(_style_done_trades(done_df),
                         use_container_width=True, height=table_h, hide_index=True)
        with col_highlights:
            if n_trades >= 2:
                _render_best_worst_panel(done_df)
            else:
                st.info('At least 2 trades needed for Hall of Fame / Hall of Shame.')
