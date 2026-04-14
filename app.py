import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components
import pyodbc
import numpy as np
import os
from mlxtend.frequent_patterns import apriori, association_rules
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from streamlit.errors import StreamlitSecretNotFoundError


st.set_page_config(page_title="Northwind Analytics Dashboard", layout="wide")
st.title("Northwind Analytics Dashboard")


@st.cache_data(show_spinner=False)
def load_data_from_sql(server, database):
    # Load and combine the reporting views used by the dashboard.
    conn = pyodbc.connect(
        f"Driver={{SQL Server}};Server={server};Database={database};Trusted_Connection=yes;"
    )
    try:
        df_sales = pd.read_sql("SELECT * FROM vw_MasterSales", conn)
        df_logistics = pd.read_sql("SELECT * FROM vw_LogisticsAndShipping", conn)
        df_inventory = pd.read_sql("SELECT * FROM vw_InventoryPerformance", conn)
        df_customer = pd.read_sql("SELECT * FROM vw_CustomerAnalytics", conn)

        df_merged = pd.merge(
            df_sales, df_logistics.drop(columns=["CustomerID"]), on="OrderID", how="left"
        )
        df_merged = pd.merge(
            df_merged,
            df_inventory.drop(columns=["ProductName", "CategoryName"]),
            on="ProductID",
            how="left",
        )
        df_final = pd.merge(df_merged, df_customer, on="CustomerID", how="left")
        return df_final
    finally:
        conn.close()


def get_secret_or_env(key):
    # Prefer Streamlit secrets; fallback to environment variables.
    try:
        return st.secrets.get(key) or os.getenv(key)
    except StreamlitSecretNotFoundError:
        return os.getenv(key)


server = get_secret_or_env("SQL_SERVER")
database = get_secret_or_env("SQL_DATABASE")

if not server or not database:
    st.error(
        "SQL connection settings are missing. "
        "Please set `SQL_SERVER` and `SQL_DATABASE` in `.streamlit/secrets.toml` "
        "or as environment variables."
    )
    st.stop()

try:
    df = load_data_from_sql(server, database)
except Exception as exc:
    st.error(f"SQL connection/data fetch error: {exc}")
    st.stop()

required_cols = [
    "OrderDate",
    "CategoryName",
    "NetSales",
    "Profit",
    "ShipperName",
    "IsLate",
    "Quantity",
    "Discount",
    "UnitPrice",
    "UnitCost",
    "DeliveryDuration",
]

missing = [col for col in required_cols if col not in df.columns]
if missing:
    st.error(f"Required columns are missing: {missing}")
    st.stop()

df["OrderDate"] = pd.to_datetime(df["OrderDate"], errors="coerce")
df = df.dropna(subset=["OrderDate"]).copy()

