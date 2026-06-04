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
        "risk_title": "🛡️ Sending vs negative trend (safety signal)",
        "risk_sub": "Negative-topic share per ASIN (from Customer Feedback). If negativity is rising — better not to push review requests for that ASIN (you'd be inviting unhappy buyers).",
        "risk_flag": "Flag", "risk_now": "Neg now", "risk_prev": "Neg prev", "risk_delta": "Δ",
        "risk_warn": "🔴 {n} ASIN(s) with rising negativity — consider pausing requests for them.",
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
        "risk_title": "🛡️ Розсилка vs тренд негативу (захисний сигнал)",
        "risk_sub": "Частка негативних тем по ASIN (з Customer Feedback). Якщо негатив росте — краще НЕ гнати запити на відгук по цьому ASIN (бо кличеш незадоволених покупців).",
        "risk_flag": "Прапор", "risk_now": "Негатив зараз", "risk_prev": "Негатив до", "risk_delta": "Δ",
        "risk_warn": "🔴 {n} ASIN з ростом негативу — варто призупинити запити по них.",
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
        "risk_title": "🛡️ Рассылка vs тренд негатива (защитный сигнал)",
        "risk_sub": "Доля негативных тем по ASIN (из Customer Feedback). Если негатив растёт — лучше НЕ слать запросы на отзыв по этому ASIN (зовёшь недовольных покупателей).",
        "risk_flag": "Флаг", "risk_now": "Негатив сейчас", "risk_prev": "Негатив до", "risk_delta": "Δ",
        "risk_warn": "🔴 {n} ASIN с ростом негатива — стоит приостановить запросы по ним.",
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
def _load_negative_trend(_engine) -> pd.DataFrame:
    """
    🆕 Захисний сигнал: динаміка частки НЕГАТИВНИХ тем по ASIN.
    Customer Feedback API не дає кількості відгуків/рейтингу — лише
    occurrence_pct тем. Беремо найгіршу (max) частку негативу по ASIN
    на ДВОХ останніх знімках (snapshot_date) і рахуємо дельту.

    delta > 0  → негатив РОСТЕ  → НЕ варто гнати розсилку по цьому ASIN
    delta < 0  → негатив падає  → можна слати

    Джерело: reviews.item_trends (sentiment='negative').
    """
    q = text("""
        WITH snaps AS (
            SELECT DISTINCT snapshot_date
            FROM reviews.item_trends
            ORDER BY snapshot_date DESC
            LIMIT 2
        ),
        ranked AS (
            SELECT snapshot_date,
                   ROW_NUMBER() OVER (ORDER BY snapshot_date DESC) AS rn
            FROM snaps
        ),
        agg AS (
            SELECT t.asin,
                   r.rn,
                   MAX(t.asin_occurrence_pct) AS neg_pct
            FROM reviews.item_trends t
            JOIN ranked r ON r.snapshot_date = t.snapshot_date
            WHERE t.sentiment = 'negative'
              AND t.asin_occurrence_pct IS NOT NULL
            GROUP BY t.asin, r.rn
        )
        SELECT
            cur.asin                              AS asin,
            cur.neg_pct                           AS neg_now,
            prev.neg_pct                          AS neg_prev,
            (cur.neg_pct - COALESCE(prev.neg_pct, cur.neg_pct)) AS neg_delta
        FROM agg cur
        LEFT JOIN agg prev ON prev.asin = cur.asin AND prev.rn = 2
        WHERE cur.rn = 1
    """)
    try:
        with _engine.connect() as conn:
            df = pd.read_sql(q, conn)
    except Exception:
        # таблиці reviews.item_trends може не бути / порожня — не валимо сторінку
        df = pd.DataFrame(columns=["asin", "neg_now", "neg_prev", "neg_delta"])
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

        # ---- 🆕 ЗАХИСНИЙ СИГНАЛ: розсилка vs тренд негативу ----
        neg = _load_negative_trend(engine)
        if not neg.empty and not by_asin.empty:
            st.markdown(f"#### {R['risk_title']}")
            st.caption(R['risk_sub'])

            risk = by_asin.merge(neg, on='asin', how='inner')
            risk = risk[risk['sent'] > 0].copy()

            if not risk.empty:
                def _flag(d):
                    if d is None:
                        return "—"
                    if d > 2:   return "🔴"   # негатив помітно росте
                    if d > 0:   return "🟡"   # трохи росте
                    return "🟢"               # падає / стабільно
                risk['flag'] = risk['neg_delta'].apply(_flag)
                risk = risk.sort_values('neg_delta', ascending=False)

                rt = risk[['flag', 'asin', 'sent', 'neg_now', 'neg_prev', 'neg_delta']].copy()
                rt['url'] = "https://www.amazon.com/dp/" + rt['asin'].astype(str)
                rt = rt.rename(columns={
                    'flag':      R['risk_flag'],
                    'asin':      R['col_asin'],
                    'sent':      R['col_sent'],
                    'neg_now':   R['risk_now'],
                    'neg_prev':  R['risk_prev'],
                    'neg_delta': R['risk_delta'],
                })
                st.dataframe(
                    rt,
                    use_container_width=True,
                    height=max(240, 36 * min(len(rt), 10)),
                    hide_index=True,
                    column_config={
                        R['risk_now']:   st.column_config.NumberColumn(format="%.1f%%"),
                        R['risk_prev']:  st.column_config.NumberColumn(format="%.1f%%"),
                        R['risk_delta']: st.column_config.NumberColumn(format="%+.1f pp"),
                        "url": st.column_config.LinkColumn(R['col_link'], display_text="🔗"),
                        R['col_asin']: st.column_config.TextColumn(R['col_asin']),
                    },
                )
                n_red = int((risk['neg_delta'] > 2).sum())
                if n_red > 0:
                    st.warning(R['risk_warn'].format(n=n_red))

    # ---- DAILY TABLE ----
    if not daily.empty:
        st.divider()
        st.markdown(f"### {R['table_title']}")
        t = daily.sort_values('day', ascending=False).copy()
        t['day'] = t['day'].dt.strftime('%Y-%m-%d')
        t = t.rename(columns={
            'day': R['col_day'], 'sent': R['col_sent'], 'already': R['col_already'],
            'outside': R['col_outside'], 'failed': R['col_failed'], 'total': R['col_total'],
        })
        st.dataframe(t, use_container_width=True, height=320)
