"""
Personal Finance Dashboard
Run with:  streamlit run app.py
"""

import io
from datetime import date, datetime

import pandas as pd
import plotly.express as px
import streamlit as st

import db

# ---------------------------------------------------------------- setup ----
st.set_page_config(page_title="Personal Finance Dashboard", page_icon="💰", layout="wide")
db.init_db()

PAGES = ["📊 Dashboard", "➕ Add Transaction", "📁 Import CSV", "🎯 Budgets"]

if "page" not in st.session_state:
    st.session_state.page = PAGES[0]

st.sidebar.title("💰 Finance Dashboard")
st.session_state.page = st.sidebar.radio("Navigate", PAGES, index=PAGES.index(st.session_state.page))

st.sidebar.divider()
st.sidebar.caption(
    "Data is stored locally in `finance.db` (SQLite) in this project folder. "
    "Nothing leaves your machine."
)


def load_df():
    rows = db.get_all_transactions()
    if not rows:
        return pd.DataFrame(columns=["id", "date", "description", "category", "amount", "type"])
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return df


# ============================================================== DASHBOARD ==
if st.session_state.page == "📊 Dashboard":
    st.title("📊 Dashboard")
    df = load_df()

    if df.empty:
        st.info("No transactions yet. Add one manually or import a CSV to get started.")
    else:
        # ---- filters ----
        col_a, col_b = st.columns(2)
        min_d, max_d = df["date"].min().date(), df["date"].max().date()
        with col_a:
            date_range = st.date_input("Date range", (min_d, max_d), min_value=min_d, max_value=max_d)
        with col_b:
            cats = sorted(df["category"].unique())
            picked_cats = st.multiselect("Categories", cats, default=cats)

        if isinstance(date_range, tuple) and len(date_range) == 2:
            start, end = date_range
        else:
            start, end = min_d, max_d

        mask = (
            (df["date"].dt.date >= start)
            & (df["date"].dt.date <= end)
            & (df["category"].isin(picked_cats))
        )
        fdf = df[mask]

        income = fdf.loc[fdf["type"] == "Income", "amount"].sum()
        expense = fdf.loc[fdf["type"] == "Expense", "amount"].sum()
        net = income - expense

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Income", f"${income:,.2f}")
        c2.metric("Total Expenses", f"${expense:,.2f}")
        c3.metric("Net Savings", f"${net:,.2f}", delta=f"{net:,.2f}")

        st.divider()

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Spending by Category")
            exp_by_cat = (
                fdf[fdf["type"] == "Expense"].groupby("category")["amount"].sum().reset_index()
            )
            if not exp_by_cat.empty:
                fig = px.pie(exp_by_cat, names="category", values="amount", hole=0.4)
                fig.update_layout(margin=dict(t=10, b=10, l=10, r=10))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.caption("No expense data in this range.")

        with col2:
            st.subheader("Income vs Expenses Over Time")
            monthly = fdf.copy()
            monthly["month"] = monthly["date"].dt.to_period("M").astype(str)
            trend = monthly.groupby(["month", "type"])["amount"].sum().reset_index()
            if not trend.empty:
                fig2 = px.bar(trend, x="month", y="amount", color="type", barmode="group")
                fig2.update_layout(margin=dict(t=10, b=10, l=10, r=10))
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.caption("No data in this range.")

        st.subheader("Net Savings Trend")
        monthly_net = fdf.copy()
        monthly_net["month"] = monthly_net["date"].dt.to_period("M").astype(str)
        monthly_net["signed"] = monthly_net.apply(
            lambda r: r["amount"] if r["type"] == "Income" else -r["amount"], axis=1
        )
        net_trend = monthly_net.groupby("month")["signed"].sum().cumsum().reset_index()
        net_trend.columns = ["month", "cumulative_net"]
        if not net_trend.empty:
            fig3 = px.line(net_trend, x="month", y="cumulative_net", markers=True)
            fig3.update_layout(margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig3, use_container_width=True)

        st.divider()

        # ---- budget vs actual (current month) ----
        budgets = db.get_budgets()
        if budgets:
            st.subheader("Budget vs Actual (current month)")
            this_month = datetime.now().strftime("%Y-%m")
            month_df = df[(df["date"].dt.strftime("%Y-%m") == this_month) & (df["type"] == "Expense")]
            actual_by_cat = month_df.groupby("category")["amount"].sum().to_dict()

            budget_rows = []
            for cat, limit in budgets.items():
                budget_rows.append(
                    {"category": cat, "Budget": limit, "Actual": actual_by_cat.get(cat, 0.0)}
                )
            bdf = pd.DataFrame(budget_rows)
            if not bdf.empty:
                fig4 = px.bar(
                    bdf.melt(id_vars="category", var_name="type", value_name="amount"),
                    x="category", y="amount", color="type", barmode="group",
                )
                fig4.update_layout(margin=dict(t=10, b=10, l=10, r=10))
                st.plotly_chart(fig4, use_container_width=True)

                for _, row in bdf.iterrows():
                    pct = (row["Actual"] / row["Budget"] * 100) if row["Budget"] > 0 else 0
                    over = row["Actual"] > row["Budget"]
                    st.progress(
                        min(pct / 100, 1.0),
                        text=f"{row['category']}: ${row['Actual']:,.2f} / ${row['Budget']:,.2f} "
                        f"({pct:.0f}%){' ⚠️ over budget' if over else ''}",
                    )
        else:
            st.caption("Set budgets in the **Budgets** tab to see budget-vs-actual tracking here.")

        st.divider()
        st.subheader("Transactions")
        show_df = fdf.sort_values("date", ascending=False)[
            ["id", "date", "description", "category", "amount", "type"]
        ]
        st.dataframe(show_df, use_container_width=True, hide_index=True)

        with st.expander("Delete a transaction"):
            del_id = st.number_input("Transaction ID to delete", min_value=0, step=1)
            if st.button("Delete", type="secondary"):
                if del_id:
                    db.delete_transaction(int(del_id))
                    st.success(f"Deleted transaction {del_id}.")
                    st.rerun()