# Global dashboard filters.
st.sidebar.header("Filters")
min_date = df["OrderDate"].min().date()
max_date = df["OrderDate"].max().date()
date_range = st.sidebar.date_input(
    "Date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start_date, end_date = date_range
elif isinstance(date_range, (tuple, list)) and len(date_range) == 1:
    start_date = end_date = date_range[0]
else:
    # Streamlit may return a single date
    start_date = end_date = date_range

if start_date > end_date:
    start_date, end_date = end_date, start_date

categories = sorted(df["CategoryName"].dropna().unique().tolist())
selected_categories = st.sidebar.multiselect(
    "Select categories", categories, default=categories
)

shippers = sorted(df["ShipperName"].dropna().unique().tolist())
selected_shippers = st.sidebar.multiselect("Select shippers", shippers, default=shippers)

filtered_df = df[
    (df["OrderDate"].dt.date >= start_date)
    & (df["OrderDate"].dt.date <= end_date)
    & (df["CategoryName"].isin(selected_categories))
    & (df["ShipperName"].isin(selected_shippers))
].copy()

if filtered_df.empty:
    st.info(
        "No data found for the selected date/category/shipper filters. "
        "Try expanding the date range."
    )
    st.stop()

col1, col2, col3, col4 = st.columns(4)
# KPI cards.
col1.metric("Total Net Sales", f"{filtered_df['NetSales'].sum():,.2f}")
col2.metric("Total Profit", f"{filtered_df['Profit'].sum():,.2f}")
col3.metric("Order Count", f"{filtered_df['OrderID'].nunique():,}")
col4.metric("Late Delivery Rate", f"{filtered_df['IsLate'].mean() * 100:.1f}%")

monthly = (
    filtered_df.set_index("OrderDate")
    .resample("ME")["NetSales"]
    .sum()
    .reset_index()
)

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

corr_cols = [
    "NetSales",
    "Profit",
    "Quantity",
    "Discount",
    "UnitPrice",
    "UnitCost",
    "DeliveryDuration",
]
corr_df = filtered_df[corr_cols].corr(numeric_only=True).reset_index()
corr_melt = corr_df.melt(id_vars="index", var_name="Metric", value_name="Correlation")
corr_melt = corr_melt.rename(columns={"index": "BaseMetric"})

left, right = st.columns(2)

with left:
    st.subheader("Monthly Net Sales Trend")
    fig_monthly = px.line(monthly, x="OrderDate", y="NetSales", markers=True)
    st.plotly_chart(fig_monthly, use_container_width=True)

    st.subheader("Top Categories: Net Sales")
    fig_cat = px.bar(
        category_perf.head(10),
        x="CategoryName",
        y=["NetSales", "Profit"],
        barmode="group",
    )
    st.plotly_chart(fig_cat, use_container_width=True)

with right:
    st.subheader("Shipper Late Delivery Rate")
    fig_ship = px.bar(ship_perf, x="ShipperName", y="LateRate", hover_data=["Orders"])
    fig_ship.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig_ship, use_container_width=True)

    st.subheader("Correlation Heatmap")
    fig_corr = px.density_heatmap(
        corr_melt,
        x="Metric",
        y="BaseMetric",
        z="Correlation",
        text_auto=".2f",
        color_continuous_scale="RdBu",
    )
    fig_corr.update_coloraxes(cmid=0)
    st.plotly_chart(fig_corr, use_container_width=True)

st.markdown("---")
st.subheader("Top Profitable Products")
if {"ProductName", "Profit"}.issubset(filtered_df.columns):
    top_n_products = st.slider(
        "Number of top profitable products",
        min_value=5,
        max_value=30,
        value=10,
        step=1,
    )
    product_profit = (
        filtered_df.groupby("ProductName", as_index=False)
        .agg(
            TotalProfit=("Profit", "sum"),
            TotalNetSales=("NetSales", "sum"),
            OrderCount=("OrderID", "nunique"),
        )
        .sort_values("TotalProfit", ascending=False)
        .head(top_n_products)
    )

    pp_col1, pp_col2 = st.columns([2, 1])
    with pp_col1:
        fig_product_profit = px.bar(
            product_profit.sort_values("TotalProfit", ascending=True),
            x="TotalProfit",
            y="ProductName",
            orientation="h",
            hover_data=["TotalNetSales", "OrderCount"],
            title="Most Profitable Products",
        )
        st.plotly_chart(fig_product_profit, use_container_width=True)
    with pp_col2:
        st.dataframe(product_profit, use_container_width=True)
else:
    st.info("`ProductName` and/or `Profit` columns are missing, so product profitability cannot be shown.")

