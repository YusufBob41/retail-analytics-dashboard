import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components
from mlxtend.frequent_patterns import apriori, association_rules
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
@@ -529,41 +528,20 @@ def load_dashboard_data():
st.markdown("---")
st.header("Power BI Report")

POWER_BI_IMAGE_CANDIDATES = (
    "assets/powerbi-report.png",
    "powerbi-report.png",
)
power_bi_image_path = next(
    (path for path in POWER_BI_IMAGE_CANDIDATES if os.path.exists(path)),
    (
        path
        for path in ("assets/powerbi-report.png", "powerbi-report.png")
        if os.path.exists(path)
    ),
None,
)
power_bi_share_url = get_secret_or_env("POWER_BI_SHARE_URL")
default_embed_url = get_secret_or_env("POWER_BI_EMBED_URL") or ""
power_bi_embed_url = st.text_input(
    "Power BI embed URL (optional)",
    value=default_embed_url,
    help="Paste the embed URL you get from 'Publish to web' or 'Embed in website/portal'.",
)

if power_bi_embed_url.strip():
    components.iframe(power_bi_embed_url.strip(), height=700, scrolling=True)
elif power_bi_image_path:
if power_bi_image_path:
st.image(
power_bi_image_path,
        caption="Power BI dashboard (static export)",
        caption="Power BI dashboard",
use_container_width=True,
)
    if power_bi_share_url:
        st.link_button("Open Power BI report in a new tab", power_bi_share_url)
else:
    if power_bi_share_url:
        st.info(
            "This share link cannot be opened inside an iframe (app.powerbi.com refused to connect). "
            "You can open the report in a new tab using the button below, or paste an embed URL to display it here."
        )
        st.link_button("Open Power BI report in a new tab", power_bi_share_url)
    else:
        st.info(
            "Add `assets/powerbi-report.png` to show a static Power BI export, "
            "or set `POWER_BI_EMBED_URL` / `POWER_BI_SHARE_URL` in secrets."
        )
    st.info("Power BI report image not found. Add `assets/powerbi-report.png` to the project.")
