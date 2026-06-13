import os

import numpy as np
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

DEFAULT_CSV_PATH = "northwind_data.csv"


st.set_page_config(page_title="Northwind Analytics Dashboard", layout="wide")
st.title("Northwind Analytics Dashboard")


def get_secret_or_env(key):
    # Prefer Streamlit secrets; fallback to environment variables.
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

# Load and combine the reporting views used by the dashboard.
conn = pyodbc.connect(
f"Driver={{SQL Server}};Server={server};Database={database};Trusted_Connection=yes;"
@@ -42,30 +59,62 @@ def load_data_from_sql(server, database):
conn.close()


def get_secret_or_env(key):
    # Prefer Streamlit secrets; fallback to environment variables.
    try:
        return st.secrets.get(key) or os.getenv(key)
    except StreamlitSecretNotFoundError:
        return os.getenv(key)
def resolve_csv_path():
    return get_secret_or_env("CSV_PATH") or DEFAULT_CSV_PATH


def load_dashboard_data():
    data_source = (get_secret_or_env("DATA_SOURCE") or "auto").strip().lower()
    csv_path = resolve_csv_path()

server = get_secret_or_env("SQL_SERVER")
database = get_secret_or_env("SQL_DATABASE")
    if data_source == "csv":
        if not os.path.exists(csv_path):
            st.error(f"CSV dataset not found: `{csv_path}`")
            st.stop()
        return load_data_from_csv(csv_path), "csv"

    server = get_secret_or_env("SQL_SERVER")
    database = get_secret_or_env("SQL_DATABASE")

    if data_source == "sql":
        if not server or not database:
            st.error(
                "SQL mode is enabled but connection settings are missing. "
                "Set `SQL_SERVER` and `SQL_DATABASE` in secrets or environment variables."
            )
            st.stop()
        try:
            return load_data_from_sql(server, database), "sql"
        except Exception as exc:
            st.error(f"SQL connection/data fetch error: {exc}")
            st.stop()

    if server and database:
        try:
            return load_data_from_sql(server, database), "sql"
        except Exception as exc:
            if os.path.exists(csv_path):
                st.warning(
                    "SQL connection failed; falling back to bundled CSV dataset. "
                    f"Details: {exc}"
                )
                return load_data_from_csv(csv_path), "csv"
            st.error(f"SQL connection/data fetch error: {exc}")
            st.stop()

    if os.path.exists(csv_path):
        return load_data_from_csv(csv_path), "csv"

if not server or not database:
st.error(
        "SQL connection settings are missing. "
        "Please set `SQL_SERVER` and `SQL_DATABASE` in `.streamlit/secrets.toml` "
        "or as environment variables."
        "No data source is available. Configure SQL secrets for local SQL Server, "
        f"or commit `{DEFAULT_CSV_PATH}` and set `DATA_SOURCE = \"csv\"` for cloud deploy."
)
st.stop()

try:
    df = load_data_from_sql(server, database)
except Exception as exc:
    st.error(f"SQL connection/data fetch error: {exc}")
    st.stop()

df, data_source = load_dashboard_data()
if data_source == "csv":
    st.caption("Data source: bundled CSV dataset (cloud-friendly mode).")

required_cols = [
"OrderDate",