st.markdown("---")
st.subheader("Inventory Status")
inventory_needed = {"ProductName", "CategoryName", "UnitsInStock", "ReorderLevel", "UnitCost"}
if inventory_needed.issubset(df.columns):
    inventory_df = (
        df.groupby(["CategoryName", "ProductName"], as_index=False)
        .agg(
            UnitsInStock=("UnitsInStock", "first"),
            ReorderLevel=("ReorderLevel", "first"),
            UnitCost=("UnitCost", "first"),
        )
    )
    inventory_df["StockValue"] = inventory_df["UnitsInStock"] * inventory_df["UnitCost"]
    inventory_df["StockStatus"] = np.where(
        inventory_df["UnitsInStock"] < inventory_df["ReorderLevel"],
        "Critical",
        "Healthy",
    )

    inv_col1, inv_col2, inv_col3 = st.columns(3)
    inv_col1.metric("Total Inventory Value", f"{inventory_df['StockValue'].sum():,.2f}")
    inv_col2.metric("Critical Products", f"{(inventory_df['StockStatus'] == 'Critical').sum():,}")
    inv_col3.metric("Unique Products", f"{inventory_df['ProductName'].nunique():,}")

    inv_left, inv_right = st.columns(2)

    with inv_left:
        category_stock = (
            inventory_df.groupby("CategoryName", as_index=False)["StockValue"]
            .sum()
            .sort_values("StockValue", ascending=False)
            .head(10)
        )
        fig_stock_cat = px.bar(
            category_stock,
            x="CategoryName",
            y="StockValue",
            title="Top Categories by Inventory Value",
        )
        st.plotly_chart(fig_stock_cat, use_container_width=True)

    with inv_right:
        critical_products = inventory_df[inventory_df["StockStatus"] == "Critical"].copy()
        critical_products = critical_products.sort_values(
            ["UnitsInStock", "ReorderLevel"], ascending=[True, False]
        )
        st.markdown("**Critical Stock Products**")
        if critical_products.empty:
            st.info("No critical stock products found.")
        else:
            st.dataframe(
                critical_products[
                    [
                        "CategoryName",
                        "ProductName",
                        "UnitsInStock",
                        "ReorderLevel",
                        "StockValue",
                    ]
                ].head(20),
                use_container_width=True,
            )
else:
    st.info(
        "Inventory columns are missing. Required: ProductName, CategoryName, UnitsInStock, ReorderLevel, UnitCost."
    )

st.subheader("Filtered Data Preview")
st.dataframe(filtered_df.head(200), use_container_width=True)

st.markdown("---")
st.header("Customer Segmentation (RFM)")

rfm_needed = {"CustomerID", "OrderDate", "OrderID", "NetSales"}
if not rfm_needed.issubset(df.columns):
    st.warning("Required columns for RFM are missing: CustomerID, OrderDate, OrderID, NetSales")
else:
    # Build RFM table per customer.
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
        # Scale transformed features before clustering.
        rfm_log = pd.DataFrame(
            {
                "Recency": np.log1p(rfm["Recency"]),
                "Frequency": np.log1p(rfm["Frequency"]),
                "Monetary": np.log1p(rfm["Monetary"]),
            },
            index=rfm.index,
        )

        scaler = StandardScaler()
        rfm_scaled = scaler.fit_transform(rfm_log)
        kmeans = KMeans(n_clusters=4, init="k-means++", max_iter=300, n_init=10, random_state=42)
        rfm["Cluster"] = kmeans.fit_predict(rfm_scaled)

        cluster_summary = (
            rfm.groupby("Cluster")
            .agg(
                Recency=("Recency", "mean"),
                Frequency=("Frequency", "mean"),
                Monetary=("Monetary", "mean"),
                CustomerCount=("Cluster", "count"),
            )
            .round(1)
            .sort_values("Monetary", ascending=False)
            .reset_index()
        )

        ordered_clusters = cluster_summary["Cluster"].tolist()
        segment_labels = [
            "Champions",
            "At Risk",
            "Potential Loyalists",
            "Lost Customers",
        ]
        cluster_to_segment = {
            cluster_id: segment_labels[idx] if idx < len(segment_labels) else f"Segment {idx + 1}"
            for idx, cluster_id in enumerate(ordered_clusters)
        }
        rfm["Segment"] = rfm["Cluster"].map(cluster_to_segment)

        seg_counts = (
            rfm["Segment"]
            .value_counts()
            .rename_axis("Segment")
            .reset_index(name="CustomerCount")
        )

        seg_col, summary_col = st.columns(2)
        with seg_col:
            fig_seg = px.bar(seg_counts, x="Segment", y="CustomerCount", color="Segment")
            st.plotly_chart(fig_seg, use_container_width=True)

        with summary_col:
            cluster_summary["Segment"] = cluster_summary["Cluster"].map(cluster_to_segment)
            st.dataframe(
                cluster_summary[["Segment", "Recency", "Frequency", "Monetary", "CustomerCount"]],
                use_container_width=True,
            )
    else:
        st.info("At least 4 unique customers are required for RFM segmentation.")

