# T & M Financial Dashboard

A personal Streamlit app for analyzing credit card statements and bank account activity exported from Israeli banks.

## How to Run

```bash
# Install dependencies (first time only)
pip install -r requirements.txt

# Launch the app
streamlit run app.py
```

The app will open automatically at `http://localhost:8501`.

## Default Folders (auto-load)

So you don't have to upload files manually every time, the app can load them
straight from local folders. Copy the template and set your paths:

```bash
cp config.example.ini config.ini
```

Then edit `config.ini`:

```ini
[paths]
credits = /path/to/your/credits/
bills   = /path/to/your/Bills/
```

On launch, every supported file in those folders is loaded automatically
(`credits` → Credit tab, `bills` → Bank tab). Each tab has an **"Auto-load …
from default folder"** checkbox to toggle this, and you can still upload extra
files on top. `config.ini` is git-ignored since it holds personal paths.

## Features

### Credit Card Analysis (Tab 1)
- Upload one or more credit card exports (`.csv` or `.xlsx`)
- Auto-detects Hebrew column headers from various Israeli bank formats
- Filter by period and category using the sidebar
- Toggle between **calendar month** and **10th-to-10th billing cycle** views
- Pie chart breakdown per period
- Side-by-side bar chart comparing months with an average overlay
- Full transaction table with total for the selected period

### Bank Account Activity (Tab 2)
- Upload bank statement exports (`.csv`, `.xls`, `.xlsx`)
- Monthly income (זכות) vs. expenses (חובה) bar chart
- Detailed transaction table with per-month income/expense/net summary

## Supported File Formats

| Source | Format |
|---|---|
| Credit card statements | `.csv` (windows-1255 or UTF-8), `.xlsx` |
| Bank statements | `.csv`, `.xls`, `.xlsx` |

The app automatically scans the first 20 rows to find the real header row, so exported files with metadata rows at the top work out of the box.
