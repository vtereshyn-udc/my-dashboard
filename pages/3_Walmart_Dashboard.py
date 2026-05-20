"""
Walmart Reports Dashboard v3.2 — SMART BI з AI Executive Briefing
ЗМІНИ vs v3.1:
- 🆕 🧠 AI Executive Briefing у Overview
  Gemini автоматично аналізує всі дані (orders, settlement, returns, wfs)
  і пише executive briefing з трьома секціями:
    📊 SITUATION — де бізнес зараз
    🎯 TOP-3 ACTIONS — найважливіші дії на тиждень з $ impact
    ⚠️ RISKS & OPPORTUNITIES
    🔮 ONE THING TO WATCH
- Виправлено tz-aware/naive datetime errors

v3.1: SMART BI structure (Executive Summary, KPIs, Waterfall, Insights)
v3.0: Категорії + 3 режими (Overview/Focus/All)
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
import os
import json
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

        # 🆕 View modes
        "view_mode": "📐 View mode",
        "view_overview": "🎯 Overview (top of each)",
        "view_focus": "🔍 Focus (pick one)",
        "view_all": "📚 All sections",
        "pick_section": "Select section",

        # 🆕 Categories
        "cat_sales": "💵 SALES & MONEY",
        "cat_ops": "📦 OPERATIONS",
        "cat_problems": "🚨 PROBLEMS & ACTIONS",
        "cat_catalog": "📋 CATALOG",
        "cat_system": "⚙️ SYSTEM",
        "cat_ai": "🤖 AI",

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

        # 🆕 View modes
        "view_mode": "📐 Режим перегляду",
        "view_overview": "🎯 Огляд (зведення)",
        "view_focus": "🔍 Фокус (один розділ)",
        "view_all": "📚 Все одразу",
        "pick_section": "Оберіть розділ",

        # 🆕 Categories
        "cat_sales": "💵 ПРОДАЖІ ТА ГРОШІ",
        "cat_ops": "📦 ОПЕРАЦІЇ",
        "cat_problems": "🚨 ПРОБЛЕМИ ТА ДІЇ",
        "cat_catalog": "📋 КАТАЛОГ",
        "cat_system": "⚙️ СИСТЕМА",
        "cat_ai": "🤖 AI",

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

        # 🆕 View modes
        "view_mode": "📐 Режим просмотра",
        "view_overview": "🎯 Обзор (сводка)",
        "view_focus": "🔍 Фокус (один раздел)",
        "view_all": "📚 Всё сразу",
        "pick_section": "Выберите раздел",

        # 🆕 Categories
        "cat_sales": "💵 ПРОДАЖИ И ДЕНЬГИ",
        "cat_ops": "📦 ОПЕРАЦИИ",
        "cat_problems": "🚨 ПРОБЛЕМЫ И ДЕЙСТВИЯ",
        "cat_catalog": "📋 КАТАЛОГ",
        "cat_system": "⚙️ СИСТЕМА",
        "cat_ai": "🤖 AI",

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
        "orders":          "SELECT * FROM walmart.orders WHERE order_date::timestamp >= CURRENT_DATE - INTERVAL '180 days'",
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
    """💎 SMART ORDERS — повноцінний BI розділ.
    Структура:
      1. Executive Summary
      2. KPI Row (8 cards)
      3. Daily Revenue Trend (з MA)
      4. Top SKUs + Geo
      5. Fulfillment & Status breakdown
      6. Anomalies & Insights
      7. Detail table
    """
    orders = data.get("orders", pd.DataFrame())
    if orders.empty:
        st.warning("⚠️ walmart.orders is empty (check loader)")
        return

    st.markdown(f"### {T['orders_section']}")
    st.caption(T["orders_subtitle"])

    # ============ Підготовка даних ============
    df = orders.copy()
    # order_date — text → datetime (naive, без tz)
    df["order_dt"] = pd.to_datetime(df["order_date"], errors='coerce', utc=True).dt.tz_localize(None)
    df = df[df["order_dt"].notna()].copy()
    df["line_total"] = pd.to_numeric(df["line_total"], errors='coerce').fillna(0)
    df["tax_total"] = pd.to_numeric(df["tax_total"], errors='coerce').fillna(0)
    df["quantity"] = pd.to_numeric(df["quantity"], errors='coerce').fillna(0)
    df["revenue"] = df["line_total"] + df["tax_total"]
    df["date"] = df["order_dt"].dt.date

    today = datetime.now().date()
    last30 = df[df["order_dt"] >= pd.Timestamp(today - timedelta(days=30))]
    last60 = df[df["order_dt"] >= pd.Timestamp(today - timedelta(days=60))]
    prev30 = df[(df["order_dt"] >= pd.Timestamp(today - timedelta(days=60))) &
                (df["order_dt"] < pd.Timestamp(today - timedelta(days=30)))]

    # ============ 1. EXECUTIVE SUMMARY ============
    total_revenue = df["revenue"].sum()
    total_orders = df["customer_order_id"].nunique()
    revenue_30d = last30["revenue"].sum()
    revenue_prev30 = prev30["revenue"].sum()
    growth = ((revenue_30d - revenue_prev30) / max(revenue_prev30, 1)) * 100 if revenue_prev30 > 0 else 0

    cancelled = df[df["line_status"].str.lower() == "cancelled"]
    cancel_rate = (len(cancelled) / max(len(df), 1)) * 100

    growth_emoji = "📈" if growth > 0 else "📉" if growth < 0 else "➡️"
    growth_color = "#51cf66" if growth > 0 else "#e03131"

    st.markdown(f"""
    <div style="background: linear-gradient(135deg, rgba(124,159,255,0.10), rgba(81,207,102,0.08));
                border-left: 4px solid #7c9fff; padding: 14px 18px; border-radius: 8px;
                margin: 8px 0 16px 0;">
        <strong style="font-size:1.05rem;">📊 Executive Summary</strong><br>
        <span style="opacity:0.9;">
        За {len(df):,} line items продано <b>${total_revenue:,.0f}</b> (з податками).
        Останні 30 днів: <b>${revenue_30d:,.0f}</b>
        <span style="color:{growth_color}; font-weight:600;">{growth_emoji} {growth:+.1f}%</span>
        проти попередніх 30 днів.
        Cancel rate: <b>{cancel_rate:.1f}%</b>.
        </span>
    </div>
    """, unsafe_allow_html=True)

    # ============ 2. KPI ROW (8 cards в 2 рядах) ============
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📦 Total Line Items", f"{len(df):,}")
    c2.metric("🛒 Unique Orders", f"{total_orders:,}")
    c3.metric("💵 Total Revenue", f"${total_revenue:,.0f}")
    c4.metric("📊 Avg Order Value", f"${(total_revenue / max(total_orders, 1)):,.2f}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📅 Last 30d Revenue", f"${revenue_30d:,.0f}", f"{growth:+.1f}%")
    c2.metric("📦 Last 30d Orders", f"{last30['customer_order_id'].nunique():,}")
    c3.metric("🚫 Cancel Rate", f"{cancel_rate:.1f}%")
    c4.metric("🎯 Unique SKUs Sold", f"{df['sku'].nunique():,}")

    st.divider()

    # ============ 3. DAILY REVENUE TREND ============
    st.markdown("#### 📈 Daily Revenue & Orders Trend")

    daily = df.groupby("date").agg(
        revenue=("revenue", "sum"),
        orders=("customer_order_id", "nunique"),
        units=("quantity", "sum"),
    ).reset_index().sort_values("date")

    # 7-day MA
    daily["rev_ma7"] = daily["revenue"].rolling(7, min_periods=1).mean()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=daily["date"], y=daily["revenue"],
        name="Daily Revenue $", marker_color="#7c9fff", yaxis="y",
        hovertemplate="<b>%{x}</b><br>Revenue: $%{y:,.2f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=daily["date"], y=daily["rev_ma7"],
        name="7-day MA", mode="lines",
        line=dict(color="#fab005", width=3, dash="dot"), yaxis="y",
    ))
    fig.add_trace(go.Scatter(
        x=daily["date"], y=daily["orders"],
        name="Orders count", mode="lines+markers",
        line=dict(color="#51cf66", width=2), yaxis="y2",
        marker=dict(size=4),
    ))
    fig.update_layout(
        height=420, template=theme["template"],
        paper_bgcolor=theme["paper_bg"], plot_bgcolor=theme["plot_bg"],
        margin=dict(l=0, r=0, t=20, b=0),
        yaxis=dict(title="Revenue $", side="left"),
        yaxis2=dict(title="Orders", overlaying="y", side="right", showgrid=False),
        legend=dict(orientation="h", y=1.12),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)

    # ============ 4. TOP SKUs + GEO ============
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("#### 🏆 Top 15 SKUs (Last 30d)")
        top_sku = last30.groupby(["sku", "product_name"]).agg(
            revenue=("revenue", "sum"),
            units=("quantity", "sum"),
            orders=("customer_order_id", "nunique"),
        ).reset_index().sort_values("revenue", ascending=False).head(15)
        top_sku["product_short"] = top_sku["product_name"].astype(str).str[:40]

        fig = px.bar(
            top_sku.sort_values("revenue"),
            x="revenue", y="sku", orientation="h",
            color="revenue", color_continuous_scale="Greens",
            hover_data={"product_short": True, "units": True, "orders": True},
            text="revenue",
        )
        fig.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
        fig.update_layout(
            height=500, template=theme["template"],
            paper_bgcolor=theme["paper_bg"], plot_bgcolor=theme["plot_bg"],
            showlegend=False, coloraxis_showscale=False,
            margin=dict(l=0, r=40, t=20, b=0), yaxis_title="",
        )
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown("#### 📍 Ship Node Distribution")
        # WFS vs Seller-fulfilled
        if "ship_node_type" in df.columns:
            node_dist = df.groupby("ship_node_type").agg(
                orders=("customer_order_id", "nunique"),
                revenue=("revenue", "sum"),
            ).reset_index().sort_values("revenue", ascending=False)

            if not node_dist.empty:
                colors_map = {
                    "WFSFulfilled": "#7c9fff",
                    "SellerFulfilled": "#fab005",
                }
                fig = px.pie(
                    node_dist, values="revenue", names="ship_node_type",
                    color="ship_node_type", color_discrete_map=colors_map,
                    hole=0.5,
                    title="Revenue Split by Fulfillment",
                )
                fig.update_traces(textposition='inside', textinfo='percent+label')
                fig.update_layout(
                    height=300, template=theme["template"],
                    paper_bgcolor=theme["paper_bg"],
                    margin=dict(l=0, r=0, t=40, b=0),
                )
                st.plotly_chart(fig, use_container_width=True)

                st.dataframe(
                    node_dist.rename(columns={
                        "ship_node_type": "Type",
                        "orders": "Orders",
                        "revenue": "Revenue",
                    }),
                    use_container_width=True, hide_index=True,
                    column_config={"Revenue": st.column_config.NumberColumn(format="$%.0f")},
                )

    st.divider()

    # ============ 5. STATUS & FULFILLMENT ============
    st.markdown("#### 📊 Status & Ship Method Breakdown")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("**Line Status**")
        status_dist = df["line_status"].fillna("UNKNOWN").value_counts().reset_index()
        status_dist.columns = ["status", "count"]
        colors_map = {
            "Delivered": "#51cf66", "Shipped": "#7c9fff",
            "Acknowledged": "#fab005", "Created": "#adb5bd",
            "Cancelled": "#e03131", "UNKNOWN": "#868e96",
        }
        fig = px.pie(
            status_dist.head(8), values="count", names="status",
            color="status", color_discrete_map=colors_map, hole=0.4,
        )
        fig.update_layout(
            height=320, template=theme["template"],
            paper_bgcolor=theme["paper_bg"],
            margin=dict(l=0, r=0, t=20, b=0),
        )
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown("**Ship Method**")
        if "ship_method" in df.columns:
            sm_dist = df["ship_method"].fillna("UNKNOWN").value_counts().reset_index()
            sm_dist.columns = ["method", "count"]
            fig = px.pie(
                sm_dist.head(8), values="count", names="method", hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig.update_layout(
                height=320, template=theme["template"],
                paper_bgcolor=theme["paper_bg"],
                margin=dict(l=0, r=0, t=20, b=0),
            )
            st.plotly_chart(fig, use_container_width=True)

    with c3:
        st.markdown("**Order Type**")
        if "order_type" in df.columns:
            ot_dist = df["order_type"].fillna("UNKNOWN").value_counts().reset_index()
            ot_dist.columns = ["type", "count"]
            fig = px.pie(
                ot_dist.head(8), values="count", names="type", hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Pastel,
            )
            fig.update_layout(
                height=320, template=theme["template"],
                paper_bgcolor=theme["paper_bg"],
                margin=dict(l=0, r=0, t=20, b=0),
            )
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ============ 6. ANOMALIES & INSIGHTS ============
    st.markdown("#### 🚨 Anomalies & Insights")

    insights = []

    # 1. Best day in last 30
    if not last30.empty:
        best_day = last30.groupby("date")["revenue"].sum().idxmax()
        best_day_rev = last30.groupby("date")["revenue"].sum().max()
        avg_day_rev = last30.groupby("date")["revenue"].sum().mean()
        if best_day_rev > avg_day_rev * 2:
            insights.append({
                "type": "info",
                "title": "📈 Outlier Day Detected",
                "text": f"{best_day} мав revenue <b>${best_day_rev:,.0f}</b> (×{best_day_rev/avg_day_rev:.1f} від середнього ${avg_day_rev:,.0f})",
            })

    # 2. Top SKU concentration
    if not last30.empty:
        sku_rev = last30.groupby("sku")["revenue"].sum().sort_values(ascending=False)
        top5_share = sku_rev.head(5).sum() / sku_rev.sum() * 100 if sku_rev.sum() > 0 else 0
        if top5_share > 40:
            insights.append({
                "type": "warn",
                "title": "⚠️ High SKU Concentration",
                "text": f"Топ-5 SKU генерують <b>{top5_share:.0f}%</b> виручки. Ризик якщо хтось з них unpublish/OOS.",
            })

    # 3. Cancellation spike
    if not last30.empty and not prev30.empty:
        c30 = (last30["line_status"].str.lower() == "cancelled").sum()
        cp30 = (prev30["line_status"].str.lower() == "cancelled").sum()
        if c30 > cp30 * 1.5 and c30 > 5:
            insights.append({
                "type": "crit",
                "title": "🔴 Cancellation Spike",
                "text": f"Cancellations зросли з {cp30} до <b>{c30}</b> (×{c30/max(cp30,1):.1f}). Перевір stock та проблемні SKU.",
            })

    # 4. WFS vs Seller share
    if "ship_node_type" in last30.columns and not last30.empty:
        wfs_share = (last30["ship_node_type"] == "WFSFulfilled").sum() / len(last30) * 100
        if wfs_share > 80:
            insights.append({
                "type": "info",
                "title": "🏭 WFS Dominance",
                "text": f"<b>{wfs_share:.0f}%</b> замовлень через WFS. Логістично оптимально, але залежність від Walmart fees.",
            })
        elif wfs_share < 30:
            insights.append({
                "type": "warn",
                "title": "📦 Low WFS Usage",
                "text": f"Тільки <b>{wfs_share:.0f}%</b> через WFS. Розгляньте міграцію на WFS для швидкої доставки.",
            })

    # 5. Growth velocity
    if abs(growth) > 30:
        if growth > 0:
            insights.append({
                "type": "info",
                "title": "🚀 Strong Growth",
                "text": f"Revenue ↑ <b>+{growth:.0f}%</b> MoM. Швидкий зріст — перевір чи inventory витримує темп.",
            })
        else:
            insights.append({
                "type": "crit",
                "title": "📉 Revenue Decline",
                "text": f"Revenue ↓ <b>{growth:.0f}%</b> MoM. Терміново розібратись — конкуренти, BB, seasonal?",
            })

    if insights:
        for ins in insights:
            cls = {"crit": "severity-crit", "warn": "severity-warn", "info": "severity-info"}[ins["type"]]
            st.markdown(f"""
            <div class="{cls}">
                <strong>{ins['title']}</strong><br>
                <span style="opacity:0.9;">{ins['text']}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.success("✅ No anomalies detected. Business operates within normal ranges.")

    st.divider()

    # ============ 7. RECENT ORDERS DETAIL ============
    st.markdown("#### 📋 Recent Orders (last 30)")

    recent = df.sort_values("order_dt", ascending=False).head(30)[[
        "customer_order_id", "order_dt", "sku", "product_name",
        "quantity", "line_total", "line_status", "ship_node_type", "carrier"
    ]].copy()
    recent["order_dt"] = recent["order_dt"].dt.strftime("%Y-%m-%d %H:%M")
    recent["product_name"] = recent["product_name"].astype(str).str[:45]
    recent = recent.rename(columns={
        "customer_order_id": T["orders_order_id"],
        "order_dt": T["orders_date_col"],
        "sku": T["sku"],
        "product_name": T["product"],
        "quantity": T["returns_qty"],
        "line_total": T["orders_amount"],
        "line_status": T["orders_status_col"],
        "ship_node_type": "Fulfillment",
        "carrier": "Carrier",
    })
    st.dataframe(
        recent, use_container_width=True, hide_index=True, height=420,
        column_config={
            T["orders_amount"]: st.column_config.NumberColumn(format="$%.2f"),
        }
    )


