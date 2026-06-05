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
from plotly.subplots import make_subplots
from sqlalchemy import text
from datetime import datetime, timedelta


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
        "cov_warn_lbl": "Attention", "cov_prob_lbl": "Low coverage",
        "cov_legend": "Status legend",
        "cov_leg_ok": "coverage at target", "cov_leg_warn": "coverage below target",
        "cov_leg_prob": "coverage below the target", "cov_about": "About the calculation", "cov_leg_ok2": "All good — requests went out, nothing to do.", "cov_leg_prob2": "Below target. For dates still within the 30-day window the requests will be sent automatically on the next run. For dates older than 30 days the window has closed and reviews are lost (see Missed orders).", "cov_leg_mat2": "Order is too fresh (under ~8 days) — the 5–30 day window hasn't opened yet. Normal, will be covered automatically.",
        "cov_c_high": "High coverage", "cov_c_norm": "Within norm",
        "cov_c_below": "Coverage below target", "cov_c_crit": "Coverage below target — resend requests",
        "flt_period": "📅 Order period", "flt_threshold": "Coverage threshold", "flt_status": "Status",
        "flt_all": "All", "kpi_orders": "🛒 Orders in period",
        "combo_title": "📊 Orders vs Requests by order date", "combo_processed": "Processed (Sent + Already)",
        "cov_note": "ℹ️ Requests can only be sent when an order is 5–30 days old. Recent dates (under ~8 days) show ⏳ Maturing — that's normal: coverage there isn't possible yet. 🔴 Low coverage marks dates whose window has already passed where requests should be resent. Increasing send frequency won't speed this up.",
        "cov_maturing": "Maturing", "cov_c_maturing": "Still within/before window", "cov_total": "▦ TOTAL", "cov_total_note": "matured dates only (excl. ⏳)",
        "cov_leg_maturing": "order too recent — wait for the send window",
        "guide_title": "📖 Guide: how to use this monitor",
        "missed_title": "💸 Missed orders (lost reviews)",
        "missed_sub": "Orders whose 5–30 day window has fully passed with NO request sent — permanently lost review chances.",
        "missed_lbl": "Missed", "missed_total": "Missed (lost)", "missed_pct_lbl": "% of orders", "missed_note": "Counted only over days when the system was active (pre-launch days are greyed out).",
        "missed_none": "✅ No missed orders — the window is fully covered.",
        "heat_title": "🗓️ Coverage heatmap (weekday × week)",
        "heat_sub": "Coverage % by day. Spot weak spots — e.g. weekends or specific days dropping.",
        "heat_none": "⚠️ Not enough matured data for the heatmap yet.",
        "heat_dow": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "guide_md": """
**What this page is**

A monitor for the automated review-request mailing (Amazon "Request a Review"). The system sends requests once a day for eligible orders. This page shows how it's doing.

**The 5–30 day window rule**

Amazon only allows a request when an order is 5–30 days old. Recent orders aren't processed yet — that's normal, they're "maturing".

**Reading the blocks top to bottom:**

1. **Filters** — order period, coverage threshold, status filter.
2. **KPI cards** — period summary: orders, sent, already, coverage %, errors.
3. **Orders vs Requests** — blue bars = all orders, teal = processed, purple line = coverage %. Dotted = threshold.
4. **Coverage control** — table by order date. Statuses:
   - 🟢 **OK** (≥90%) — coverage on target.
   - 🟡 **Attention** — slightly below target.
   - 🔴 **Low coverage** — window passed but coverage low → look into it / resend.
   - ⏳ **Maturing** — order too recent, coverage not possible yet. Normal.
5. **Daily volume** — sends by status, by send date.
6. **By ASIN** — which products got requests (7/14/30 days) + Amazon links.
7. **Safety signal** — top negative topic per ASIN.

**FAQ:**

- *Why are recent dates red/zero?* — Orders aren't in the 5–30 day window yet. They'll turn green on their own.
- *Should I send more than once a day?* — No. Orders can't be processed before the window regardless.
- *Is "Already" bad?* — No. The request was sent earlier; Amazon declined the duplicate. Normal.
""",
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
        "cov_warn_lbl": "Увага", "cov_prob_lbl": "Низьке покриття",
        "cov_legend": "Легенда статусів",
        "cov_leg_ok": "покриття на цільовому рівні", "cov_leg_warn": "покриття нижче цілі",
        "cov_leg_prob": "покриття нижче цілі", "cov_about": "Про розрахунок покриття", "cov_leg_ok2": "Усе добре — запити пішли, нічого робити не треба.", "cov_leg_prob2": "Нижче цілі. Для дат у межах 30 днів запити дошлються автоматично наступного прогону. Для дат, старших за 30 днів, вікно закрилось — відгуки втрачені (див. Упущені).", "cov_leg_mat2": "Замовлення надто свіже (молодше ~8 днів) — вікно 5–30 днів ще не відкрилось. Це норма, покриється автоматично.",
        "cov_c_high": "Високе покриття", "cov_c_norm": "У межах норми",
        "cov_c_below": "Покриття нижче цілі", "cov_c_crit": "Покриття нижче цілі — дослати запити",
        "flt_period": "📅 Період замовлення", "flt_threshold": "Поріг покриття", "flt_status": "Статус",
        "flt_all": "Усі", "kpi_orders": "🛒 Orders у періоді",
        "combo_title": "📊 Orders vs Requests по датах замовлення", "combo_processed": "Оброблено (Sent + Already)",
        "cov_note": "ℹ️ Запит можна відправити лише коли замовленню 5–30 днів. Свіжі дати (молодші ~8 днів) показують ⏳ Зріє — це норма: покриття там ще неможливе. 🔴 Низьке покриття позначає дати з уже минулим вікном, де варто дослати запити. Збільшення частоти відправки це НЕ прискорить.",
        "cov_maturing": "Зріє", "cov_c_maturing": "Ще у вікні / до вікна", "cov_total": "▦ РАЗОМ", "cov_total_note": "лише дозрілі дати (без ⏳)",
        "cov_leg_maturing": "замовлення надто свіже — чекаємо вікно відправки",
        "guide_title": "📖 Інструкція: як користуватися цим монітором",
        "missed_title": "💸 Упущені замовлення (втрачені відгуки)",
        "missed_sub": "Замовлення, у яких вікно 5–30 днів повністю минуло БЕЗ відправки запиту — безповоротно втрачені шанси на відгук.",
        "missed_lbl": "Упущено", "missed_total": "Упущено (втрачено)", "missed_pct_lbl": "% замовлень", "missed_note": "Рахується лише по днях, коли система працювала (доба до запуску — сірим).",
        "missed_none": "✅ Упущених немає — вікно повністю покрите.",
        "heat_title": "🗓️ Heatmap покриття (день × тиждень)",
        "heat_sub": "% покриття по днях. Лови слабкі місця — напр. вихідні чи певні дні просідають.",
        "heat_none": "⚠️ Ще замало дозрілих даних для heatmap.",
        "heat_dow": ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"],
        "guide_md": """
**Що це за сторінка**

Це монітор автоматичної розсилки запитів на відгук (Amazon «Request a Review»). Система раз на день сама надсилає покупцям запити по підходящих замовленнях. Тут видно, як вона працює.

**Головне правило вікна 5–30 днів**

Amazon дозволяє надіслати запит лише коли замовленню від 5 до 30 днів. Раніше не можна, пізніше — пізно. Тому свіжі замовлення ще не оброблені — це норма, вони «зріють».

**Як читати блоки згори вниз:**

1. **Фільтри** — період замовлення, поріг покриття і фільтр за статусом.
2. **KPI-картки** — зведення за період: замовлень, надіслано, already, % покриття, помилок.
3. **Orders vs Requests** — сині стовпчики це всі замовлення, бірюзові — оброблені, фіолетова лінія — % покриття. Пунктир — твій поріг.
4. **Контроль покриття** — таблиця по датах замовлення. Статуси:
   - 🟢 **OK** (≥90%) — покриття в нормі.
   - 🟡 **Увага** — трохи нижче цілі.
   - 🔴 **Низьке покриття** — вікно вже минуло, а покриття низьке → варто дослати.
   - ⏳ **Зріє** — замовлення надто свіже, покриття ще неможливе. Це норма.
5. **Обсяг по днях** — відправки по статусах за датою відправки.
6. **По ASIN** — по яких товарах йшли запити (7/14/30 днів) + посилання на Amazon.
7. **Захисний сигнал** — топова негативна тема по ASIN.

**Часті питання:**

- *Чому свіжі дати червоні/нульові?* — Замовлення ще не у вікні 5–30 днів. Зачекай — стануть зеленими.
- *Чи треба слати частіше разу на день?* — Ні. До вікна замовлення все одно не обробити.
- *Already — це погано?* — Ні. Запит уже слали раніше, Amazon відхилив дубль. Норма.
""",
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
        "cov_warn_lbl": "Внимание", "cov_prob_lbl": "Низкое покрытие",
        "cov_legend": "Легенда статусов",
        "cov_leg_ok": "покрытие на целевом уровне", "cov_leg_warn": "покрытие ниже цели",
        "cov_leg_prob": "покрытие ниже цели", "cov_about": "О расчёте покрытия", "cov_leg_ok2": "Всё хорошо — запросы ушли, делать ничего не нужно.", "cov_leg_prob2": "Ниже цели. Для дат в пределах 30 дней запросы дошлются автоматически в следующем прогоне. Для дат старше 30 дней окно закрылось — отзывы потеряны (см. Упущенные).", "cov_leg_mat2": "Заказ слишком свежий (моложе ~8 дней) — окно 5–30 дней ещё не открылось. Это норма, покроется автоматически.",
        "cov_c_high": "Высокое покрытие", "cov_c_norm": "В пределах нормы",
        "cov_c_below": "Покрытие ниже цели", "cov_c_crit": "Покрытие ниже цели — дослать запросы",
        "flt_period": "📅 Период заказа", "flt_threshold": "Порог покрытия", "flt_status": "Статус",
        "flt_all": "Все", "kpi_orders": "🛒 Orders в периоде",
        "combo_title": "📊 Orders vs Requests по датам заказа", "combo_processed": "Обработано (Sent + Already)",
        "cov_note": "ℹ️ Запрос можно отправить только когда заказу 5–30 дней. Свежие даты (моложе ~8 дней) показывают ⏳ Зреет — это норма: покрытие там ещё невозможно. 🔴 Низкое покрытие отмечает даты с уже прошедшим окном, где стоит дослать запросы. Увеличение частоты отправки это НЕ ускорит.",
        "cov_maturing": "Зреет", "cov_c_maturing": "Ещё в окне / до окна", "cov_total": "▦ ИТОГО", "cov_total_note": "только дозревшие даты (без ⏳)",
        "cov_leg_maturing": "заказ слишком свежий — ждём окно отправки",
        "guide_title": "📖 Инструкция: как пользоваться этим монитором",
        "missed_title": "💸 Упущенные заказы (потерянные отзывы)",
        "missed_sub": "Заказы, у которых окно 5–30 дней полностью прошло БЕЗ отправки запроса — безвозвратно потерянные шансы на отзыв.",
        "missed_lbl": "Упущено", "missed_total": "Упущено (потеряно)", "missed_pct_lbl": "% заказов", "missed_note": "Считается только по дням, когда система работала (дни до запуска — серым).",
        "missed_none": "✅ Упущенных нет — окно полностью покрыто.",
        "heat_title": "🗓️ Heatmap покрытия (день × неделя)",
        "heat_sub": "% покрытия по дням. Лови слабые места — напр. выходные или отдельные дни проседают.",
        "heat_none": "⚠️ Пока мало дозревших данных для heatmap.",
        "heat_dow": ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"],
        "guide_md": """
**Что это за страница**

Это монитор автоматической рассылки запросов на отзыв (Amazon «Request a Review»). Система раз в день сама отправляет покупателям запросы на отзыв по подходящим заказам. Здесь видно, как она работает.

**Главное правило окна 5–30 дней**

Amazon разрешает отправлять запрос только когда заказу от 5 до 30 дней. Раньше нельзя, позже — поздно. Поэтому свежие заказы (последние ~дни) ещё не обработаны — это нормально, они «зреют».

**Как читать блоки сверху вниз:**

1. **Фильтры** — период заказа, порог покрытия и фильтр по статусу. Меняй период, чтобы смотреть нужный диапазон.
2. **KPI-карточки** — сводка за выбранный период: заказов, отправлено, already, % покрытия, ошибок.
3. **Orders vs Requests** — синие столбики это все заказы, бирюзовые — обработанные, фиолетовая линия — % покрытия. Пунктир — твой порог.
4. **Контроль покрытия** — таблица по датам заказа. Статусы:
   - 🟢 **OK** (≥90%) — покрытие в норме.
   - 🟡 **Внимание** — покрытие чуть ниже цели.
   - 🔴 **Низкое покрытие** — окно уже прошло, а покрытие низкое → стоит разобраться/дослать.
   - ⏳ **Зреет** — заказ слишком свежий, покрытие ещё физически невозможно. Это норма, не ошибка.
5. **Объём по дням** — отправки по статусам (sent / already / outside / failed) по дате отправки.
6. **По ASIN** — по каким товарам шли запросы (переключатель 7/14/30 дней) + ссылки на Amazon.
7. **Защитный сигнал** — топовая негативная тема по ASIN. Подсказывает, по каким товарам осторожнее с рассылкой.

**Частые вопросы:**

- *Почему свежие даты красные/нулевые?* — Заказы ещё не вошли в окно 5–30 дней. Подожди — станут зелёными сами.
- *Надо ли слать чаще раза в день?* — Нет. Раньше окна заказ всё равно не обработать, частота ничего не ускорит.
- *Already — это плохо?* — Нет. Значит запрос по заказу уже слали раньше, Amazon отклонил дубль. Это нормально.
""",
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
def _load_coverage(_engine, date_from, date_to) -> pd.DataFrame:
    """
    🆕 Контроль покриття request review ПО ДАТІ ЗАМОВЛЕННЯ (purchase_date),
    у межах [date_from, date_to].
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
              AND o.purchase_date::date BETWEEN :df AND :dt
            GROUP BY o.purchase_date::date
        ),
        lg AS (
            SELECT o.purchase_date::date AS day,
                   COUNT(DISTINCT l.amazon_order_id) FILTER (WHERE l.status='sent')             AS sent,
                   COUNT(DISTINCT l.amazon_order_id) FILTER (WHERE l.status='already_reviewed') AS already,
                   COUNT(DISTINCT l.amazon_order_id) FILTER (WHERE l.status='failed')           AS errors
            FROM public.review_request_log l
            JOIN spapi.all_orders o ON o.amazon_order_id = l.amazon_order_id
            WHERE o.purchase_date::date BETWEEN :df AND :dt
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
        df = pd.read_sql(q, conn, params={"df": date_from, "dt": date_to})
    if df.empty:
        return df
    df['covered']     = df['sent'] + df['already']
    df['unprocessed'] = (df['orders'] - df['covered']).clip(lower=0)
    df['coverage']    = (df['covered'] / df['orders'].replace(0, pd.NA) * 100).round(1)
    return df


@st.cache_data(ttl=900)
def _load_missed(_engine, days_back: int = 60) -> pd.DataFrame:
    """
    🆕 #2 УПУЩЕНІ замовлення: вікно (5-30 днів) ВЖЕ МИНУЛО,
    а запит так і не пішов (немає sent/already в логу).

    'has_activity' = чи система ВЗАГАЛІ працювала по цьому дню (були спроби
    sent/already/outside/failed). Якщо 0 активності — це доба ДО запуску
    системи, її НЕ рахуємо в чесний підсумок втрат.
    """
    q = text("""
        SELECT o.purchase_date::date AS day,
               COUNT(DISTINCT o.amazon_order_id) AS orders,
               COUNT(DISTINCT o.amazon_order_id) FILTER (
                   WHERE NOT EXISTS (
                       SELECT 1 FROM public.review_request_log l
                       WHERE l.amazon_order_id = o.amazon_order_id
                         AND l.status IN ('sent','already_reviewed')
                   )
               ) AS missed,
               COUNT(DISTINCT l2.amazon_order_id) AS any_activity
        FROM spapi.all_orders o
        LEFT JOIN public.review_request_log l2
               ON l2.amazon_order_id = o.amazon_order_id
        WHERE o.order_status = 'Shipped'
          AND o.purchase_date::date <  NOW()::date - INTERVAL '30 days'
          AND o.purchase_date::date >= NOW()::date - (:days || ' days')::interval
        GROUP BY o.purchase_date::date
        ORDER BY o.purchase_date::date
    """)
    with _engine.connect() as conn:
        df = pd.read_sql(q, conn, params={"days": days_back})
    return df


@st.cache_data(ttl=900)
def _load_heatmap(_engine, weeks_back: int = 8) -> pd.DataFrame:
    """
    🆕 #3 Heatmap покриття: % покриття по (тиждень × день тижня).
    Тільки «дозрілі» дати (старші 8 днів), щоб не показувати незрілі як провал.
    """
    q = text("""
        WITH ord AS (
            SELECT o.purchase_date::date AS day,
                   COUNT(DISTINCT o.amazon_order_id) AS orders
            FROM spapi.all_orders o
            WHERE o.order_status = 'Shipped'
              AND o.purchase_date::date <  NOW()::date - INTERVAL '8 days'
              AND o.purchase_date::date >= NOW()::date - (:wk * 7 || ' days')::interval
            GROUP BY o.purchase_date::date
        ),
        cov AS (
            SELECT o.purchase_date::date AS day,
                   COUNT(DISTINCT l.amazon_order_id) FILTER (
                       WHERE l.status IN ('sent','already_reviewed')
                   ) AS covered
            FROM public.review_request_log l
            JOIN spapi.all_orders o ON o.amazon_order_id = l.amazon_order_id
            WHERE o.purchase_date::date <  NOW()::date - INTERVAL '8 days'
              AND o.purchase_date::date >= NOW()::date - (:wk * 7 || ' days')::interval
            GROUP BY o.purchase_date::date
        )
        SELECT ord.day,
               ord.orders,
               COALESCE(cov.covered, 0) AS covered
        FROM ord LEFT JOIN cov ON cov.day = ord.day
        ORDER BY ord.day
    """)
    with _engine.connect() as conn:
        df = pd.read_sql(q, conn, params={"wk": weeks_back})
    if df.empty:
        return df
    df['day']      = pd.to_datetime(df['day'])
    df['coverage'] = (df['covered'] / df['orders'].replace(0, pd.NA) * 100).round(0)
    df['dow']      = df['day'].dt.dayofweek          # 0=Пн
    df['week']     = df['day'].dt.strftime('%d.%m')  # підпис тижня (поч. дня)
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
    with st.expander(R['guide_title']):
        st.markdown(R['guide_md'])
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

    # ---- 🆕 ФІЛЬТРИ (період / поріг / статус) ----
    fa, fb, fc = st.columns([2, 1, 1])
    with fa:
        default_from = (datetime.now().date() - timedelta(days=30))
        default_to   = datetime.now().date()
        date_range = st.date_input(
            R['flt_period'],
            value=(default_from, default_to),
            key="cov_date_range",
        )
        if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
            d_from, d_to = date_range
        else:
            d_from, d_to = default_from, default_to
    with fb:
        threshold = st.selectbox(R['flt_threshold'], [90, 85, 80, 75, 70], index=2)
    with fc:
        status_opt = st.selectbox(
            R['flt_status'],
            [R['flt_all'], "🟢 OK",
             "🔴 " + R['cov_prob_lbl'], "⏳ " + R['cov_maturing']],
        )

    cov = _load_coverage(engine, d_from, d_to)

    # ---- 🆕 KPI ПОКРИТТЯ (по обраному періоду) ----
    if not cov.empty:
        tot_orders  = int(cov['orders'].sum())
        tot_sent    = int(cov['sent'].sum())
        tot_already = int(cov['already'].sum())
        tot_errors  = int(cov['errors'].sum())
        tot_cov     = (cov['covered'].sum() / tot_orders * 100) if tot_orders else 0.0

        k1, k2, k3, k4, k5, k6 = st.columns(6)
        k1.metric(R['kpi_orders'],   f"{tot_orders:,}")
        k2.metric(R['cov_sent'],     f"{tot_sent:,}")
        k3.metric(R['col_already'],  f"{tot_already:,}")
        k4.metric(R['cov_pct'],      f"{tot_cov:.1f}%")
        k5.metric(R['cov_errors'],   f"{tot_errors:,}", delta_color="inverse")
        last_str = kpi['last_sent'].strftime('%d.%m %H:%M') if kpi['last_sent'] else "—"
        k6.metric(R['kpi_last'], last_str)

    st.divider()

    # ---- 🆕 ГРАФІК Orders vs Requests + Coverage % лінія ----
    if not cov.empty:
        st.markdown(f"### {R['combo_title']}")
        cc = cov.sort_values('day').copy()
        cc['day_str'] = pd.to_datetime(cc['day']).dt.strftime('%d.%m')
        figc = make_subplots(specs=[[{"secondary_y": True}]])
        figc.add_trace(go.Bar(name=R['kpi_orders'], x=cc['day_str'], y=cc['orders'],
                              marker_color='#3b5bdb'), secondary_y=False)
        figc.add_trace(go.Bar(name=R['combo_processed'], x=cc['day_str'], y=cc['covered'],
                              marker_color='#22b8cf'), secondary_y=False)
        figc.add_trace(go.Scatter(name=R['cov_pct'], x=cc['day_str'], y=cc['coverage'],
                              mode='lines+markers', line=dict(color='#cc5de8', width=2)),
                       secondary_y=True)
        # лінія порогу
        figc.add_hline(y=threshold, line_dash="dot", line_color="#ffd43b",
                       secondary_y=True, opacity=0.6)
        figc.update_layout(
            barmode='group', height=380, template=theme['template'],
            paper_bgcolor=theme['paper_bg'], plot_bgcolor=theme['plot_bg'],
            margin=dict(l=0, r=0, t=10, b=0), hovermode='x unified',
            legend=dict(orientation="h", y=1.1))
        figc.update_xaxes(gridcolor=theme['grid'])
        figc.update_yaxes(gridcolor=theme['grid'], secondary_y=False)
        figc.update_yaxes(range=[0, 105], secondary_y=True, ticksuffix="%", showgrid=False)
        st.plotly_chart(figc, use_container_width=True)

    st.divider()

    # ---- COVERAGE CONTROL (по дате заказа) ----
    if not cov.empty:
        st.markdown(f"### {R['cov_title']}")
        st.info(R['cov_note'])

        cL, cR = st.columns([3, 1])

        with cL:
            disp = cov.copy()
            # 🆕 вік замовлення в днях (вікно відправки Amazon = 5-30 днів)
            today = pd.Timestamp(datetime.now().date())
            disp['age_days'] = (today - pd.to_datetime(disp['day'])).dt.days

            def _status(row):
                c = row['coverage']
                age = row['age_days']
                # дата ще не «дозріла»: молодша 8 днів → покриття фізично неможливе
                if age < 8:
                    return "⏳ " + R['cov_maturing']
                if c is None or pd.isna(c):
                    return "⚪ —"
                if c >= threshold:    return "🟢 OK"
                return "🔴 " + R['cov_prob_lbl']
            disp['status'] = disp.apply(_status, axis=1)

            def _comment(row):
                c = row['coverage']
                age = row['age_days']
                if age < 8:
                    return R['cov_c_maturing']   # ще у вікні / не дозріло
                if c is None or pd.isna(c):
                    return "—"
                if c >= 95:         return R['cov_c_high']
                if c >= threshold:  return R['cov_c_norm']
                return R['cov_c_crit']
            disp['comment'] = disp.apply(_comment, axis=1)

            # 🆕 фільтр по статусу
            if status_opt != R['flt_all']:
                disp = disp[disp['status'].str.startswith(status_opt.split()[0])]

            disp['day'] = pd.to_datetime(disp['day']).dt.strftime('%d.%m.%Y')
            disp = disp[['day', 'orders', 'sent', 'already', 'errors',
                         'coverage', 'unprocessed', 'status', 'comment']]

            # 🆕 ИТОГОВАЯ строка — считаем ТОЛЬКО дозревшие даты (без ⏳ «Зреет»),
            #    иначе нули незрелых дней занижают общий % (60% вместо реальных ~96%).
            matured = disp[~disp['status'].str.startswith("⏳")]
            t_orders = int(matured['orders'].sum())
            t_sent   = int(matured['sent'].sum())
            t_alr    = int(matured['already'].sum())
            t_err    = int(matured['errors'].sum())
            t_unproc = int(matured['unprocessed'].sum())
            t_cov    = round((t_sent + t_alr) / t_orders * 100, 1) if t_orders else 0.0

            # 🆕 ПЛАШКА с итоговыми KPI над таблицей
            p1, p2, p3, p4, p5 = st.columns(5)
            p1.metric(R['cov_orders'],  f"{t_orders:,}")
            p2.metric(R['cov_sent'],    f"{t_sent:,}")
            p3.metric(R['cov_pct'],     f"{t_cov:.1f}%")
            p4.metric(R['cov_unproc'],  f"{t_unproc:,}")
            p5.metric(R['cov_errors'],  f"{t_err:,}", delta_color="inverse")
            st.caption(R['cov_total_note'])

            total_row = pd.DataFrame([{
                'day': R['cov_total'], 'orders': t_orders, 'sent': t_sent,
                'already': t_alr, 'errors': t_err, 'coverage': t_cov,
                'unprocessed': t_unproc, 'status': '', 'comment': R['cov_total_note'],
            }])
            disp = pd.concat([total_row, disp], ignore_index=True)

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

            # 🆕 підсвічуємо рядок ИТОГО (перший) фоном + жирним + контрастний текст
            is_light = theme['bg'] == "#f5f7fa"
            hl_bg   = "#dbe4ff" if is_light else "#3b4a82"
            hl_text = "#1e293b" if is_light else "#ffffff"
            def _hl_total(row):
                if row.name == 0:   # перший рядок = ИТОГО
                    return [f'background-color: {hl_bg}; color: {hl_text}; font-weight: 700;'] * len(row)
                return [''] * len(row)
            styler = disp.style.apply(_hl_total, axis=1).format({R['cov_pct']: "{:.1f}%"})

            st.dataframe(
                styler, use_container_width=True, hide_index=True,
                height=max(320, 36 * min(len(disp), 16)),
            )

        with cR:
            st.markdown(f"**{R['cov_legend']}**")
            st.markdown(
                f"🟢 **OK** (≥{threshold}%)\n\n"
                f"<span style='opacity:.75'>{R['cov_leg_ok2']}</span>\n\n"
                f"🔴 **{R['cov_prob_lbl']}** (<{threshold}%)\n\n"
                f"<span style='opacity:.75'>{R['cov_leg_prob2']}</span>\n\n"
                f"⏳ **{R['cov_maturing']}**\n\n"
                f"<span style='opacity:.75'>{R['cov_leg_mat2']}</span>",
                unsafe_allow_html=True,
            )
            st.caption(
                f"**{R['cov_about']}**\n\n"
                f"`Coverage % = (Sent + Already) / Orders × 100`\n\n"
                f"`{R['cov_unproc']} = Orders − (Sent + Already)`"
            )

    st.divider()

    # ---- 🆕 #2 УПУЩЕННЫЕ ЗАКАЗЫ (потери) + #3 HEATMAP ----
    missed = _load_missed(engine, 60)
    heat   = _load_heatmap(engine, 8)

    mL, mR = st.columns(2)

    with mL:
        st.markdown(f"### {R['missed_title']}")
        st.caption(R['missed_sub'])
        if not missed.empty and missed['missed'].sum() > 0:
            md = missed.copy()
            md['day_dt'] = pd.to_datetime(md['day'])
            md['day'] = md['day_dt'].dt.strftime('%d.%m')
            # 🆕 день вважається «робочим», якщо система мала хоч якусь активність
            md['active'] = md['any_activity'] > 0
            bar_colors = ['#e8590c' if a else '#adb5bd' for a in md['active']]

            figm = go.Figure()
            figm.add_trace(go.Bar(x=md['day'], y=md['missed'],
                                  marker_color=bar_colors, name=R['missed_lbl']))
            figm.update_layout(
                height=320, template=theme['template'],
                paper_bgcolor=theme['paper_bg'], plot_bgcolor=theme['plot_bg'],
                margin=dict(l=0, r=0, t=10, b=0), showlegend=False)
            figm.update_xaxes(gridcolor=theme['grid'])
            figm.update_yaxes(gridcolor=theme['grid'])
            st.plotly_chart(figm, use_container_width=True)

            # 🆕 ЧЕСНИЙ ітог: лише дні, коли система ПРАЦЮВАЛА (active)
            act = md[md['active']]
            total_missed = int(act['missed'].sum())
            total_ord    = int(act['orders'].sum())
            pct = (total_missed / total_ord * 100) if total_ord else 0
            mm1, mm2 = st.columns(2)
            mm1.metric(R['missed_total'], f"{total_missed:,}")
            mm2.metric(R['missed_pct_lbl'], f"{pct:.1f}%")
            st.caption(R['missed_note'])
        else:
            st.success(R['missed_none'])

    with mR:
        st.markdown(f"### {R['heat_title']}")
        st.caption(R['heat_sub'])
        if not heat.empty:
            dow_names = R['heat_dow']  # список 7 коротких назв (Пн..Вс)
            piv = heat.pivot_table(index='dow', columns='week',
                                   values='coverage', aggfunc='mean')
            piv = piv.reindex(range(7))
            figh = go.Figure(data=go.Heatmap(
                z=piv.values,
                x=list(piv.columns),
                y=[dow_names[i] for i in piv.index],
                colorscale=[[0, '#e03131'], [0.8, '#ffd43b'], [1, '#2f9e44']],
                zmin=0, zmax=100,
                colorbar=dict(title="%", ticksuffix="%"),
                hovertemplate="%{y} · %{x}<br>%{z:.0f}%<extra></extra>"))
            figh.update_layout(
                height=320, template=theme['template'],
                paper_bgcolor=theme['paper_bg'], plot_bgcolor=theme['plot_bg'],
                margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(figh, use_container_width=True)
        else:
            st.info(R['heat_none'])

    st.divider()

    # ---- DAILY VOLUME (stacked bars, по даті відправки) ----
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
