"""Simple personal To‑Do app for Windows 11.

Run by double-clicking this .pyw file (uses pythonw.exe, no console window).
Tasks are saved to %APPDATA%\\PersonalTodo\\tasks.json.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk
from uuid import uuid4


APP_DIR = Path(os.getenv("APPDATA", Path.home())) / "PersonalTodo"
TASK_FILE = APP_DIR / "tasks.json"


@dataclass
class Task:
    id: str
    text: str
    done: bool = False


class TodoApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Personal To-Do")
        self.geometry("560x420")
        self.minsize(420, 320)

        self.tasks: list[Task] = []
        self._build_ui()
        self._load_tasks()
        self._refresh_list()

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # Top input row
        top = ttk.Frame(self, padding=10)
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(0, weight=1)

        self.task_var = tk.StringVar()
        entry = ttk.Entry(top, textvariable=self.task_var)
        entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        entry.bind("<Return>", lambda _e: self.add_task())

        add_btn = ttk.Button(top, text="Add Task", command=self.add_task)
        add_btn.grid(row=0, column=1)

        # List and scrollbar
        center = ttk.Frame(self, padding=(10, 0, 10, 10))
        center.grid(row=1, column=0, sticky="nsew")
        center.columnconfigure(0, weight=1)
        center.rowconfigure(0, weight=1)

        self.listbox = tk.Listbox(center, activestyle="none", selectmode=tk.EXTENDED)
        self.listbox.grid(row=0, column=0, sticky="nsew")

        scroll = ttk.Scrollbar(center, orient="vertical", command=self.listbox.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.listbox.configure(yscrollcommand=scroll.set)

        self.listbox.bind("<Double-Button-1>", lambda _e: self.toggle_selected())

        # Bottom action row
        actions = ttk.Frame(self, padding=10)
        actions.grid(row=2, column=0, sticky="ew")

        ttk.Button(actions, text="Toggle Done", command=self.toggle_selected).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(actions, text="Delete", command=self.delete_selected).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(actions, text="Clear Completed", command=self.clear_completed).pack(
            side="left"
        )

        ttk.Button(actions, text="Save", command=self.save_tasks).pack(side="right")

    def _load_tasks(self) -> None:
        if not TASK_FILE.exists():
            return

        try:
            payload = json.loads(TASK_FILE.read_text(encoding="utf-8"))
            self.tasks = [Task(**item) for item in payload]
        except (json.JSONDecodeError, OSError, TypeError, ValueError):
            messagebox.showwarning(
                "Load issue",
                f"Could not read tasks from:\n{TASK_FILE}\n\nStarting with an empty list.",
            )
            self.tasks = []

    def save_tasks(self) -> None:
        try:
            APP_DIR.mkdir(parents=True, exist_ok=True)
            payload = [asdict(task) for task in self.tasks]
            TASK_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("Save failed", f"Could not save tasks:\n{exc}")
            return

        self.title("Personal To-Do ✓ saved")
        self.after(1500, lambda: self.title("Personal To-Do"))

    def add_task(self) -> None:
        text = self.task_var.get().strip()
        if not text:
            return

        self.tasks.append(Task(id=str(uuid4()), text=text, done=False))
        self.task_var.set("")
        self._refresh_list()
        self.save_tasks()

    def _selected_indexes(self) -> list[int]:
        return list(self.listbox.curselection())

    def toggle_selected(self) -> None:
        indexes = self._selected_indexes()
        if not indexes:
            return

        for idx in indexes:
            self.tasks[idx].done = not self.tasks[idx].done
        self._refresh_list()
        self.save_tasks()

    def delete_selected(self) -> None:
        indexes = self._selected_indexes()
        if not indexes:
            return

        for idx in sorted(indexes, reverse=True):
            del self.tasks[idx]

        self._refresh_list()
        self.save_tasks()

    def clear_completed(self) -> None:
        before = len(self.tasks)
        self.tasks = [task for task in self.tasks if not task.done]
        if len(self.tasks) == before:
            return

        self._refresh_list()
        self.save_tasks()

    def _refresh_list(self) -> None:
        self.listbox.delete(0, tk.END)
        for task in self.tasks:
            marker = "✓" if task.done else "•"
            self.listbox.insert(tk.END, f"{marker} {task.text}")


if __name__ == "__main__":
    app = TodoApp()
    app.mainloop()