# ========================================================= ADD TRANSACTION ==
elif st.session_state.page == "➕ Add Transaction":
    st.title("➕ Add Transaction")

    with st.form("add_txn_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            txn_date = st.date_input("Date", value=date.today())
            txn_type = st.selectbox("Type", ["Expense", "Income"])
        with c2:
            category = st.selectbox("Category", db.DEFAULT_CATEGORIES)
            amount = st.number_input("Amount", min_value=0.0, step=0.01, format="%.2f")

        description = st.text_input("Description (optional)")
        submitted = st.form_submit_button("Add Transaction", type="primary")

        if submitted:
            if amount <= 0:
                st.error("Amount must be greater than 0.")
            else:
                db.add_transaction(txn_date, description, category, amount, txn_type)
                st.success(f"Added {txn_type.lower()} of ${amount:,.2f} in {category}.")


# ================================================================ IMPORT ====
elif st.session_state.page == "📁 Import CSV":
    st.title("📁 Import CSV")
    st.write(
        "Upload a CSV export from your bank or card. You'll map its columns to the "
        "fields the dashboard needs, preview the result, then confirm the import."
    )

    st.download_button(
        "Download sample CSV format",
        data="date,description,category,amount,type\n"
        "2026-08-01,Paycheck,Salary,3200.00,Income\n"
        "2026-08-02,Whole Foods,Groceries,84.32,Expense\n"
        "2026-08-03,Netflix,Entertainment,15.99,Expense\n",
        file_name="sample_transactions.csv",
        mime="text/csv",
    )

    uploaded = st.file_uploader("Choose a CSV file", type=["csv"])
    if uploaded:
        try:
            raw = pd.read_csv(uploaded)
        except Exception as e:
            st.error(f"Could not read that file: {e}")
            raw = None

        if raw is not None and not raw.empty:
            st.subheader("Map your columns")
            cols = list(raw.columns)

            c1, c2 = st.columns(2)
            with c1:
                col_date = st.selectbox("Date column", cols)
                col_desc = st.selectbox("Description column", ["(none)"] + cols)
                col_cat = st.selectbox("Category column", ["(none)"] + cols)
            with c2:
                col_amount = st.selectbox("Amount column", cols)
                col_type = st.selectbox("Type column (Income/Expense)", ["(none)"] + cols)
                default_type = st.selectbox(
                    "If no type column, treat amounts as", ["Expense", "Income", "Auto (sign of amount)"]
                )
            default_category = st.selectbox("If no category column, default category to", db.DEFAULT_CATEGORIES)

            preview = pd.DataFrame()
            preview["date"] = pd.to_datetime(raw[col_date], errors="coerce")
            preview["description"] = raw[col_desc] if col_desc != "(none)" else ""
            preview["category"] = raw[col_cat] if col_cat != "(none)" else default_category

            amounts = pd.to_numeric(raw[col_amount], errors="coerce")

            if col_type != "(none)":
                preview["type"] = raw[col_type].str.title()
                preview["amount"] = amounts.abs()
            elif default_type == "Auto (sign of amount)":
                preview["type"] = amounts.apply(lambda x: "Income" if x >= 0 else "Expense")
                preview["amount"] = amounts.abs()
            else:
                preview["type"] = default_type
                preview["amount"] = amounts.abs()

            preview = preview.dropna(subset=["date", "amount"])

            st.subheader(f"Preview ({len(preview)} rows)")
            st.dataframe(preview, use_container_width=True, hide_index=True)

            if st.button("Confirm Import", type="primary", disabled=preview.empty):
                rows = [
                    (r.date.strftime("%Y-%m-%d"), r.description, r.category, float(r.amount), r.type)
                    for r in preview.itertuples()
                ]
                db.add_transactions_bulk(rows)
                st.success(f"Imported {len(rows)} transactions.")


# ================================================================ BUDGETS ===
elif st.session_state.page == "🎯 Budgets":
    st.title("🎯 Budgets")
    st.write("Set a monthly spending limit per category. These show up as budget-vs-actual bars on the Dashboard.")

    budgets = db.get_budgets()

    with st.form("budget_form"):
        c1, c2 = st.columns(2)
        with c1:
            category = st.selectbox("Category", db.DEFAULT_CATEGORIES)
        with c2:
            limit = st.number_input("Monthly limit", min_value=0.0, step=10.0, format="%.2f")
        if st.form_submit_button("Save Budget", type="primary"):
            db.set_budget(category, limit)
            st.success(f"Budget for {category} set to ${limit:,.2f}/month.")
            st.rerun()

    if budgets:
        st.subheader("Current Budgets")
        for cat, limit in budgets.items():
            c1, c2, c3 = st.columns([3, 2, 1])
            c1.write(cat)
            c2.write(f"${limit:,.2f}/month")
            if c3.button("Remove", key=f"rm_{cat}"):
                db.delete_budget(cat)
                st.rerun()
    else:
        st.caption("No budgets set yet.")
