import os

import networkx as nx
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from mlxtend.frequent_patterns import apriori, association_rules
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from streamlit.errors import StreamlitSecretNotFoundError

DEFAULT_CSV_PATH = "northwind_data.csv"

COLOR_PRIMARY = "#4C9BE8"
COLOR_ACCENT = "#E8834C"
PLOTLY_TEMPLATE = "plotly_dark"


def styled_metric(label, value):
    st.markdown(
        f"""
        <div style="background:#1E2130;border-radius:10px;padding:16px 20px;border-left:4px solid {COLOR_PRIMARY};">
            <div style="font-size:0.78rem;color:#8B9BB4;text-transform:uppercase;letter-spacing:0.05em;">{label}</div>
            <div style="font-size:1.6rem;font-weight:700;color:#FAFAFA;margin-top:4px;">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def create_network_diagram(rules_df):
    G = nx.DiGraph()
    for _, row in rules_df.iterrows():
        G.add_edge(
            row["antecedents"],
            row["consequents"],
            weight=row["lift"],
            confidence=row["confidence"],
        )

    pos = nx.spring_layout(G, k=2, iterations=50, seed=42)

    edge_x, edge_y = [], []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y, mode="lines",
        line=dict(width=2, color="#444"),
        hoverinfo="none", showlegend=False,
    )

    node_x, node_y, node_text, node_color = [], [], [], []
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_text.append(node)
        node_color.append(G.degree(node))

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode="markers+text",
        text=node_text,
        textposition="top center",
        hoverinfo="text",
        marker=dict(
            size=22, color=node_color, colorscale="Viridis", showscale=True,
            colorbar=dict(thickness=15, title=dict(text="Connections")),
        ),
        showlegend=False,
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
        title="Product Association Network",
        template=PLOTLY_TEMPLATE,
        showlegend=False,
        hovermode="closest",
        height=600,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def create_sunburst(rules_df):
    ids = ["root"]
    labels = ["All Products"]
    parents = [""]
    values = [0]
    colors = [1.0]

    for ant in rules_df["antecedents"].unique():
        ant_id = f"ant::{ant}"
        ids.append(ant_id)
        labels.append(ant)
        parents.append("root")
        values.append(int((rules_df["antecedents"] == ant).sum()))
        colors.append(float(rules_df.loc[rules_df["antecedents"] == ant, "lift"].mean()))

    for _, row in rules_df.iterrows():
        cons_id = f"cons::{row['antecedents']}::{row['consequents']}"
        ids.append(cons_id)
        labels.append(row["consequents"])
        parents.append(f"ant::{row['antecedents']}")
        values.append(1)
        colors.append(float(row["lift"]))

    fig = go.Figure(go.Sunburst(
        ids=ids, labels=labels, parents=parents, values=values,
        branchvalues="total",
        marker=dict(
            colors=colors, colorscale="RdYlGn", cmid=2,
            colorbar=dict(title="Lift"),
            line=dict(color="#0F1117", width=2),
        ),
        hovertemplate="<b>%{label}</b><br>Lift: %{color:.2f}<extra></extra>",
    ))
    fig.update_layout(
        height=700,
        title="Product Association Hierarchy",
        template=PLOTLY_TEMPLATE,
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Northwind Analytics", layout="wide", page_icon="📊")

st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background-color: #0F1117; }
    [data-testid="stSidebar"] { background-color: #1E2130; }
    [data-testid="stHeader"] { background-color: #0F1117; }
    h1, h2, h3 { color: #FAFAFA !important; }
    .block-container { padding-top: 2rem; }
    [data-testid="stMetric"] { display: none; }
</style>
""", unsafe_allow_html=True)

st.markdown(
    f"<h1 style='color:#FAFAFA;margin-bottom:0.2rem;'>📊 Northwind Analytics Dashboard</h1>"
    f"<p style='color:#8B9BB4;margin-top:0;'>Sales · Logistics · Inventory · Customer Segmentation · Market Basket</p>",
    unsafe_allow_html=True,
)
st.markdown("---")


# ── Helpers ───────────────────────────────────────────────────────────────────
def get_secret_or_env(key):
    try:
        return st.secrets.get(key) or os.getenv(key)
    except StreamlitSecretNotFoundError:
        return os.getenv(key)


@st.cache_data(show_spinner=False)
def load_data_from_csv(csv_path):
    return pd.read_csv(csv_path)


