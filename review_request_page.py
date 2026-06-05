"""
review_request_page.py — сторінка "Review Request" для існуючого дашборда.

v1.1 — додано блок "По ASIN": які товари і скільки запитів по них пішло,
        з клікабельними ASIN-посиланнями на Amazon + бар-чарт топ-ASIN.

Підключення в твоєму головному файлі (Sales & Traffic Dashboard v1.3):

  1. Зверху додай імпорт:
        from review_request_page import render_review_page, REVIEW_TRANSLATIONS

  2. У main(), у блоці `with st.sidebar:` ПІСЛЯ вибору мови (lang) додай перемикач сторінок:

        page = st.radio(
            REVIEW_TRANSLATIONS[lang]["nav_label"],
            [REVIEW_TRANSLATIONS[lang]["nav_sales"],
             REVIEW_TRANSLATIONS[lang]["nav_review"]],
            horizontal=False,
        )

  3. У main() ПІСЛЯ apply_theme(theme), розгалуж рендер:

        if page == REVIEW_TRANSLATIONS[lang]["nav_review"]:
            render_review_page(get_engine, T, theme, lang)
            return   # <- важливо: не рендеримо Sales нижче

        # ...далі йде твій звичайний Sales-рендер...

Все. get_engine, T, theme, lang беруться з твого існуючого коду — нічого не дублюється.

ВАЖЛИВО про схему: цей модуль читає
  - public.review_request_log (amazon_order_id, sent_at, status)
  - spapi.all_orders (amazon_order_id, asin, order_status, purchase_date)
ASIN у review_request_log НЕ зберігається → тягнемо JOIN-ом з all_orders.
Фільтри returns/refunds/replacements у підрахунку пулу свідомо НЕ застосовані
для швидкості (це оглядовий монітор).
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import text
from datetime import datetime


# ============================================================
# 🌐 ПЕРЕКЛАДИ (доповнюють твій TRANSLATIONS)
# ============================================================

REVIEW_TRANSLATIONS = {
    "EN": {
        "nav_label": "🧭 Page",
        "nav_sales": "📈 Sales & Traffic",
        "nav_review": "📨 Review Requests",
        "title": "📨 Review Request Monitor",
        "sub": "Amazon review solicitations — daily volume, pool & urgency",
        "kpi_today": "📤 Sent today",
        "kpi_7d": "📊 Sent (7d)",
        "kpi_pool": "🎯 Pool (candidates)",
        "kpi_burning": "🔥 Burning (<5d left)",
        "kpi_failed_7d": "❌ Failed (7d)",
        "kpi_last": "⏱️ Last sent",
        "health_ok": "✅ Healthy — last run within 25h",
        "health_warn": "🚨 NO SEND for {h:.0f}h (threshold 25h)",
        "daily_title": "📈 Daily volume (by status)",
        "legend_hint": "💡 <b>Sent</b> — Amazon accepted the request · <b>Already</b> — request was already sent for this order earlier (Amazon declined the duplicate, this is normal) · <b>Outside</b> — order is outside the 5-30 day window (will retry later) · <b>Failed</b> — technical error (e.g. expired token); these orders return to the pool and get retried next run.",
        "pool_title": "🎯 Candidate pool by urgency",
        "pool_fresh": "Fresh (8-15d)",
        "pool_mid": "Mid (15-25d)",
        "pool_burning": "🔥 Burning (25-30d)",
        "funnel_title": "🔁 Funnel: orders → sent",
        "f_orders": "Shipped orders (30d)",
        "f_pool": "Eligible pool",
        "f_sent": "Sent (30d)",
        "table_title": "📋 Daily breakdown",
        "no_data": "⚠️ No review_request_log data found.",
        "col_day": "Day", "col_sent": "Sent", "col_already": "Already",
        "col_outside": "Outside", "col_failed": "Failed", "col_total": "Total",
        "loading": "Loading review data...",
        # 🆕 ASIN block
        "asin_title": "📦 By ASIN",
        "asin_sub": "Which products review requests were sent for. Click ASIN to open on Amazon.",
        "asin_chart_title": "🏆 Top ASIN by sent requests",
        "asin_table_title": "📋 ASIN breakdown",
        "col_asin": "ASIN", "col_link": "Link", "asin_no_data": "⚠️ No ASIN data (no log↔orders match).",
        "per_label": "Period", "per_7": "7 days", "per_14": "14 days", "per_30": "30 days",
        "sum_sent": "✅ Sent", "sum_already": "⏭️ Already", "sum_outside": "⏰ Outside",
        "sum_failed": "❌ Failed", "sum_asins": "📦 ASINs active",
        "risk_title": "🛡️ Sending vs top negative topic (safety signal)",
        "risk_sub": "The #1 negative topic per ASIN (from Customer Feedback) and how much it drags the rating. If a topic hurts the rating a lot — better not to push review requests for that ASIN.",
        "risk_flag": "Flag", "risk_topic": "Top negative topic", "risk_pct": "Mentions", "risk_impact": "★ impact",
        "risk_warn": "🔴 {n} ASIN(s) with a strongly rating-damaging topic — consider pausing requests for them.",
        "cov_title": "📋 Request-review coverage control by order date",
        "cov_date": "Order date", "cov_orders": "Orders", "cov_sent": "Requests sent",
        "cov_errors": "Errors", "cov_pct": "Coverage %", "cov_unproc": "Unprocessed",
        "cov_status": "Status", "cov_comment": "Comment",
        "cov_warn_lbl": "Attention", "cov_prob_lbl": "Problem",
        "cov_legend": "Status legend",
        "cov_leg_ok": "coverage at target", "cov_leg_warn": "coverage below target",
        "cov_leg_prob": "coverage critically low", "cov_about": "About the calculation",
        "cov_c_high": "High coverage", "cov_c_norm": "Within norm",
        "cov_c_below": "Coverage below target", "cov_c_crit": "Coverage critically low",
    },
    "UA": {
        "nav_label": "🧭 Сторінка",
        "nav_sales": "📈 Продажі і трафік",
        "nav_review": "📨 Запити на відгуки",
        "title": "📨 Монітор запитів на відгуки",
        "sub": "Amazon review solicitations — обсяг, пул і терміновість",
        "kpi_today": "📤 Надіслано сьогодні",
        "kpi_7d": "📊 Надіслано (7д)",
        "kpi_pool": "🎯 Пул (кандидати)",
        "kpi_burning": "🔥 Горить (<5д)",
        "kpi_failed_7d": "❌ Помилок (7д)",
        "kpi_last": "⏱️ Остання відправка",
        "health_ok": "✅ Здорово — останній прогін у межах 25 год",
        "health_warn": "🚨 НЕМАЄ РОЗСИЛКИ {h:.0f} год (поріг 25 год)",
        "daily_title": "📈 Обсяг по днях (за статусом)",
        "legend_hint": "💡 <b>Надіслано</b> — Amazon прийняв запит · <b>Already</b> — запит по цьому замовленню вже слали раніше (Amazon відмовив у дублі, це нормально) · <b>Outside</b> — замовлення поза вікном 5-30 днів (повторимо пізніше) · <b>Помилок</b> — технічна помилка (напр. протух токен); ці замовлення повертаються в пул і повторюються наступного прогону.",
        "pool_title": "🎯 Пул кандидатів за терміновістю",
        "pool_fresh": "Свіжі (8-15д)",
        "pool_mid": "Середні (15-25д)",
        "pool_burning": "🔥 Горять (25-30д)",
        "funnel_title": "🔁 Воронка: замовлення → надіслано",
        "f_orders": "Shipped замовлень (30д)",
        "f_pool": "Пул кандидатів",
        "f_sent": "Надіслано (30д)",
        "table_title": "📋 Розбивка по днях",
        "no_data": "⚠️ Немає даних review_request_log.",
        "col_day": "День", "col_sent": "Надіслано", "col_already": "Already",
        "col_outside": "Outside", "col_failed": "Помилок", "col_total": "Всього",
        "loading": "Завантажуємо дані розсилки...",
        # 🆕 ASIN block
        "asin_title": "📦 По ASIN",
        "asin_sub": "По яких товарах слали запити на відгук. Клікни ASIN — відкриється на Amazon.",
        "asin_chart_title": "🏆 Топ ASIN за надісланими запитами",
        "asin_table_title": "📋 Розбивка по ASIN",
        "col_asin": "ASIN", "col_link": "Посилання", "asin_no_data": "⚠️ Немає даних по ASIN (немає звʼязку log↔orders).",
        "per_label": "Період", "per_7": "7 днів", "per_14": "14 днів", "per_30": "30 днів",
        "sum_sent": "✅ Надіслано", "sum_already": "⏭️ Already", "sum_outside": "⏰ Outside",
        "sum_failed": "❌ Помилок", "sum_asins": "📦 Активних ASIN",
        "risk_title": "🛡️ Розсилка vs топова негативна тема (захисний сигнал)",
        "risk_sub": "Головна негативна тема по ASIN (з Customer Feedback) і наскільки вона тягне рейтинг вниз. Якщо тема сильно шкодить рейтингу — краще НЕ гнати запити по цьому ASIN.",
        "risk_flag": "Прапор", "risk_topic": "Топ негативна тема", "risk_pct": "Згадувань", "risk_impact": "★ вплив",
        "risk_warn": "🔴 {n} ASIN із темою, що сильно псує рейтинг — варто призупинити запити по них.",
        "cov_title": "📋 Контроль покриття request review по датах замовлень",
        "cov_date": "Дата замовлення", "cov_orders": "Orders", "cov_sent": "Requests sent",
        "cov_errors": "Errors", "cov_pct": "Coverage %", "cov_unproc": "Не оброблено",
        "cov_status": "Статус", "cov_comment": "Коментар",
        "cov_warn_lbl": "Увага", "cov_prob_lbl": "Проблема",
        "cov_legend": "Легенда статусів",
        "cov_leg_ok": "покриття на цільовому рівні", "cov_leg_warn": "покриття нижче цілі",
        "cov_leg_prob": "покриття критично низьке", "cov_about": "Про розрахунок покриття",
        "cov_c_high": "Високе покриття", "cov_c_norm": "У межах норми",
        "cov_c_below": "Покриття нижче цілі", "cov_c_crit": "Покриття критично низьке",
    },
    "RU": {
        "nav_label": "🧭 Страница",
        "nav_sales": "📈 Продажи и трафик",
        "nav_review": "📨 Запросы на отзывы",
        "title": "📨 Монитор запросов на отзывы",
        "sub": "Amazon review solicitations — объём, пул и срочность",
        "kpi_today": "📤 Отправлено сегодня",
        "kpi_7d": "📊 Отправлено (7д)",
        "kpi_pool": "🎯 Пул (кандидаты)",
        "kpi_burning": "🔥 Горит (<5д)",
        "kpi_failed_7d": "❌ Ошибок (7д)",
        "kpi_last": "⏱️ Последняя отправка",
        "health_ok": "✅ Здорово — последний прогон в пределах 25ч",
        "health_warn": "🚨 НЕТ РАССЫЛКИ {h:.0f}ч (порог 25ч)",
        "daily_title": "📈 Объём по дням (по статусу)",
        "legend_hint": "💡 <b>Отправлено</b> — Amazon принял запрос · <b>Already</b> — запрос по этому заказу уже отправляли ранее (Amazon отклонил дубль, это нормально) · <b>Outside</b> — заказ вне окна 5-30 дней (повторим позже) · <b>Ошибок</b> — техническая ошибка (напр. истёк токен); эти заказы возвращаются в пул и повторяются в следующем прогоне.",
        "pool_title": "🎯 Пул кандидатов по срочности",
        "pool_fresh": "Свежие (8-15д)",
        "pool_mid": "Средние (15-25д)",
        "pool_burning": "🔥 Горят (25-30д)",
        "funnel_title": "🔁 Воронка: заказы → отправлено",
        "f_orders": "Shipped заказов (30д)",
        "f_pool": "Пул кандидатов",
        "f_sent": "Отправлено (30д)",
        "table_title": "📋 Разбивка по дням",
        "no_data": "⚠️ Нет данных review_request_log.",
        "col_day": "День", "col_sent": "Отправлено", "col_already": "Already",
        "col_outside": "Outside", "col_failed": "Ошибок", "col_total": "Всего",
        "loading": "Загружаем данные рассылки...",
        # 🆕 ASIN block
        "asin_title": "📦 По ASIN",
        "asin_sub": "По каким товарам слали запросы на отзыв. Кликни ASIN — откроется на Amazon.",
        "asin_chart_title": "🏆 Топ ASIN по отправленным запросам",
        "asin_table_title": "📋 Разбивка по ASIN",
        "col_asin": "ASIN", "col_link": "Ссылка", "asin_no_data": "⚠️ Нет данных по ASIN (нет связи log↔orders).",
        "per_label": "Период", "per_7": "7 дней", "per_14": "14 дней", "per_30": "30 дней",
        "sum_sent": "✅ Отправлено", "sum_already": "⏭️ Already", "sum_outside": "⏰ Outside",
        "sum_failed": "❌ Ошибок", "sum_asins": "📦 Активных ASIN",
        "risk_title": "🛡️ Рассылка vs топовая негативная тема (защитный сигнал)",
        "risk_sub": "Главная негативная тема по ASIN (из Customer Feedback) и насколько она тянет рейтинг вниз. Если тема сильно вредит рейтингу — лучше НЕ слать запросы по этому ASIN.",
        "risk_flag": "Флаг", "risk_topic": "Топ негативная тема", "risk_pct": "Упоминаний", "risk_impact": "★ влияние",
        "risk_warn": "🔴 {n} ASIN с темой, сильно портящей рейтинг — стоит приостановить запросы по ним.",
        "cov_title": "📋 Контроль покрытия request review по датам заказов",
        "cov_date": "Дата заказа", "cov_orders": "Orders", "cov_sent": "Requests sent",
        "cov_errors": "Errors", "cov_pct": "Coverage %", "cov_unproc": "Не обработано",
        "cov_status": "Статус", "cov_comment": "Комментарий",
        "cov_warn_lbl": "Внимание", "cov_prob_lbl": "Проблема",
        "cov_legend": "Легенда статусов",
        "cov_leg_ok": "покрытие на целевом уровне", "cov_leg_warn": "покрытие ниже цели",
        "cov_leg_prob": "покрытие критически низкое", "cov_about": "О расчёте покрытия",
        "cov_c_high": "Высокое покрытие", "cov_c_norm": "В пределах нормы",
        "cov_c_below": "Покрытие ниже цели", "cov_c_crit": "Покрытие критически низкое",
    },
}


# ============================================================
# 🗄️ ЗАПИТИ ДО БД (кешовані)
# ============================================================

@st.cache_data(ttl=900)
def _load_daily(_engine, days_back: int = 30) -> pd.DataFrame:
    """Розсилка по днях за статусом."""
    q = text("""
        SELECT sent_at::date AS day,
               COUNT(*) FILTER (WHERE status='sent')             AS sent,
               COUNT(*) FILTER (WHERE status='already_reviewed') AS already,
               COUNT(*) FILTER (WHERE status='outside_window')   AS outside,
               COUNT(*) FILTER (WHERE status='failed')           AS failed,
               COUNT(*)                                          AS total
        FROM public.review_request_log
        WHERE sent_at >= NOW() - (:days || ' days')::interval
        GROUP BY sent_at::date
        ORDER BY day
    """)
    with _engine.connect() as conn:
        df = pd.read_sql(q, conn, params={"days": days_back})
    if not df.empty:
        df['day'] = pd.to_datetime(df['day'])
    return df


@st.cache_data(ttl=900)
def _load_coverage(_engine, days_back: int = 30) -> pd.DataFrame:
    """
    🆕 Контроль покриття request review ПО ДАТІ ЗАМОВЛЕННЯ (purchase_date).
    Coverage % = (sent + already) / orders * 100
    Не оброблено = orders - (sent + already)
    orders = всі Shipped замовлення за день (чесний знаменник).
    """
    q = text("""
        WITH ord AS (
            SELECT o.purchase_date::date AS day,
                   COUNT(DISTINCT o.amazon_order_id) AS orders
            FROM spapi.all_orders o
            WHERE o.order_status = 'Shipped'
              AND o.purchase_date >= NOW() - (:days || ' days')::interval
            GROUP BY o.purchase_date::date
        ),
        lg AS (
            SELECT o.purchase_date::date AS day,
                   COUNT(DISTINCT l.amazon_order_id) FILTER (WHERE l.status='sent')             AS sent,
                   COUNT(DISTINCT l.amazon_order_id) FILTER (WHERE l.status='already_reviewed') AS already,
                   COUNT(DISTINCT l.amazon_order_id) FILTER (WHERE l.status='failed')           AS errors
            FROM public.review_request_log l
            JOIN spapi.all_orders o ON o.amazon_order_id = l.amazon_order_id
            WHERE o.purchase_date >= NOW() - (:days || ' days')::interval
            GROUP BY o.purchase_date::date
        )
        SELECT ord.day,
               ord.orders,
               COALESCE(lg.sent, 0)    AS sent,
               COALESCE(lg.already, 0) AS already,
               COALESCE(lg.errors, 0)  AS errors
        FROM ord
        LEFT JOIN lg ON lg.day = ord.day
        ORDER BY ord.day DESC
    """)
    with _engine.connect() as conn:
        df = pd.read_sql(q, conn, params={"days": days_back})
    if df.empty:
        return df
    df['covered']     = df['sent'] + df['already']
    df['unprocessed'] = (df['orders'] - df['covered']).clip(lower=0)
    df['coverage']    = (df['covered'] / df['orders'].replace(0, pd.NA) * 100).round(1)
    return df


@st.cache_data(ttl=900)
def _load_kpis(_engine) -> dict:
    """Зведені KPI одним проходом."""
    out = {}
    with _engine.connect() as conn:
        # надіслано сьогодні / 7д / помилок 7д / останній sent
        row = conn.execute(text("""
            SELECT
              COUNT(*) FILTER (WHERE status='sent' AND sent_at::date=CURRENT_DATE)        AS today,
              COUNT(*) FILTER (WHERE status='sent' AND sent_at>=NOW()-INTERVAL '7 days')  AS sent7,
              COUNT(*) FILTER (WHERE status='failed' AND sent_at>=NOW()-INTERVAL '7 days') AS failed7,
              MAX(sent_at) FILTER (WHERE status='sent')                                   AS last_sent
            FROM public.review_request_log
        """)).fetchone()
        out['today']     = row[0] or 0
        out['sent7']     = row[1] or 0
        out['failed7']   = row[2] or 0
        out['last_sent'] = row[3]

        # годин з останньої відправки (для health)
        if out['last_sent']:
            h = conn.execute(text(
                "SELECT EXTRACT(EPOCH FROM (NOW() - :ts))/3600"
            ), {"ts": out['last_sent']}).scalar()
            out['hours_since'] = float(h) if h is not None else None
        else:
            out['hours_since'] = None
    return out


@st.cache_data(ttl=900)
def _load_pool(_engine) -> dict:
    """Пул кандидатів за терміновістю + воронка."""
    base = """
        FROM spapi.all_orders o
        WHERE o.order_status = 'Shipped'
          AND o.purchase_date BETWEEN NOW() - INTERVAL '30 days'
                                  AND NOW() - INTERVAL '8 days'
          AND NOT EXISTS (
              SELECT 1 FROM public.review_request_log l
              WHERE l.amazon_order_id = o.amazon_order_id
                AND l.status IN ('sent','already_reviewed')
          )
    """
    out = {}
    with _engine.connect() as conn:
        row = conn.execute(text(f"""
            SELECT
              COUNT(*) FILTER (WHERE purchase_date >= NOW()-INTERVAL '15 days')                                AS fresh,
              COUNT(*) FILTER (WHERE purchase_date <  NOW()-INTERVAL '15 days'
                                 AND purchase_date >= NOW()-INTERVAL '25 days')                                 AS mid,
              COUNT(*) FILTER (WHERE purchase_date <  NOW()-INTERVAL '25 days')                                 AS burning,
              COUNT(*)                                                                                          AS pool
            {base}
        """)).fetchone()
        out['fresh']   = row[0] or 0
        out['mid']     = row[1] or 0
        out['burning'] = row[2] or 0
        out['pool']    = row[3] or 0

        # воронка: всі Shipped 30д
        out['orders30'] = conn.execute(text("""
            SELECT COUNT(*) FROM spapi.all_orders
            WHERE order_status='Shipped'
              AND purchase_date >= NOW()-INTERVAL '30 days'
        """)).scalar() or 0

        out['sent30'] = conn.execute(text("""
            SELECT COUNT(*) FROM public.review_request_log
            WHERE status='sent' AND sent_at >= NOW()-INTERVAL '30 days'
        """)).scalar() or 0
    return out


@st.cache_data(ttl=900)
def _load_by_asin(_engine, days_back: int = 30) -> pd.DataFrame:
    """
    🆕 Розбивка по ASIN: скільки запитів кожного статусу пішло по кожному товару.
    ASIN у review_request_log немає → JOIN з spapi.all_orders по amazon_order_id.
    Один order може мати кілька ASIN (по item на рядок) → COUNT(DISTINCT order_id)
    щоб не роздути лічильник за рахунок multi-item замовлень.
    """
    q = text("""
        SELECT o.asin AS asin,
               COUNT(DISTINCT l.amazon_order_id) FILTER (WHERE l.status='sent')             AS sent,
               COUNT(DISTINCT l.amazon_order_id) FILTER (WHERE l.status='already_reviewed') AS already,
               COUNT(DISTINCT l.amazon_order_id) FILTER (WHERE l.status='outside_window')   AS outside,
               COUNT(DISTINCT l.amazon_order_id) FILTER (WHERE l.status='failed')           AS failed
        FROM public.review_request_log l
        JOIN spapi.all_orders o
          ON o.amazon_order_id = l.amazon_order_id
        WHERE l.sent_at >= NOW() - (:days || ' days')::interval
          AND o.asin IS NOT NULL
        GROUP BY o.asin
        ORDER BY sent DESC, already DESC
    """)
    with _engine.connect() as conn:
        df = pd.read_sql(q, conn, params={"days": days_back})
    return df


@st.cache_data(ttl=900)
def _load_top_negative(_engine) -> pd.DataFrame:
    """
    🆕 Топова НЕГАТИВНА тема по кожному ASIN (останній знімок).
    Customer Feedback API не дає кількості відгуків/рейтингу — лише теми.
    Беремо найвпливовішу негативну тему: topic_rank=1 (вона ж найчастіша),
    + star impact (на скільки ★ тягне вниз) + % згадувань.

    Джерело: reviews.item_topics (sentiment='negative').
    star_impact зазвичай ВІДʼЄМНИЙ (тягне рейтинг вниз) → беремо найменший (MIN).
    """
    q = text("""
        WITH last_snap AS (
            SELECT MAX(snapshot_date) AS d FROM reviews.item_topics
        ),
        neg AS (
            SELECT t.asin,
                   t.topic,
                   t.asin_occurrence_pct,
                   t.parent_star_impact,
                   ROW_NUMBER() OVER (
                       PARTITION BY t.asin
                       ORDER BY t.parent_star_impact ASC NULLS LAST, t.topic_rank ASC
                   ) AS rn
            FROM reviews.item_topics t, last_snap s
            WHERE t.snapshot_date = s.d
              AND t.sentiment = 'negative'
        )
        SELECT asin,
               topic                AS top_topic,
               asin_occurrence_pct  AS topic_pct,
               parent_star_impact   AS star_impact
        FROM neg
        WHERE rn = 1
    """)
    try:
        with _engine.connect() as conn:
            df = pd.read_sql(q, conn)
    except Exception:
        df = pd.DataFrame(columns=["asin", "top_topic", "topic_pct", "star_impact"])
    return df


# ============================================================
# 📊 РЕНДЕР
# ============================================================

def render_review_page(get_engine, T_main, theme, lang):
    """
    get_engine — твоя існуюча функція (@st.cache_resource) що повертає engine
    T_main     — НЕ використовується тут (свої переклади), лишено для сумісності
    theme      — твій DARK_THEME / LIGHT_THEME dict
    lang       — "RU" | "UA" | "EN"
    """
    R = REVIEW_TRANSLATIONS.get(lang, REVIEW_TRANSLATIONS["EN"])
    engine = get_engine()

    st.markdown(f"## {R['title']}")
    st.caption(f"{R['sub']} · {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    st.divider()

    with st.spinner(R['loading']):
        kpi   = _load_kpis(engine)
        pool  = _load_pool(engine)
        daily = _load_daily(engine, 30)

    if daily.empty and pool['pool'] == 0:
        st.warning(R['no_data'])
        return

    # ---- HEALTH BANNER (dead man's switch, візуальний) ----
    hrs = kpi.get('hours_since')
    if hrs is not None and hrs > 25:
        st.error(R['health_warn'].format(h=hrs))
    else:
        st.success(R['health_ok'])

    # ---- KPI ROW ----
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric(R['kpi_today'],     f"{kpi['today']:,}")
    c2.metric(R['kpi_7d'],        f"{kpi['sent7']:,}")
    c3.metric(R['kpi_pool'],      f"{pool['pool']:,}")
    c4.metric(R['kpi_burning'],   f"{pool['burning']:,}",
              delta="⚠️" if pool['burning'] > 0 else None,
              delta_color="inverse")
    c5.metric(R['kpi_failed_7d'], f"{kpi['failed7']:,}",
              delta_color="inverse")
    last_str = kpi['last_sent'].strftime('%d.%m %H:%M') if kpi['last_sent'] else "—"
    c6.metric(R['kpi_last'], last_str)

    st.divider()

    # ---- DAILY VOLUME (stacked bars) ----
    st.markdown(f"### {R['daily_title']}")
    st.caption(R['legend_hint'], unsafe_allow_html=True)
    if not daily.empty:
        fig = go.Figure()
        fig.add_trace(go.Bar(name=R['col_sent'], x=daily['day'], y=daily['sent'],
                             marker_color='#64c896'))
        fig.add_trace(go.Bar(name=R['col_already'], x=daily['day'], y=daily['already'],
                             marker_color='#7c9fff'))
        fig.add_trace(go.Bar(name=R['col_outside'], x=daily['day'], y=daily['outside'],
                             marker_color='#ffd700'))
        fig.add_trace(go.Bar(name=R['col_failed'], x=daily['day'], y=daily['failed'],
                             marker_color='#e03131'))
        fig.update_layout(
            barmode='stack', height=380, template=theme['template'],
            paper_bgcolor=theme['paper_bg'], plot_bgcolor=theme['plot_bg'],
            margin=dict(l=0, r=0, t=10, b=0), hovermode='x unified',
            legend=dict(orientation="h", y=1.08))
        fig.update_xaxes(gridcolor=theme['grid'])
        fig.update_yaxes(gridcolor=theme['grid'])
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ---- POOL BY URGENCY + FUNNEL ----
    cL, cR = st.columns(2)
    with cL:
        st.markdown(f"### {R['pool_title']}")
        pool_df = pd.DataFrame({
            "bucket": [R['pool_fresh'], R['pool_mid'], R['pool_burning']],
            "count":  [pool['fresh'], pool['mid'], pool['burning']],
        })
        figp = px.bar(pool_df, x="count", y="bucket", orientation="h",
                      color="bucket",
                      color_discrete_sequence=['#64c896', '#ffd700', '#e03131'])
        figp.update_layout(
            height=300, template=theme['template'],
            paper_bgcolor=theme['paper_bg'], plot_bgcolor=theme['plot_bg'],
            showlegend=False, margin=dict(l=0, r=0, t=10, b=0),
            yaxis=dict(autorange='reversed'))
        figp.update_xaxes(gridcolor=theme['grid'])
        st.plotly_chart(figp, use_container_width=True)

    with cR:
        st.markdown(f"### {R['funnel_title']}")
        figf = go.Figure(go.Funnel(
            y=[R['f_orders'], R['f_pool'], R['f_sent']],
            x=[pool['orders30'], pool['pool'], pool['sent30']],
            textinfo="value+percent initial",
            marker=dict(color=['#7c9fff', '#ffd700', '#64c896'])))
        figf.update_layout(
            height=300, template=theme['template'],
            paper_bgcolor=theme['paper_bg'], plot_bgcolor=theme['plot_bg'],
            margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(figf, use_container_width=True)

    # ---- 🆕 BY ASIN ----
    st.divider()
    st.markdown(f"### {R['asin_title']}")
    st.caption(R['asin_sub'])

    # 🆕 перемикач періоду: 7 / 14 / 30 днів
    period_label_map = {R['per_7']: 7, R['per_14']: 14, R['per_30']: 30}
    sel = st.radio(R['per_label'], list(period_label_map.keys()),
                   index=2, horizontal=True, key="asin_period")
    days_sel = period_label_map[sel]

    by_asin = _load_by_asin(engine, days_sel)

    # 🆕 загальна зведена строка за обраний період
    if not by_asin.empty:
        tot_sent    = int(by_asin['sent'].sum())
        tot_already = int(by_asin['already'].sum())
        tot_outside = int(by_asin['outside'].sum())
        tot_failed  = int(by_asin['failed'].sum())
        n_asins     = int((by_asin['sent'] > 0).sum())
        s1, s2, s3, s4, s5 = st.columns(5)
        s1.metric(R['sum_sent'], f"{tot_sent:,}")
        s2.metric(R['sum_already'], f"{tot_already:,}")
        s3.metric(R['sum_outside'], f"{tot_outside:,}")
        s4.metric(R['sum_failed'], f"{tot_failed:,}")
        s5.metric(R['sum_asins'], f"{n_asins:,}")

    if by_asin.empty:
        st.info(R['asin_no_data'])
    else:
        aL, aR = st.columns([1, 1])

        # ---- ЛІВО: бар-чарт топ-15 ASIN за sent ----
        with aL:
            st.markdown(f"#### {R['asin_chart_title']}")
            top = by_asin.sort_values('sent', ascending=False).head(15)
            figa = px.bar(top, x="sent", y="asin", orientation="h",
                          color="sent",
                          color_continuous_scale=['#7c9fff', '#64c896'])
            figa.update_layout(
                height=max(300, 26 * len(top)), template=theme['template'],
                paper_bgcolor=theme['paper_bg'], plot_bgcolor=theme['plot_bg'],
                showlegend=False, coloraxis_showscale=False,
                margin=dict(l=0, r=0, t=10, b=0),
                yaxis=dict(autorange='reversed', title=None),
                xaxis=dict(title=None))
            figa.update_xaxes(gridcolor=theme['grid'])
            st.plotly_chart(figa, use_container_width=True)

        # ---- ПРАВО: таблиця з клікабельними ASIN ----
        with aR:
            st.markdown(f"#### {R['asin_table_title']}")
            tbl = by_asin.copy()
            # клікабельне посилання на Amazon (US dp)
            tbl['url'] = "https://www.amazon.com/dp/" + tbl['asin'].astype(str)
            tbl = tbl.rename(columns={
                'asin':    R['col_asin'],
                'sent':    R['col_sent'],
                'already': R['col_already'],
                'outside': R['col_outside'],
                'failed':  R['col_failed'],
            })
            st.dataframe(
                tbl,
                use_container_width=True,
                height=max(320, 36 * min(len(tbl), 12)),
                hide_index=True,
                column_config={
                    "url": st.column_config.LinkColumn(
                        R['col_link'], display_text="🔗 Amazon"
                    ),
                    R['col_asin']: st.column_config.TextColumn(R['col_asin']),
                },
            )

        # ---- 🆕 ЗАХИСНИЙ СИГНАЛ: розсилка vs топова негативна тема ----
        neg = _load_top_negative(engine)
        if not neg.empty and not by_asin.empty:
            st.markdown(f"#### {R['risk_title']}")
            st.caption(R['risk_sub'])

            risk = by_asin.merge(neg, on='asin', how='inner')
            risk = risk[risk['sent'] > 0].copy()

            if not risk.empty:
                def _flag(impact):
                    # star_impact відʼємний → що менший, то сильніше тягне рейтинг вниз
                    if impact is None:
                        return "⚪"
                    if impact <= -0.3:  return "🔴"   # сильно тягне вниз
                    if impact <= -0.1:  return "🟡"   # помітно
                    return "🟢"                        # слабкий вплив
                risk['flag'] = risk['star_impact'].apply(_flag)
                # сортуємо: спершу найшкідливіші теми (найменший star_impact)
                risk = risk.sort_values('star_impact', ascending=True, na_position='last')

                rt = risk[['flag', 'asin', 'sent', 'top_topic', 'topic_pct', 'star_impact']].copy()
                rt['url'] = "https://www.amazon.com/dp/" + rt['asin'].astype(str)
                rt = rt.rename(columns={
                    'flag':       R['risk_flag'],
                    'asin':       R['col_asin'],
                    'sent':       R['col_sent'],
                    'top_topic':  R['risk_topic'],
                    'topic_pct':  R['risk_pct'],
                    'star_impact': R['risk_impact'],
                })
                st.dataframe(
                    rt,
                    use_container_width=True,
                    height=max(240, 36 * min(len(rt), 12)),
                    hide_index=True,
                    column_config={
                        R['risk_pct']:    st.column_config.NumberColumn(format="%.0f%%"),
                        R['risk_impact']: st.column_config.NumberColumn(format="%.2f ★"),
                        "url": st.column_config.LinkColumn(R['col_link'], display_text="🔗"),
                        R['col_asin']: st.column_config.TextColumn(R['col_asin']),
                        R['risk_topic']: st.column_config.TextColumn(R['risk_topic'], width="medium"),
                    },
                )
                n_red = int((risk['star_impact'] <= -0.3).sum())
                if n_red > 0:
                    st.warning(R['risk_warn'].format(n=n_red))

    # ---- COVERAGE CONTROL (по дате заказа) ----
    cov = _load_coverage(engine, 30)
    if not cov.empty:
        st.divider()
        st.markdown(f"### {R['cov_title']}")

        cL, cR = st.columns([3, 1])

        with cL:
            disp = cov.copy()
            disp['day'] = pd.to_datetime(disp['day']).dt.strftime('%d.%m.%Y')

            def _status(c):
                if c is None or pd.isna(c):
                    return "⚪ —"
                if c >= 90:  return "🟢 OK"
                if c >= 80:  return "🟡 " + R['cov_warn_lbl']
                return "🔴 " + R['cov_prob_lbl']
            disp['status'] = disp['coverage'].apply(_status)

            def _comment(c):
                if c is None or pd.isna(c):
                    return "—"
                if c >= 92:  return R['cov_c_high']
                if c >= 90:  return R['cov_c_norm']
                if c >= 80:  return R['cov_c_below']
                return R['cov_c_crit']
            disp['comment'] = disp['coverage'].apply(_comment)

            disp = disp[['day', 'orders', 'sent', 'already', 'errors',
                         'coverage', 'unprocessed', 'status', 'comment']]
            disp = disp.rename(columns={
                'day':         R['cov_date'],
                'orders':      R['cov_orders'],
                'sent':        R['cov_sent'],
                'already':     R['col_already'],
                'errors':      R['cov_errors'],
                'coverage':    R['cov_pct'],
                'unprocessed': R['cov_unproc'],
                'status':      R['cov_status'],
                'comment':     R['cov_comment'],
            })
            st.dataframe(
                disp, use_container_width=True, hide_index=True,
                height=max(320, 36 * min(len(disp), 16)),
                column_config={
                    R['cov_pct']: st.column_config.NumberColumn(format="%.1f%%"),
                },
            )

        with cR:
            st.markdown(f"**{R['cov_legend']}**")
            st.markdown(
                f"🟢 **OK** (≥90%) — {R['cov_leg_ok']}\n\n"
                f"🟡 **{R['cov_warn_lbl']}** (80–89.9%) — {R['cov_leg_warn']}\n\n"
                f"🔴 **{R['cov_prob_lbl']}** (<80%) — {R['cov_leg_prob']}"
            )
            st.caption(
                f"**{R['cov_about']}**\n\n"
                f"`Coverage % = (Sent + Already) / Orders × 100`\n\n"
                f"`{R['cov_unproc']} = Orders − (Sent + Already)`"
            ) 
