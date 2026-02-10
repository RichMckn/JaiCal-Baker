# Daily Journal 8 (Python `.pyw` app)

A lightweight desktop daily journal inspired by Journal 8 style journaling flow:

- One entry per day (`YYYY-MM-DD`)
- Quick mood + tags tracking
- Prompt-guided writing
- Search by title/tags/content
- Export all entries to JSON or TXT
- Local-only SQLite storage

## Run on Windows 11 Pro

1. Install Python 3.10+ from [python.org](https://www.python.org/downloads/windows/)
2. Make sure **tkinter** is included (default installer option)
3. Copy `DailyJournal8.pyw` to any folder
4. Double-click `DailyJournal8.pyw`

Because it uses `.pyw`, it opens as a GUI app with no terminal window.

## Data location

The app creates `daily_journal.db` in the same folder as `DailyJournal8.pyw`.

## Optional: make a desktop shortcut

- Right-click `DailyJournal8.pyw` → **Show more options** → **Send to** → **Desktop (create shortcut)**