@st.cache_data(show_spinner=False)
def load_data_from_sql(server, database):
    import pyodbc
    conn = pyodbc.connect(
        f"Driver={{ODBC Driver 17 for SQL Server}};Server={server};Database={database};Trusted_Connection=yes;"
    )
    try:
        df_sales = pd.read_sql("SELECT * FROM vw_MasterSales", conn)
        df_logistics = pd.read_sql("SELECT * FROM vw_LogisticsAndShipping", conn)
        df_inventory = pd.read_sql("SELECT * FROM vw_InventoryPerformance", conn)
        df_customer = pd.read_sql("SELECT * FROM vw_CustomerAnalytics", conn)
        df_merged = pd.merge(df_sales, df_logistics.drop(columns=["CustomerID"]), on="OrderID", how="left")
        df_merged = pd.merge(df_merged, df_inventory.drop(columns=["ProductName", "CategoryName"]), on="ProductID", how="left")
        return pd.merge(df_merged, df_customer, on="CustomerID", how="left")
    finally:
        conn.close()


def load_dashboard_data():
    data_source = (get_secret_or_env("DATA_SOURCE") or "auto").strip().lower()
    csv_path = get_secret_or_env("CSV_PATH") or DEFAULT_CSV_PATH

    if data_source == "csv":
        if not os.path.exists(csv_path):
            st.error(f"CSV not found: `{csv_path}`")
            st.stop()
        return load_data_from_csv(csv_path), "csv"

    server = get_secret_or_env("SQL_SERVER")
    database = get_secret_or_env("SQL_DATABASE")

    if data_source == "sql":
        if not server or not database:
            st.error("SQL mode requires SQL_SERVER and SQL_DATABASE.")
            st.stop()
        try:
            return load_data_from_sql(server, database), "sql"
        except Exception as exc:
            st.error(f"SQL error: {exc}")
            st.stop()

    if server and database:
        try:
            return load_data_from_sql(server, database), "sql"
        except Exception as exc:
            if os.path.exists(csv_path):
                st.warning(f"SQL failed, using CSV. ({exc})")
                return load_data_from_csv(csv_path), "csv"
            st.error(f"SQL error: {exc}")
            st.stop()

    if os.path.exists(csv_path):
        return load_data_from_csv(csv_path), "csv"

    st.error("No data source available.")
    st.stop()


# ── Load data ─────────────────────────────────────────────────────────────────
df, data_source = load_dashboard_data()

required_cols = ["OrderDate", "CategoryName", "NetSales", "Profit", "ShipperName",
                 "IsLate", "Quantity", "Discount", "UnitPrice", "UnitCost", "DeliveryDuration"]
missing = [c for c in required_cols if c not in df.columns]
if missing:
    st.error(f"Missing columns: {missing}")
    st.stop()

df["OrderDate"] = pd.to_datetime(df["OrderDate"], errors="coerce")
df = df.dropna(subset=["OrderDate"]).copy()


# ── Sidebar filters ───────────────────────────────────────────────────────────
st.sidebar.markdown(f"<h2 style='color:#FAFAFA;'>🔍 Filters</h2>", unsafe_allow_html=True)

if data_source == "csv":
    st.sidebar.caption("📁 Data source: CSV (cloud mode)")

