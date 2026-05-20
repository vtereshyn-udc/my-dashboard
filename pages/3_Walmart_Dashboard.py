"""
Walmart Reports Dashboard v2.1
ЗМІНИ vs v2.0:
- ДОДАНО розділ 📦 Orders/Sales (walmart.orders)
- Гнучкий пошук колонок (працює з будь-якою схемою таблиці orders)

v2.0:
- ДОДАНО 3 розділи: WFS Shipments, Settlement, Customer Returns
- McKinsey-level action items
- Trilingual (RU/UA/EN), dark/light themes

Drop into Streamlit `pages/` folder.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Walmart Dashboard",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# 🌐 ПЕРЕВОДЫ
# ============================================================

TRANSLATIONS = {
    "EN": {
        "title": "🏪 Walmart Dashboard — UDC Mower Parts",
        "refresh": "🔄 Refresh",
        "sections": "📊 Sections",
        "loading": "Loading data...",
        "no_data": "⚠️ No data. Run loaders first.",
        "language": "🌐 Language",
        "theme": "🎨 Theme", "dark": "Dark", "light": "Light",

        # KPI
        "total_skus": "Total SKUs",
        "gmv_30d": "GMV",
        "refunds_30d": "Refunds",
        "bb_win": "Buy Box Win",
        "cap_skus": "CAP Discount SKUs",
        "problems": "Problem SKUs",

        # Health
        "health_section": "🚨 Health Check — Action Items",
        "health_subtitle": "Issues sorted by revenue impact",
        "issue": "Issue", "severity": "Severity", "affected": "Affected",
        "impact": "Impact", "action": "Recommended Action", "owner": "Owner",

        # Buybox
        "buybox_section": "💰 Walmart CAP Discount Analysis",
        "buybox_subtitle": "How much Walmart cuts your listed price via CAP",
        "buybox_hidden_loss": "Hidden Margin Loss",
        "cap_top": "Top SKUs with Biggest Cut",
        "seller_price": "Your Price", "buybox_price": "BuyBox Price",
        "cut_pct": "Cut %", "margin_lost": "Lost $/unit",
        "sku": "SKU", "product": "Product",

        # Performance
        "performance_section": "📈 Item Performance",
        "performance_subtitle": "GMV, refunds, dead SKUs",
        "dead_skus_title": "Dead SKUs (had LY sales, now zero)",
        "neg_gmv_title": "Negative GMV SKUs",
        "top_gmv": "Top 15 by GMV", "top_refund": "Top 10 by Refunds",
        "gmv_label": "GMV", "refund_label": "Refunded",
        "net_label": "Net (GMV - Refunds)",
        "ly_gmv": "Last Year GMV", "units": "Units",

        # Status
        "status_section": "📋 Item Status Distribution",
        "problem_skus_title": "Problem SKUs details",
        "status_col": "Status", "reason_col": "Reason",

        # Cancellations
        "cancel_section": "🔄 Cancellations",
        "cancel_subtitle": "All cancelled orders with reasons",
        "repeat_offenders": "Repeat offenders",
        "cancel_count": "Cancellations",

        # 🆕 WFS Shipments
        "wfs_section": "🚛 WFS Inbound Shipments",
        "wfs_subtitle": "Active and historical inbound shipments to Walmart FCs",
        "wfs_total_ships": "Total Shipments",
        "wfs_in_transit": "In Transit",
        "wfs_pending_units": "Pending Units",
        "wfs_closed": "Closed",
        "wfs_cancelled": "Cancelled",
        "wfs_active_title": "Active Shipments (AWAITING_DELIVERY)",
        "wfs_eta_title": "Upcoming Deliveries (next 14 days)",
        "wfs_top_skus_pending": "Top SKUs Pending in Transit",
        "wfs_by_fc": "Shipments by Fulfillment Center",
        "wfs_by_carrier": "Shipments by Carrier",
        "wfs_status": "Status",
        "wfs_fc": "FC", "wfs_carrier": "Carrier", "wfs_eta": "ETA",
        "wfs_skus": "SKUs", "wfs_pending": "Pending", "wfs_received": "Received",

        # 🆕 Settlement
        "settlement_section": "💰 Settlement / Payouts",
        "settlement_subtitle": "Marketplace reconciliation — payments, fees, refunds",
        "settlement_periods": "Settlement Periods",
        "settlement_net_paid": "Total Net Paid",
        "settlement_sales": "Gross Sales",
        "settlement_fees": "Total Fees",
        "settlement_refunds_total": "Total Refunds",
        "payouts_chart_title": "Payouts to PAYONEER (timeline)",
        "settlement_by_type": "Money flow by Transaction Type",
        "settlement_recent": "Recent Payment Summaries",
        "top_sku_revenue": "Top SKUs by Net Revenue",
        "sku_lifetime_value": "Per-SKU lifetime (2 years)",
        "txn_type": "Type", "txn_count": "Count", "txn_amount": "Amount",
        "period": "Period", "deposit": "Deposit", "channel": "Channel",

        # 🆕 Customer Returns
        "returns_section": "🔄 Customer Returns",
        "returns_subtitle": "Customer-initiated returns with reasons, status, tracking",
        "returns_total": "Total Returns",
        "returns_skus": "Unique SKUs",
        "returns_refunded_amt": "Total Refunded",
        "returns_by_reason": "Returns by Reason",
        "returns_by_status": "Refund Status",
        "returns_killer_skus": "Top Killer SKUs ($ lost)",
        "returns_recent": "Recent Returns (last 20)",
        "returns_reason": "Reason", "returns_qty": "Qty",
        "returns_refund_amt": "Refund $", "returns_status_col": "Status",
        "returns_date": "Date", "returns_carrier": "Carrier",
        "returns_fix_listings": "💡 LISTING FIX OPPORTUNITY",
        "returns_fix_text": "% of returns due to listing issues (compatibility / wrong item / description)",

        # 🆕 Orders
        "orders_section": "📦 Orders / Sales",
        "orders_subtitle": "Customer orders, daily sales, top buyers, ship-to locations",
        "orders_total": "Total Orders",
        "orders_30d": "Orders 30d",
        "orders_revenue": "Revenue 30d",
        "orders_aov": "Avg Order Value",
        "orders_units": "Units Sold 30d",
        "orders_daily_trend": "Daily Sales Trend",
        "orders_by_state": "Sales by State (Ship-to)",
        "orders_top_skus": "Top SKUs by Revenue",
        "orders_recent": "Recent Orders",
        "orders_status_dist": "Order Status Distribution",
        "orders_order_id": "Order ID",
        "orders_date_col": "Date",
        "orders_status_col": "Status",
        "orders_amount": "Amount",
        "orders_state": "State",

        # Loader health
        "loader_section": "⏱️ Loader Runs",
        "report_type": "Report Type", "status": "Status",
        "rows_loaded": "Rows", "started_at": "Started",

        # AI
        "ai_section": "🤖 AI Insights — Ask anything",
        "ai_prompt_label": "💬 Ask anything",
        "ai_prompt_placeholder": "Which SKUs lost most money to returns?",
        "ai_ask": "Ask AI",
        "ai_loading": "🤖 Gemini analyzing...",
        "ai_error": "❌ Gemini API error",
        "ai_no_key": "⚠️ Add GEMINI_API_KEY to Streamlit Secrets",
        "ai_sql_expander": "🔎 SQL generated by AI",
        "ai_result_expander": "📊 Data from DB",
    },
    "UA": {
        "title": "🏪 Walmart Дашборд — UDC Parts",
        "refresh": "🔄 Оновити", "sections": "📊 Розділи",
        "loading": "Завантажуємо дані...",
        "no_data": "⚠️ Немає даних. Запустіть лоадери спочатку.",
        "language": "🌐 Мова",
        "theme": "🎨 Тема", "dark": "Темна", "light": "Світла",

        "total_skus": "Всього SKU", "gmv_30d": "GMV",
        "refunds_30d": "Повернення", "bb_win": "Buy Box Wins",
        "cap_skus": "CAP Discount SKU", "problems": "Проблемні SKU",

        "health_section": "🚨 Health Check — Що робити",
        "health_subtitle": "Проблеми за впливом на виручку",
        "issue": "Проблема", "severity": "Критичність",
        "affected": "Кількість", "impact": "Вплив",
        "action": "Рекомендована дія", "owner": "Відповідальний",

        "buybox_section": "💰 Walmart CAP Discount",
        "buybox_subtitle": "Скільки Walmart ріже з вашої ціни через CAP",
        "buybox_hidden_loss": "Прихована втрата маржі",
        "cap_top": "Топ SKU з найбільшим урізанням",
        "seller_price": "Ваша ціна", "buybox_price": "BuyBox ціна",
        "cut_pct": "Cut %", "margin_lost": "Втрата $/од",
        "sku": "SKU", "product": "Товар",

        "performance_section": "📈 Продуктивність товарів",
        "performance_subtitle": "GMV, повернення, мертві SKU",
        "dead_skus_title": "Мертві SKU (продавались LY, зараз 0)",
        "neg_gmv_title": "SKU з негативним GMV",
        "top_gmv": "Топ-15 за GMV", "top_refund": "Топ-10 за поверненнями",
        "gmv_label": "GMV", "refund_label": "Повернено",
        "net_label": "Чисто (GMV - Повернення)",
        "ly_gmv": "GMV минулого року", "units": "Одиниці",

        "status_section": "📋 Розподіл статусів",
        "problem_skus_title": "Проблемні SKU — деталі",
        "status_col": "Статус", "reason_col": "Причина",

        "cancel_section": "🔄 Скасування замовлень",
        "cancel_subtitle": "Всі скасовані замовлення",
        "repeat_offenders": "SKU скасовано >1 раз",
        "cancel_count": "Скасувань",

        # 🆕 WFS Shipments
        "wfs_section": "🚛 WFS Inbound Shipments",
        "wfs_subtitle": "Активні та історичні поставки до Walmart FC",
        "wfs_total_ships": "Всього shipments",
        "wfs_in_transit": "В дорозі",
        "wfs_pending_units": "Units в дорозі",
        "wfs_closed": "Closed",
        "wfs_cancelled": "Cancelled",
        "wfs_active_title": "Активні поставки (AWAITING_DELIVERY)",
        "wfs_eta_title": "Прибудуть в найближчі 14 днів",
        "wfs_top_skus_pending": "Топ SKU в дорозі",
        "wfs_by_fc": "Поставки по FC",
        "wfs_by_carrier": "Поставки по перевізнику",
        "wfs_status": "Статус",
        "wfs_fc": "FC", "wfs_carrier": "Carrier", "wfs_eta": "ETA",
        "wfs_skus": "SKU", "wfs_pending": "В дорозі", "wfs_received": "Прийнято",

        # 🆕 Settlement
        "settlement_section": "💰 Settlement / Виплати",
        "settlement_subtitle": "Marketplace reconciliation — виплати, fees, refunds",
        "settlement_periods": "Settlement періодів",
        "settlement_net_paid": "Всього виплачено",
        "settlement_sales": "Gross Sales",
        "settlement_fees": "Total Fees",
        "settlement_refunds_total": "Total Refunds",
        "payouts_chart_title": "Виплати в PAYONEER (timeline)",
        "settlement_by_type": "Грошові потоки за типом",
        "settlement_recent": "Останні виплати",
        "top_sku_revenue": "Топ SKU за чистим доходом",
        "sku_lifetime_value": "Lifetime SKU (2 роки)",
        "txn_type": "Тип", "txn_count": "Кількість", "txn_amount": "Сума",
        "period": "Період", "deposit": "Виплата", "channel": "Канал",

        # 🆕 Returns
        "returns_section": "🔄 Customer Returns",
        "returns_subtitle": "Повернення клієнтів з причинами та статусом",
        "returns_total": "Всього повернень",
        "returns_skus": "Унікальних SKU",
        "returns_refunded_amt": "Всього повернено",
        "returns_by_reason": "Повернення за причиною",
        "returns_by_status": "Refund Status",
        "returns_killer_skus": "Топ-killer SKU ($ втрачено)",
        "returns_recent": "Останні повернення (20)",
        "returns_reason": "Причина", "returns_qty": "Шт",
        "returns_refund_amt": "Refund $", "returns_status_col": "Статус",
        "returns_date": "Дата", "returns_carrier": "Carrier",
        "returns_fix_listings": "💡 МОЖЛИВІСТЬ ФІКС ЛІСТИНГІВ",
        "returns_fix_text": "% повернень через проблеми з лістингом",

        # 🆕 Orders
        "orders_section": "📦 Замовлення / Продажі",
        "orders_subtitle": "Замовлення клієнтів, щоденні продажі, ТОП покупці, штати доставки",
        "orders_total": "Всього замовлень",
        "orders_30d": "Замовлень за 30д",
        "orders_revenue": "Виручка 30д",
        "orders_aov": "Сер. чек",
        "orders_units": "Юнітів продано 30д",
        "orders_daily_trend": "Щоденний тренд продажів",
        "orders_by_state": "Продажі по штатах",
        "orders_top_skus": "Топ SKU за виручкою",
        "orders_recent": "Останні замовлення",
        "orders_status_dist": "Розподіл статусів",
        "orders_order_id": "Order ID",
        "orders_date_col": "Дата",
        "orders_status_col": "Статус",
        "orders_amount": "Сума",
        "orders_state": "Штат",

        "loader_section": "⏱️ Запуски лодерів",
        "report_type": "Тип відчіту", "status": "Статус",
        "rows_loaded": "Рядків", "started_at": "Запущено",

        "ai_section": "🤖 AI Інсайти",
        "ai_prompt_label": "💬 Запитай будь-що",
        "ai_prompt_placeholder": "Які SKU втратили найбільше через returns?",
        "ai_ask": "Запитати AI",
        "ai_loading": "🤖 Gemini аналізує...",
        "ai_error": "❌ Помилка Gemini API",
        "ai_no_key": "⚠️ Додайте GEMINI_API_KEY до Streamlit Secrets",
        "ai_sql_expander": "🔎 SQL запит від AI",
        "ai_result_expander": "📊 Дані з бази",
    },
    "RU": {
        "title": "🏪 Walmart Дашборд — UDC Parts",
        "refresh": "🔄 Обновить", "sections": "📊 Разделы",
        "loading": "Загружаем данные...",
        "no_data": "⚠️ Нет данных. Запустите лодеры сначала.",
        "language": "🌐 Язык",
        "theme": "🎨 Тема", "dark": "Тёмная", "light": "Светлая",

        "total_skus": "Всего SKU", "gmv_30d": "GMV",
        "refunds_30d": "Возвраты", "bb_win": "Buy Box Win",
        "cap_skus": "CAP Discount SKU", "problems": "Проблемные SKU",

        "health_section": "🚨 Health Check — Что делать",
        "health_subtitle": "Проблемы по влиянию на выручку",
        "issue": "Проблема", "severity": "Критичность",
        "affected": "Количество", "impact": "Влияние",
        "action": "Рекомендация", "owner": "Ответственный",

        "buybox_section": "💰 Walmart CAP Discount",
        "buybox_subtitle": "Сколько Walmart режет с вашей цены",
        "buybox_hidden_loss": "Скрытая потеря маржи",
        "cap_top": "Топ SKU с самой большой обрезкой",
        "seller_price": "Ваша цена", "buybox_price": "BuyBox цена",
        "cut_pct": "Cut %", "margin_lost": "Потеря $/ед",
        "sku": "SKU", "product": "Товар",

        "performance_section": "📈 Производительность",
        "performance_subtitle": "GMV, возвраты, мёртвые SKU",
        "dead_skus_title": "Мёртвые SKU (LY продавались, сейчас 0)",
        "neg_gmv_title": "SKU с негативным GMV",
        "top_gmv": "Топ-15 по GMV", "top_refund": "Топ-10 по возвратам",
        "gmv_label": "GMV", "refund_label": "Возвращено",
        "net_label": "Чисто (GMV - Возвраты)",
        "ly_gmv": "GMV прошлого года", "units": "Единицы",

        "status_section": "📋 Распределение статусов",
        "problem_skus_title": "Проблемные SKU — детали",
        "status_col": "Статус", "reason_col": "Причина",

        "cancel_section": "🔄 Отмены заказов",
        "cancel_subtitle": "Все отменённые заказы",
        "repeat_offenders": "SKU отменяли >1 раз",
        "cancel_count": "Отмен",

        # 🆕 WFS Shipments
        "wfs_section": "🚛 WFS Inbound Shipments",
        "wfs_subtitle": "Активные и исторические поставки в Walmart FC",
        "wfs_total_ships": "Всего shipments",
        "wfs_in_transit": "В пути",
        "wfs_pending_units": "Units в пути",
        "wfs_closed": "Closed",
        "wfs_cancelled": "Cancelled",
        "wfs_active_title": "Активные поставки (AWAITING_DELIVERY)",
        "wfs_eta_title": "Прибудут в ближайшие 14 дней",
        "wfs_top_skus_pending": "Топ SKU в пути",
        "wfs_by_fc": "Поставки по FC",
        "wfs_by_carrier": "Поставки по перевозчику",
        "wfs_status": "Статус",
        "wfs_fc": "FC", "wfs_carrier": "Carrier", "wfs_eta": "ETA",
        "wfs_skus": "SKU", "wfs_pending": "В пути", "wfs_received": "Принято",

        # 🆕 Settlement
        "settlement_section": "💰 Settlement / Выплаты",
        "settlement_subtitle": "Marketplace reconciliation — выплаты, fees, refunds",
        "settlement_periods": "Settlement периодов",
        "settlement_net_paid": "Всего выплачено",
        "settlement_sales": "Gross Sales",
        "settlement_fees": "Total Fees",
        "settlement_refunds_total": "Total Refunds",
        "payouts_chart_title": "Выплаты в PAYONEER (timeline)",
        "settlement_by_type": "Денежные потоки по типу",
        "settlement_recent": "Последние выплаты",
        "top_sku_revenue": "Топ SKU по чистому доходу",
        "sku_lifetime_value": "Lifetime SKU (2 года)",
        "txn_type": "Тип", "txn_count": "Количество", "txn_amount": "Сумма",
        "period": "Период", "deposit": "Выплата", "channel": "Канал",

        # 🆕 Returns
        "returns_section": "🔄 Customer Returns",
        "returns_subtitle": "Возвраты клиентов с причинами и статусом",
        "returns_total": "Всего возвратов",
        "returns_skus": "Уникальных SKU",
        "returns_refunded_amt": "Всего возвращено",
        "returns_by_reason": "Возвраты по причине",
        "returns_by_status": "Refund Status",
        "returns_killer_skus": "Топ-killer SKU ($ потеряно)",
        "returns_recent": "Последние возвраты (20)",
        "returns_reason": "Причина", "returns_qty": "Шт",
        "returns_refund_amt": "Refund $", "returns_status_col": "Статус",
        "returns_date": "Дата", "returns_carrier": "Carrier",
        "returns_fix_listings": "💡 ВОЗМОЖНОСТЬ FIX ЛИСТИНГОВ",
        "returns_fix_text": "% возвратов из-за проблем с листингом",

        # 🆕 Orders
        "orders_section": "📦 Заказы / Продажи",
        "orders_subtitle": "Заказы клиентов, дневные продажи, ТОП покупатели, штаты доставки",
        "orders_total": "Всего заказов",
        "orders_30d": "Заказов за 30д",
        "orders_revenue": "Выручка 30д",
        "orders_aov": "Сред. чек",
        "orders_units": "Юнитов продано 30д",
        "orders_daily_trend": "Дневной тренд продаж",
        "orders_by_state": "Продажи по штатам",
        "orders_top_skus": "Топ SKU по выручке",
        "orders_recent": "Последние заказы",
        "orders_status_dist": "Распределение статусов",
        "orders_order_id": "Order ID",
        "orders_date_col": "Дата",
        "orders_status_col": "Статус",
        "orders_amount": "Сумма",
        "orders_state": "Штат",

        "loader_section": "⏱️ Запуски лодеров",
        "report_type": "Тип отчёта", "status": "Статус",
        "rows_loaded": "Строк", "started_at": "Запущен",

        "ai_section": "🤖 AI Инсайты",
        "ai_prompt_label": "💬 Спроси любое",
        "ai_prompt_placeholder": "Какие SKU потеряли больше всего из-за returns?",
        "ai_ask": "Спросить AI",
        "ai_loading": "🤖 Gemini анализирует...",
        "ai_error": "❌ Ошибка Gemini API",
        "ai_no_key": "⚠️ Добавьте GEMINI_API_KEY в Streamlit Secrets",
        "ai_sql_expander": "🔎 SQL запрос от AI",
        "ai_result_expander": "📊 Данные из БД",
    },
}

# ============================================================
# 🎨 ТЕМЫ
# ============================================================

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
        [data-testid="stSidebar"] {{
            background-color: {t['sidebar_bg']} !important;
            border-right: 1px solid {t['card_border']};
        }}
        [data-testid="stSidebar"] * {{ color: {sidebar_text} !important; }}
        [data-testid="stSidebar"] .stSelectbox > div > div {{
            background-color: {input_bg} !important;
            color: {input_text} !important;
        }}
        [data-testid="stSidebar"] label {{ color: {sidebar_text} !important; }}
        p, span, div {{ color: {t['text']}; }}
        .stMarkdown p {{ color: {t['text']} !important; }}
        div[data-baseweb="popover"] ul {{ background-color: {input_bg} !important; }}
        div[data-baseweb="popover"] ul li {{
            background-color: {input_bg} !important;
            color: {input_text} !important;
        }}
        div[data-baseweb="popover"] ul li:hover {{
            background-color: {t['card_border']} !important;
        }}
        .stButton button, div.stButton > button {{
            background-color: {input_bg} !important;
            color: {input_text} !important;
            border: 1px solid {t['card_border']} !important;
        }}
        .stButton button:hover, div.stButton > button:hover {{
            border-color: {t['metric_val']} !important;
            color: {t['metric_val']} !important;
        }}
        .stButton button[kind="primary"], div.stButton > button[kind="primary"] {{
            background-color: #e03131 !important;
            color: #ffffff !important;
            border: none !important;
        }}
        .stButton button[kind="primary"]:hover {{
            background-color: #c92a2a !important;
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
        .severity-crit {{
            background: rgba(224, 49, 49, 0.15);
            border-left: 4px solid #e03131;
            padding: 10px 14px; border-radius: 6px; margin: 4px 0;
        }}
        .severity-warn {{
            background: rgba(250, 176, 5, 0.12);
            border-left: 4px solid #fab005;
            padding: 10px 14px; border-radius: 6px; margin: 4px 0;
        }}
        .severity-info {{
            background: rgba(34, 139, 230, 0.10);
            border-left: 4px solid #228be6;
            padding: 10px 14px; border-radius: 6px; margin: 4px 0;
        }}
        .opportunity-box {{
            background: linear-gradient(135deg, rgba(81, 207, 102, 0.15), rgba(34, 139, 230, 0.10));
            border-left: 4px solid #51cf66;
            padding: 14px 18px; border-radius: 8px; margin: 10px 0;
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
def load_walmart_data():
    """Загружает все Walmart таблицы — old + new."""
    eng = get_engine()
    data = {}
    queries = {
        # Старі
        "items":           "SELECT * FROM walmart.items",
        "performance":     "SELECT * FROM walmart.item_performance WHERE report_date >= CURRENT_DATE - INTERVAL '30 days'",
        "inventory":       "SELECT * FROM walmart.inventory_report",
        "inventory_new":   "SELECT * FROM walmart.inventory",
        "buybox":          "SELECT * FROM walmart.buybox",
        "cancellations":   "SELECT * FROM walmart.cancellations ORDER BY cancel_date DESC NULLS LAST",
        "report_runs":     "SELECT * FROM walmart.report_runs ORDER BY started_at DESC LIMIT 30",

        # 🆕 НОВІ ТАБЛИЦІ
        "wfs_shipments":   "SELECT * FROM walmart.wfs_shipments",
        "settlement":      "SELECT * FROM walmart.settlement",
        "returns":         "SELECT * FROM walmart.returns",
        "orders":          "SELECT * FROM walmart.orders WHERE order_date >= CURRENT_DATE - INTERVAL '90 days'",
    }
    try:
        with eng.connect() as conn:
            for k, q in queries.items():
                try:
                    data[k] = pd.read_sql(text(q), conn)
                except Exception:
                    data[k] = pd.DataFrame()
    except Exception as e:
        st.error(f"❌ DB Error: {e}")
        return None
    return data


# ============================================================
# 📊 KPI ROW
# ============================================================

def kpi_row(data, T):
    items = data.get("items", pd.DataFrame())
    perf = data.get("performance", pd.DataFrame())
    buybox = data.get("buybox", pd.DataFrame())

    total_skus = len(items) if not items.empty else 0
    gmv = perf["gmv"].sum() if not perf.empty and "gmv" in perf else 0
    refunds = perf["refunded_sales"].sum() if not perf.empty and "refunded_sales" in perf else 0

    bb_wins = 0
    bb_total = 0
    if not buybox.empty and "is_seller_buybox_winner" in buybox:
        bb_wins = (buybox["is_seller_buybox_winner"] == "Y").sum()
        bb_total = len(buybox)
    bb_pct = (100 * bb_wins / bb_total) if bb_total > 0 else 0

    cap_skus = 0
    if not buybox.empty and "price_diff_pct" in buybox:
        cap_skus = (buybox["price_diff_pct"].fillna(0) > 0.10).sum()

    problems = 0
    if not items.empty and "publish_status" in items:
        problems = (~items["publish_status"].isin(["PUBLISHED"])).sum()

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric(T["total_skus"], f"{total_skus:,}")
    c2.metric(T["gmv_30d"], f"${float(gmv):,.0f}")
    c3.metric(T["refunds_30d"], f"${float(refunds):,.0f}")
    c4.metric(T["bb_win"], f"{bb_pct:.1f}%")
    c5.metric(T["cap_skus"], f"{int(cap_skus)}")
    c6.metric(T["problems"], f"{int(problems)}")


# ============================================================
# 📦 ORDERS SECTION 🆕
# ============================================================

def _pick_col(df, *candidates):
    """Знаходить першу існуючу колонку зі списку кандидатів."""
    for c in candidates:
        if c in df.columns:
            return c
    return None


def render_orders(data, T, theme):
    orders = data.get("orders", pd.DataFrame())
    if orders.empty:
        st.warning("⚠️ walmart.orders is empty")
        return

    st.markdown(f"### {T['orders_section']}")
    st.caption(T["orders_subtitle"])

    # Знаходимо колонки (гнучко)
    date_col   = _pick_col(orders, "order_date", "purchase_date", "created_at", "order_create_date")
    amount_col = _pick_col(orders, "total_amount", "order_total", "amount", "total_price", "subtotal")
    status_col = _pick_col(orders, "order_status", "status", "order_state")
    sku_col    = _pick_col(orders, "sku", "seller_sku", "partner_sku", "item_sku")
    qty_col    = _pick_col(orders, "quantity", "qty", "units", "order_quantity")
    state_col  = _pick_col(orders, "ship_to_state", "state", "destination_state", "shipping_state")
    order_id_col = _pick_col(orders, "order_id", "purchase_order_id", "customer_order_id", "po_id")

    if date_col is None:
        st.warning("⚠️ Could not find date column in walmart.orders")
        st.dataframe(orders.head(20), use_container_width=True)
        return

    # Конвертуємо дату
    orders_df = orders.copy()
    orders_df[date_col] = pd.to_datetime(orders_df[date_col], errors='coerce')
    orders_df = orders_df[orders_df[date_col].notna()]

    if orders_df.empty:
        st.warning("⚠️ No valid dates in orders")
        return

    # Останні 30 днів
    today = datetime.now().date()
    cutoff = pd.Timestamp(today - timedelta(days=30))
    last30 = orders_df[orders_df[date_col] >= cutoff]

    # ===== KPI =====
    total_orders = len(orders_df)
    orders_30d = len(last30)

    revenue_30d = 0
    aov = 0
    units_30d = 0

    if amount_col and amount_col in last30:
        revenue_30d = pd.to_numeric(last30[amount_col], errors='coerce').sum()
        aov = revenue_30d / max(orders_30d, 1)
    if qty_col and qty_col in last30:
        units_30d = pd.to_numeric(last30[qty_col], errors='coerce').sum()

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric(T["orders_total"], f"{total_orders:,}")
    c2.metric(T["orders_30d"], f"{orders_30d:,}")
    c3.metric(T["orders_revenue"], f"${float(revenue_30d):,.0f}")
    c4.metric(T["orders_aov"], f"${float(aov):,.2f}")
    c5.metric(T["orders_units"], f"{int(units_30d):,}")

    # ===== Daily trend =====
    st.markdown(f"#### 📈 {T['orders_daily_trend']}")

    daily_agg = {date_col: orders_df.groupby(orders_df[date_col].dt.date).size().reset_index(name="orders_count")}
    daily = daily_agg[date_col]
    daily.columns = ["date", "orders"]

    if amount_col:
        rev_daily = orders_df.groupby(orders_df[date_col].dt.date)[amount_col].apply(
            lambda x: pd.to_numeric(x, errors='coerce').sum()
        ).reset_index()
        rev_daily.columns = ["date", "revenue"]
        daily = daily.merge(rev_daily, on="date", how="left")

    daily = daily.sort_values("date")

    # Двохосний графік: bars=orders, line=revenue
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=daily["date"], y=daily["orders"],
        name="Orders", marker_color="#7c9fff", yaxis="y",
    ))
    if "revenue" in daily.columns:
        fig.add_trace(go.Scatter(
            x=daily["date"], y=daily["revenue"],
            name="Revenue $", mode="lines+markers",
            line=dict(color="#51cf66", width=3), yaxis="y2",
        ))
    fig.update_layout(
        height=400, template=theme["template"],
        paper_bgcolor=theme["paper_bg"], plot_bgcolor=theme["plot_bg"],
        margin=dict(l=0, r=0, t=20, b=0),
        yaxis=dict(title="Orders"),
        yaxis2=dict(title="Revenue $", overlaying="y", side="right"),
        legend=dict(orientation="h", y=1.1),
    )
    st.plotly_chart(fig, use_container_width=True)

    # ===== By state + Top SKUs =====
    c1, c2 = st.columns(2)

    with c1:
        if state_col and state_col in last30:
            st.markdown(f"#### 🗺️ {T['orders_by_state']}")
            by_state = last30.groupby(state_col).agg(
                orders=(date_col, "count"),
            ).reset_index().sort_values("orders", ascending=False).head(15)
            by_state = by_state[by_state[state_col].notna() & (by_state[state_col] != "")]
            if not by_state.empty:
                fig = px.bar(
                    by_state.sort_values("orders"),
                    x="orders", y=state_col, orientation="h",
                    color="orders", color_continuous_scale="Blues",
                )
                fig.update_layout(
                    height=450, template=theme["template"],
                    paper_bgcolor=theme["paper_bg"], plot_bgcolor=theme["plot_bg"],
                    showlegend=False, coloraxis_showscale=False,
                    margin=dict(l=0, r=0, t=20, b=0),
                    yaxis_title="",
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("State column not found in orders")

    with c2:
        if sku_col and amount_col and sku_col in last30 and amount_col in last30:
            st.markdown(f"#### 🏆 {T['orders_top_skus']}")
            top_sku = last30.copy()
            top_sku[amount_col] = pd.to_numeric(top_sku[amount_col], errors='coerce')
            top_sku_agg = top_sku.groupby(sku_col).agg(
                revenue=(amount_col, "sum"),
                orders=(date_col, "count"),
            ).reset_index().sort_values("revenue", ascending=False).head(15)

            fig = px.bar(
                top_sku_agg.sort_values("revenue"),
                x="revenue", y=sku_col, orientation="h",
                color="revenue", color_continuous_scale="Greens",
                hover_data={"orders": True},
            )
            fig.update_layout(
                height=450, template=theme["template"],
                paper_bgcolor=theme["paper_bg"], plot_bgcolor=theme["plot_bg"],
                showlegend=False, coloraxis_showscale=False,
                margin=dict(l=0, r=0, t=20, b=0),
                yaxis_title="",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("SKU/amount columns not found")

    # ===== Status distribution =====
    if status_col and status_col in orders_df:
        st.markdown(f"#### 📊 {T['orders_status_dist']}")
        status_dist = orders_df[status_col].fillna("UNKNOWN").value_counts().reset_index()
        status_dist.columns = ["status", "count"]
        status_dist = status_dist.head(8)
        c1, c2 = st.columns([1, 2])
        with c1:
            colors_map = {
                "Acknowledged": "#7c9fff", "Shipped": "#51cf66",
                "Delivered": "#40c057", "Cancelled": "#e03131",
                "Created": "#fab005", "UNKNOWN": "#868e96",
            }
            fig = px.pie(
                status_dist, values="count", names="status",
                color="status", color_discrete_map=colors_map, hole=0.4,
            )
            fig.update_layout(height=300, template=theme["template"], paper_bgcolor=theme["paper_bg"])
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.dataframe(status_dist, use_container_width=True, hide_index=True, height=300)

    # ===== Recent orders =====
    st.markdown(f"#### 📋 {T['orders_recent']}")

    display_cols = []
    rename_map = {}
    if order_id_col:
        display_cols.append(order_id_col)
        rename_map[order_id_col] = T["orders_order_id"]
    if date_col:
        display_cols.append(date_col)
        rename_map[date_col] = T["orders_date_col"]
    if status_col:
        display_cols.append(status_col)
        rename_map[status_col] = T["orders_status_col"]
    if sku_col:
        display_cols.append(sku_col)
        rename_map[sku_col] = T["sku"]
    if qty_col:
        display_cols.append(qty_col)
        rename_map[qty_col] = T["returns_qty"]
    if amount_col:
        display_cols.append(amount_col)
        rename_map[amount_col] = T["orders_amount"]
    if state_col:
        display_cols.append(state_col)
        rename_map[state_col] = T["orders_state"]

    if display_cols:
        recent = orders_df.sort_values(date_col, ascending=False).head(30)[display_cols].copy()
        recent[date_col] = pd.to_datetime(recent[date_col]).dt.strftime("%Y-%m-%d %H:%M")
        recent = recent.rename(columns=rename_map)
        st.dataframe(recent, use_container_width=True, hide_index=True, height=400,
            column_config={
                T["orders_amount"]: st.column_config.NumberColumn(format="$%.2f") if amount_col else None,
            })


# ============================================================
# 🚛 WFS SHIPMENTS SECTION 🆕
# ============================================================

def render_wfs_shipments(data, T, theme):
    wfs = data.get("wfs_shipments", pd.DataFrame())
    if wfs.empty:
        st.warning("⚠️ walmart.wfs_shipments is empty")
        return

    st.markdown(f"### {T['wfs_section']}")
    st.caption(T["wfs_subtitle"])

    # ===== KPI =====
    n_ships = wfs["shipment_id"].nunique()
    awaiting = wfs[wfs["po_status"] == "AWAITING_DELIVERY"]["shipment_id"].nunique()
    closed = wfs[wfs["po_status"] == "CLOSED"]["shipment_id"].nunique()
    cancelled = wfs[wfs["po_status"] == "CANCELLED"]["shipment_id"].nunique()

    awaiting_df = wfs[wfs["po_status"] == "AWAITING_DELIVERY"]
    pending_units = int((awaiting_df["expected_units"].fillna(0) - awaiting_df["received_units"].fillna(0)).sum()) if not awaiting_df.empty else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric(T["wfs_total_ships"], f"{n_ships}")
    c2.metric(T["wfs_in_transit"], f"{awaiting}")
    c3.metric(T["wfs_pending_units"], f"{pending_units:,}")
    c4.metric(T["wfs_closed"], f"{closed}")
    c5.metric(T["wfs_cancelled"], f"{cancelled}")

    # ===== Active shipments table =====
    st.markdown(f"#### 🚛 {T['wfs_active_title']}")

    if not awaiting_df.empty:
        agg = awaiting_df.groupby("shipment_id").agg(
            fc=("fc_name", "first"),
            carrier=("carrier_name", "first"),
            eta=("expected_delivery_date", "max"),
            skus=("sku", "nunique"),
            expected=("expected_units", "sum"),
            received=("received_units", "sum"),
        ).reset_index()
        agg["pending"] = (agg["expected"].fillna(0) - agg["received"].fillna(0)).astype(int)
        agg["eta"] = pd.to_datetime(agg["eta"]).dt.strftime("%Y-%m-%d")
        agg = agg.rename(columns={
            "shipment_id": "Shipment",
            "fc": T["wfs_fc"],
            "carrier": T["wfs_carrier"],
            "eta": T["wfs_eta"],
            "skus": T["wfs_skus"],
            "expected": "Expected",
            "received": T["wfs_received"],
            "pending": T["wfs_pending"],
        })
        st.dataframe(agg, use_container_width=True, hide_index=True,
            column_config={
                "Expected": st.column_config.NumberColumn(format="%d"),
                T["wfs_received"]: st.column_config.NumberColumn(format="%d"),
                T["wfs_pending"]: st.column_config.NumberColumn(format="%d"),
            })
    else:
        st.info("No active shipments")

    # ===== Top SKUs pending =====
    if not awaiting_df.empty:
        st.markdown(f"#### 🎯 {T['wfs_top_skus_pending']}")
        sku_pend = awaiting_df.groupby(["sku", "description"]).agg(
            pending=("expected_units", lambda x: x.sum() - awaiting_df.loc[x.index, "received_units"].fillna(0).sum()),
            ships=("shipment_id", "nunique"),
        ).reset_index().sort_values("pending", ascending=False).head(15)
        sku_pend["description"] = sku_pend["description"].astype(str).str[:50]

        fig = px.bar(
            sku_pend.sort_values("pending"),
            x="pending", y="sku", orientation="h",
            color="pending", color_continuous_scale="Blues",
            hover_data={"description": True, "ships": True},
        )
        fig.update_layout(
            height=500, template=theme["template"],
            paper_bgcolor=theme["paper_bg"], plot_bgcolor=theme["plot_bg"],
            showlegend=False, coloraxis_showscale=False,
            margin=dict(l=0, r=0, t=20, b=0),
        )
        st.plotly_chart(fig, use_container_width=True)

    # ===== By FC and Carrier =====
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"#### 🏭 {T['wfs_by_fc']}")
        fc_dist = wfs.groupby("fc_name")["shipment_id"].nunique().reset_index().sort_values("shipment_id", ascending=False)
        if not fc_dist.empty:
            fig = px.pie(fc_dist, values="shipment_id", names="fc_name", hole=0.4)
            fig.update_layout(height=350, template=theme["template"], paper_bgcolor=theme["paper_bg"])
            st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown(f"#### 🚚 {T['wfs_by_carrier']}")
        carr_dist = wfs[wfs["carrier_name"].notna() & (wfs["carrier_name"] != "")].groupby("carrier_name")["shipment_id"].nunique().reset_index().sort_values("shipment_id", ascending=False)
        if not carr_dist.empty:
            fig = px.pie(carr_dist, values="shipment_id", names="carrier_name", hole=0.4)
            fig.update_layout(height=350, template=theme["template"], paper_bgcolor=theme["paper_bg"])
            st.plotly_chart(fig, use_container_width=True)


# ============================================================
# 💰 SETTLEMENT SECTION 🆕
# ============================================================

def render_settlement(data, T, theme):
    settle = data.get("settlement", pd.DataFrame())
    if settle.empty:
        st.warning("⚠️ walmart.settlement is empty")
        return

    st.markdown(f"### {T['settlement_section']}")
    st.caption(T["settlement_subtitle"])

    # ===== KPI =====
    n_periods = settle["report_date"].nunique() if "report_date" in settle else 0

    payments = settle[settle["transaction_type"] == "PaymentSummary"]
    net_paid = payments["total_payable"].sum() if not payments.empty else 0

    sales = settle[settle["transaction_type"] == "Sale"]["amount"].sum()
    fees = settle[settle["transaction_type"].isin(["Service Fee", "Campaigns"])]["amount"].sum()
    refunds = settle[settle["transaction_type"] == "Refund"]["amount"].sum()

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric(T["settlement_periods"], f"{n_periods}")
    c2.metric(T["settlement_net_paid"], f"${float(net_paid):,.2f}")
    c3.metric(T["settlement_sales"], f"${float(sales):,.0f}")
    c4.metric(T["settlement_fees"], f"${float(fees):,.0f}")
    c5.metric(T["settlement_refunds_total"], f"${float(refunds):,.0f}")

    # ===== Payouts timeline =====
    st.markdown(f"#### 📈 {T['payouts_chart_title']}")
    if not payments.empty:
        ptime = payments[["report_date", "total_payable", "transaction_description"]].copy()
        ptime["report_date"] = pd.to_datetime(ptime["report_date"])
        ptime = ptime.sort_values("report_date")

        # Колір залежно від знака
        ptime["color"] = ptime["total_payable"].apply(lambda x: "Deposit" if x > 0 else "Debit")

        fig = px.bar(
            ptime, x="report_date", y="total_payable",
            color="color",
            color_discrete_map={"Deposit": "#51cf66", "Debit": "#e03131"},
            hover_data={"transaction_description": True},
        )
        fig.update_layout(
            height=400, template=theme["template"],
            paper_bgcolor=theme["paper_bg"], plot_bgcolor=theme["plot_bg"],
            margin=dict(l=0, r=0, t=20, b=0),
            xaxis_title="", yaxis_title="USD",
        )
        st.plotly_chart(fig, use_container_width=True)

    # ===== Transaction types breakdown =====
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"#### 💱 {T['settlement_by_type']}")
        by_type = settle.groupby("transaction_type").agg(
            cnt=("amount", "count"),
            amt=("amount", "sum")
        ).reset_index().sort_values("amt", ascending=False)
        if not by_type.empty:
            by_type = by_type.rename(columns={
                "transaction_type": T["txn_type"],
                "cnt": T["txn_count"],
                "amt": T["txn_amount"],
            })
            st.dataframe(by_type, use_container_width=True, hide_index=True, height=350,
                column_config={
                    T["txn_amount"]: st.column_config.NumberColumn(format="$%.2f"),
                })

    with c2:
        st.markdown(f"#### 🏆 {T['top_sku_revenue']}")
        sku_rev = settle[(settle["transaction_type"] == "Sale") & (settle["partner_item_id"].notna()) & (settle["partner_item_id"] != "")]
        if not sku_rev.empty:
            top_sku = sku_rev.groupby(["partner_item_id", "partner_item_name"]).agg(
                rev=("amount", "sum"),
                cnt=("amount", "count"),
            ).reset_index().sort_values("rev", ascending=False).head(10)
            top_sku["partner_item_name"] = top_sku["partner_item_name"].astype(str).str[:35]
            top_sku = top_sku.rename(columns={
                "partner_item_id": T["sku"],
                "partner_item_name": T["product"],
                "rev": "Revenue",
                "cnt": "Sales",
            })
            st.dataframe(top_sku, use_container_width=True, hide_index=True, height=350,
                column_config={
                    "Revenue": st.column_config.NumberColumn(format="$%.2f"),
                })

    # ===== Recent payments =====
    st.markdown(f"#### 💰 {T['settlement_recent']}")
    if not payments.empty:
        recent_pay = payments[["report_date", "total_payable", "transaction_description"]].sort_values("report_date", ascending=False).head(10).copy()
        recent_pay = recent_pay.rename(columns={
            "report_date": T["period"],
            "total_payable": T["deposit"],
            "transaction_description": T["channel"],
        })
        st.dataframe(recent_pay, use_container_width=True, hide_index=True,
            column_config={T["deposit"]: st.column_config.NumberColumn(format="$%.2f")})


# ============================================================
# 🔄 CUSTOMER RETURNS SECTION 🆕
# ============================================================

def render_returns(data, T, theme):
    ret = data.get("returns", pd.DataFrame())
    if ret.empty:
        st.warning("⚠️ walmart.returns is empty")
        return

    st.markdown(f"### {T['returns_section']}")
    st.caption(T["returns_subtitle"])

    # ===== KPI =====
    n_returns = ret["return_order_id"].nunique() if "return_order_id" in ret else 0
    n_skus = ret["sku"].nunique() if "sku" in ret else 0
    total_refund = ret["total_refund_amount"].sum() if "total_refund_amount" in ret else 0

    # Listing fix opportunity: returns через INCORRECT_ITEM, DIFFICULT_TO_SETUP, NOT_AS_DESCRIBED
    listing_issues = ["INCORRECT_ITEM", "DIFFICULT_TO_SETUP_NOT_COMPATIBLE", "NOT_AS_DESCRIBED_PICTURED", "DEFECTIVE"]
    if "return_reason" in ret:
        listing_issue_count = ret[ret["return_reason"].isin(listing_issues)].shape[0]
        listing_pct = (100 * listing_issue_count / max(len(ret), 1)) if len(ret) else 0
        listing_loss = ret[ret["return_reason"].isin(listing_issues)]["unit_price"].sum() if "unit_price" in ret else 0
    else:
        listing_issue_count = 0
        listing_pct = 0
        listing_loss = 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(T["returns_total"], f"{n_returns}")
    c2.metric(T["returns_skus"], f"{n_skus}")
    c3.metric(T["returns_refunded_amt"], f"${float(total_refund):,.2f}")
    c4.metric("Listing Issues", f"{listing_pct:.0f}%")

    # ===== Listing fix opportunity callout =====
    if listing_pct > 30:
        st.markdown(f"""
        <div class="opportunity-box">
            <strong style="font-size:1.05rem;">{T['returns_fix_listings']}</strong><br>
            <span style="opacity:0.9;">{listing_issue_count} returns ({listing_pct:.0f}%) {T['returns_fix_text']}.
            Potential recoverable: <strong>${float(listing_loss):,.2f}</strong></span><br>
            <span style="opacity:0.7; font-size:0.9rem;">→ Action: improve product descriptions, fix compatibility info, update photos</span>
        </div>
        """, unsafe_allow_html=True)

    # ===== Reasons & Status =====
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"#### 📊 {T['returns_by_reason']}")
        if "return_reason" in ret:
            reasons = ret.groupby("return_reason").agg(
                cnt=("return_order_id", "count"),
                qty=("quantity", "sum"),
            ).reset_index().sort_values("cnt", ascending=False)

            fig = px.bar(
                reasons.sort_values("cnt"),
                x="cnt", y="return_reason", orientation="h",
                color="cnt", color_continuous_scale="Reds",
                hover_data={"qty": True},
            )
            fig.update_layout(
                height=450, template=theme["template"],
                paper_bgcolor=theme["paper_bg"], plot_bgcolor=theme["plot_bg"],
                showlegend=False, coloraxis_showscale=False,
                margin=dict(l=0, r=0, t=20, b=0),
                yaxis_title="",
            )
            st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown(f"#### 🎯 {T['returns_by_status']}")
        if "current_refund_status" in ret:
            statuses = ret["current_refund_status"].fillna("UNKNOWN").value_counts().reset_index()
            statuses.columns = ["status", "count"]
            colors = {
                "REFUND_COMPLETED": "#51cf66",
                "REFUND_INITIATED": "#fab005",
                "CANCELLED": "#868e96",
                "NOT_REFUNDED": "#e03131",
                "UNKNOWN": "#adb5bd",
            }
            fig = px.pie(
                statuses, values="count", names="status",
                color="status", color_discrete_map=colors, hole=0.4,
            )
            fig.update_layout(height=450, template=theme["template"], paper_bgcolor=theme["paper_bg"])
            st.plotly_chart(fig, use_container_width=True)

    # ===== Killer SKUs =====
    st.markdown(f"#### 💸 {T['returns_killer_skus']}")
    if "sku" in ret and "unit_price" in ret:
        killer = ret[(ret["sku"].notna()) & (ret["sku"] != "")].copy()
        killer["lost"] = killer["unit_price"].fillna(0) * killer["quantity"].fillna(1)
        killer_agg = killer.groupby(["sku", "item_name"]).agg(
            returns=("return_order_id", "count"),
            units=("quantity", "sum"),
            lost=("lost", "sum"),
        ).reset_index().sort_values("lost", ascending=False).head(15)
        killer_agg["item_name"] = killer_agg["item_name"].astype(str).str[:50]
        killer_agg = killer_agg.rename(columns={
            "sku": T["sku"],
            "item_name": T["product"],
            "returns": "Returns",
            "units": "Units",
            "lost": "$ Lost",
        })
        st.dataframe(killer_agg, use_container_width=True, hide_index=True, height=400,
            column_config={
                "$ Lost": st.column_config.NumberColumn(format="$%.2f"),
            })

    # ===== Recent returns =====
    st.markdown(f"#### 📋 {T['returns_recent']}")
    if not ret.empty:
        recent = ret[["return_order_date", "sku", "item_name", "return_reason",
                      "quantity", "total_refund_amount", "current_refund_status", "carrier_name"]].copy()
        recent = recent.sort_values("return_order_date", ascending=False).head(20)
        recent["return_order_date"] = pd.to_datetime(recent["return_order_date"]).dt.strftime("%Y-%m-%d %H:%M")
        recent["item_name"] = recent["item_name"].astype(str).str[:40]
        recent = recent.rename(columns={
            "return_order_date": T["returns_date"],
            "sku": T["sku"],
            "item_name": T["product"],
            "return_reason": T["returns_reason"],
            "quantity": T["returns_qty"],
            "total_refund_amount": T["returns_refund_amt"],
            "current_refund_status": T["returns_status_col"],
            "carrier_name": T["returns_carrier"],
        })
        st.dataframe(recent, use_container_width=True, hide_index=True, height=400,
            column_config={
                T["returns_refund_amt"]: st.column_config.NumberColumn(format="$%.2f"),
            })


# ============================================================
# 🚨 HEALTH CHECK (старий)
# ============================================================

def _severity_class(s):
    return {"CRITICAL": "severity-crit", "WARNING": "severity-warn", "INFO": "severity-info"}.get(s, "severity-info")


def build_action_items(data, lang):
    items = data.get("items", pd.DataFrame())
    perf = data.get("performance", pd.DataFrame())
    buybox = data.get("buybox", pd.DataFrame())
    cancel = data.get("cancellations", pd.DataFrame())
    returns = data.get("returns", pd.DataFrame())

    actions = []

    # SYSTEM_PROBLEM SKUs
    if not items.empty:
        problem = items[items["publish_status"].isin(["SYSTEM_PROBLEM", "UNPUBLISHED", "STAGE"])]
        if len(problem) > 0:
            for reason_key, sub in problem.groupby("status_change_reason"):
                skus = sub["sku"].tolist()
                reason_str = reason_key or "Unknown"
                if "Brand" in reason_str:
                    act = {"RU": "Подтвердить бренд UDC Parts в Brand Portal",
                           "UA": "Підтвердити бренд UDC Parts в Brand Portal",
                           "EN": "Confirm UDC Parts brand in Brand Portal"}[lang]
                    owner = "Catalog ops"
                elif "Product Type" in reason_str or "Default" in reason_str:
                    act = {"RU": "Назначить правильную категорию",
                           "UA": "Призначити правильну категорію",
                           "EN": "Set correct category"}[lang]
                    owner = "Catalog ops"
                elif "Price" in reason_str:
                    act = {"RU": "Снизить цену до reasonable price",
                           "UA": "Знизити ціну до reasonable price",
                           "EN": "Lower price to reasonable level"}[lang]
                    owner = "Pricing"
                else:
                    act = {"RU": "Проверить в Seller Center",
                           "UA": "Перевірити в Seller Center",
                           "EN": "Check Seller Center"}[lang]
                    owner = "Catalog ops"
                actions.append({
                    "severity": "CRITICAL", "issue": reason_str, "count": len(skus),
                    "impact_ru": f"Не покупаются: {', '.join(skus[:3])}",
                    "impact_ua": f"Не купуються: {', '.join(skus[:3])}",
                    "impact_en": f"Cannot be purchased: {', '.join(skus[:3])}",
                    "action": act, "owner": owner, "skus": skus,
                })

    # CAP heavy
    if not buybox.empty and "price_diff_pct" in buybox:
        heavy = buybox[buybox["price_diff_pct"].fillna(0) > 0.20]
        if len(heavy) > 0:
            loss = (heavy["seller_item_price"] - heavy["buybox_item_price"]).sum()
            actions.append({
                "severity": "CRITICAL", "issue": "CAP Discount 20%+", "count": len(heavy),
                "impact_ru": f"Walmart режет {len(heavy)} SKU >20%. Loss: ${float(loss):.2f}/ед",
                "impact_ua": f"Walmart ріже {len(heavy)} SKU >20%. Loss: ${float(loss):.2f}/од",
                "impact_en": f"Walmart cuts {len(heavy)} SKUs >20%. Loss: ${float(loss):.2f}/unit",
                "action": {"RU": "Поднять Min Allowed Price",
                           "UA": "Підняти Min Allowed Price",
                           "EN": "Raise Min Allowed Price"}[lang],
                "owner": "Pricing", "skus": heavy["sku"].tolist(),
            })

    # 🆕 RETURN KILLER SKUS
    if not returns.empty and "sku" in returns and "unit_price" in returns:
        listing_issues = ["INCORRECT_ITEM", "DIFFICULT_TO_SETUP_NOT_COMPATIBLE", "NOT_AS_DESCRIBED_PICTURED"]
        killer = returns[returns["return_reason"].isin(listing_issues)]
        if not killer.empty:
            sku_returns = killer.groupby("sku").size().reset_index(name="cnt")
            heavy = sku_returns[sku_returns["cnt"] >= 5]
            if not heavy.empty:
                total_lost = (killer["unit_price"].fillna(0) * killer["quantity"].fillna(1)).sum()
                actions.append({
                    "severity": "WARNING",
                    "issue": "Listing issues causing returns",
                    "count": len(heavy),
                    "impact_ru": f"{len(heavy)} SKU мають 5+ повернень через лістинг. Потеря: ${float(total_lost):.2f}",
                    "impact_ua": f"{len(heavy)} SKU мають 5+ повернень через лістинг. Втрата: ${float(total_lost):.2f}",
                    "impact_en": f"{len(heavy)} SKUs have 5+ returns due to listings. Lost: ${float(total_lost):.2f}",
                    "action": {"RU": "Покращити compatibility info та фото в листингу",
                               "UA": "Покращити compatibility info та фото в лістингу",
                               "EN": "Improve compatibility info and photos in listing"}[lang],
                    "owner": "Content / Listings",
                    "skus": heavy["sku"].tolist(),
                })

    # Repeat cancellations
    if not cancel.empty and "catalog_item_id" in cancel:
        rep = cancel.groupby("catalog_item_id").size().reset_index(name="cnt")
        rep = rep[rep["cnt"] > 1]
        if len(rep) > 0:
            actions.append({
                "severity": "WARNING", "issue": "Repeat OOS cancellations", "count": len(rep),
                "impact_ru": f"{len(rep)} SKU повторно скасовуються",
                "impact_ua": f"{len(rep)} SKU повторно скасовуються",
                "impact_en": f"{len(rep)} SKUs repeatedly cancelled",
                "action": {"RU": "Терміново пополнити запас або quantity=0",
                           "UA": "Терміново поповнити запас або quantity=0",
                           "EN": "Urgently restock or set quantity=0"}[lang],
                "owner": "Logistics", "skus": rep["catalog_item_id"].tolist(),
            })

    sev_order = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
    actions.sort(key=lambda a: (sev_order.get(a["severity"], 3), -a["count"]))
    return actions


def render_health_check(data, T, theme, lang):
    st.markdown(f"### {T['health_section']}")
    st.caption(T['health_subtitle'])

    actions = build_action_items(data, lang)

    if not actions:
        st.success("✅ All clear")
        return

    impact_key = f"impact_{lang.lower()}"

    for act in actions:
        cls = _severity_class(act["severity"])
        impact = act.get(impact_key, act.get("impact_en", ""))
        emoji = {"CRITICAL": "🔴", "WARNING": "🟡", "INFO": "🔵"}.get(act["severity"], "⚪")

        st.markdown(f"""
        <div class="{cls}">
            <div style="display:flex; justify-content:space-between;">
                <div><strong>{emoji} {act['issue']}</strong> · {T['affected']}: <b>{act['count']}</b></div>
                <div style="opacity:0.6; font-size:0.85rem;">👤 {act['owner']}</div>
            </div>
            <div style="margin-top:6px; opacity:0.9;">{impact}</div>
            <div style="margin-top:8px;"><strong>→ {T['action']}:</strong> {act['action']}</div>
        </div>
        """, unsafe_allow_html=True)

        if act.get("skus"):
            with st.expander(f"🔽 SKU list ({len(act['skus'])})"):
                st.code("\n".join(act["skus"]), language=None)


# ============================================================
# 💰 BUYBOX (старий)
# ============================================================

def render_buybox(data, T, theme):
    buybox = data.get("buybox", pd.DataFrame())
    if buybox.empty:
        return

    st.markdown(f"### {T['buybox_section']}")
    st.caption(T["buybox_subtitle"])

    cut_skus = buybox[buybox["price_diff_pct"].fillna(0) > 0.05]
    total_loss = (cut_skus["seller_item_price"] - cut_skus["buybox_item_price"]).sum()

    c1, c2, c3 = st.columns(3)
    c1.metric("Cut SKUs (5%+)", f"{len(cut_skus)}")
    c2.metric("Cut SKUs (10%+)", f"{(buybox['price_diff_pct'].fillna(0) > 0.10).sum()}")
    c3.metric(T["buybox_hidden_loss"], f"${float(total_loss):.2f}")

    st.markdown(f"#### {T['cap_top']}")
    top = cut_skus.nlargest(20, "price_diff_pct")[
        ["sku", "product_name", "seller_item_price", "buybox_item_price", "price_diff_pct", "is_seller_buybox_winner"]
    ].copy()
    top["margin_lost"] = (top["seller_item_price"] - top["buybox_item_price"]).round(2)
    top["price_diff_pct"] = (top["price_diff_pct"] * 100).round(1)
    top = top.rename(columns={
        "sku": T["sku"], "product_name": T["product"],
        "seller_item_price": T["seller_price"], "buybox_item_price": T["buybox_price"],
        "price_diff_pct": T["cut_pct"], "is_seller_buybox_winner": "BB",
        "margin_lost": T["margin_lost"],
    })
    top[T["product"]] = top[T["product"]].astype(str).str[:50]

    st.dataframe(top, use_container_width=True, height=400,
        column_config={
            T["seller_price"]: st.column_config.NumberColumn(format="$%.2f"),
            T["buybox_price"]: st.column_config.NumberColumn(format="$%.2f"),
            T["margin_lost"]: st.column_config.NumberColumn(format="$%.2f"),
            T["cut_pct"]: st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=30),
        })


# ============================================================
# 📈 PERFORMANCE (старий)
# ============================================================

def render_performance(data, T, theme):
    perf = data.get("performance", pd.DataFrame())
    if perf.empty:
        return

    st.markdown(f"### {T['performance_section']}")
    st.caption(T["performance_subtitle"])

    dead = perf[(perf["gmv"].fillna(0) == 0) & (perf["total_ly_gmv"].fillna(0) > 0)]
    if len(dead) > 0:
        st.markdown(f"#### 💀 {T['dead_skus_title']} — {len(dead)}")
        d = dead[["sku", "product_name", "total_ly_gmv", "product_level_pageviews"]].copy()
        d["product_name"] = d["product_name"].astype(str).str[:60]
        d = d.rename(columns={
            "sku": T["sku"], "product_name": T["product"],
            "total_ly_gmv": T["ly_gmv"], "product_level_pageviews": "Pageviews",
        })
        d = d.sort_values(T["ly_gmv"], ascending=False)
        st.dataframe(d, use_container_width=True, height=300,
            column_config={T["ly_gmv"]: st.column_config.NumberColumn(format="$%.2f")})

    neg = perf[
        (perf["gmv"].fillna(0) < 0) |
        ((perf["refunded_sales"].fillna(0) > 0) &
         (perf["gmv"].fillna(0) - perf["refunded_sales"].fillna(0) < 0))
    ]
    if len(neg) > 0:
        st.markdown(f"#### 📉 {T['neg_gmv_title']} — {len(neg)}")
        n = neg[["sku", "product_name", "gmv", "refunded_sales"]].copy()
        n["net"] = (n["gmv"].fillna(0) - n["refunded_sales"].fillna(0)).round(2)
        n["product_name"] = n["product_name"].astype(str).str[:60]
        n = n.rename(columns={
            "sku": T["sku"], "product_name": T["product"],
            "gmv": T["gmv_label"], "refunded_sales": T["refund_label"], "net": T["net_label"],
        })
        n = n.sort_values(T["net_label"])
        st.dataframe(n, use_container_width=True, height=300,
            column_config={
                T["gmv_label"]: st.column_config.NumberColumn(format="$%.2f"),
                T["refund_label"]: st.column_config.NumberColumn(format="$%.2f"),
                T["net_label"]: st.column_config.NumberColumn(format="$%.2f"),
            })

    c1, c2 = st.columns(2)
    with c1:
        top_gmv = perf[perf["gmv"].fillna(0) > 0].nlargest(15, "gmv")
        if len(top_gmv) > 0:
            fig = px.bar(top_gmv.sort_values("gmv"), x="gmv", y="sku", orientation='h',
                title=T["top_gmv"], color="gmv", color_continuous_scale="Greens",
                hover_data={"product_name": True, "total_units_sold": True})
            fig.update_layout(height=500, template=theme["template"],
                paper_bgcolor=theme["paper_bg"], plot_bgcolor=theme["plot_bg"],
                showlegend=False, coloraxis_showscale=False, margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig, use_container_width=True)

    with c2:
        top_refund = perf[perf["refunded_sales"].fillna(0) > 0].nlargest(10, "refunded_sales")
        if len(top_refund) > 0:
            fig = px.bar(top_refund.sort_values("refunded_sales"),
                x="refunded_sales", y="sku", orientation='h',
                title=T["top_refund"], color="refunded_sales", color_continuous_scale="Reds",
                hover_data={"product_name": True, "gmv": True})
            fig.update_layout(height=500, template=theme["template"],
                paper_bgcolor=theme["paper_bg"], plot_bgcolor=theme["plot_bg"],
                showlegend=False, coloraxis_showscale=False, margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig, use_container_width=True)


# ============================================================
# 📋 ITEM STATUS (старий)
# ============================================================

def render_item_status(data, T, theme):
    items = data.get("items", pd.DataFrame())
    if items.empty:
        return

    st.markdown(f"### {T['status_section']}")
    c1, c2 = st.columns([1, 1.5])

    with c1:
        status_counts = items["publish_status"].fillna("NULL").value_counts().reset_index()
        status_counts.columns = ["status", "count"]
        fig = px.pie(status_counts, values="count", names="status",
            color_discrete_sequence=["#51cf66", "#ff6b6b", "#fab005", "#868e96"])
        fig.update_layout(height=300, template=theme["template"],
            paper_bgcolor=theme["paper_bg"], margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        probs = items[items["publish_status"].isin(["SYSTEM_PROBLEM", "UNPUBLISHED", "STAGE"])]
        if len(probs) > 0:
            st.markdown(f"#### {T['problem_skus_title']}")
            p = probs[["sku", "publish_status", "status_change_reason", "product_name"]].copy()
            p["product_name"] = p["product_name"].astype(str).str[:45]
            p = p.rename(columns={
                "sku": T["sku"], "publish_status": T["status_col"],
                "status_change_reason": T["reason_col"], "product_name": T["product"],
            })
            st.dataframe(p, use_container_width=True, height=280)


# ============================================================
# 🔄 CANCELLATIONS (старий)
# ============================================================

def render_cancellations(data, T, theme):
    cancel = data.get("cancellations", pd.DataFrame())
    if cancel.empty:
        return

    st.markdown(f"### {T['cancel_section']}")
    st.caption(T["cancel_subtitle"])

    total = len(cancel)
    by_reason = cancel["cancel_reason"].fillna("UNKNOWN").value_counts().reset_index()
    by_reason.columns = ["reason", "count"]

    c1, c2 = st.columns([1, 1])
    with c1:
        st.metric("Total Cancellations", total)
        if len(by_reason) > 0:
            st.dataframe(by_reason, use_container_width=True, hide_index=True)

    with c2:
        if "catalog_item_id" in cancel.columns:
            rep = cancel.groupby("catalog_item_id").size().reset_index(name="cnt")
            rep = rep[rep["cnt"] > 1].sort_values("cnt", ascending=False)
            if len(rep) > 0:
                st.markdown(f"#### 🚨 {T['repeat_offenders']}")
                rep = rep.rename(columns={"catalog_item_id": T["sku"], "cnt": T["cancel_count"]})
                st.dataframe(rep, use_container_width=True, hide_index=True)
            else:
                st.info("No repeat offenders ✅")


# ============================================================
# ⏱️ LOADER RUNS (старий)
# ============================================================

def render_loader_runs(data, T, theme):
    runs = data.get("report_runs", pd.DataFrame())
    if runs.empty:
        return

    st.markdown(f"### {T['loader_section']}")
    r = runs[["report_type", "status", "rows_loaded", "started_at", "error_message"]].copy()
    r = r.rename(columns={
        "report_type": T["report_type"], "status": T["status"],
        "rows_loaded": T["rows_loaded"], "started_at": T["started_at"],
        "error_message": "Error",
    })
    r[T["started_at"]] = pd.to_datetime(r[T["started_at"]], errors='coerce').dt.strftime("%Y-%m-%d %H:%M")
    st.dataframe(r, use_container_width=True, height=350, hide_index=True)


# ============================================================
# 🤖 GEMINI AI (оновлено для нових таблиць)
# ============================================================

def call_gemini(prompt: str):
    import requests as req
    api_key = st.secrets.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return None, None
    MODELS = [
        st.secrets.get("GEMINI_MODEL", "gemini-2.5-flash"),
        "gemini-2.0-flash",
        "gemini-flash-latest",
    ]
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    for model in MODELS:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            r = req.post(url, json=payload, timeout=45)
            result = r.json()
            if "error" in result:
                continue
            if "candidates" in result and result["candidates"]:
                return result["candidates"][0]["content"]["parts"][0]["text"], model
        except Exception:
            continue
    return None, None


SCHEMA_DESCRIPTION = """
Schema: walmart