# ============================================================
# 🚛 WFS SHIPMENTS SECTION 🆕
# ============================================================

def render_wfs_shipments(data, T, theme):
    """💎 SMART WFS — повноцінний BI для inbound shipments.
    Структура:
      1. Executive Summary
      2. KPI Row
      3. Active Shipments details
      4. ETA Timeline
      5. SKU Pipeline depth
      6. FC + Carrier breakdown
      7. Insights
    """
    wfs = data.get("wfs_shipments", pd.DataFrame())
    if wfs.empty:
        st.warning("⚠️ walmart.wfs_shipments is empty")
        return

    st.markdown(f"### {T['wfs_section']}")
    st.caption(T["wfs_subtitle"])

    # ============ Підготовка ============
    wfs["expected_delivery_date"] = pd.to_datetime(wfs["expected_delivery_date"], errors='coerce', utc=True).dt.tz_localize(None)
    wfs["po_create_date"] = pd.to_datetime(wfs["po_create_date"], errors='coerce', utc=True).dt.tz_localize(None)
    wfs["expected_units"] = pd.to_numeric(wfs["expected_units"], errors='coerce').fillna(0)
    wfs["received_units"] = pd.to_numeric(wfs["received_units"], errors='coerce').fillna(0)

    awaiting_df = wfs[wfs["po_status"] == "AWAITING_DELIVERY"]
    closed_df = wfs[wfs["po_status"] == "CLOSED"]

    n_ships = wfs["shipment_id"].nunique()
    n_awaiting = awaiting_df["shipment_id"].nunique()
    n_closed = closed_df["shipment_id"].nunique()
    n_cancelled = wfs[wfs["po_status"] == "CANCELLED"]["shipment_id"].nunique()

    pending_units = int((awaiting_df["expected_units"] - awaiting_df["received_units"]).sum())
    total_pending_skus = awaiting_df["sku"].nunique()

    # Naerest ETA
    next_eta = awaiting_df[awaiting_df["expected_delivery_date"].notna()]["expected_delivery_date"].min()
    days_to_next = (next_eta.date() - datetime.now().date()).days if pd.notna(next_eta) else None

    # ============ 1. EXECUTIVE SUMMARY ============
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, rgba(124,159,255,0.10), rgba(81,207,102,0.08));
                border-left: 4px solid #7c9fff; padding: 14px 18px; border-radius: 8px;
                margin: 8px 0 16px 0;">
        <strong style="font-size:1.05rem;">🚛 Logistics Pipeline</strong><br>
        <span style="opacity:0.9;">
        <b>{n_awaiting}</b> активних поставок з <b>{pending_units:,}</b> units по <b>{total_pending_skus}</b> SKU в дорозі.
        {f"Найближча ETA: <b>{next_eta.strftime('%Y-%m-%d')}</b> (через {days_to_next} днів)." if days_to_next is not None else ""}<br>
        Завершено: <b>{n_closed}</b> · Скасовано: <b>{n_cancelled}</b> з <b>{n_ships}</b> загалом.
        </span>
    </div>
    """, unsafe_allow_html=True)

    # ============ 2. KPI ============
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric(T["wfs_total_ships"], f"{n_ships}")
    c2.metric(T["wfs_in_transit"], f"{n_awaiting}")
    c3.metric(T["wfs_pending_units"], f"{pending_units:,}")
    c4.metric(T["wfs_closed"], f"{n_closed}")
    c5.metric(T["wfs_cancelled"], f"{n_cancelled}")

    st.divider()

    # ============ 3. ACTIVE SHIPMENTS DETAIL ============
    st.markdown(f"#### 🚛 {T['wfs_active_title']}")

    if not awaiting_df.empty:
        agg = awaiting_df.groupby("shipment_id").agg(
            fc=("fc_name", "first"),
            carrier=("carrier_name", "first"),
            tracking=("tracking_no", "first"),
            created=("po_create_date", "min"),
            eta=("expected_delivery_date", "max"),
            skus=("sku", "nunique"),
            expected=("expected_units", "sum"),
            received=("received_units", "sum"),
        ).reset_index()
        agg["pending"] = (agg["expected"] - agg["received"]).astype(int)
        agg["days_to_eta"] = ((agg["eta"] - pd.Timestamp(datetime.now().date())).dt.days).astype("Int64")
        agg["eta"] = pd.to_datetime(agg["eta"]).dt.strftime("%Y-%m-%d")
        agg["created"] = pd.to_datetime(agg["created"]).dt.strftime("%Y-%m-%d")

        # Sort by ETA
        agg = agg.sort_values("eta", na_position="last")

        agg = agg.rename(columns={
            "shipment_id": "Shipment",
            "fc": T["wfs_fc"],
            "carrier": T["wfs_carrier"],
            "tracking": "Tracking",
            "created": "Created",
            "eta": T["wfs_eta"],
            "days_to_eta": "Days",
            "skus": T["wfs_skus"],
            "expected": "Expected",
            "received": T["wfs_received"],
            "pending": T["wfs_pending"],
        })
        st.dataframe(
            agg, use_container_width=True, hide_index=True, height=300,
            column_config={
                "Expected": st.column_config.NumberColumn(format="%d"),
                T["wfs_received"]: st.column_config.NumberColumn(format="%d"),
                T["wfs_pending"]: st.column_config.NumberColumn(format="%d"),
                "Days": st.column_config.NumberColumn(format="%d days"),
            },
        )
    else:
        st.info("No active shipments")

    # ============ 4. ETA TIMELINE ============
    if not awaiting_df.empty:
        st.markdown("#### 📅 Upcoming Deliveries Timeline")

        eta_data = awaiting_df.groupby("shipment_id").agg(
            eta=("expected_delivery_date", "max"),
            fc=("fc_name", "first"),
            units=("expected_units", lambda x: x.sum() - awaiting_df.loc[x.index, "received_units"].sum()),
            skus=("sku", "nunique"),
        ).reset_index()
        eta_data = eta_data[eta_data["eta"].notna()].sort_values("eta")

        if not eta_data.empty:
            fig = px.scatter(
                eta_data,
                x="eta", y="units", size="units", color="fc",
                hover_data={"shipment_id": True, "skus": True},
                size_max=60,
            )
            fig.update_layout(
                height=350, template=theme["template"],
                paper_bgcolor=theme["paper_bg"], plot_bgcolor=theme["plot_bg"],
                margin=dict(l=0, r=0, t=20, b=0),
                xaxis_title="Expected Delivery", yaxis_title="Units Pending",
            )
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ============ 5. SKU PIPELINE ============
    if not awaiting_df.empty:
        st.markdown(f"#### 🎯 {T['wfs_top_skus_pending']}")
        sku_pend = awaiting_df.copy()
        sku_pend["pending"] = sku_pend["expected_units"] - sku_pend["received_units"]
        sku_pend_agg = sku_pend.groupby(["sku", "description"]).agg(
            pending=("pending", "sum"),
            ships=("shipment_id", "nunique"),
        ).reset_index().sort_values("pending", ascending=False).head(20)
        sku_pend_agg["description"] = sku_pend_agg["description"].astype(str).str[:50]

        fig = px.bar(
            sku_pend_agg.sort_values("pending"),
            x="pending", y="sku", orientation="h",
            color="pending", color_continuous_scale="Blues",
            hover_data={"description": True, "ships": True},
            text="pending",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(
            height=600, template=theme["template"],
            paper_bgcolor=theme["paper_bg"], plot_bgcolor=theme["plot_bg"],
            showlegend=False, coloraxis_showscale=False,
            margin=dict(l=0, r=40, t=20, b=0), yaxis_title="",
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ============ 6. FC + CARRIER ============
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"#### 🏭 {T['wfs_by_fc']}")
        fc_dist = wfs.groupby("fc_name").agg(
            ships=("shipment_id", "nunique"),
            units=("expected_units", "sum"),
        ).reset_index().sort_values("units", ascending=False)
        fc_dist = fc_dist[fc_dist["fc_name"].notna() & (fc_dist["fc_name"] != "")]
        if not fc_dist.empty:
            fig = px.pie(
                fc_dist, values="units", names="fc_name", hole=0.5,
                title="Units by FC",
            )
            fig.update_traces(textposition="inside", textinfo="percent+label")
            fig.update_layout(
                height=350, template=theme["template"], paper_bgcolor=theme["paper_bg"],
                margin=dict(l=0, r=0, t=40, b=0),
            )
            st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown(f"#### 🚚 {T['wfs_by_carrier']}")
        carr_dist = wfs[wfs["carrier_name"].notna() & (wfs["carrier_name"] != "")].groupby("carrier_name").agg(
            ships=("shipment_id", "nunique"),
        ).reset_index().sort_values("ships", ascending=False)
        if not carr_dist.empty:
            fig = px.pie(
                carr_dist, values="ships", names="carrier_name", hole=0.5,
                title="Shipments by Carrier",
            )
            fig.update_traces(textposition="inside", textinfo="percent+label")
            fig.update_layout(
                height=350, template=theme["template"], paper_bgcolor=theme["paper_bg"],
                margin=dict(l=0, r=0, t=40, b=0),
            )
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ============ 7. INSIGHTS ============
    st.markdown("#### 🚨 Logistics Insights")

    insights = []

    # Large incoming shipment alert
    if pending_units > 10000:
        insights.append({
            "type": "info",
            "title": "📦 Major Restock Incoming",
            "text": f"<b>{pending_units:,}</b> units в дорозі по <b>{total_pending_skus}</b> SKU. "
                    f"Підготуй PPC бюджет та monitoring після прибуття.",
        })

    # Imminent deliveries
    if days_to_next is not None and days_to_next <= 7:
        nearest_ship = awaiting_df[awaiting_df["expected_delivery_date"] == next_eta]
        nearest_units = int((nearest_ship["expected_units"] - nearest_ship["received_units"]).sum())
        insights.append({
            "type": "warn",
            "title": "⏰ Imminent Delivery",
            "text": f"Через <b>{days_to_next} днів</b> прибуде <b>{nearest_units:,}</b> units. "
                    f"Готуй receiving capacity на складі.",
        })

    # Cancellation rate
    if n_ships > 5:
        cancel_rate = (n_cancelled / n_ships) * 100
        if cancel_rate > 10:
            insights.append({
                "type": "warn",
                "title": "🚫 High Cancellation Rate",
                "text": f"<b>{cancel_rate:.0f}%</b> shipments скасовано. Перевір процес inbound планування.",
            })

    # FC concentration
    if not awaiting_df.empty:
        fc_pending = awaiting_df.groupby("fc_name")["sku"].nunique()
        if len(fc_pending) > 0:
            top_fc = fc_pending.idxmax()
            top_fc_pct = (fc_pending.max() / fc_pending.sum()) * 100
            if top_fc_pct > 70:
                insights.append({
                    "type": "info",
                    "title": "🏭 FC Concentration",
                    "text": f"<b>{top_fc_pct:.0f}%</b> SKU йдуть на <b>{top_fc}</b>. "
                            f"Розглянь географічну диверсифікацію складів.",
                })

    if insights:
        for ins in insights:
            cls = {"crit": "severity-crit", "warn": "severity-warn", "info": "severity-info"}[ins["type"]]
            st.markdown(f"""
            <div class="{cls}">
                <strong>{ins['title']}</strong><br>
                <span style="opacity:0.9;">{ins['text']}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.success("✅ Logistics pipeline operating smoothly.")


