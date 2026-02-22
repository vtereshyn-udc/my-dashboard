"""
Sales & Traffic Dashboard v1.1
Amazon SP-API → spapi.sales_traffic_report → Streamlit
Схема: date, parent_asin, child_asin, title, sku + sessions, page_views, sales...
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Sales & Traffic Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

TABLE = "spapi.sales_traffic_report"

st.markdown("""
<style>
    .stApp { background-color: #0f1117; color: #e0e0e0; }
    [data-testid="metric-container"] {
        background: linear-gradient(135deg, #1a1d2e, #252840);
        border: 1px solid #2d3561;
        border-radius: 12px;
        padding: 16px;
    }
    [data-testid="stMetricValue"] { color: #7c9fff; font-size: 1.8rem !important; }
    [data-testid="stMetricLabel"] { color: #8892b0; font-size: 0.8rem; }
    h1 { color: #7c9fff !important; }
    h2, h3 { color: #ccd6f6 !important; }
    [data-testid="stSidebar"] { background-color: #0d1117; border-right: 1px solid #21262d; }
    hr { border-color: #21262d; }
</style>
""", unsafe_allow_html=True)


# ============================================================
# 🗄️ БД
# ============================================================

@st.cache_resource
def get_engine():
    db_url = os.getenv("DATABASE_URL") or (
        f"postgresql://{os.getenv('DB_USER','postgres')}:"
        f"{os.getenv('DB_PASSWORD','')}@"
        f"{os.getenv('DB_HOST','localhost')}:"
        f"{os.getenv('DB_PORT','5432')}/"
        f"{os.getenv('DB_NAME','amazon')}"
    )
    if "sslmode" not in db_url:
        db_url += "?sslmode=require"
    return create_engine(db_url)


@st.cache_data(ttl=1800)
def load_data(days_back: int = 30, child_asin: str = "Все") -> pd.DataFrame:
    engine = get_engine()
    date_from = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
    asin_filter = "AND child_asin = :asin" if child_asin != "Все" else ""

    query = f"""
        SELECT
            date, parent_asin, child_asin, title, sku,
            sessions, sessions_b2b,
            browser_sessions, mobile_app_sessions,
            session_percentage,
            page_views, page_views_b2b,
            browser_page_views, mobile_app_page_views,
            page_views_percentage,
            buy_box_percentage, buy_box_percentage_b2b,
            unit_session_percentage, unit_session_percentage_b2b,
            units_ordered, units_ordered_b2b,
            ordered_product_sales, ordered_product_sales_b2b,
            total_order_items, total_order_items_b2b
        FROM {TABLE}
        WHERE date >= :date_from {asin_filter}
        ORDER BY date DESC, ordered_product_sales DESC
    """
    params = {"date_from": date_from}
    if child_asin != "Все":
        params["asin"] = child_asin

    try:
        with engine.connect() as conn:
            df = pd.read_sql(text(query), conn, params=params)
        df['date'] = pd.to_datetime(df['date'])
        return df
    except Exception as e:
        st.error(f"❌ Ошибка БД: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=3600)
def load_asin_list() -> list:
    try:
        with get_engine().connect() as conn:
            rows = conn.execute(text(
                f"SELECT DISTINCT child_asin FROM {TABLE} ORDER BY child_asin"
            ))
            return ["Все"] + [r[0] for r in rows if r[0]]
    except:
        return ["Все"]


# ============================================================
# 📊 БЛОКИ
# ============================================================

def kpi_row(df):
    c1,c2,c3,c4,c5,c6 = st.columns(6)
    c1.metric("💰 Продажи",   f"${df['ordered_product_sales'].sum():,.0f}")
    c2.metric("📦 Юниты",     f"{df['units_ordered'].sum():,}")
    c3.metric("👥 Сессии",    f"{df['sessions'].sum():,}")
    c4.metric("👁️ Просмотры", f"{df['page_views'].sum():,}")
    c5.metric("🎯 CVR",       f"{df['unit_session_percentage'].mean():.1f}%")
    c6.metric("🏆 Buy Box",   f"{df['buy_box_percentage'].mean():.1f}%")


def chart_sales_sessions(df):
    daily = df.groupby('date').agg(
        sales=('ordered_product_sales','sum'),
        sessions=('sessions','sum'),
        cvr=('unit_session_percentage','mean'),
    ).reset_index()

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        subplot_titles=["💰 Продажи ($) и Сессии", "🎯 CVR (%)"],
        row_heights=[0.65, 0.35], vertical_spacing=0.08
    )
    fig.add_trace(go.Bar(x=daily['date'], y=daily['sales'],
        name="Продажи $", marker_color='#7c9fff', opacity=0.85), row=1, col=1)
    fig.add_trace(go.Scatter(x=daily['date'], y=daily['sessions'],
        name="Сессии", line=dict(color='#ff7c7c', width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=daily['date'], y=daily['cvr'],
        name="CVR %", fill='tozeroy',
        fillcolor='rgba(100,200,150,0.15)',
        line=dict(color='#64c896', width=2)), row=2, col=1)

    fig.update_layout(
        height=450, template='plotly_dark',
        paper_bgcolor='#1a1d2e', plot_bgcolor='#1a1d2e',
        legend=dict(orientation="h", y=1.05),
        margin=dict(l=0,r=0,t=40,b=0), hovermode='x unified',
    )
    fig.update_xaxes(gridcolor='#2d3561')
    fig.update_yaxes(gridcolor='#2d3561')
    st.plotly_chart(fig, use_container_width=True)


def chart_top_asins(df):
    top = (
        df.groupby('child_asin').agg(
            sales=('ordered_product_sales','sum'),
            units=('units_ordered','sum'),
            sessions=('sessions','sum'),
            cvr=('unit_session_percentage','mean'),
            buybox=('buy_box_percentage','mean'),
            title=('title','first'),
        ).reset_index()
        .sort_values('sales', ascending=False).head(15)
    )

    c1, c2 = st.columns([1.2, 1])
    with c1:
        fig = px.bar(top, x='sales', y='child_asin', orientation='h',
            title="🏆 Топ ASIN по продажам ($)",
            color='sales', color_continuous_scale='Blues',
            hover_data={'title':True,'units':True})
        fig.update_layout(height=400, template='plotly_dark',
            paper_bgcolor='#1a1d2e', plot_bgcolor='#1a1d2e',
            showlegend=False, coloraxis_showscale=False,
            margin=dict(l=0,r=0,t=40,b=0),
            yaxis=dict(autorange='reversed'))
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        fig2 = px.scatter(top, x='sessions', y='cvr',
            size='sales', color='buybox',
            title="🎯 Сессии vs CVR (размер=продажи, цвет=BuyBox)",
            hover_name='child_asin', hover_data={'title':True},
            color_continuous_scale='RdYlGn',
            labels={'cvr':'CVR %','buybox':'Buy Box %'})
        fig2.update_layout(height=400, template='plotly_dark',
            paper_bgcolor='#1a1d2e', plot_bgcolor='#1a1d2e',
            margin=dict(l=0,r=0,t=40,b=0))
        st.plotly_chart(fig2, use_container_width=True)


def chart_traffic_split(df):
    c1, c2 = st.columns(2)
    with c1:
        fig = go.Figure(data=[go.Pie(
            labels=['Browser','Mobile App'],
            values=[df['browser_page_views'].sum(), df['mobile_app_page_views'].sum()],
            hole=0.5, marker_colors=['#7c9fff','#ff9f7c'])])
        fig.update_layout(title="👁️ Просмотры: браузер vs мобайл",
            height=300, template='plotly_dark',
            paper_bgcolor='#1a1d2e', margin=dict(l=0,r=0,t=40,b=0))
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        fig2 = go.Figure(data=[go.Pie(
            labels=['Browser','Mobile App'],
            values=[df['browser_sessions'].sum(), df['mobile_app_sessions'].sum()],
            hole=0.5, marker_colors=['#64c896','#c864c8'])])
        fig2.update_layout(title="👥 Сессии: браузер vs мобайл",
            height=300, template='plotly_dark',
            paper_bgcolor='#1a1d2e', margin=dict(l=0,r=0,t=40,b=0))
        st.plotly_chart(fig2, use_container_width=True)


def chart_b2b(df):
    daily = df.groupby('date').agg(
        sales=('ordered_product_sales','sum'),
        sales_b2b=('ordered_product_sales_b2b','sum'),
    ).reset_index()
    daily['sales_b2c'] = daily['sales'] - daily['sales_b2b']

    fig = go.Figure()
    fig.add_trace(go.Bar(name='B2C', x=daily['date'], y=daily['sales_b2c'], marker_color='#7c9fff'))
    fig.add_trace(go.Bar(name='B2B', x=daily['date'], y=daily['sales_b2b'], marker_color='#ffd700'))
    fig.update_layout(
        barmode='stack', title="🏢 Продажи B2C vs B2B по дням",
        height=300, template='plotly_dark',
        paper_bgcolor='#1a1d2e', plot_bgcolor='#1a1d2e',
        margin=dict(l=0,r=0,t=40,b=0),
        hovermode='x unified', legend=dict(orientation="h", y=1.05))
    st.plotly_chart(fig, use_container_width=True)


def table_detail(df):
    cols = ['date','child_asin','title','sku',
            'ordered_product_sales','units_ordered',
            'sessions','page_views',
            'unit_session_percentage','buy_box_percentage']
    cols = [c for c in cols if c in df.columns]
    t = df[cols].copy()
    t['date'] = t['date'].dt.strftime('%Y-%m-%d')
    t = t.rename(columns={
        'child_asin':'ASIN','ordered_product_sales':'Sales $',
        'units_ordered':'Units','sessions':'Sessions',
        'page_views':'Page Views',
        'unit_session_percentage':'CVR %','buy_box_percentage':'Buy Box %'})
    st.dataframe(t, use_container_width=True, height=320,
        column_config={
            "Sales $": st.column_config.NumberColumn(format="$%.2f"),
            "CVR %": st.column_config.NumberColumn(format="%.1f%%"),
            "Buy Box %": st.column_config.NumberColumn(format="%.1f%%"),
        })


# ============================================================
# 🚀 MAIN
# ============================================================

def main():
    st.markdown("## 📈 Sales & Traffic Dashboard")
    st.caption(f"`{TABLE}` · {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    st.divider()

    with st.sidebar:
        st.markdown("### ⚙️ Фильтры")
        days_back = st.selectbox("📅 Период", [7,14,30,60,90], index=2,
            format_func=lambda x: f"Последние {x} дней")
        asin_list = load_asin_list()
        selected_asin = st.selectbox("🔍 ASIN", asin_list)
        st.divider()
        if st.button("🔄 Обновить", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        st.divider()
        st.markdown("### 📊 Разделы")
        show_traffic = st.checkbox("📱 Трафик браузер/мобайл", True)
        show_b2b     = st.checkbox("🏢 B2B vs B2C", True)
        show_table   = st.checkbox("📋 Детальная таблица", False)

    with st.spinner("Загружаем данные..."):
        df = load_data(days_back, selected_asin)

    if df.empty:
        st.warning("⚠️ Нет данных. Проверьте подключение к БД.")
        with st.expander("💡 Настройка подключения"):
            st.code('DATABASE_URL = "postgresql://user:pass@host:5432/dbname"')
            st.markdown("Streamlit Cloud → **Settings → Secrets**")
        return

    kpi_row(df)
    st.divider()
    chart_sales_sessions(df)
    st.divider()

    st.markdown("### 🏆 Анализ по ASIN")
    chart_top_asins(df)

    if show_traffic:
        st.divider()
        st.markdown("### 📱 Источники трафика")
        chart_traffic_split(df)

    if show_b2b:
        st.divider()
        st.markdown("### 🏢 B2C vs B2B")
        chart_b2b(df)

    if show_table:
        st.divider()
        st.markdown("### 📋 Детальные данные")
        table_detail(df)

    with st.expander("ℹ️ Статистика выборки"):
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Строк", f"{len(df):,}")
        c2.metric("ASIN", f"{df['child_asin'].nunique():,}")
        c3.metric("Дней", f"{df['date'].nunique():,}")
        c4.metric("SKU",  f"{df['sku'].nunique():,}")


if __name__ == "__main__":
    main()
