# Northwind Analytics Dashboard

Interactive analytics dashboard built with Streamlit on top of the Northwind database.  
The application combines sales, logistics, inventory, and customer behavior analysis in a single interface.

## Screenshots

### Streamlit Dashboard

![Streamlit Dashboard](assets/dashboard-screenshot.png)

Additional dashboard views:

![Dashboard View 1](assets/dashboard-1.png)
![Dashboard View 2](assets/dashboard-2.png)
![Dashboard View 3](assets/dashboard-3.png)
![Dashboard View 4](assets/dashboard-4.png)

### Power BI Report

Add your Power BI screenshot to `assets/powerbi-report.png`, then it will appear here automatically:

![Power BI Report](assets/powerbi-report.png)

## What This Project Includes

- Executive KPIs (net sales, profit, order count, late delivery rate)
- Time and category based performance analysis
- Logistics and late shipment monitoring by shipper
- Inventory health and critical stock tracking
- Customer segmentation with RFM + KMeans
- Market basket analysis with Apriori association rules
- Optional Power BI report integration section

## Tech Stack

- Python
- Streamlit
- Pandas / NumPy
- Plotly
- scikit-learn
- mlxtend
- pyodbc (SQL Server connection)

## Required Database Objects

The app expects these SQL views in the `Northwind` database:

- `vw_MasterSales`
- `vw_LogisticsAndShipping`
- `vw_InventoryPerformance`
- `vw_CustomerAnalytics`

## Project Structure

- `app.py` - Streamlit application
- `requirements.txt` - Python dependencies
- `sql/` - SQL Server view scripts required by the app
- `.streamlit/secrets.toml` - local secrets (ignored by git)
- `.streamlit/secrets.example.toml` - example config template
- `exploratory_data_analysis.ipynb` - exploratory notebook

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Create local secrets file:

```bash
mkdir .streamlit
```

Create `.streamlit/secrets.toml` and add:

```toml
SQL_SERVER = "localhost\\SQLEXPRESS"
SQL_DATABASE = "Northwind"
POWER_BI_SHARE_URL = "https://app.powerbi.com/links/your-share-link"
POWER_BI_EMBED_URL = ""
```

Notes:
- `POWER_BI_SHARE_URL` is optional. It is used for opening the report in a new tab.
- `POWER_BI_EMBED_URL` is optional. If provided, it is embedded directly in the app.
- You can also use environment variables instead of `secrets.toml`.

3. Create the required SQL views by running these scripts in order:

```text
sql/01_vw_MasterSales.sql
sql/02_vw_LogisticsAndShipping.sql
sql/03_vw_InventoryPerformance.sql
sql/04_vw_CustomerAnalytics.sql
```

## Run

```bash
streamlit run app.py
```

Open the local URL shown in terminal (usually `http://localhost:8501`).

## Security Notes

- `.streamlit/secrets.toml` is ignored via `.gitignore` and should not be committed.
- Keep credentials, tokens, and private URLs in local secrets or environment variables.
- If a secret was committed previously, rotate it and clean git history if needed.

## Troubleshooting

- **`StreamlitSecretNotFoundError`**  
  Create `.streamlit/secrets.toml` and set `SQL_SERVER` / `SQL_DATABASE`.

- **Power BI iframe shows "refused to connect"**  
  Share links (`app.powerbi.com/links/...`) may not support iframe embedding.  
  Use a proper embed URL, or open via the new-tab button in the app.

- **SQL connection error**  
  Check SQL Server instance name, database name, and that required views exist.

## Business Insights & Strategic Recommendations

This project translates raw operational data into strategic decisions across four focus areas:

### 1) Financial Performance and Profitability

- **Profit engine:** *Beverages* is a key profit driver, contributing a major share of total profit with a strong margin.
- **Operational efficiency:** *Confections* shows the highest margin, indicating high value creation with relatively lower cost pressure.
- **Risk area:** *Meat/Poultry* is the weakest-margin category due to high supply costs.
- **Discount trap identified:** Aggressive discounts on low-margin products can push margins negative. A maximum discount threshold by product/category is recommended.

### 2) Operational Efficiency and Logistics

- **Top logistics partner:** *Federal Shipping* performs as the most reliable carrier in delivery speed and cost balance.
- **Working capital pressure:** A significant amount of capital is tied up in inventory, with selected categories accounting for a large share.
- **Critical stock warnings:** Multiple products are below reorder level, and some items experienced stockout risk, creating potential revenue loss.

### 3) Customer Segmentation (RFM)

Customers are grouped into four behavior-based clusters:

- **Champions:** Most loyal and highest-value customers. Strategy: premium loyalty programs and non-discount benefits.
- **At-Risk Loyalists:** Historically high-value customers with recent inactivity. Strategy: targeted win-back campaigns.
- **Potential Loyalists / Dormant Customers:** Growth and reactivation opportunities. Strategy: basket expansion offers and lifecycle automation.

### 4) Market Basket Analysis

Using Apriori association rules, high-affinity product combinations were identified:

- Certain product pairs strongly increase the probability of additional item purchases.
- Findings support bundling strategies and smarter shelf/warehouse placement.

## Key Strategic Actions

- Implement a margin-aware dynamic discount policy.
- Prioritize replenishment for critical stockout-risk products.
- Build cross-sell recommendations based on basket rules in the dashboard UI.

## License

This project is licensed under the MIT License.