min_date, max_date = df["OrderDate"].min().date(), df["OrderDate"].max().date()
date_range = st.sidebar.date_input("Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date)

if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date = end_date = date_range[0] if isinstance(date_range, (tuple, list)) else date_range

if start_date > end_date:
    start_date, end_date = end_date, start_date

categories = sorted(df["CategoryName"].dropna().unique().tolist())
selected_categories = st.sidebar.multiselect("Categories", categories, default=categories)

shippers = sorted(df["ShipperName"].dropna().unique().tolist())
selected_shippers = st.sidebar.multiselect("Shippers", shippers, default=shippers)

filtered_df = df[
    (df["OrderDate"].dt.date >= start_date) &
    (df["OrderDate"].dt.date <= end_date) &
    (df["CategoryName"].isin(selected_categories)) &
    (df["ShipperName"].isin(selected_shippers))
].copy()

if filtered_df.empty:
    st.info("No data for selected filters. Try expanding the date range.")
    st.stop()


# ── KPI cards ─────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
with k1:
    styled_metric("Total Net Sales", f"${filtered_df['NetSales'].sum():,.0f}")
with k2:
    styled_metric("Total Profit", f"${filtered_df['Profit'].sum():,.0f}")
with k3:
    styled_metric("Order Count", f"{filtered_df['OrderID'].nunique():,}")
with k4:
    late_rate = filtered_df['IsLate'].mean() * 100
    styled_metric("Late Delivery Rate", f"{late_rate:.1f}%")

st.markdown("<br>", unsafe_allow_html=True)


# ── Sales & logistics charts ──────────────────────────────────────────────────
monthly = filtered_df.set_index("OrderDate").resample("ME")["NetSales"].sum().reset_index()
category_perf = (
    filtered_df.groupby("CategoryName", as_index=False)
    .agg(NetSales=("NetSales", "sum"), Profit=("Profit", "sum"))
    .sort_values("NetSales", ascending=False)
)
ship_perf = (
    filtered_df.groupby("ShipperName", as_index=False)
    .agg(LateRate=("IsLate", "mean"), Orders=("OrderID", "nunique"))
    .sort_values("LateRate", ascending=False)
)
corr_cols = ["NetSales", "Profit", "Quantity", "Discount", "UnitPrice", "UnitCost", "DeliveryDuration"]
corr_melt = (
    filtered_df[corr_cols].corr(numeric_only=True)
    .reset_index()
    .melt(id_vars="index", var_name="Metric", value_name="Correlation")
    .rename(columns={"index": "BaseMetric"})
)

left, right = st.columns(2)

with left:
    st.subheader("Monthly Net Sales Trend")
    fig_monthly = px.line(monthly, x="OrderDate", y="NetSales", markers=True, template=PLOTLY_TEMPLATE)
    fig_monthly.update_traces(line_color=COLOR_PRIMARY, marker_color=COLOR_PRIMARY)
    fig_monthly.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_monthly, use_container_width=True)

    st.subheader("Top Categories: Net Sales vs Profit")
    fig_cat = px.bar(
        category_perf.head(10), x="CategoryName", y=["NetSales", "Profit"],
        barmode="group", template=PLOTLY_TEMPLATE,
        color_discrete_sequence=[COLOR_PRIMARY, COLOR_ACCENT],
    )
    fig_cat.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_cat, use_container_width=True)

with right:
    st.subheader("Shipper Late Delivery Rate")
    fig_ship = px.bar(
        ship_perf, x="ShipperName", y="LateRate", hover_data=["Orders"],
        template=PLOTLY_TEMPLATE, color="LateRate", color_continuous_scale="RdYlGn_r",
    )
    fig_ship.update_yaxes(tickformat=".0%")
    fig_ship.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_ship, use_container_width=True)

    st.subheader("Correlation Heatmap")
    fig_corr = px.density_heatmap(
        corr_melt, x="Metric", y="BaseMetric", z="Correlation",
        text_auto=".2f", color_continuous_scale="RdBu", template=PLOTLY_TEMPLATE,
    )
    fig_corr.update_coloraxes(cmid=0)
    fig_corr.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_corr, use_container_width=True)


# ── Top Profitable Products ───────────────────────────────────────────────────
st.markdown("---")
st.subheader("🏆 Top Profitable Products")

if {"ProductName", "Profit"}.issubset(filtered_df.columns):
    top_n = st.slider("Number of products", min_value=5, max_value=30, value=10, step=1)
    product_profit = (
        filtered_df.groupby("ProductName", as_index=False)
        .agg(TotalProfit=("Profit", "sum"), TotalNetSales=("NetSales", "sum"), OrderCount=("OrderID", "nunique"))
        .sort_values("TotalProfit", ascending=False)
        .head(top_n)
    )
    pp1, pp2 = st.columns([2, 1])
    with pp1:
        fig_pp = px.bar(
            product_profit.sort_values("TotalProfit", ascending=True),
            x="TotalProfit", y="ProductName", orientation="h",
            hover_data=["TotalNetSales", "OrderCount"],
            template=PLOTLY_TEMPLATE,
            color="TotalProfit", color_continuous_scale="Blues",
        )
        fig_pp.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=False)
        st.plotly_chart(fig_pp, use_container_width=True)
    with pp2:
        st.dataframe(product_profit, use_container_width=True, hide_index=True)
else:
    st.info("ProductName and/or Profit columns are missing.")


# ── Inventory ─────────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("📦 Inventory Status")

