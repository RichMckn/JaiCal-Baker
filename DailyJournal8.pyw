import json
import sqlite3
from datetime import datetime, date
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

APP_TITLE = "Daily Journal 8"
DB_NAME = "daily_journal.db"
DATE_FMT = "%Y-%m-%d"

PROMPTS = [
    "What made today meaningful?",
    "What am I grateful for right now?",
    "What challenge did I face and how did I respond?",
    "What would I like to improve tomorrow?",
    "How did I care for my mind and body today?",
]


class JournalDB:
    def __init__(self, db_path: Path):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS entries (
                entry_date TEXT PRIMARY KEY,
                title TEXT NOT NULL DEFAULT '',
                mood TEXT NOT NULL DEFAULT '',
                tags TEXT NOT NULL DEFAULT '',
                content TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self.conn.commit()

    def upsert_entry(self, entry_date, title, mood, tags, content):
        now = datetime.now().isoformat(timespec="seconds")
        self.conn.execute(
            """
            INSERT INTO entries (entry_date, title, mood, tags, content, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(entry_date) DO UPDATE SET
                title=excluded.title,
                mood=excluded.mood,
                tags=excluded.tags,
                content=excluded.content,
                updated_at=excluded.updated_at
            """,
            (entry_date, title, mood, tags, content, now, now),
        )
        self.conn.commit()

    def delete_entry(self, entry_date):
        self.conn.execute("DELETE FROM entries WHERE entry_date = ?", (entry_date,))
        self.conn.commit()

    def get_entry(self, entry_date):
        row = self.conn.execute(
            "SELECT * FROM entries WHERE entry_date = ?", (entry_date,)
        ).fetchone()
        return dict(row) if row else None

    def list_entries(self, search_text=""):
        search_text = search_text.strip()
        if not search_text:
            query = "SELECT entry_date, title, mood FROM entries ORDER BY entry_date DESC"
            rows = self.conn.execute(query).fetchall()
        else:
            query = (
                "SELECT entry_date, title, mood FROM entries "
                "WHERE title LIKE ? OR tags LIKE ? OR content LIKE ? "
                "ORDER BY entry_date DESC"
            )
            term = f"%{search_text}%"
            rows = self.conn.execute(query, (term, term, term)).fetchall()
        return [dict(r) for r in rows]

    def export_all(self):
        rows = self.conn.execute(
            "SELECT entry_date, title, mood, tags, content, created_at, updated_at "
            "FROM entries ORDER BY entry_date"
        ).fetchall()
        return [dict(r) for r in rows]


class DailyJournalApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1100x680")
        self.minsize(980, 620)

        self.db = JournalDB(Path(__file__).with_name(DB_NAME))
        self.current_date = tk.StringVar(value=date.today().strftime(DATE_FMT))
        self.search_text = tk.StringVar()
        self.title_text = tk.StringVar()
        self.mood_text = tk.StringVar()
        self.tags_text = tk.StringVar()
        self.prompt_text = tk.StringVar(value=PROMPTS[0])
        self.status_text = tk.StringVar(value="Ready")

        self._build_ui()
        self.refresh_entries(select_date=self.current_date.get())
        self.load_entry(self.current_date.get(), create_if_missing=False)

    def _build_ui(self):
        outer = ttk.Frame(self, padding=10)
        outer.pack(fill="both", expand=True)

        toolbar = ttk.Frame(outer)
        toolbar.pack(fill="x", pady=(0, 8))

        ttk.Label(toolbar, text="Date (YYYY-MM-DD):").pack(side="left")
        self.date_entry = ttk.Entry(toolbar, textvariable=self.current_date, width=14)
        self.date_entry.pack(side="left", padx=(6, 6))

        ttk.Button(toolbar, text="Today", command=self.set_today).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Load", command=self.on_load_clicked).pack(side="left", padx=4)
        ttk.Button(toolbar, text="New", command=self.new_blank_entry).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Save", command=self.save_entry).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Delete", command=self.delete_entry).pack(side="left", padx=4)

        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=8)

        ttk.Button(toolbar, text="Export JSON", command=self.export_json).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Export TXT", command=self.export_text).pack(side="left", padx=4)

        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=8)

        ttk.Label(toolbar, text="Search:").pack(side="left")
        search_entry = ttk.Entry(toolbar, textvariable=self.search_text, width=24)
        search_entry.pack(side="left", padx=(6, 4))
        search_entry.bind("<Return>", lambda _e: self.refresh_entries())
        ttk.Button(toolbar, text="Go", command=self.refresh_entries).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Clear", command=self.clear_search).pack(side="left", padx=4)

        main = ttk.PanedWindow(outer, orient="horizontal")
        main.pack(fill="both", expand=True)

        left_frame = ttk.Frame(main, padding=(0, 0, 10, 0))
        main.add(left_frame, weight=1)

        ttk.Label(left_frame, text="Entries").pack(anchor="w")
        self.entries_list = tk.Listbox(left_frame, activestyle="dotbox")
        self.entries_list.pack(fill="both", expand=True, pady=(4, 0))
        self.entries_list.bind("<<ListboxSelect>>", self.on_list_select)

        right_frame = ttk.Frame(main)
        main.add(right_frame, weight=4)

        form = ttk.Frame(right_frame)
        form.pack(fill="x")

        ttk.Label(form, text="Title:").grid(row=0, column=0, sticky="w", pady=2)
        ttk.Entry(form, textvariable=self.title_text).grid(row=0, column=1, sticky="ew", pady=2)

        ttk.Label(form, text="Mood:").grid(row=1, column=0, sticky="w", pady=2)
        mood_combo = ttk.Combobox(
            form,
            textvariable=self.mood_text,
            values=["Great", "Good", "Okay", "Low", "Struggling"],
            state="normal",
        )
        mood_combo.grid(row=1, column=1, sticky="ew", pady=2)

        ttk.Label(form, text="Tags (comma separated):").grid(row=2, column=0, sticky="w", pady=2)
        ttk.Entry(form, textvariable=self.tags_text).grid(row=2, column=1, sticky="ew", pady=2)

        ttk.Label(form, text="Prompt:").grid(row=3, column=0, sticky="w", pady=2)
        prompt_combo = ttk.Combobox(form, textvariable=self.prompt_text, values=PROMPTS, state="readonly")
        prompt_combo.grid(row=3, column=1, sticky="ew", pady=2)

        form.columnconfigure(1, weight=1)

        ttk.Label(right_frame, text="Journal Entry").pack(anchor="w", pady=(10, 4))
        self.content_text = tk.Text(right_frame, wrap="word", undo=True)
        self.content_text.pack(fill="both", expand=True)
        self.content_text.bind("<<Modified>>", self.on_text_modified)

        meta = ttk.Frame(right_frame)
        meta.pack(fill="x", pady=(6, 0))
        self.word_count_label = ttk.Label(meta, text="Words: 0")
        self.word_count_label.pack(side="left")

        ttk.Label(meta, textvariable=self.status_text).pack(side="right")

    def validate_date(self, value):
        try:
            datetime.strptime(value, DATE_FMT)
            return True
        except ValueError:
            return False

    def set_status(self, text):
        self.status_text.set(text)

    def set_today(self):
        today = date.today().strftime(DATE_FMT)
        self.current_date.set(today)
        self.load_entry(today, create_if_missing=True)

    def clear_search(self):
        self.search_text.set("")
        self.refresh_entries()

    def on_load_clicked(self):
        entry_date = self.current_date.get().strip()
        self.load_entry(entry_date, create_if_missing=True)

    def new_blank_entry(self):
        self.title_text.set("")
        self.mood_text.set("")
        self.tags_text.set("")
        self.content_text.delete("1.0", "end")
        self.update_word_count()
        self.set_status("New blank entry ready")

    def get_content(self):
        return self.content_text.get("1.0", "end").rstrip()

    def save_entry(self):
        entry_date = self.current_date.get().strip()
        if not self.validate_date(entry_date):
            messagebox.showerror("Invalid Date", "Please use YYYY-MM-DD format.")
            return

        title = self.title_text.get().strip()
        mood = self.mood_text.get().strip()
        tags = self.tags_text.get().strip()
        content = self.get_content()

        if not title:
            title = f"Journal Entry {entry_date}"

        self.db.upsert_entry(entry_date, title, mood, tags, content)
        self.refresh_entries(select_date=entry_date)
        self.set_status(f"Saved entry for {entry_date}")

    def delete_entry(self):
        entry_date = self.current_date.get().strip()
        if not self.validate_date(entry_date):
            messagebox.showerror("Invalid Date", "Please use YYYY-MM-DD format.")
            return
        if not self.db.get_entry(entry_date):
            messagebox.showinfo("Not Found", f"No entry exists for {entry_date}.")
            return
        if not messagebox.askyesno("Delete", f"Delete entry for {entry_date}?"):
            return
        self.db.delete_entry(entry_date)
        self.new_blank_entry()
        self.refresh_entries()
        self.set_status(f"Deleted entry for {entry_date}")

    def load_entry(self, entry_date, create_if_missing=False):
        if not self.validate_date(entry_date):
            messagebox.showerror("Invalid Date", "Please use YYYY-MM-DD format.")
            return

        row = self.db.get_entry(entry_date)
        if row:
            self.title_text.set(row["title"])
            self.mood_text.set(row["mood"])
            self.tags_text.set(row["tags"])
            self.content_text.delete("1.0", "end")
            self.content_text.insert("1.0", row["content"])
            self.set_status(f"Loaded entry for {entry_date}")
        else:
            self.new_blank_entry()
            if create_if_missing:
                self.title_text.set(f"Journal Entry {entry_date}")
            self.set_status(f"No entry found for {entry_date}; showing blank draft")

        self.current_date.set(entry_date)
        self.update_word_count()
        self.select_in_list(entry_date)

    def refresh_entries(self, select_date=None):
        rows = self.db.list_entries(self.search_text.get())
        self.entries_list.delete(0, "end")
        for item in rows:
            mood = f" [{item['mood']}]" if item["mood"] else ""
            title = item["title"] if item["title"] else "Untitled"
            self.entries_list.insert("end", f"{item['entry_date']} | {title}{mood}")

        if select_date:
            self.select_in_list(select_date)

    def select_in_list(self, entry_date):
        for idx in range(self.entries_list.size()):
            value = self.entries_list.get(idx)
            if value.startswith(entry_date):
                self.entries_list.selection_clear(0, "end")
                self.entries_list.selection_set(idx)
                self.entries_list.see(idx)
                return

    def on_list_select(self, _event):
        selection = self.entries_list.curselection()
        if not selection:
            return
        raw = self.entries_list.get(selection[0])
        entry_date = raw.split("|", 1)[0].strip()
        self.load_entry(entry_date, create_if_missing=False)

    def on_text_modified(self, _event):
        self.content_text.edit_modified(False)
        self.update_word_count()

    def update_word_count(self):
        content = self.get_content()
        words = len(content.split()) if content else 0
        self.word_count_label.configure(text=f"Words: {words}")

    def export_json(self):
        rows = self.db.export_all()
        if not rows:
            messagebox.showinfo("Export", "No entries to export yet.")
            return

        path = filedialog.asksaveasfilename(
            title="Export Journal as JSON",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=f"daily-journal-export-{date.today().strftime(DATE_FMT)}.json",
        )
        if not path:
            return

        with open(path, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=2, ensure_ascii=False)

        self.set_status(f"Exported {len(rows)} entries to JSON")
        messagebox.showinfo("Export Complete", f"Exported {len(rows)} entries to:\n{path}")

    def export_text(self):
        rows = self.db.export_all()
        if not rows:
            messagebox.showinfo("Export", "No entries to export yet.")
            return

        path = filedialog.asksaveasfilename(
            title="Export Journal as Text",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=f"daily-journal-export-{date.today().strftime(DATE_FMT)}.txt",
        )
        if not path:
            return

        blocks = []
        for row in rows:
            blocks.append(
                "\n".join(
                    [
                        f"Date: {row['entry_date']}",
                        f"Title: {row['title']}",
                        f"Mood: {row['mood']}",
                        f"Tags: {row['tags']}",
                        "-" * 40,
                        row["content"],
                        "=" * 70,
                    ]
                )
            )

        with open(path, "w", encoding="utf-8") as f:
            f.write("\n\n".join(blocks))

        self.set_status(f"Exported {len(rows)} entries to text")
        messagebox.showinfo("Export Complete", f"Exported {len(rows)} entries to:\n{path}")


if __name__ == "__main__":
    app = DailyJournalApp()
    app.mainloop()
