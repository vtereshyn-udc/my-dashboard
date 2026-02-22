"""
Sales & Traffic Dashboard v1.3
+ AI-инсайты через Google Gemini
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

# ============================================================
# 🌐 ПЕРЕВОДЫ
# ============================================================

TRANSLATIONS = {
    "EN": {
        "title": "📈 Sales & Traffic Dashboard",
        "period": "📅 Period",
        "asin": "🔍 ASIN",
        "refresh": "🔄 Refresh",
        "sections": "📊 Sections",
        "traffic_split": "📱 Browser / Mobile Traffic",
        "b2b": "🏢 B2B vs B2C",
        "table": "📋 Detailed Table",
        "sales": "💰 Sales",
        "units": "📦 Units",
        "sessions": "👥 Sessions",
        "pageviews": "👁️ Page Views",
        "cvr": "🎯 CVR",
        "buybox": "🏆 Buy Box",
        "all": "All",
        "days": lambda x: f"Last {x} days",
        "loading": "Loading data...",
        "no_data": "⚠️ No data. Check DB connection.",
        "top_asins": "🏆 Top ASINs by Sales",
        "scatter_title": "🎯 Sessions vs CVR (size=sales, color=BuyBox)",
        "sales_sessions_title": "💰 Sales ($) and Sessions",
        "cvr_title": "🎯 CVR (%)",
        "pv_title": "👁️ Page Views: Browser vs Mobile",
        "sess_title": "👥 Sessions: Browser vs Mobile",
        "b2b_title": "🏢 Sales B2C vs B2B by Day",
        "rows": "Rows", "days_label": "Days", "sku": "SKU",
        "info": "ℹ️ Query stats",
        "browser": "Browser", "mobile": "Mobile App",
        "theme": "🎨 Theme", "dark": "Dark", "light": "Light",
        "language": "🌐 Language",
        "ai_section": "🤖 AI Insights",
        "ai_button": "✨ Analyze with Gemini AI",
        "ai_loading": "🤖 Gemini is analyzing your data...",
        "ai_prompt_label": "💬 Ask a question about your data",
        "ai_prompt_placeholder": "Why did sales drop? What are the top growth opportunities?",
        "ai_ask": "Ask AI",
        "ai_error": "❌ Gemini API error",
        "ai_no_key": "⚠️ Add GEMINI_API_KEY to Streamlit Secrets",
    },
    "UA": {
        "title": "📈 Дашборд продажів і трафіку",
        "period": "📅 Період",
        "asin": "🔍 ASIN",
        "refresh": "🔄 Оновити",
        "sections": "📊 Розділи",
        "traffic_split": "📱 Трафік браузер/мобайл",
        "b2b": "🏢 B2B vs B2C",
        "table": "📋 Детальна таблиця",
        "sales": "💰 Продажі",
        "units": "📦 Юніти",
        "sessions": "👥 Сесії",
        "pageviews": "👁️ Перегляди",
        "cvr": "🎯 CVR",
        "buybox": "🏆 Buy Box",
        "all": "Всі",
        "days": lambda x: f"Останні {x} днів",
        "loading": "Завантажуємо дані...",
        "no_data": "⚠️ Немає даних. Перевірте підключення до БД.",
        "top_asins": "🏆 Топ ASIN за продажами",
        "scatter_title": "🎯 Сесії vs CVR (розмір=продажі, колір=BuyBox)",
        "sales_sessions_title": "💰 Продажі ($) і Сесії",
        "cvr_title": "🎯 CVR (%)",
        "pv_title": "👁️ Перегляди: браузер vs мобайл",
        "sess_title": "👥 Сесії: браузер vs мобайл",
        "b2b_title": "🏢 Продажі B2C vs B2B по днях",
        "rows": "Рядків", "days_label": "Днів", "sku": "SKU",
        "info": "ℹ️ Статистика вибірки",
        "browser": "Браузер", "mobile": "Мобайл",
        "theme": "🎨 Тема", "dark": "Темна", "light": "Світла",
        "language": "🌐 Мова",
        "ai_section": "🤖 AI Аналіз",
        "ai_button": "✨ Аналізувати з Gemini AI",
        "ai_loading": "🤖 Gemini аналізує ваші дані...",
        "ai_prompt_label": "💬 Запитайте про ваші дані",
        "ai_prompt_placeholder": "Чому впали продажі? Які можливості для зростання?",
        "ai_ask": "Запитати AI",
        "ai_error": "❌ Помилка Gemini API",
        "ai_no_key": "⚠️ Додайте GEMINI_API_KEY до Streamlit Secrets",
    },
    "RU": {
        "title": "📈 Дашборд продаж и трафика",
        "period": "📅 Период",
        "asin": "🔍 ASIN",
        "refresh": "🔄 Обновить",
        "sections": "📊 Разделы",
        "traffic_split": "📱 Трафик браузер/мобайл",
        "b2b": "🏢 B2B vs B2C",
        "table": "📋 Детальная таблица",
        "sales": "💰 Продажи",
        "units": "📦 Юниты",
        "sessions": "👥 Сессии",
        "pageviews": "👁️ Просмотры",
        "cvr": "🎯 CVR",
        "buybox": "🏆 Buy Box",
        "all": "Все",
        "days": lambda x: f"Последние {x} дней",
        "loading": "Загружаем данные...",
        "no_data": "⚠️ Нет данных. Проверьте подключение к БД.",
        "top_asins": "🏆 Топ ASIN по продажам",
        "scatter_title": "🎯 Сессии vs CVR (размер=продажи, цвет=BuyBox)",
        "sales_sessions_title": "💰 Продажи ($) и Сессии",
        "cvr_title": "🎯 CVR (%)",
        "pv_title": "👁️ Просмотры: браузер vs мобайл",
        "sess_title": "👥 Сессии: браузер vs мобайл",
        "b2b_title": "🏢 Продажи B2C vs B2B по дням",
        "rows": "Строк", "days_label": "Дней", "sku": "SKU",
        "info": "ℹ️ Статистика выборки",
        "browser": "Браузер", "mobile": "Мобайл",
        "theme": "🎨 Тема", "dark": "Тёмная", "light": "Светлая",
        "language": "🌐 Язык",
        "ai_section": "🤖 AI Инсайты",
        "ai_button": "✨ Анализировать с Gemini AI",
        "ai_loading": "🤖 Gemini анализирует ваши данные...",
        "ai_prompt_label": "💬 Задайте вопрос о ваших данных",
        "ai_prompt_placeholder": "Почему упали продажи? Какие возможности для роста?",
        "ai_ask": "Спросить AI",
        "ai_error": "❌ Ошибка Gemini API",
        "ai_no_key": "⚠️ Добавьте GEMINI_API_KEY в Streamlit Secrets",
    },
}

DARK_THEME = {
    "bg": "#0f1117", "sidebar_bg": "#0d1117",
    "card_bg": "linear-gradient(135deg, #1a1d2e, #252840)",
    "card_border": "#2d3561", "text": "#e0e0e0", "label": "#8892b0",
    "metric_val": "#7c9fff", "hr": "#21262d",
    "plot_bg": "#1a1d2e", "paper_bg": "#1a1d2e", "grid": "#2d3561",
    "template": "plotly_dark",
    "ai_bg": "#1a1d2e", "ai_border": "#2d3561",
}

LIGHT_THEME = {
    "bg": "#f5f7fa", "sidebar_bg": "#ffffff",
    "card_bg": "linear-gradient(135deg, #ffffff, #eef2ff)",
    "card_border": "#c7d2fe", "text": "#1e293b", "label": "#64748b",
    "metric_val": "#3b5bdb", "hr": "#e2e8f0",
    "plot_bg": "#ffffff", "paper_bg": "#f8fafc", "grid": "#e2e8f0",
    "template": "plotly_white",
    "ai_bg": "#eef2ff", "ai_border": "#c7d2fe",
}


def apply_theme(t):
    is_light = t['bg'] == "#f5f7fa"
    sidebar_text = "#1e293b" if is_light else "#e0e0e0"
    input_bg = "#ffffff" if is_light else "#1a1d2e"
    input_text = "#1e293b" if is_light else "#e0e0e0"

    st.markdown(f"""
    <style>
        .stApp {{ background-color: {t['bg']}; color: {t['text']}; }}
        [data-testid="metric-container"] {{
            background: {t['card_bg']};
            border: 1px solid {t['card_border']};
            border-radius: 12px; padding: 16px;
        }}
        [data-testid="stMetricValue"] {{ color: {t['metric_val']}; font-size: 1.8rem !important; }}
        [data-testid="stMetricLabel"] {{ color: {t['label']}; font-size: 0.8rem; }}
        h1, h2, h3 {{ color: {t['metric_val']} !important; }}

        /* Сайдбар — текст и фон */
        [data-testid="stSidebar"] {{
            background-color: {t['sidebar_bg']} !important;
            border-right: 1px solid {t['card_border']};
        }}
        [data-testid="stSidebar"] * {{
            color: {sidebar_text} !important;
        }}

        /* Селекторы и инпуты */
        [data-testid="stSidebar"] .stSelectbox > div > div {{
            background-color: {input_bg} !important;
            color: {input_text} !important;
        }}
        [data-testid="stSidebar"] label {{
            color: {sidebar_text} !important;
        }}
        [data-testid="stSidebar"] .stRadio label {{
            color: {sidebar_text} !important;
        }}
        [data-testid="stSidebar"] .stCheckbox label {{
            color: {sidebar_text} !important;
        }}

        /* Основной контент */
        p, span, div {{ color: {t['text']}; }}
        .stMarkdown p {{ color: {t['text']} !important; }}

        /* Выпадающий список — опции */
        [data-testid="stSidebar"] ul[data-testid="stSelectboxVirtualDropdown"] {{
            background-color: {input_bg} !important;
        }}
        [data-testid="stSidebar"] ul li span {{
            color: {input_text} !important;
        }}
        /* Общий фикс для всех дропдаунов */
        div[data-baseweb="popover"] ul {{
            background-color: {input_bg} !important;
        }}
        div[data-baseweb="popover"] ul li {{
            background-color: {input_bg} !important;
            color: {input_text} !important;
        }}
        div[data-baseweb="popover"] ul li:hover {{
            background-color: {t['card_border']} !important;
        }}

        hr {{ border-color: {t['hr']}; }}
        .ai-box {{
            background: {t['ai_bg']};
            border: 1px solid {t['ai_border']};
            border-radius: 16px;
            padding: 24px;
            margin-top: 12px;
            line-height: 1.8;
            font-size: 1rem;
            color: {t['text']};
        }}
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
    asin_filter = "AND child_asin = :asin" if child_asin not in ("Все","All","Всі") else ""

    query = f"""
        SELECT date, parent_asin, child_asin, title, sku,
            sessions, sessions_b2b, browser_sessions, mobile_app_sessions, session_percentage,
            page_views, page_views_b2b, browser_page_views, mobile_app_page_views, page_views_percentage,
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
    if asin_filter:
        params["asin"] = child_asin

    try:
        with engine.connect() as conn:
            df = pd.read_sql(text(query), conn, params=params)
        df['date'] = pd.to_datetime(df['date'])
        return df
    except Exception as e:
        st.error(f"❌ DB Error: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=3600)
def load_asin_list() -> list:
    try:
        with get_engine().connect() as conn:
            rows = conn.execute(text(f"SELECT DISTINCT child_asin FROM {TABLE} ORDER BY child_asin"))
            return [r[0] for r in rows if r[0]]
    except:
        return []


# ============================================================
# 🤖 GEMINI AI
# ============================================================

def build_data_summary(df: pd.DataFrame, lang: str) -> str:
    """Формирует краткое саммари данных для промпта"""
    daily = df.groupby('date').agg(
        sales=('ordered_product_sales','sum'),
        sessions=('sessions','sum'),
        cvr=('unit_session_percentage','mean'),
        buybox=('buy_box_percentage','mean'),
        units=('units_ordered','sum'),
    ).reset_index().sort_values('date')

    top_asins = (
        df.groupby('child_asin').agg(
            sales=('ordered_product_sales','sum'),
            cvr=('unit_session_percentage','mean'),
            buybox=('buy_box_percentage','mean'),
            title=('title','first'),
        ).reset_index().sort_values('sales', ascending=False).head(5)
    )

    total_sales   = df['ordered_product_sales'].sum()
    total_units   = df['units_ordered'].sum()
    total_sessions= df['sessions'].sum()
    avg_cvr       = df['unit_session_percentage'].mean()
    avg_buybox    = df['buy_box_percentage'].mean()
    days          = df['date'].nunique()
    num_asins     = df['child_asin'].nunique()

    # Тренд (сравниваем первую и вторую половину)
    mid = len(daily) // 2
    if mid > 0:
        first_half  = daily.iloc[:mid]['sales'].mean()
        second_half = daily.iloc[mid:]['sales'].mean()
        trend_pct   = ((second_half - first_half) / first_half * 100) if first_half > 0 else 0
        trend_str   = f"+{trend_pct:.1f}%" if trend_pct >= 0 else f"{trend_pct:.1f}%"
    else:
        trend_str = "N/A"

    # Лучший и худший день
    if not daily.empty:
        best_day  = daily.loc[daily['sales'].idxmax()]
        worst_day = daily.loc[daily['sales'].idxmin()]
        best_str  = f"{best_day['date'].strftime('%Y-%m-%d')} (${best_day['sales']:,.0f})"
        worst_str = f"{worst_day['date'].strftime('%Y-%m-%d')} (${worst_day['sales']:,.0f})"
    else:
        best_str = worst_str = "N/A"

    top_list = "\n".join([
        f"  {i+1}. {row['child_asin']} ({row['title'][:40]}): "
        f"${row['sales']:,.0f}, CVR={row['cvr']:.1f}%, BuyBox={row['buybox']:.1f}%"
        for i, (_, row) in enumerate(top_asins.iterrows())
    ])

    summary = f"""
