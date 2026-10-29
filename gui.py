#!/usr/bin/env python3
"""Interface do macro do Discord.  Uso: python3 gui.py"""
from __future__ import annotations

import queue
import subprocess
import time
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

import macro


def parse_time(text: str) -> int:
    """'10:40' = 10min40s; '8:00:00' = 8h; '15' = 15 min. Retorna segundos."""
    parts = [int(p) for p in text.strip().split(":")]
    if len(parts) == 1:
        return parts[0] * 60
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    raise ValueError(text)


def fmt_time(sec: int) -> str:
    h, rest = divmod(int(sec), 3600)
    m, s = divmod(rest, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


class TaskRow:
    def __init__(self, parent: ttk.Frame, row: int, task: dict, on_remove):
        self.enabled = tk.BooleanVar(value=task.get("enabled", True))
        self.on_start = tk.BooleanVar(value=task.get("on_start", False))
        self.cmds = tk.StringVar(value=", ".join(task["cmds"]))
        self.lo = tk.StringVar(value=fmt_time(task["lo"]))
        self.hi = tk.StringVar(value=fmt_time(task["hi"]))
        self.next_label = tk.StringVar(value="-")
        self.widgets = [
            ttk.Checkbutton(parent, variable=self.enabled),
            ttk.Entry(parent, textvariable=self.cmds, width=38),
            ttk.Entry(parent, textvariable=self.lo, width=9, justify="center"),
            ttk.Entry(parent, textvariable=self.hi, width=9, justify="center"),
            ttk.Checkbutton(parent, variable=self.on_start),
            ttk.Label(parent, textvariable=self.next_label, width=12, anchor="center"),
            ttk.Button(parent, text="✕", width=3, command=lambda: on_remove(self)),
        ]
        for col, w in enumerate(self.widgets):
            w.grid(row=row, column=col, padx=4, pady=3)

    def destroy(self) -> None:
        for w in self.widgets:
            w.destroy()

    def to_task(self) -> dict:
        cmds = [c.strip() for c in self.cmds.get().split(",") if c.strip()]
        if not cmds:
            raise ValueError("Informe ao menos um comando.")
        lo, hi = parse_time(self.lo.get()), parse_time(self.hi.get())
        if lo <= 0 or hi < lo:
            raise ValueError(f"Intervalo inválido para {cmds[0]}: o mínimo deve ser > 0 e <= máximo.")
        return {
            "enabled": self.enabled.get(),
            "cmds": cmds,
            "lo": lo,
            "hi": hi,
            "on_start": self.on_start.get(),
        }


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Macro Discord - Guifons Empire")
        self.resizable(False, False)
        self.runner: macro.Runner | None = None
        self.caffeinate: subprocess.Popen | None = None
        self.logs: queue.Queue[str] = queue.Queue()
        self.rows: list[TaskRow] = []
        self.active_rows: list[TaskRow] = []

        config = macro.load_config()
        frame = ttk.Frame(self, padding=12)
        frame.pack()

        ttk.Label(
            frame,
            text="Comandos: separe por vírgula para sortear entre eles. "
            "Tempos em mm:ss ou h:mm:ss (ex.: 10:40 ou 8:00:00).",
        ).pack(anchor="w")

        self.table = ttk.Frame(frame)
        self.table.pack(pady=6)
        for col, title in enumerate(["Ativo", "Comando(s)", "Mínimo", "Máximo", "Ao iniciar", "Próximo em", ""]):
            ttk.Label(self.table, text=title, font=("", 0, "bold")).grid(row=0, column=col, padx=4)
        for task in config["tasks"]:
            self.add_row(task)

        ttk.Button(frame, text="+ Adicionar comando", command=self.add_blank_row).pack(anchor="w")

        limit = ttk.Frame(frame)
        limit.pack(anchor="w", pady=8)
        ttk.Label(limit, text="Tempo máximo de execução:").pack(side="left")
        h, m = divmod(config.get("max_seconds", 0) // 60, 60)
        self.max_h = tk.StringVar(value=str(h))
        self.max_m = tk.StringVar(value=str(m))
        ttk.Entry(limit, textvariable=self.max_h, width=4, justify="center").pack(side="left", padx=(8, 2))
        ttk.Label(limit, text="h").pack(side="left")
        ttk.Entry(limit, textvariable=self.max_m, width=4, justify="center").pack(side="left", padx=(8, 2))
        ttk.Label(limit, text="min   (0 e 0 = sem limite)").pack(side="left")
        self.remaining = tk.StringVar(value="")
        ttk.Label(limit, textvariable=self.remaining).pack(side="left", padx=12)

        # Lido pela thread do macro; por isso é um bool simples e não uma variável do Tk.
        self.sound_on = bool(config.get("sound", False))
        self.sound_var = tk.BooleanVar(value=self.sound_on)
        ttk.Checkbutton(
            frame,
            text="🔔 Tocar som a cada comando enviado (desligue para parar o aviso)",
            variable=self.sound_var,
            command=self.toggle_sound,
        ).pack(anchor="w", pady=(0, 8))

        buttons = ttk.Frame(frame)
        buttons.pack(anchor="w")
        self.start_btn = ttk.Button(buttons, text="▶ Iniciar", command=self.start)
        self.start_btn.pack(side="left")
        self.stop_btn = ttk.Button(buttons, text="■ Parar", command=self.stop, state="disabled")
        self.stop_btn.pack(side="left", padx=6)
        ttk.Button(buttons, text="Salvar", command=self.save).pack(side="left")
        self.status = tk.StringVar(value="Parado")
        ttk.Label(buttons, textvariable=self.status).pack(side="left", padx=12)

        self.log_box = tk.Text(frame, height=12, width=95, state="disabled")
        self.log_box.pack(pady=(8, 0))

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(500, self.tick)

    def add_row(self, task: dict) -> None:
        self.rows.append(TaskRow(self.table, len(self.rows) + 1, task, self.remove_row))

    def add_blank_row(self) -> None:
        self.add_row({"enabled": True, "cmds": ["$"], "lo": 600, "hi": 720, "on_start": False})

    def remove_row(self, row: TaskRow) -> None:
        if self.runner:
            messagebox.showinfo("Macro rodando", "Pare o macro antes de remover comandos.")
            return
        row.destroy()
        self.rows.remove(row)

    def toggle_sound(self) -> None:
        self.sound_on = self.sound_var.get()
        if self.sound_on:
            self.play_sound()  # toca uma vez para testar o volume
        self.log("Aviso sonoro " + ("ligado." if self.sound_on else "desligado."))

    def play_sound(self, _cmd: str = "") -> None:
        if self.sound_on:
            subprocess.Popen(["afplay", "/System/Library/Sounds/Glass.aiff"])

    def collect(self) -> dict:
        tasks = [r.to_task() for r in self.rows]
        try:
            max_seconds = int(self.max_h.get() or 0) * 3600 + int(self.max_m.get() or 0) * 60
        except ValueError:
            raise ValueError("Tempo máximo inválido: use números inteiros em horas e minutos.")
        return {"max_seconds": max_seconds, "sound": self.sound_var.get(), "tasks": tasks}

    def save(self) -> dict | None:
        try:
            config = self.collect()
        except ValueError as e:
            messagebox.showerror("Configuração inválida", str(e))
            return None
        macro.save_config(config)
        return config

    def log(self, msg: str) -> None:
        self.logs.put(f"[{datetime.now():%H:%M:%S}] {msg}\n")

    def start(self) -> None:
        config = self.save()
        if config is None:
            return
        self.active_rows = [r for r, t in zip(self.rows, config["tasks"]) if t["enabled"]]
        tasks = [t for t in config["tasks"] if t["enabled"]]
        if not tasks:
            messagebox.showwarning("Nada para rodar", "Ative pelo menos um comando.")
            return
        # Mantém o Mac acordado e com a tela ativa enquanto o macro roda.
        self.caffeinate = subprocess.Popen(["caffeinate", "-dimsu"])
        self.runner = macro.Runner(tasks, config["max_seconds"], log=self.log, on_send=self.play_sound)
        self.runner.start()
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.status.set("Rodando")

    def stop(self) -> None:
        if self.runner:
            self.runner.stop()
            self.log("Parado pelo usuário.")
            self.finish()

    def finish(self) -> None:
        self.runner = None
        if self.caffeinate:
            self.caffeinate.terminate()
            self.caffeinate = None
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.status.set("Parado")
        self.remaining.set("")
        for r in self.rows:
            r.next_label.set("-")

    def tick(self) -> None:
        while not self.logs.empty():
            self.log_box.config(state="normal")
            self.log_box.insert("end", self.logs.get())
            self.log_box.see("end")
            self.log_box.config(state="disabled")
        if self.runner:
            if self.runner.stop_event.is_set():  # terminou sozinho (limite de tempo)
                self.finish()
            else:
                now = time.time()
                for row, nxt in zip(self.active_rows, self.runner.next_run):
                    row.next_label.set(macro.fmt_secs(max(0, nxt - now)))
                if self.runner.end_time:
                    self.remaining.set(f"Encerra em {macro.fmt_secs(max(0, self.runner.end_time - now))}")
        self.after(500, self.tick)

    def on_close(self) -> None:
        if self.runner:
            self.runner.stop()
        if self.caffeinate:
            self.caffeinate.terminate()
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