Table: walmart.items (193 rows)
Columns: sku, item_id, product_name, lifecycle_status, publish_status,
  status_change_reason, price NUMERIC, msrp, brand,
  reviews_count, average_rating, minimum_seller_allowed_price

Table: walmart.item_performance (137 rows, keyed by (report_date, sku))
Columns: report_date DATE, sku, gmv NUMERIC, refunded_sales,
  total_units_sold, total_ly_gmv, item_conversion_rate

Table: walmart.buybox (133 rows)
Columns: sku, seller_item_price, buybox_item_price,
  price_diff_pct (e.g. 0.277 = 27.7%), is_seller_buybox_winner

Table: walmart.cancellations
Columns: sales_order, cancel_date, catalog_item_id, cancel_reason

🆕 Table: walmart.wfs_shipments (538 rows, 27 ships, 226 SKU)
Columns: shipment_id, inbound_order_id, sku, gtin, description,
  po_status (AWAITING_DELIVERY/CLOSED/CANCELLED),
  fc_name (MCO1/DFW2n/PHL5s/KY1),
  carrier_name, tracking_no,
  po_create_date, expected_delivery_date, po_delivered_date,
  expected_units INT, received_units INT, damaged_units INT

🆕 Table: walmart.settlement (22,678 rows, 53 periods, 2 years history)
Columns: report_date DATE, period_start_date, period_end_date,
  total_payable NUMERIC, amount NUMERIC, amount_type,
  transaction_type (Sale/Refund/Adjustment/Service Fee/Campaigns/PaymentSummary),
  transaction_description, customer_order_id,
  partner_item_id (SKU!), partner_gtin, partner_item_name,
  ship_qty, ship_to_state, ship_to_city,
  commission_rate, original_commission, campaign_id

