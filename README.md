# Personal Finance Dashboard

A local Streamlit dashboard for tracking income/expenses, with manual entry,
CSV import, category charts, monthly trends, and budget-vs-actual tracking.
Data is stored in a local SQLite file (`finance.db`) — nothing leaves your machine.



- Go to **Import CSV** and upload `sample_transactions.csv` (included) to load a
  few months of sample data, then check out the **Dashboard** tab.
- Add a budget in the **Budgets** tab (e.g. "Groceries" → 400) to see the
  budget-vs-actual bars appear on the Dashboard.
- Add your own transactions manually via **Add Transaction**.

## Project structure

```
finance-dashboard/
├── app.py                   # Streamlit UI — all four pages
├── db.py                    # SQLite data layer (transactions + budgets)
├── requirements.txt
├── sample_transactions.csv  # sample data for testing CSV import
├── finance.db                # created automatically on first run
└── README.md
```

## Where to go next

Some natural extensions once you're comfortable with the code:
- Recurring transactions (rent, subscriptions) auto-added each month
- Multiple accounts/currencies
- Export filtered transactions back to CSV/PDF
- Auto-categorization of imported transactions using keyword rules
- Savings goals with progress tracking
- Swap SQLite for Postgres if you want to sync across devices