inventory_needed = {"ProductName", "CategoryName", "UnitsInStock", "ReorderLevel", "UnitCost"}
if inventory_needed.issubset(df.columns):
    inventory_df = (
        df.groupby(["CategoryName", "ProductName"], as_index=False)
        .agg(UnitsInStock=("UnitsInStock", "first"), ReorderLevel=("ReorderLevel", "first"), UnitCost=("UnitCost", "first"))
    )
    inventory_df["StockValue"] = inventory_df["UnitsInStock"] * inventory_df["UnitCost"]
    inventory_df["StockStatus"] = np.where(inventory_df["UnitsInStock"] < inventory_df["ReorderLevel"], "Critical", "Healthy")

    i1, i2, i3 = st.columns(3)
    with i1:
        styled_metric("Total Inventory Value", f"${inventory_df['StockValue'].sum():,.0f}")
    with i2:
        styled_metric("Critical Products", str((inventory_df["StockStatus"] == "Critical").sum()))
    with i3:
        styled_metric("Unique Products", str(inventory_df["ProductName"].nunique()))

    st.markdown("<br>", unsafe_allow_html=True)
    inv_l, inv_r = st.columns(2)

    with inv_l:
        cat_stock = (
            inventory_df.groupby("CategoryName", as_index=False)["StockValue"]
            .sum().sort_values("StockValue", ascending=False).head(10)
        )
        fig_inv = px.bar(
            cat_stock, x="CategoryName", y="StockValue",
            template=PLOTLY_TEMPLATE, color="StockValue", color_continuous_scale="Blues",
            title="Inventory Value by Category",
        )
        fig_inv.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_inv, use_container_width=True)

    with inv_r:
        critical = inventory_df[inventory_df["StockStatus"] == "Critical"].sort_values(
            ["UnitsInStock", "ReorderLevel"], ascending=[True, False]
        )
        st.markdown("**⚠️ Critical Stock Products**")
        if critical.empty:
            st.success("All products are above reorder level.")
        else:
            st.dataframe(
                critical[["CategoryName", "ProductName", "UnitsInStock", "ReorderLevel", "StockValue"]].head(20),
                use_container_width=True, hide_index=True,
            )
else:
    st.info("Inventory columns missing: ProductName, CategoryName, UnitsInStock, ReorderLevel, UnitCost.")


# ── RFM Segmentation ──────────────────────────────────────────────────────────
st.markdown("---")
st.header("👥 Customer Segmentation (RFM + KMeans)")

rfm_needed = {"CustomerID", "OrderDate", "OrderID", "NetSales"}
if not rfm_needed.issubset(df.columns):
    st.warning("RFM requires: CustomerID, OrderDate, OrderID, NetSales")
else:
    rfm_source = df.dropna(subset=["CustomerID", "OrderDate"]).copy()
    snapshot_date = rfm_source["OrderDate"].max() + pd.Timedelta(days=1)

    rfm = (
        rfm_source.groupby("CustomerID")
        .agg(
            Recency=("OrderDate", lambda x: (snapshot_date - x.max()).days),
            Frequency=("OrderID", "nunique"),
            Monetary=("NetSales", "sum"),
        )
        .clip(lower=0)
    )

    if len(rfm) >= 4:
        rfm_log = pd.DataFrame({
            "Recency": np.log1p(rfm["Recency"]),
            "Frequency": np.log1p(rfm["Frequency"]),
            "Monetary": np.log1p(rfm["Monetary"]),
        }, index=rfm.index)

        scaler = StandardScaler()
        rfm_scaled = scaler.fit_transform(rfm_log)
        kmeans = KMeans(n_clusters=4, init="k-means++", max_iter=300, n_init=10, random_state=42)
        rfm["Cluster"] = kmeans.fit_predict(rfm_scaled)

        cluster_summary = (
            rfm.groupby("Cluster")
            .agg(Recency=("Recency", "mean"), Frequency=("Frequency", "mean"),
                 Monetary=("Monetary", "mean"), CustomerCount=("Cluster", "count"))
            .round(1).sort_values("Monetary", ascending=False).reset_index()
        )

        segment_labels = ["Champions", "At Risk", "Potential Loyalists", "Lost Customers"]
        cluster_to_segment = {cid: segment_labels[i] for i, cid in enumerate(cluster_summary["Cluster"].tolist())}
        rfm["Segment"] = rfm["Cluster"].map(cluster_to_segment)

        seg_counts = rfm["Segment"].value_counts().rename_axis("Segment").reset_index(name="CustomerCount")

        seg_col, sum_col = st.columns(2)
        with seg_col:
            fig_seg = px.bar(
                seg_counts, x="Segment", y="CustomerCount", color="Segment",
                template=PLOTLY_TEMPLATE,
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig_seg.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=False)
            st.plotly_chart(fig_seg, use_container_width=True)

        with sum_col:
            cluster_summary["Segment"] = cluster_summary["Cluster"].map(cluster_to_segment)
            st.dataframe(
                cluster_summary[["Segment", "Recency", "Frequency", "Monetary", "CustomerCount"]],
                use_container_width=True, hide_index=True,
            )
    else:
        st.info("At least 4 unique customers are needed for RFM segmentation.")