🆕 Table: walmart.returns (202 rows, 82 SKU)
Columns: return_order_id, customer_order_id, customer_email,
  return_order_date TIMESTAMPTZ, return_by_date,
  total_refund_amount NUMERIC, currency,
  return_channel, refund_mode, return_method,
  sku, item_name, item_condition, item_weight,
  return_reason (NO_LONGER_WANTED/INCORRECT_ITEM/DIFFICULT_TO_SETUP_NOT_COMPATIBLE/
    NOT_AS_DESCRIBED_PICTURED/DEFECTIVE/LOST_IN_TRANSIT/Other),
  is_keep_it BOOL, refund_covered_by (Seller/Walmart),
  quantity, unit_price NUMERIC,
  status, current_delivery_status, current_refund_status,
  carrier_name, carrier_tracking_no, return_label_url,
  latest_tracking_event
"""


def ai_generate_sql(user_question: str, lang: str) -> str:
    prompt = f"""You are a PostgreSQL expert working with Walmart Marketplace data for UDC Mower Parts LLC.

{SCHEMA_DESCRIPTION}

User question: "{user_question}"

Write ONE SQL SELECT query.
- Tables in schema `walmart` — use full qualifier (walmart.items, walmart.settlement etc.)
- Max 50 rows
- ONLY pure SQL, no markdown, no ``` blocks, no explanations
- Start with SELECT"""

    sql, _ = call_gemini(prompt)
    if sql:
        sql = sql.strip().replace("```sql", "").replace("```", "").strip()
    return sql


def ai_analyze_results(user_question, sql, df_result, lang):
    lang_instruction = {
        "RU": "Отвечай на русском.",
        "UA": "Відповідай українською.",
        "EN": "Respond in English.",
    }.get(lang, "Respond in English.")

    if len(df_result) > 30:
        data_str = df_result.head(30).to_string(index=False) + f"\n... (showing 30 of {len(df_result)} rows)"
    else:
        data_str = df_result.to_string(index=False)

    prompt = f"""You are McKinsey-level Walmart consultant.
{lang_instruction}

User asked: "{user_question}"
SQL: {sql}
Results:
{data_str}

Provide:
1. Direct answer (1-2 sentences)
2. Key insights with specific numbers
3. Action items — WHO does WHAT by WHEN

Use bullets. Max 300 words."""

    answer, model = call_gemini(prompt)
    return answer, model


def render_ai_section(T, lang):
    st.markdown(f"### {T['ai_section']}")

    api_key = st.secrets.get("GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        st.warning(T["ai_no_key"])
        with st.expander("💡 How to add"):
            st.code('GEMINI_API_KEY = "AIzaSy..."', language="toml")
            st.markdown("Streamlit Cloud → **Settings → Secrets**")
        return

    # Швидкі питання — 🆕 додано нові
    quick_q = {
        "RU": [
            "Сколько денег выплачено в PAYONEER за последние 3 месяца?",
            "Какие SKU имеют больше всего returns по причине INCORRECT_ITEM?",
            "Какие активные shipments прибудут в ближайшие 7 дней?",
        ],
        "UA": [
            "Скільки грошей виплачено в PAYONEER за останні 3 місяці?",
            "Які SKU мають найбільше returns через INCORRECT_ITEM?",
            "Які активні shipments прибудуть в найближчі 7 днів?",
        ],
        "EN": [
            "How much was paid to PAYONEER in last 3 months?",
            "Which SKUs have most returns due to INCORRECT_ITEM?",
            "Which active shipments arrive in next 7 days?",
        ],
    }
    questions = quick_q.get(lang, quick_q["EN"])

    c1, c2, c3 = st.columns(3)
    b1 = c1.button(f"💰 {questions[0][:30]}...", use_container_width=True, key="q1")
    b2 = c2.button(f"🔄 {questions[1][:30]}...", use_container_width=True, key="q2")
    b3 = c3.button(f"🚛 {questions[2][:30]}...", use_container_width=True, key="q3")

    user_q = st.text_input(T["ai_prompt_label"], placeholder=T["ai_prompt_placeholder"], key="ai_input")
    ask = st.button(T["ai_ask"], type="primary", key="ai_ask")

    final_q = None
    if b1: final_q = questions[0]
    elif b2: final_q = questions[1]
    elif b3: final_q = questions[2]
    elif ask and user_q: final_q = user_q

    if final_q:
        with st.spinner("🔍 AI генерує SQL..."):
            sql = ai_generate_sql(final_q, lang)
        if not sql:
            st.error(f"{T['ai_error']}: не вдалось згенерувати SQL")
            return

        with st.expander(T["ai_sql_expander"]):
            st.code(sql, language="sql")

        with st.spinner("⚡ Виконуємо запит..."):
            try:
                with get_engine().connect() as conn:
                    df_res = pd.read_sql(text(sql), conn)
            except Exception as e:
                st.error(f"❌ SQL error: {e}")
                return

        if df_res.empty:
            st.warning("⚠️ Empty result")
            return

        with st.expander(f"{T['ai_result_expander']} ({len(df_res)} rows)"):
            st.dataframe(df_res, use_container_width=True)

        with st.spinner(T["ai_loading"]):
            answer, model = ai_analyze_results(final_q, sql, df_res, lang)

        if answer:
            st.caption(f"🤖 Model: `{model}`")
            st.markdown(f'<div class="ai-box">{answer}</div>', unsafe_allow_html=True)
        else:
            st.error(T["ai_error"])


# ============================================================
# 🚀 MAIN
# ============================================================

def main():
    with st.sidebar:
        try:
            st.image(
                "https://udcparts.com/cdn/shop/files/logo.svg?v=1701894617&width=300",
                use_container_width=True
            )
        except Exception:
            st.markdown("### 🏪 UDC Parts")

        st.divider()
        lang = st.selectbox("🌐 Language / Мова / Язык", ["RU", "UA", "EN"], index=0, key="wm_lang")
        T = TRANSLATIONS[lang]
        theme_name = st.radio(T["theme"], [T["dark"], T["light"]], horizontal=True, key="wm_theme")
        theme = DARK_THEME if theme_name == T["dark"] else LIGHT_THEME

        st.divider()
        if st.button(T["refresh"], use_container_width=True, key="wm_refresh"):
            st.cache_data.clear()
            st.rerun()

        st.divider()
        st.markdown(f"### {T['sections']}")

        # 🆕 Нові розділи на початку
        show_orders = st.checkbox(T["orders_section"], True, key="wm_orders")
        show_wfs = st.checkbox(T["wfs_section"], True, key="wm_wfs")
        show_settle = st.checkbox(T["settlement_section"], True, key="wm_settle")
        show_returns = st.checkbox(T["returns_section"], True, key="wm_returns")
        st.markdown("---")
        # Старі
        show_health = st.checkbox(T["health_section"], True, key="wm_s1")
        show_buybox = st.checkbox(T["buybox_section"], False, key="wm_s2")
        show_perf = st.checkbox(T["performance_section"], False, key="wm_s3")
        show_status = st.checkbox(T["status_section"], False, key="wm_s4")
        show_cancel = st.checkbox(T["cancel_section"], False, key="wm_s5")
        show_loader = st.checkbox(T["loader_section"], False, key="wm_s6")
        st.markdown("---")
        show_ai = st.checkbox(T["ai_section"], True, key="wm_s7")

    apply_theme(theme)

    st.markdown(f"## {T['title']}")
    st.caption(f"`walmart.*` · {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    st.divider()

    with st.spinner(T["loading"]):
        data = load_walmart_data()

    if data is None or all(df.empty for df in data.values()):
        st.warning(T["no_data"])
        return

    kpi_row(data, T)
    st.divider()

    # 🆕 НОВІ РОЗДІЛИ
    if show_orders:
        render_orders(data, T, theme)
        st.divider()

    if show_wfs:
        render_wfs_shipments(data, T, theme)
        st.divider()

    if show_settle:
        render_settlement(data, T, theme)
        st.divider()

    if show_returns:
        render_returns(data, T, theme)
        st.divider()

    # СТАРІ
    if show_health:
        render_health_check(data, T, theme, lang)
        st.divider()

    if show_buybox:
        render_buybox(data, T, theme)
        st.divider()

    if show_perf:
        render_performance(data, T, theme)
        st.divider()

    if show_status:
        render_item_status(data, T, theme)
        st.divider()

    if show_cancel:
        render_cancellations(data, T, theme)
        st.divider()

    if show_loader:
        render_loader_runs(data, T, theme)
        st.divider()

    if show_ai:
        render_ai_section(T, lang)


if __name__ == "__main__":
    main()