PERIOD: {days} days | ASINs: {num_asins}
TOTAL SALES: ${total_sales:,.0f}
TOTAL UNITS: {total_units:,}
TOTAL SESSIONS: {total_sessions:,}
AVG CVR: {avg_cvr:.1f}%
AVG BUY BOX: {avg_buybox:.1f}%
SALES TREND (first half vs second half): {trend_str}
BEST DAY: {best_str}
WORST DAY: {worst_str}

TOP 5 ASINs BY SALES:
{top_list}
"""
    return summary


def ask_gemini(data_summary: str, user_question: str, lang: str) -> str:
    """Отправляет запрос в Gemini API — перебирает модели пока одна не сработает"""
    api_key = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return None

    lang_instruction = {
        "RU": "Отвечай на русском языке.",
        "UA": "Відповідай українською мовою.",
        "EN": "Respond in English.",
    }.get(lang, "Respond in English.")

    prompt = f"""You are an expert Amazon seller analytics consultant.
{lang_instruction}

Here is the Sales & Traffic data summary for analysis:
{data_summary}

User question: {user_question}

Provide a concise, actionable analysis. Use bullet points where helpful.
Focus on: key trends, anomalies, specific ASIN insights, and concrete recommendations.
Keep response under 400 words.
"""

    # Модель берётся из Secrets → GEMINI_MODEL, иначе дефолт
    MODELS = [
        st.secrets.get("GEMINI_MODEL", "gemini-2.5-flash"),
        "gemini-2.0-flash",
        "gemini-flash-latest",
    ]

    import requests as req
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    for model in MODELS:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            response = req.post(url, json=payload, timeout=30)
            result = response.json()

            if "error" in result:
                continue  # эта модель недоступна → пробуем следующую

            if "candidates" in result and result["candidates"]:
                st.caption(f"🤖 Модель: `{model}`")
                return result["candidates"][0]["content"]["parts"][0]["text"]

        except Exception:
            continue

    return "Error: ни одна модель не доступна для вашего API ключа"




def render_ai_section(df: pd.DataFrame, T: dict, theme: dict, lang: str):
    """Блок AI-инсайтов"""
    st.markdown(f"### {T['ai_section']}")

    api_key = st.secrets.get("GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        st.warning(T['ai_no_key'])
        with st.expander("💡 Как добавить"):
            st.code('GEMINI_API_KEY = "AIzaSy..."', language="toml")
            st.markdown("Streamlit Cloud → **Settings → Secrets**")
        return

    # Показываем доступные модели для диагностики
    with st.expander("🔍 Доступные модели Gemini для вашего ключа"):
        try:
            import requests as req
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
            resp = req.get(url, timeout=10)
            models_list = resp.json().get("models", [])
            for m in models_list:
                if "generateContent" in m.get("supportedGenerationMethods", []):
                    st.markdown(f"✅ `{m['name'].replace('models/','')}`")
        except Exception as e:
            st.error(f"Ошибка: {e}")

    data_summary = build_data_summary(df, lang)

    # Быстрые кнопки-вопросы
    col1, col2, col3 = st.columns(3)

    quick_questions = {
        "RU": [
            "Проанализируй тренды продаж и выяви аномалии",
            "Какие ASIN показывают низкий Buy Box и что с этим делать?",
            "Где самый высокий CVR и почему? Дай рекомендации",
        ],
        "UA": [
            "Проаналізуй тренди продажів та знайди аномалії",
            "Які ASIN мають низький Buy Box і що з цим робити?",
            "Де найвищий CVR і чому? Дай рекомендації",
        ],
        "EN": [
            "Analyze sales trends and identify anomalies",
            "Which ASINs have low Buy Box and what to do?",
            "Where is the highest CVR and why? Give recommendations",
        ],
    }

    questions = quick_questions.get(lang, quick_questions["EN"])

    btn1 = col1.button(f"📈 {questions[0][:35]}...", use_container_width=True)
    btn2 = col2.button(f"🏆 {questions[1][:35]}...", use_container_width=True)
    btn3 = col3.button(f"🎯 {questions[2][:35]}...", use_container_width=True)

    # Своей вопрос
    user_q = st.text_input(T['ai_prompt_label'], placeholder=T['ai_prompt_placeholder'])
    ask_btn = st.button(T['ai_ask'], type="primary")

    # Определяем финальный вопрос
    final_question = None
    if btn1: final_question = questions[0]
    elif btn2: final_question = questions[1]
    elif btn3: final_question = questions[2]
    elif ask_btn and user_q: final_question = user_q

    if final_question:
        with st.spinner(T['ai_loading']):
            answer = ask_gemini(data_summary, final_question, lang)

        if answer and not answer.startswith("Error"):
            st.markdown(f'<div class="ai-box">{answer}</div>', unsafe_allow_html=True)
        else:
            st.error(f"{T['ai_error']}: {answer}")


# ============================================================
# 📊 БЛОКИ
# ============================================================

def kpi_row(df, T):
    c1,c2,c3,c4,c5,c6 = st.columns(6)
    c1.metric(T['sales'],    f"${df['ordered_product_sales'].sum():,.0f}")
    c2.metric(T['units'],    f"{df['units_ordered'].sum():,}")
    c3.metric(T['sessions'], f"{df['sessions'].sum():,}")
    c4.metric(T['pageviews'],f"{df['page_views'].sum():,}")
    c5.metric(T['cvr'],      f"{df['unit_session_percentage'].mean():.1f}%")
    c6.metric(T['buybox'],   f"{df['buy_box_percentage'].mean():.1f}%")


def chart_sales_sessions(df, T, theme):
    daily = df.groupby('date').agg(
        sales=('ordered_product_sales','sum'),
        sessions=('sessions','sum'),
        cvr=('unit_session_percentage','mean'),
    ).reset_index()

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
        subplot_titles=[T['sales_sessions_title'], T['cvr_title']],
        row_heights=[0.65, 0.35], vertical_spacing=0.08)
    fig.add_trace(go.Bar(x=daily['date'], y=daily['sales'],
        name=T['sales'], marker_color='#7c9fff', opacity=0.85), row=1, col=1)
    fig.add_trace(go.Scatter(x=daily['date'], y=daily['sessions'],
        name=T['sessions'], line=dict(color='#ff7c7c', width=2)), row=1, col=1)
    fig.add_trace(go.Scatter(x=daily['date'], y=daily['cvr'],
        name=T['cvr'], fill='tozeroy',
        fillcolor='rgba(100,200,150,0.15)',
        line=dict(color='#64c896', width=2)), row=2, col=1)
    fig.update_layout(height=450, template=theme['template'],
        paper_bgcolor=theme['paper_bg'], plot_bgcolor=theme['plot_bg'],
        legend=dict(orientation="h", y=1.05),
        margin=dict(l=0,r=0,t=40,b=0), hovermode='x unified')
    fig.update_xaxes(gridcolor=theme['grid'])
    fig.update_yaxes(gridcolor=theme['grid'])
    st.plotly_chart(fig, use_container_width=True)


def chart_top_asins(df, T, theme):
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
            title=T['top_asins'], color='sales',
            color_continuous_scale='Blues',
            hover_data={'title':True,'units':True})
        fig.update_layout(height=400, template=theme['template'],
            paper_bgcolor=theme['paper_bg'], plot_bgcolor=theme['plot_bg'],
            showlegend=False, coloraxis_showscale=False,
            margin=dict(l=0,r=0,t=40,b=0),
            yaxis=dict(autorange='reversed'))
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig2 = px.scatter(top, x='sessions', y='cvr',
            size='sales', color='buybox',
            title=T['scatter_title'],
            hover_name='child_asin', hover_data={'title':True},
            color_continuous_scale='RdYlGn',
            labels={'cvr':'CVR %','buybox':'Buy Box %'})
        fig2.update_layout(height=400, template=theme['template'],
            paper_bgcolor=theme['paper_bg'], plot_bgcolor=theme['plot_bg'],
            margin=dict(l=0,r=0,t=40,b=0))
        st.plotly_chart(fig2, use_container_width=True)


def chart_traffic_split(df, T, theme):
    c1, c2 = st.columns(2)
    with c1:
        fig = go.Figure(data=[go.Pie(
            labels=[T['browser'],T['mobile']],
            values=[df['browser_page_views'].sum(), df['mobile_app_page_views'].sum()],
            hole=0.5, marker_colors=['#7c9fff','#ff9f7c'])])
        fig.update_layout(title=T['pv_title'], height=300,
            template=theme['template'], paper_bgcolor=theme['paper_bg'],
            margin=dict(l=0,r=0,t=40,b=0))
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig2 = go.Figure(data=[go.Pie(
            labels=[T['browser'],T['mobile']],
            values=[df['browser_sessions'].sum(), df['mobile_app_sessions'].sum()],
            hole=0.5, marker_colors=['#64c896','#c864c8'])])
        fig2.update_layout(title=T['sess_title'], height=300,
            template=theme['template'], paper_bgcolor=theme['paper_bg'],
            margin=dict(l=0,r=0,t=40,b=0))
        st.plotly_chart(fig2, use_container_width=True)


def chart_b2b(df, T, theme):
    daily = df.groupby('date').agg(
        sales=('ordered_product_sales','sum'),
        sales_b2b=('ordered_product_sales_b2b','sum'),
    ).reset_index()
    daily['sales_b2c'] = daily['sales'] - daily['sales_b2b']
    fig = go.Figure()
    fig.add_trace(go.Bar(name='B2C', x=daily['date'], y=daily['sales_b2c'], marker_color='#7c9fff'))
    fig.add_trace(go.Bar(name='B2B', x=daily['date'], y=daily['sales_b2b'], marker_color='#ffd700'))
    fig.update_layout(barmode='stack', title=T['b2b_title'], height=300,
        template=theme['template'], paper_bgcolor=theme['paper_bg'], plot_bgcolor=theme['plot_bg'],
        margin=dict(l=0,r=0,t=40,b=0),
        hovermode='x unified', legend=dict(orientation="h", y=1.05))
    st.plotly_chart(fig, use_container_width=True)


def table_detail(df, T):
    cols = ['date','child_asin','title','sku',
            'ordered_product_sales','units_ordered',
            'sessions','page_views',
            'unit_session_percentage','buy_box_percentage']
    cols = [c for c in cols if c in df.columns]
    t = df[cols].copy()
    t['date'] = t['date'].dt.strftime('%Y-%m-%d')
    t = t.rename(columns={
        'child_asin':'ASIN','ordered_product_sales': T['sales'],
        'units_ordered': T['units'], 'sessions': T['sessions'],
        'page_views': T['pageviews'],
        'unit_session_percentage':'CVR %','buy_box_percentage':'Buy Box %'})
    st.dataframe(t, use_container_width=True, height=320,
        column_config={
            T['sales']: st.column_config.NumberColumn(format="$%.2f"),
            "CVR %": st.column_config.NumberColumn(format="%.1f%%"),
            "Buy Box %": st.column_config.NumberColumn(format="%.1f%%"),
        })


# ============================================================
# 🚀 MAIN
# ============================================================

def main():
    with st.sidebar:
        st.image(
            "https://udcparts.com/cdn/shop/files/logo.svg?v=1701894617&width=300",
            use_container_width=True
        )
        st.divider()
        lang = st.selectbox("🌐 Language / Мова / Язык", ["RU","UA","EN"], index=0)
        T = TRANSLATIONS[lang]
        theme_name = st.radio(T['theme'], [T['dark'], T['light']], horizontal=True)
        theme = DARK_THEME if theme_name == T['dark'] else LIGHT_THEME
        st.divider()
        st.markdown(f"### ⚙️ {T['period']}")
        days_back = st.selectbox(T['period'], [7,14,30,60,90], index=2,
            format_func=lambda x: T['days'](x))
        asin_raw = load_asin_list()
        all_label = T['all']
        selected_asin = st.selectbox(T['asin'], [all_label] + asin_raw)
        st.divider()
        if st.button(T['refresh'], use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        st.divider()
        st.markdown(f"### {T['sections']}")
        show_ai      = st.checkbox(T['ai_section'], True)
        show_traffic = st.checkbox(T['traffic_split'], True)
        show_b2b     = st.checkbox(T['b2b'], True)
        show_table   = st.checkbox(T['table'], False)

    apply_theme(theme)

    st.markdown(f"## {T['title']}")
    st.caption(f"`{TABLE}` · {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    st.divider()

    with st.spinner(T['loading']):
        df = load_data(days_back, selected_asin)

    if df.empty:
        st.warning(T['no_data'])
        with st.expander("💡 Connection setup"):
            st.code('DATABASE_URL = "postgresql://user:pass@host:5432/dbname"')
        return

    kpi_row(df, T)
    st.divider()
    chart_sales_sessions(df, T, theme)
    st.divider()

    st.markdown(f"### {T['top_asins']}")
    chart_top_asins(df, T, theme)

    if show_traffic:
        st.divider()
        st.markdown(f"### {T['traffic_split']}")
        chart_traffic_split(df, T, theme)

    if show_b2b:
        st.divider()
        st.markdown(f"### {T['b2b']}")
        chart_b2b(df, T, theme)

    if show_table:
        st.divider()
        st.markdown(f"### {T['table']}")
        table_detail(df, T)

    if show_ai:
        st.divider()
        render_ai_section(df, T, theme, lang)

    with st.expander(T['info']):
        c1,c2,c3,c4 = st.columns(4)
        c1.metric(T['rows'],       f"{len(df):,}")
        c2.metric("ASIN",          f"{df['child_asin'].nunique():,}")
        c3.metric(T['days_label'], f"{df['date'].nunique():,}")
        c4.metric(T['sku'],        f"{df['sku'].nunique():,}")


if __name__ == "__main__":
    main()
