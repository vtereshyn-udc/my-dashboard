import streamlit as st

st.set_page_config(
    page_title="UDC BI Dashboard",
    page_icon="📊",
    layout="wide",
)

st.title("📊 UDC Parts BI Dashboard")

st.markdown("""
## Welcome

Choose a dashboard from the sidebar ←

- 📈 **Amazon Dashboard** — Sales & Traffic analytics for  and other Amazon UDC Parts LLC
- 🏪 **Walmart Dashboard** — Walmart Marketplace data for UDC Parts LLC

Data is updated automatically twice a day via ETL pipeline.
""")

st.divider()
st.caption("Data source: PostgreSQL on Heroku · Last sync visible in each dashboard")