# ============================================================
# 💰 SETTLEMENT SECTION 🆕
# ============================================================

def render_settlement(data, T, theme):
    """💎 SMART SETTLEMENT — повноцінний фінансовий BI.
    Структура:
      1. Executive Summary (2-річний overview)
      2. KPI Row
      3. Monthly P&L timeline
      4. Money Flow waterfall (Sales→Refunds→Fees→Net)
      5. Top SKUs Revenue
      6. Anomalies & Insights
      7. Recent Payouts
    """
    settle = data.get("settlement", pd.DataFrame())
    if settle.empty:
        st.warning("⚠️ walmart.settlement is empty (run walmart_settlement_loader)")
        return

    st.markdown(f"### {T['settlement_section']}")
    st.caption(T["settlement_subtitle"])

    # ============ Підготовка ============
    settle["report_date"] = pd.to_datetime(settle["report_date"], errors='coerce', utc=True).dt.tz_localize(None)
    settle["amount"] = pd.to_numeric(settle["amount"], errors='coerce').fillna(0)
    settle["total_payable"] = pd.to_numeric(settle["total_payable"], errors='coerce').fillna(0)

    payments = settle[settle["transaction_type"] == "PaymentSummary"]
    sales_df = settle[settle["transaction_type"] == "Sale"]
    refunds_df = settle[settle["transaction_type"] == "Refund"]
    adj_df = settle[settle["transaction_type"] == "Adjustment"]
    fees_df = settle[settle["transaction_type"].isin(["Service Fee", "Campaigns"])]

    net_paid = payments["total_payable"].sum()
    total_sales = sales_df["amount"].sum()
    total_refunds = refunds_df["amount"].sum()
    total_adj = adj_df["amount"].sum()
    total_fees = fees_df["amount"].sum()
    margin_pct = (net_paid / max(total_sales, 1)) * 100 if total_sales > 0 else 0

    # ============ 1. EXECUTIVE SUMMARY ============
    n_periods = settle["report_date"].nunique()
    date_min = settle["report_date"].min()
    date_max = settle["report_date"].max()
    years_span = (date_max - date_min).days / 365 if pd.notna(date_min) else 0

    # Last month
    last_month_payments = payments[payments["report_date"] >= pd.Timestamp(datetime.now().date() - timedelta(days=30))]
    last_month_paid = last_month_payments["total_payable"].sum()

    st.markdown(f"""
    <div style="background: linear-gradient(135deg, rgba(81,207,102,0.10), rgba(124,159,255,0.08));
                border-left: 4px solid #51cf66; padding: 14px 18px; border-radius: 8px;
                margin: 8px 0 16px 0;">
        <strong style="font-size:1.05rem;">💰 Financial Summary ({years_span:.1f} years)</strong><br>
        <span style="opacity:0.9;">
        За <b>{n_periods}</b> settlement періодів виплачено <b>${net_paid:,.0f}</b>
        (margin: <b>{margin_pct:.0f}%</b> з gross sales <b>${total_sales:,.0f}</b>).<br>
        Refunds: <b>${abs(total_refunds):,.0f}</b> &nbsp;·&nbsp;
        Adjustments: <b>${abs(total_adj):,.0f}</b> &nbsp;·&nbsp;
        Fees+Ads: <b>${abs(total_fees):,.0f}</b><br>
        Останні 30 днів виплачено: <b>${last_month_paid:,.0f}</b>
        </span>
    </div>
    """, unsafe_allow_html=True)

    # ============ 2. KPI ============
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("📅 Periods", f"{n_periods}")
    c2.metric("💰 Net Paid", f"${net_paid:,.0f}")
    c3.metric("📈 Gross Sales", f"${total_sales:,.0f}")
    c4.metric("📉 Total Costs", f"${abs(total_refunds + total_adj + total_fees):,.0f}")
    c5.metric("🎯 Margin", f"{margin_pct:.0f}%")

    st.divider()

    # ============ 3. MONTHLY P&L TIMELINE ============
    st.markdown("#### 📈 Monthly P&L Timeline")

    settle["month"] = settle["report_date"].dt.to_period("M").dt.to_timestamp()

    monthly = settle.groupby(["month", "transaction_type"])["amount"].sum().reset_index()
    monthly_pivot = monthly.pivot_table(
        index="month", columns="transaction_type", values="amount", aggfunc="sum"
    ).fillna(0).reset_index()

    # Сума net по місяцях з payments
    payments["month"] = payments["report_date"].dt.to_period("M").dt.to_timestamp()
    net_monthly = payments.groupby("month")["total_payable"].sum().reset_index()

    fig = go.Figure()

    if "Sale" in monthly_pivot.columns:
        fig.add_trace(go.Bar(
            x=monthly_pivot["month"], y=monthly_pivot["Sale"],
            name="💵 Sales", marker_color="#51cf66",
        ))
    if "Refund" in monthly_pivot.columns:
        fig.add_trace(go.Bar(
            x=monthly_pivot["month"], y=monthly_pivot["Refund"],
            name="🔄 Refunds", marker_color="#e03131",
        ))
    if "Service Fee" in monthly_pivot.columns:
        fig.add_trace(go.Bar(
            x=monthly_pivot["month"], y=monthly_pivot["Service Fee"],
            name="💸 Fees", marker_color="#fab005",
        ))
    if "Campaigns" in monthly_pivot.columns:
        fig.add_trace(go.Bar(
            x=monthly_pivot["month"], y=monthly_pivot["Campaigns"],
            name="📣 Ads", marker_color="#9775fa",
        ))
    if "Adjustment" in monthly_pivot.columns:
        fig.add_trace(go.Bar(
            x=monthly_pivot["month"], y=monthly_pivot["Adjustment"],
            name="⚖️ Adjustments", marker_color="#868e96",
        ))

    # Net line поверх
    if not net_monthly.empty:
        fig.add_trace(go.Scatter(
            x=net_monthly["month"], y=net_monthly["total_payable"],
            name="💰 Net Paid", mode="lines+markers",
            line=dict(color="#7c9fff", width=4),
            marker=dict(size=10, symbol="diamond"),
        ))

    fig.update_layout(
        height=450, template=theme["template"],
        paper_bgcolor=theme["paper_bg"], plot_bgcolor=theme["plot_bg"],
        barmode="relative",
        margin=dict(l=0, r=0, t=20, b=0),
        hovermode="x unified",
        legend=dict(orientation="h", y=1.12),
        yaxis_title="USD",
    )
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ============ 4. MONEY FLOW WATERFALL ============
    st.markdown("#### 💱 Money Flow — How $1 of Sales Becomes Payout")

    flow_data = [
        ("💵 Gross Sales", total_sales, "#51cf66"),
        ("🔄 - Refunds", -abs(total_refunds), "#e03131"),
        ("⚖️ - Adjustments", -abs(total_adj), "#868e96"),
        ("💸 - Service Fees", -abs(fees_df[fees_df["transaction_type"] == "Service Fee"]["amount"].sum()), "#fab005"),
        ("📣 - Ads (Campaigns)", -abs(fees_df[fees_df["transaction_type"] == "Campaigns"]["amount"].sum()), "#9775fa"),
        ("💰 Net to PAYONEER", net_paid, "#7c9fff"),
    ]

    fig = go.Figure(go.Waterfall(
        name="Flow",
        orientation="v",
        measure=["absolute", "relative", "relative", "relative", "relative", "total"],
        x=[d[0] for d in flow_data],
        y=[d[1] for d in flow_data],
        text=[f"${abs(d[1]):,.0f}" for d in flow_data],
        textposition="outside",
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        increasing={"marker": {"color": "#51cf66"}},
        decreasing={"marker": {"color": "#e03131"}},
        totals={"marker": {"color": "#7c9fff"}},
    ))
    fig.update_layout(
        height=450, template=theme["template"],
        paper_bgcolor=theme["paper_bg"], plot_bgcolor=theme["plot_bg"],
        margin=dict(l=0, r=0, t=20, b=0),
        showlegend=False,
        yaxis_title="USD",
    )
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ============ 5. TOP SKUs by Revenue ============
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("#### 🏆 Top 15 SKUs (2-year lifetime)")
        sku_rev = sales_df[(sales_df["partner_item_id"].notna()) & (sales_df["partner_item_id"] != "")]
        if not sku_rev.empty:
            top_sku = sku_rev.groupby(["partner_item_id", "partner_item_name"]).agg(
                rev=("amount", "sum"),
                qty=("ship_qty", "sum"),
                cnt=("amount", "count"),
            ).reset_index().sort_values("rev", ascending=False).head(15)
            top_sku["partner_item_name"] = top_sku["partner_item_name"].astype(str).str[:35]

            fig = px.bar(
                top_sku.sort_values("rev"),
                x="rev", y="partner_item_id", orientation="h",
                color="rev", color_continuous_scale="Greens",
                hover_data={"partner_item_name": True, "cnt": True},
                text="rev",
            )
            fig.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
            fig.update_layout(
                height=500, template=theme["template"],
                paper_bgcolor=theme["paper_bg"], plot_bgcolor=theme["plot_bg"],
                showlegend=False, coloraxis_showscale=False,
                margin=dict(l=0, r=40, t=20, b=0),
                yaxis_title="",
            )
            st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown("#### 🥧 Transaction Types Breakdown")
        by_type = settle.groupby("transaction_type").agg(
            cnt=("amount", "count"),
            amt=("amount", "sum"),
        ).reset_index()
        by_type["abs_amt"] = by_type["amt"].abs()
        by_type = by_type.sort_values("abs_amt", ascending=False)

        fig = px.pie(
            by_type, values="abs_amt", names="transaction_type",
            hole=0.5,
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(
            height=500, template=theme["template"],
            paper_bgcolor=theme["paper_bg"],
            margin=dict(l=0, r=0, t=20, b=0),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ============ 6. ANOMALIES & INSIGHTS ============
    st.markdown("#### 🚨 Financial Insights")

    insights = []

    # Margin check
    if margin_pct < 30:
        insights.append({
            "type": "crit",
            "title": "📉 Low Margin",
            "text": f"Margin <b>{margin_pct:.0f}%</b> нижче 30%. Перевір fees, ads, refunds.",
        })
    elif margin_pct > 50:
        insights.append({
            "type": "info",
            "title": "🎯 Healthy Margin",
            "text": f"Margin <b>{margin_pct:.0f}%</b> вище 50% — це топ для marketplace.",
        })

    # Refund rate
    refund_rate = (abs(total_refunds) / max(total_sales, 1)) * 100
    if refund_rate > 7:
        insights.append({
            "type": "warn",
            "title": "🔄 High Refund Rate",
            "text": f"Refunds = <b>{refund_rate:.1f}%</b> sales (норма 3-5%). Перевір returns dashboard.",
        })

    # Best month
    if not net_monthly.empty and len(net_monthly) > 1:
        best_month_idx = net_monthly["total_payable"].idxmax()
        best_month_val = net_monthly.loc[best_month_idx, "total_payable"]
        best_month_dt = net_monthly.loc[best_month_idx, "month"]
        avg_month = net_monthly["total_payable"].mean()
        if best_month_val > avg_month * 2:
            insights.append({
                "type": "info",
                "title": "🏆 Outlier Month",
                "text": f"<b>{best_month_dt.strftime('%B %Y')}</b> = ${best_month_val:,.0f} (×{best_month_val/avg_month:.1f} від avg ${avg_month:,.0f})",
            })

    # Ads spend
    ads_total = abs(fees_df[fees_df["transaction_type"] == "Campaigns"]["amount"].sum())
    if ads_total > 0:
        ads_pct = (ads_total / max(total_sales, 1)) * 100
        if ads_pct > 10:
            insights.append({
                "type": "warn",
                "title": "📣 High Ad Spend",
                "text": f"Ads <b>{ads_pct:.1f}%</b> від sales (${ads_total:,.0f}). Перевір ROAS на топ SKU.",
            })

    # Growth trend
    if not net_monthly.empty and len(net_monthly) >= 6:
        net_monthly_sorted = net_monthly.sort_values("month")
        last3 = net_monthly_sorted.tail(3)["total_payable"].sum()
        prev3 = net_monthly_sorted.tail(6).head(3)["total_payable"].sum()
        if prev3 > 0:
            growth_q = ((last3 - prev3) / prev3) * 100
            if growth_q > 50:
                insights.append({
                    "type": "info",
                    "title": "🚀 Accelerating Growth",
                    "text": f"Останні 3 місяці vs попередні 3 = <b>+{growth_q:.0f}%</b>. Масштабуйся!",
                })
            elif growth_q < -20:
                insights.append({
                    "type": "crit",
                    "title": "📉 Declining Trend",
                    "text": f"Останні 3 місяці vs попередні 3 = <b>{growth_q:.0f}%</b>. Терміново розібратись.",
                })

    if insights:
        for ins in insights:
            cls = {"crit": "severity-crit", "warn": "severity-warn", "info": "severity-info"}[ins["type"]]
            st.markdown(f"""
            <div class="{cls}">
                <strong>{ins['title']}</strong><br>
                <span style="opacity:0.9;">{ins['text']}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.success("✅ Financial metrics look healthy.")

    st.divider()

    # ============ 7. RECENT PAYOUTS ============
    st.markdown("#### 💰 Recent PAYONEER Deposits")
    if not payments.empty:
        recent_pay = payments[["report_date", "total_payable", "transaction_description"]].copy()
        recent_pay = recent_pay.sort_values("report_date", ascending=False).head(15)
        recent_pay["report_date"] = recent_pay["report_date"].dt.strftime("%Y-%m-%d")
        recent_pay = recent_pay.rename(columns={
            "report_date": T["period"],
            "total_payable": T["deposit"],
            "transaction_description": T["channel"],
        })
        st.dataframe(
            recent_pay, use_container_width=True, hide_index=True, height=400,
            column_config={T["deposit"]: st.column_config.NumberColumn(format="$%.2f")},
        )


# ============================================================
# 🔄 CUSTOMER RETURNS SECTION 🆕
# ============================================================

def render_returns(data, T, theme):
    """💎 SMART RETURNS — повноцінний BI для повернень.
    Структура:
      1. Executive Summary
      2. KPI Row
      3. Returns Timeline (daily)
      4. Reasons heatmap + Status pie
      5. Killer SKUs table
      6. Anomalies & Insights
      7. Customer detail
    """
    ret = data.get("returns", pd.DataFrame())
    if ret.empty:
        st.warning("⚠️ walmart.returns is empty (run walmart_returns_loader)")
        return

    st.markdown(f"### {T['returns_section']}")
    st.caption(T["returns_subtitle"])

    # ============ Підготовка ============
    ret["return_order_date"] = pd.to_datetime(ret["return_order_date"], errors='coerce', utc=True).dt.tz_localize(None)
    ret["unit_price"] = pd.to_numeric(ret["unit_price"], errors='coerce').fillna(0)
    ret["quantity"] = pd.to_numeric(ret["quantity"], errors='coerce').fillna(1)
    ret["total_refund_amount"] = pd.to_numeric(ret["total_refund_amount"], errors='coerce').fillna(0)
    ret["lost"] = ret["unit_price"] * ret["quantity"]
    ret = ret[ret["return_order_date"].notna()].copy()

    listing_issues = ["INCORRECT_ITEM", "DIFFICULT_TO_SETUP_NOT_COMPATIBLE",
                      "NOT_AS_DESCRIBED_PICTURED", "DEFECTIVE"]

    # ============ 1. EXECUTIVE SUMMARY ============
    n_returns = ret["return_order_id"].nunique()
    n_skus = ret["sku"].nunique()
    total_refund = ret["total_refund_amount"].sum()
    listing_cnt = ret[ret["return_reason"].isin(listing_issues)].shape[0]
    listing_pct = (100 * listing_cnt / max(len(ret), 1))
    listing_loss = ret[ret["return_reason"].isin(listing_issues)]["lost"].sum()

    # Seller vs Walmart split
    seller_paid = ret[ret["refund_covered_by"] == "Seller"]["total_refund_amount"].sum()

    st.markdown(f"""
    <div style="background: linear-gradient(135deg, rgba(224,49,49,0.10), rgba(250,176,5,0.08));
                border-left: 4px solid #e03131; padding: 14px 18px; border-radius: 8px;
                margin: 8px 0 16px 0;">
        <strong style="font-size:1.05rem;">🔄 Returns Analysis</strong><br>
        <span style="opacity:0.9;">
        <b>{n_returns}</b> returns на <b>{n_skus}</b> SKU. Виплачено: <b>${total_refund:,.2f}</b>
        (Seller's частина: <b>${seller_paid:,.2f}</b>).<br>
        <b>{listing_pct:.0f}%</b> returns ({listing_cnt} cases) через <b>проблеми з лістингом</b>
        — можна fix і повернути <b>${listing_loss:,.0f}</b>.
        </span>
    </div>
    """, unsafe_allow_html=True)

    # ============ 2. KPI ============
    today = datetime.now().date()
    last30 = ret[ret["return_order_date"] >= pd.Timestamp(today - timedelta(days=30))]
    prev30 = ret[(ret["return_order_date"] >= pd.Timestamp(today - timedelta(days=60))) &
                 (ret["return_order_date"] < pd.Timestamp(today - timedelta(days=30)))]

    growth = ((len(last30) - len(prev30)) / max(len(prev30), 1)) * 100 if len(prev30) > 0 else 0

    completed = ret[ret["current_refund_status"] == "REFUND_COMPLETED"].shape[0]
    completed_pct = (completed / max(len(ret), 1)) * 100

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📦 Total Returns", f"{n_returns}", f"{growth:+.0f}% vs prev30")
    c2.metric("🏷️ Unique SKUs", f"{n_skus}")
    c3.metric("💸 Total Refunded", f"${total_refund:,.0f}")
    c4.metric("✅ Completed", f"{completed_pct:.0f}%")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("⚠️ Listing Issues", f"{listing_pct:.0f}%")
    c2.metric("💡 Recoverable $", f"${listing_loss:,.0f}")
    c3.metric("👤 Seller Pays", f"${seller_paid:,.0f}")
    c4.metric("🏛️ Walmart Pays", f"${total_refund - seller_paid:,.0f}")

    # Special callout if listing issues high
    if listing_pct > 30:
        st.markdown(f"""
        <div class="opportunity-box">
            <strong style="font-size:1.05rem;">💡 LISTING FIX OPPORTUNITY — ${listing_loss:,.0f} recoverable</strong><br>
            <span style="opacity:0.9;">
            {listing_cnt} returns ({listing_pct:.0f}%) сталось через INCORRECT_ITEM /
            COMPATIBILITY / NOT_AS_DESCRIBED. Фікс листингів зменшить returns на 30-50%.
            </span><br>
            <span style="opacity:0.7; font-size:0.9rem;">
            → Action: оновити compatibility info, фото, опис для топ-killer SKU
            </span>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # ============ 3. TIMELINE ============
    st.markdown("#### 📈 Returns Timeline (daily)")

    ret["date"] = ret["return_order_date"].dt.date
    daily_ret = ret.groupby("date").agg(
        returns=("return_order_id", "count"),
        refund=("total_refund_amount", "sum"),
    ).reset_index().sort_values("date")
    daily_ret["ma7"] = daily_ret["returns"].rolling(7, min_periods=1).mean()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=daily_ret["date"], y=daily_ret["returns"],
        name="Returns count", marker_color="#e03131", yaxis="y",
    ))
    fig.add_trace(go.Scatter(
        x=daily_ret["date"], y=daily_ret["ma7"],
        name="7-day MA", mode="lines",
        line=dict(color="#fab005", width=3, dash="dot"),
    ))
    fig.add_trace(go.Scatter(
        x=daily_ret["date"], y=daily_ret["refund"],
        name="Refund $", mode="lines+markers",
        line=dict(color="#9775fa", width=2), yaxis="y2",
        marker=dict(size=4),
    ))
    fig.update_layout(
        height=400, template=theme["template"],
        paper_bgcolor=theme["paper_bg"], plot_bgcolor=theme["plot_bg"],
        margin=dict(l=0, r=0, t=20, b=0),
        yaxis=dict(title="Returns"),
        yaxis2=dict(title="Refund $", overlaying="y", side="right", showgrid=False),
        legend=dict(orientation="h", y=1.12),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ============ 4. REASONS + STATUS ============
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("#### 📊 Return Reasons (with $ impact)")
        reasons = ret.groupby("return_reason").agg(
            cnt=("return_order_id", "count"),
            qty=("quantity", "sum"),
            lost=("lost", "sum"),
        ).reset_index().sort_values("cnt", ascending=False)

        fig = px.bar(
            reasons.sort_values("cnt"),
            x="cnt", y="return_reason", orientation="h",
            color="lost", color_continuous_scale="Reds",
            hover_data={"qty": True, "lost": ":$.2f"},
            text="cnt",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(
            height=450, template=theme["template"],
            paper_bgcolor=theme["paper_bg"], plot_bgcolor=theme["plot_bg"],
            showlegend=False, margin=dict(l=0, r=40, t=20, b=0),
            yaxis_title="", coloraxis_colorbar=dict(title="$ Lost"),
        )
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown("#### 🎯 Refund Status")
        statuses = ret["current_refund_status"].fillna("UNKNOWN").value_counts().reset_index()
        statuses.columns = ["status", "count"]
        colors = {
            "REFUND_COMPLETED": "#51cf66", "REFUND_INITIATED": "#fab005",
            "CANCELLED": "#868e96", "NOT_REFUNDED": "#e03131", "UNKNOWN": "#adb5bd",
        }
        fig = px.pie(
            statuses, values="count", names="status",
            color="status", color_discrete_map=colors, hole=0.5,
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(
            height=450, template=theme["template"],
            paper_bgcolor=theme["paper_bg"],
            margin=dict(l=0, r=0, t=20, b=0),
        )
        st.plotly_chart(fig, use_container_width=True)

        # Who pays
        st.markdown("**💰 Refund Coverage:**")
        coverage = ret.groupby("refund_covered_by").agg(
            cnt=("return_order_id", "count"),
            amt=("total_refund_amount", "sum"),
        ).reset_index().sort_values("amt", ascending=False)
        coverage = coverage[coverage["refund_covered_by"].notna() & (coverage["refund_covered_by"] != "")]
        if not coverage.empty:
            coverage.columns = ["Payer", "Returns", "Amount"]
            st.dataframe(
                coverage, use_container_width=True, hide_index=True,
                column_config={"Amount": st.column_config.NumberColumn(format="$%.2f")},
            )

    st.divider()

    # ============ 5. KILLER SKUs ============
    st.markdown("#### 💸 Top 15 Killer SKUs ($ lost)")
    killer = ret[(ret["sku"].notna()) & (ret["sku"] != "")].copy()
    killer_agg = killer.groupby(["sku", "item_name"]).agg(
        returns=("return_order_id", "count"),
        units=("quantity", "sum"),
        lost=("lost", "sum"),
    ).reset_index().sort_values("lost", ascending=False).head(15)
    killer_agg["item_name"] = killer_agg["item_name"].astype(str).str[:45]

    # Reason mix per SKU
    sku_reasons = killer.groupby(["sku", "return_reason"]).size().reset_index(name="n")
    main_reasons = sku_reasons.loc[sku_reasons.groupby("sku")["n"].idxmax()]
    main_reasons = main_reasons[["sku", "return_reason"]].rename(columns={"return_reason": "main_reason"})
    killer_agg = killer_agg.merge(main_reasons, on="sku", how="left")

    killer_agg = killer_agg.rename(columns={
        "sku": T["sku"], "item_name": T["product"],
        "returns": "Returns", "units": "Units", "lost": "$ Lost",
        "main_reason": "Main Reason",
    })
    st.dataframe(
        killer_agg, use_container_width=True, hide_index=True, height=480,
        column_config={"$ Lost": st.column_config.NumberColumn(format="$%.2f")},
    )

    st.divider()

    # ============ 6. INSIGHTS ============
    st.markdown("#### 🚨 Insights & Anomalies")

    insights = []

    # 1. Listing issue analysis
    if listing_pct > 50:
        insights.append({
            "type": "crit",
            "title": "🔴 Listing-driven returns dominate",
            "text": f"<b>{listing_pct:.0f}%</b> returns через проблеми з лістингом. Це <b>${listing_loss:,.0f}</b> "
                    f"втрат, які можна повернути ревью топ-10 листингів.",
        })

    # 2. Specific killer
    if len(killer_agg) > 0:
        top_killer = killer_agg.iloc[0]
        if top_killer["Returns"] >= 5:
            insights.append({
                "type": "warn",
                "title": f"🎯 Worst SKU: {top_killer[T['sku']]}",
                "text": f"<b>{int(top_killer['Returns'])}</b> returns причина: <b>{top_killer.get('Main Reason', 'N/A')}</b>. "
                        f"Втрата ${top_killer['$ Lost']:,.0f}. Подивись listing.",
            })

    # 3. Growth trend
    if growth > 50 and len(last30) > 5:
        insights.append({
            "type": "crit",
            "title": "📈 Returns Spike",
            "text": f"Returns зросли <b>+{growth:.0f}%</b> за останні 30 днів (з {len(prev30)} до {len(last30)}). "
                    f"Перевір нові PPC кампанії та inventory quality.",
        })
    elif growth < -30:
        insights.append({
            "type": "info",
            "title": "📉 Returns Declining",
            "text": f"Returns ↓ <b>{growth:.0f}%</b> — ймовірно last_30 ще не повністю отримав returns "
                    f"(вікно 30 днів на повернення).",
        })

    # 4. Refund completion
    if completed_pct < 50:
        insights.append({
            "type": "warn",
            "title": "⏳ Slow Refund Completion",
            "text": f"Тільки <b>{completed_pct:.0f}%</b> refunds completed. Решта в процесі або blocked.",
        })

    # 5. NO_LONGER_WANTED vs INCORRECT_ITEM ratio
    nlw = ret[ret["return_reason"] == "NO_LONGER_WANTED"].shape[0]
    inc = ret[ret["return_reason"] == "INCORRECT_ITEM"].shape[0]
    if inc > nlw * 0.8:
        insights.append({
            "type": "crit",
            "title": "⚠️ INCORRECT_ITEM Epidemic",
            "text": f"INCORRECT_ITEM ({inc}) майже = NO_LONGER_WANTED ({nlw}). Це не норма — "
                    f"листинги вводять в оману щодо compatibility.",
        })

    # 6. Cancellation rate
    cancelled_pct = (ret[ret["current_refund_status"] == "CANCELLED"].shape[0] / max(len(ret), 1)) * 100
    if cancelled_pct > 15:
        insights.append({
            "type": "info",
            "title": "↩️ High Return Cancellation",
            "text": f"<b>{cancelled_pct:.0f}%</b> returns скасовано клієнтом (передумали повертати).",
        })

    if insights:
        for ins in insights:
            cls = {"crit": "severity-crit", "warn": "severity-warn", "info": "severity-info"}[ins["type"]]
            st.markdown(f"""
            <div class="{cls}">
                <strong>{ins['title']}</strong><br>
                <span style="opacity:0.9;">{ins['text']}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.success("✅ Returns metrics within normal range.")

    st.divider()

    # ============ 7. RECENT RETURNS ============
    st.markdown("#### 📋 Recent 20 Returns")
    recent = ret[["return_order_date", "sku", "item_name", "return_reason",
                  "quantity", "total_refund_amount", "current_refund_status",
                  "refund_covered_by", "carrier_name"]].copy()
    recent = recent.sort_values("return_order_date", ascending=False).head(20)
    recent["return_order_date"] = recent["return_order_date"].dt.strftime("%Y-%m-%d %H:%M")
    recent["item_name"] = recent["item_name"].astype(str).str[:40]
    recent = recent.rename(columns={
        "return_order_date": T["returns_date"], "sku": T["sku"],
        "item_name": T["product"], "return_reason": T["returns_reason"],
        "quantity": T["returns_qty"], "total_refund_amount": T["returns_refund_amt"],
        "current_refund_status": T["returns_status_col"],
        "refund_covered_by": "Paid By", "carrier_name": T["returns_carrier"],
    })
    st.dataframe(
        recent, use_container_width=True, hide_index=True, height=420,
        column_config={T["returns_refund_amt"]: st.column_config.NumberColumn(format="$%.2f")},
    )


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
# 🧠 AI EXECUTIVE SUMMARY (для Overview)
# ============================================================

def ai_executive_summary(data, lang):
    """Готує дані для AI і просить написати executive summary."""
    api_key = st.secrets.get("GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        return None, None

    # Збираємо stats з усіх таблиць
    stats = {}

    # Orders
    orders = data.get("orders", pd.DataFrame())
    if not orders.empty:
        try:
            o = orders.copy()
            o["order_dt"] = pd.to_datetime(o["order_date"], errors='coerce', utc=True).dt.tz_localize(None)
            o["line_total"] = pd.to_numeric(o["line_total"], errors='coerce').fillna(0)
            o["quantity"] = pd.to_numeric(o["quantity"], errors='coerce').fillna(0)
            o = o[o["order_dt"].notna()]
            today = datetime.now().date()
            last30 = o[o["order_dt"] >= pd.Timestamp(today - timedelta(days=30))]
            prev30 = o[(o["order_dt"] >= pd.Timestamp(today - timedelta(days=60))) &
                       (o["order_dt"] < pd.Timestamp(today - timedelta(days=30)))]
            rev30 = last30["line_total"].sum()
            rev_prev30 = prev30["line_total"].sum()
            growth = ((rev30 - rev_prev30) / max(rev_prev30, 1)) * 100 if rev_prev30 > 0 else 0
            cancel_rate = (o["line_status"].str.lower() == "cancelled").sum() / max(len(o), 1) * 100
            top_skus = last30.groupby("sku")["line_total"].sum().nlargest(5).to_dict()
            stats["orders"] = {
                "total_line_items": len(o),
                "unique_orders": o["customer_order_id"].nunique(),
                "revenue_30d": float(rev30),
                "revenue_prev30": float(rev_prev30),
                "growth_pct": float(growth),
                "cancel_rate_pct": float(cancel_rate),
                "top_5_skus_last30": {k: float(v) for k, v in top_skus.items()},
            }
        except Exception as e:
            stats["orders_error"] = str(e)

    # Settlement
    settle = data.get("settlement", pd.DataFrame())
    if not settle.empty:
        try:
            s = settle.copy()
            s["amount"] = pd.to_numeric(s["amount"], errors='coerce').fillna(0)
            s["total_payable"] = pd.to_numeric(s["total_payable"], errors='coerce').fillna(0)
            payments = s[s["transaction_type"] == "PaymentSummary"]
            net_paid = payments["total_payable"].sum()
            total_sales = s[s["transaction_type"] == "Sale"]["amount"].sum()
            total_refunds = s[s["transaction_type"] == "Refund"]["amount"].sum()
            total_fees = s[s["transaction_type"].isin(["Service Fee", "Campaigns"])]["amount"].sum()
            margin = (net_paid / max(total_sales, 1)) * 100
            stats["settlement"] = {
                "net_paid_lifetime": float(net_paid),
                "gross_sales": float(total_sales),
                "total_refunds": float(abs(total_refunds)),
                "total_fees_ads": float(abs(total_fees)),
                "margin_pct": float(margin),
                "periods_count": int(s["report_date"].nunique()) if "report_date" in s else 0,
            }
        except Exception as e:
            stats["settlement_error"] = str(e)

    # Returns
    ret = data.get("returns", pd.DataFrame())
    if not ret.empty:
        try:
            r = ret.copy()
            r["unit_price"] = pd.to_numeric(r["unit_price"], errors='coerce').fillna(0)
            r["quantity"] = pd.to_numeric(r["quantity"], errors='coerce').fillna(1)
            r["total_refund_amount"] = pd.to_numeric(r["total_refund_amount"], errors='coerce').fillna(0)
            r["lost"] = r["unit_price"] * r["quantity"]
            listing_issues = ["INCORRECT_ITEM", "DIFFICULT_TO_SETUP_NOT_COMPATIBLE",
                              "NOT_AS_DESCRIBED_PICTURED", "DEFECTIVE"]
            listing_cnt = r[r["return_reason"].isin(listing_issues)].shape[0]
            listing_loss = r[r["return_reason"].isin(listing_issues)]["lost"].sum()
            top_reasons = r["return_reason"].value_counts().head(5).to_dict()
            killer = r.groupby("sku")["lost"].sum().nlargest(5).to_dict()
            stats["returns"] = {
                "total_returns": int(r["return_order_id"].nunique()),
                "total_refund_amount": float(r["total_refund_amount"].sum()),
                "listing_issues_count": int(listing_cnt),
                "listing_issues_pct": float(listing_cnt / max(len(r), 1) * 100),
                "recoverable_if_fixed": float(listing_loss),
                "top_5_reasons": top_reasons,
                "top_5_killer_skus": {k: float(v) for k, v in killer.items()},
                "seller_paid": float(r[r["refund_covered_by"] == "Seller"]["total_refund_amount"].sum()),
            }
        except Exception as e:
            stats["returns_error"] = str(e)

    # WFS
    wfs = data.get("wfs_shipments", pd.DataFrame())
    if not wfs.empty:
        try:
            w = wfs.copy()
            w["expected_units"] = pd.to_numeric(w["expected_units"], errors='coerce').fillna(0)
            w["received_units"] = pd.to_numeric(w["received_units"], errors='coerce').fillna(0)
            awaiting = w[w["po_status"] == "AWAITING_DELIVERY"]
            pending = int((awaiting["expected_units"] - awaiting["received_units"]).sum())
            stats["logistics"] = {
                "active_shipments": int(awaiting["shipment_id"].nunique()),
                "pending_units": pending,
                "pending_skus": int(awaiting["sku"].nunique()),
                "closed_total": int(w[w["po_status"] == "CLOSED"]["shipment_id"].nunique()),
            }
        except Exception as e:
            stats["logistics_error"] = str(e)

    # Items / Catalog problems
    items = data.get("items", pd.DataFrame())
    if not items.empty and "publish_status" in items:
        try:
            stats["catalog"] = {
                "total_skus": len(items),
                "unpublished_skus": int((~items["publish_status"].isin(["PUBLISHED"])).sum()),
            }
        except Exception:
            pass

    # CAP discount
    buybox = data.get("buybox", pd.DataFrame())
    if not buybox.empty and "price_diff_pct" in buybox:
        try:
            heavy = buybox[buybox["price_diff_pct"].fillna(0) > 0.20]
            stats["pricing"] = {
                "cap_heavy_count": int(len(heavy)),
                "hidden_loss_per_unit": float((heavy["seller_item_price"] - heavy["buybox_item_price"]).sum()) if len(heavy) > 0 else 0,
            }
        except Exception:
            pass

    # ============ PROMPT ============
    lang_inst = {
        "RU": "Отвечай на русском, кратко, без воды.",
        "UA": "Відповідай українською, стисло, без води.",
        "EN": "Respond in English, concise, no fluff.",
    }.get(lang, "Respond in English.")

    prompt = f"""You are a senior McKinsey-level analyst for a Walmart Marketplace seller (UDC Mower Parts LLC — lawn mower replacement parts).

{lang_inst}

Below is the current business state as JSON snapshot. Analyze it and write a sharp executive briefing.

DATA:
{json.dumps(stats, indent=2, default=str)}

Write the briefing in this EXACT format (use HTML tags like <b>, <br>, no markdown):

<b>📊 SITUATION</b><br>
[2-3 sentences: where business stands now, top numbers, growth direction]

<b>🎯 TOP-3 ACTIONS THIS WEEK</b><br>
1. [Most urgent action with $ impact estimate]<br>
2. [Second action with rationale]<br>
3. [Third action]<br>

<b>⚠️ RISKS & OPPORTUNITIES</b><br>
• [Risk 1 with $ exposure]<br>
• [Opportunity 1 with $ upside]<br>

<b>🔮 ONE THING TO WATCH</b><br>
[The one metric or trend that matters most over next 30 days]

Be specific with numbers from data. Use $ amounts. Reference SKU codes where applicable. Maximum 200 words total."""

    import requests as req
    MODELS = [
        st.secrets.get("GEMINI_MODEL", "gemini-2.0-flash"),
        "gemini-2.5-flash",
        "gemini-flash-latest",
    ]
    for model in MODELS:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            r = req.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=45)
            result = r.json()
            if "error" in result:
                continue
            if "candidates" in result and result["candidates"]:
                return result["candidates"][0]["content"]["parts"][0]["text"], model
        except Exception:
            continue
    return None, None






def render_overview(data, T, theme, lang):
    """Показує найважливіше з кожного розділу в одному вікні.
    Як виконавчий summary."""

    # ============ 🧠 AI EXECUTIVE SUMMARY ============
    api_key = st.secrets.get("GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
    if api_key:
        with st.spinner("🧠 AI analyzes your business state..."):
            ai_summary, ai_model = ai_executive_summary(data, lang)

        if ai_summary:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, rgba(151,117,250,0.12), rgba(124,159,255,0.08));
                        border-left: 4px solid #9775fa; padding: 20px 24px; border-radius: 12px;
                        margin: 8px 0 20px 0; line-height: 1.8;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                    <strong style="font-size:1.15rem;">🧠 AI Executive Briefing</strong>
                    <span style="opacity:0.6; font-size:0.8rem;">Model: {ai_model}</span>
                </div>
                <div style="font-size:0.98rem;">{ai_summary}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning("⚠️ AI summary failed. Check GEMINI_API_KEY in Secrets.")
    else:
        st.info("💡 Add `GEMINI_API_KEY` to Streamlit Secrets to enable AI Executive Briefing")

    st.divider()

    # ============ 💵 SALES & MONEY ============
    st.markdown(f"### {T['cat_sales']}")

    settle = data.get("settlement", pd.DataFrame())
    orders = data.get("orders", pd.DataFrame())

    c1, c2, c3, c4 = st.columns(4)

    # Settlement KPI
    if not settle.empty:
        payments = settle[settle["transaction_type"] == "PaymentSummary"]
        net_paid = payments["total_payable"].sum() if not payments.empty else 0
        sales_total = settle[settle["transaction_type"] == "Sale"]["amount"].sum()
        c1.metric("💰 Net Paid (lifetime)", f"${float(net_paid):,.0f}")
        c2.metric("📈 Gross Sales", f"${float(sales_total):,.0f}")

    # Orders KPI
    if not orders.empty:
        date_col = _pick_col(orders, "order_date", "purchase_date", "created_at")
        amount_col = _pick_col(orders, "total_amount", "order_total", "amount", "line_total")
        if date_col:
            orders_df = orders.copy()
            orders_df[date_col] = pd.to_datetime(orders_df[date_col], errors='coerce', utc=True).dt.tz_localize(None)
            last30 = orders_df[orders_df[date_col] >= pd.Timestamp(datetime.now().date() - timedelta(days=30))]
            c3.metric("📦 Orders 30d", f"{len(last30):,}")
            if amount_col:
                rev30 = pd.to_numeric(last30[amount_col], errors='coerce').sum()
                c4.metric("💵 Revenue 30d", f"${float(rev30):,.0f}")

    # Mini payouts timeline
    if not settle.empty:
        payments = settle[settle["transaction_type"] == "PaymentSummary"]
        if not payments.empty:
            ptime = payments[["report_date", "total_payable"]].copy()
            ptime["report_date"] = pd.to_datetime(ptime["report_date"], errors='coerce', utc=True).dt.tz_localize(None)
            ptime = ptime.sort_values("report_date").tail(12)
            ptime["color"] = ptime["total_payable"].apply(lambda x: "Deposit" if x > 0 else "Debit")
            fig = px.bar(ptime, x="report_date", y="total_payable", color="color",
                color_discrete_map={"Deposit": "#51cf66", "Debit": "#e03131"},
                title="💰 Last 12 Payouts → PAYONEER")
            fig.update_layout(height=250, template=theme["template"],
                paper_bgcolor=theme["paper_bg"], plot_bgcolor=theme["plot_bg"],
                showlegend=False, margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ============ 📦 OPERATIONS ============
    st.markdown(f"### {T['cat_ops']}")

    wfs = data.get("wfs_shipments", pd.DataFrame())
    inv = data.get("inventory_new", pd.DataFrame())

    c1, c2, c3, c4 = st.columns(4)
    if not wfs.empty:
        awaiting = wfs[wfs["po_status"] == "AWAITING_DELIVERY"]["shipment_id"].nunique()
        awaiting_df = wfs[wfs["po_status"] == "AWAITING_DELIVERY"]
        pending = int((awaiting_df["expected_units"].fillna(0) - awaiting_df["received_units"].fillna(0)).sum()) if not awaiting_df.empty else 0
        c1.metric("🚛 In Transit", f"{awaiting} ships")
        c2.metric("📦 Pending Units", f"{pending:,}")

    if not inv.empty:
        if "current_quantity" in inv:
            total_stock = pd.to_numeric(inv["current_quantity"], errors='coerce').sum()
            c3.metric("💾 In Stock", f"{int(total_stock):,} units")
        if "available_quantity" in inv:
            oos = (pd.to_numeric(inv["available_quantity"], errors='coerce') == 0).sum()
            c4.metric("🔴 OOS SKUs", f"{int(oos)}")

    # Найближчі поставки
    if not wfs.empty:
        wfs_copy = wfs.copy()
        wfs_copy["expected_delivery_date"] = pd.to_datetime(wfs_copy["expected_delivery_date"], errors='coerce', utc=True).dt.tz_localize(None)
        upcoming = wfs_copy[(wfs_copy["po_status"] == "AWAITING_DELIVERY") & (wfs_copy["expected_delivery_date"].notna())]
        if not upcoming.empty:
            upcoming_agg = upcoming.groupby("shipment_id").agg(
                fc=("fc_name", "first"),
                eta=("expected_delivery_date", "max"),
                skus=("sku", "nunique"),
                pending_u=("expected_units", lambda x: x.sum() - upcoming.loc[x.index, "received_units"].fillna(0).sum()),
            ).reset_index().sort_values("eta").head(5)
            upcoming_agg["eta"] = pd.to_datetime(upcoming_agg["eta"]).dt.strftime("%Y-%m-%d")
            upcoming_agg["pending_u"] = upcoming_agg["pending_u"].astype(int)
            upcoming_agg.columns = ["Shipment", "FC", "ETA", "SKUs", "Pending Units"]
            st.markdown("**🚛 Next 5 deliveries:**")
            st.dataframe(upcoming_agg, use_container_width=True, hide_index=True)

    st.divider()

    # ============ 🚨 PROBLEMS & ACTIONS ============
    st.markdown(f"### {T['cat_problems']}")

    ret = data.get("returns", pd.DataFrame())
    items = data.get("items", pd.DataFrame())
    buybox = data.get("buybox", pd.DataFrame())

    c1, c2, c3, c4 = st.columns(4)

    if not ret.empty:
        listing_issues = ["INCORRECT_ITEM", "DIFFICULT_TO_SETUP_NOT_COMPATIBLE", "NOT_AS_DESCRIBED_PICTURED"]
        listing_cnt = ret[ret["return_reason"].isin(listing_issues)].shape[0] if "return_reason" in ret else 0
        listing_pct = (100 * listing_cnt / max(len(ret), 1))
        c1.metric("🔄 Returns total", f"{len(ret)}")
        c2.metric("⚠️ Listing issues", f"{listing_pct:.0f}%")

    if not items.empty and "publish_status" in items:
        problems = (~items["publish_status"].isin(["PUBLISHED"])).sum()
        c3.metric("📋 Unpublished SKU", f"{int(problems)}")

    if not buybox.empty and "price_diff_pct" in buybox:
        cap_heavy = (buybox["price_diff_pct"].fillna(0) > 0.20).sum()
        c4.metric("💸 CAP >20%", f"{int(cap_heavy)} SKU")

    # Топ action items (з health check)
    actions = build_action_items(data, lang)
    if actions:
        st.markdown("**🎯 Top Action Items:**")
        impact_key = f"impact_{lang.lower()}"
        for act in actions[:3]:  # Тільки топ-3
            cls = _severity_class(act["severity"])
            impact = act.get(impact_key, act.get("impact_en", ""))
            emoji = {"CRITICAL": "🔴", "WARNING": "🟡", "INFO": "🔵"}.get(act["severity"], "⚪")
            st.markdown(f"""
            <div class="{cls}">
                <strong>{emoji} {act['issue']}</strong> · {T['affected']}: {act['count']}<br>
                <span style="opacity:0.85;">{impact}</span><br>
                <strong>→ {T['action']}:</strong> {act['action']}
            </div>
            """, unsafe_allow_html=True)

    st.divider()


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

        # 🆕 РЕЖИМ ПЕРЕГЛЯДУ
        st.markdown(f"### {T['view_mode']}")
        view_mode = st.radio(
            T["view_mode"],
            [T["view_overview"], T["view_focus"], T["view_all"]],
            label_visibility="collapsed",
            key="wm_view_mode",
        )

        st.divider()

        # 🆕 СПИСОК ВСІХ РОЗДІЛІВ (для focus / all)
        # Структура: (category, key, title, render_fn)
        SECTIONS = [
            # 💵 SALES & MONEY
            (T["cat_sales"], "orders",   T["orders_section"],       render_orders),
            (T["cat_sales"], "settle",   T["settlement_section"],   render_settlement),

            # 📦 OPERATIONS
            (T["cat_ops"],   "wfs",      T["wfs_section"],          render_wfs_shipments),
            (T["cat_ops"],   "returns",  T["returns_section"],      render_returns),
            (T["cat_ops"],   "cancel",   T["cancel_section"],       render_cancellations),

            # 🚨 PROBLEMS & ACTIONS
            (T["cat_problems"], "health", T["health_section"],      lambda d, t, th: render_health_check(d, t, th, lang)),
            (T["cat_problems"], "buybox", T["buybox_section"],      render_buybox),

            # 📋 CATALOG
            (T["cat_catalog"], "perf",   T["performance_section"],  render_performance),
            (T["cat_catalog"], "status", T["status_section"],       render_item_status),

            # ⚙️ SYSTEM
            (T["cat_system"], "loader",  T["loader_section"],       render_loader_runs),
        ]

        # FOCUS режим — selectbox
        focus_choice = None
        if view_mode == T["view_focus"]:
            options = [f"{cat} → {title}" for cat, _, title, _ in SECTIONS]
            keys = [key for _, key, _, _ in SECTIONS]
            focus_label = st.selectbox(T["pick_section"], options, key="wm_focus_pick")
            focus_choice = keys[options.index(focus_label)]

        # ALL режим — категорії з expander + checkboxes
        all_enabled = {}
        if view_mode == T["view_all"]:
            st.markdown(f"### {T['sections']}")

            # Групуємо по категоріях
            from collections import defaultdict
            cats = defaultdict(list)
            for cat, key, title, fn in SECTIONS:
                cats[cat].append((key, title, fn))

            for cat_name, items_list in cats.items():
                with st.expander(cat_name, expanded=True):
                    for key, title, _ in items_list:
                        all_enabled[key] = st.checkbox(title, True, key=f"wm_cb_{key}")

        # AI завжди окремий
        st.divider()
        show_ai = st.checkbox(T["ai_section"], view_mode == T["view_all"], key="wm_s_ai")

    apply_theme(theme)

    st.markdown(f"## {T['title']}")
    st.caption(f"`walmart.*` · {datetime.now().strftime('%d.%m.%Y %H:%M')}  ·  Mode: {view_mode}")
    st.divider()

    with st.spinner(T["loading"]):
        data = load_walmart_data()

    if data is None or all(df.empty for df in data.values()):
        st.warning(T["no_data"])
        return

    # KPI завжди показуємо
    kpi_row(data, T)
    st.divider()

    # ============ РЕНДЕР ЗА РЕЖИМОМ ============

    if view_mode == T["view_overview"]:
        # 🎯 OVERVIEW — швидке зведення
        render_overview(data, T, theme, lang)

    elif view_mode == T["view_focus"]:
        # 🔍 FOCUS — один розділ повністю
        for cat, key, title, fn in SECTIONS:
            if key == focus_choice:
                fn(data, T, theme)
                break

    elif view_mode == T["view_all"]:
        # 📚 ALL — всі вибрані розділи
        for cat, key, title, fn in SECTIONS:
            if all_enabled.get(key, False):
                fn(data, T, theme)
                st.divider()

    if show_ai:
        render_ai_section(T, lang)


if __name__ == "__main__":
    main() 