# ── Market Basket ─────────────────────────────────────────────────────────────
st.markdown("---")
st.header("🛒 Frequently Bought Together (Market Basket)")

basket_needed = {"OrderID", "ProductName", "Quantity"}
if not basket_needed.issubset(df.columns):
    st.warning("Market basket requires: OrderID, ProductName, Quantity")
else:
    basket = df.groupby(["OrderID", "ProductName"])["Quantity"].sum().unstack(fill_value=0)
    product_counts = basket.gt(0).sum(axis=0).sort_values(ascending=False)
    max_products = min(200, len(product_counts))
    min_products = 5 if max_products >= 5 else 1
    default_products = min(120, max_products) if max_products >= 20 else max_products

    top_n_products = st.slider(
        "Number of products to include",
        min_value=min_products, max_value=max_products,
        value=default_products,
        step=10 if max_products >= 30 else 1,
    )

    selected_products = product_counts.head(top_n_products).index
    basket_bool = basket[selected_products].gt(0)

    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        min_support = st.slider("Min support", min_value=0.001, max_value=0.05, value=0.005, step=0.001)
    with col_s2:
        min_lift = st.slider("Min lift", min_value=1.0, max_value=10.0, value=1.0, step=0.1)
    with col_s3:
        max_len = st.slider("Max itemset size", min_value=2, max_value=4, value=2, step=1)

    st.caption(
        f"Top {len(selected_products)} products · {basket_bool.shape[0]} orders · "
        f"support={min_support} · lift≥{min_lift}"
    )

    try:
        freq_items = apriori(basket_bool, min_support=min_support, use_colnames=True, max_len=max_len, low_memory=True)
    except MemoryError:
        st.error("Memory limit reached. Increase min support or reduce product count.")
        st.stop()
    except Exception as exc:
        st.error(f"Apriori failed: {exc}")
        st.stop()

    if freq_items.empty:
        st.info("No frequent itemsets found. Try lowering min support.")
    else:
        rules = association_rules(freq_items, metric="lift", min_threshold=min_lift)
        if rules.empty:
            st.info("No rules found. Try lowering min lift.")
        else:
            rules = rules.sort_values("lift", ascending=False).copy()
            rules_copy = rules.copy()
            rules_copy["antecedents"] = rules_copy["antecedents"].apply(lambda x: ", ".join(sorted(x)))
            rules_copy["consequents"] = rules_copy["consequents"].apply(lambda x: ", ".join(sorted(x)))

            tab1, tab2, tab3 = st.tabs(["📋 Rules Table", "🕸️ Network", "🌀 Sunburst"])

            with tab1:
                show_rules = rules_copy[["antecedents", "consequents", "support", "confidence", "lift"]].head(15)
                st.dataframe(show_rules, use_container_width=True, hide_index=True)
                fig_rules = px.bar(
                    show_rules.head(10), x="lift", y="antecedents", color="confidence",
                    hover_data=["consequents", "support"], orientation="h",
                    template=PLOTLY_TEMPLATE, color_continuous_scale="Blues",
                    title="Top Rules by Lift",
                )
                fig_rules.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_rules, use_container_width=True)

            with tab2:
                st.plotly_chart(create_network_diagram(show_rules), use_container_width=True)

            with tab3:
                st.plotly_chart(create_sunburst(show_rules), use_container_width=True)


# ── Power BI ──────────────────────────────────────────────────────────────────
st.markdown("---")
st.header("📈 Power BI Report")
power_bi_path = next(
    (p for p in ("assets/powerbi-report.png", "powerbi-report.png") if os.path.exists(p)), None
)
if power_bi_path:
    st.image(power_bi_path, caption="Power BI Dashboard", use_container_width=True)
else:
    st.info("Power BI görseli bulunamadı. `assets/powerbi-report.png` dosyasını projeye ekle.")

st.markdown("---")
st.markdown(
    "<p style='text-align:center;color:#8B9BB4;font-size:0.8rem;'>Northwind Analytics Dashboard · Built with Streamlit & Plotly</p>",
    unsafe_allow_html=True,
)