st.markdown("---")
st.header("Frequently Bought Together (Market Basket)")

basket_needed = {"OrderID", "ProductName", "Quantity"}
if not basket_needed.issubset(df.columns):
    st.warning("Required columns for market basket are missing: OrderID, ProductName, Quantity")
else:
    # Convert transactions into an order-product matrix for Apriori.
    basket = (
        df.groupby(["OrderID", "ProductName"])["Quantity"]
        .sum()
        .unstack(fill_value=0)
    )
    product_counts = basket.gt(0).sum(axis=0).sort_values(ascending=False)
    max_products = min(200, len(product_counts))
    min_products = 5 if max_products >= 5 else 1
    default_products = min(120, max_products) if max_products >= 20 else max_products
    top_n_products = st.slider(
        "Number of products to include",
        min_value=min_products,
        max_value=max_products,
        value=default_products,
        step=10 if max_products >= 30 else 1,
    )

    selected_products = product_counts.head(top_n_products).index
    basket_bool = basket[selected_products].gt(0)

    min_support = st.slider("Min support", min_value=0.001, max_value=0.05, value=0.01, step=0.001)
    min_lift = st.slider("Min lift", min_value=1.0, max_value=10.0, value=1.0, step=0.1)
    max_len = st.slider("Max itemset size", min_value=2, max_value=4, value=2, step=1)

    st.caption(
        f"Using top {len(selected_products)} products by frequency "
        f"across {basket_bool.shape[0]} orders to keep memory usage stable."
    )

    try:
        freq_items = apriori(
            basket_bool,
            min_support=min_support,
            use_colnames=True,
            max_len=max_len,
            low_memory=True,
        )
    except MemoryError:
        st.error(
            "Memory limit reached while running Apriori. "
            "Increase min support or reduce product count/max itemset size."
        )
        st.stop()
    except Exception as exc:
        st.error(f"Apriori failed: {exc}")
        st.stop()

    if freq_items.empty:
        st.info("No frequent itemsets found with this support value.")
    else:
        rules = association_rules(freq_items, metric="lift", min_threshold=min_lift)
        if rules.empty:
            st.info("No rules found with this lift threshold.")
        else:
            # Make rule itemsets readable in the table.
            rules = rules.sort_values("lift", ascending=False).copy()
            rules["antecedents"] = rules["antecedents"].apply(lambda x: ", ".join(sorted(list(x))))
            rules["consequents"] = rules["consequents"].apply(lambda x: ", ".join(sorted(list(x))))
            show_rules = rules[["antecedents", "consequents", "support", "confidence", "lift"]].head(15)

            st.dataframe(show_rules, use_container_width=True)
            fig_rules = px.bar(
                show_rules.head(10),
                x="lift",
                y="antecedents",
                color="confidence",
                hover_data=["consequents", "support"],
                orientation="h",
                title="Top Rules by Lift",
            )
            st.plotly_chart(fig_rules, use_container_width=True)

st.markdown("---")
st.header("Power BI Report")
# If embed is not available, use share link as a fallback.
power_bi_share_url = get_secret_or_env("POWER_BI_SHARE_URL")
default_embed_url = get_secret_or_env("POWER_BI_EMBED_URL") or ""
power_bi_embed_url = st.text_input(
    "Power BI embed URL (optional)",
    value=default_embed_url,
    help="Paste the embed URL you get from 'Publish to web' or 'Embed in website/portal'.",
)

if power_bi_embed_url.strip():
    components.iframe(power_bi_embed_url.strip(), height=700, scrolling=True)
else:
    if power_bi_share_url:
        st.info(
            "This share link cannot be opened inside an iframe (app.powerbi.com refused to connect). "
            "You can open the report in a new tab using the button below, or paste an embed URL to display it here."
        )
        st.link_button("Open Power BI report in a new tab", power_bi_share_url)
    else:
        st.info(
            "Set `POWER_BI_SHARE_URL` in `.streamlit/secrets.toml` "
            "or paste an embed URL above to display your Power BI report."
        )
