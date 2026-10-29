#!/usr/bin/env python3
"""Motor do macro do Discord (Guifons Empire, canal #fisherman).

Cada tarefa envia um comando (sorteado entre uma lista) num momento aleatório
dentro de uma janela [mín, máx] de segundos. As tarefas ficam em config.json
(editável pela interface: gui.py). Também dá para rodar direto no terminal:

    caffeinate -dimsu python3 macro.py

Usa o Quick Switcher do Discord (Cmd+K) e o osascript do macOS. Só usa a
biblioteca padrão. Parar: Ctrl+C.
"""
from __future__ import annotations

import json
import random
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

CONFIG_PATH = Path(__file__).with_name("config.json")
QUICK_SWITCH_QUERY = "#fisherman guifons"  # texto digitado no Cmd+K
MIN = 60

DEFAULT_CONFIG = {
    "max_seconds": 0,  # 0 = sem limite de tempo
    "tasks": [
        {"enabled": True, "cmds": ["$p"], "lo": 10 * MIN + 40, "hi": 13 * MIN + 36, "on_start": True},
        {"enabled": True, "cmds": ["$correr", "$supino", "$agachamento"], "lo": 35 * MIN, "hi": 42 * MIN, "on_start": False},
        {"enabled": True, "cmds": ["$presentear yor forger"], "lo": 8 * 60 * MIN, "hi": 8 * 60 * MIN + 5 * MIN, "on_start": False},
    ],
}


def load_config() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text())
    except (OSError, ValueError):
        return json.loads(json.dumps(DEFAULT_CONFIG))


def save_config(config: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False))


def osa(script: str) -> None:
    subprocess.run(["osascript", "-e", script], check=True)


def send_command(cmd: str) -> None:
    script = f'''
    set prevApp to (path to frontmost application as text)
    tell application "Discord" to activate
    delay 1.0
    tell application "System Events"
        tell process "Discord"
            keystroke "k" using command down
            delay 0.6
            keystroke "{QUICK_SWITCH_QUERY}"
            delay 1.0
            key code 36
            delay 1.2
            keystroke "{cmd}"
            delay 0.6
            key code 36
        end tell
    end tell
    delay 0.5
    tell application prevApp to activate
    '''
    osa(script)


def fmt_secs(total: float) -> str:
    h, rest = divmod(round(total), 3600)
    m, s = divmod(rest, 60)
    return f"{h}h{m:02d}min{s:02d}s" if h else f"{m}min{s:02d}s"


def default_log(msg: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


class Runner(threading.Thread):
    """Executa as tarefas até ser parado ou até estourar max_seconds (0 = sem limite)."""

    def __init__(self, tasks: list[dict], max_seconds: int = 0, log=default_log, on_send=None):
        super().__init__(daemon=True)
        self.tasks = tasks
        self.max_seconds = max_seconds
        self.log = log
        self.on_send = on_send  # chamado depois de cada comando enviado com sucesso
        self.stop_event = threading.Event()
        self.next_run: list[float] = []
        self.end_time: float | None = None

    def stop(self) -> None:
        self.stop_event.set()

    def run(self) -> None:
        now = time.time()
        self.end_time = now + self.max_seconds if self.max_seconds else None
        self.next_run = [
            now if t["on_start"] else now + random.uniform(t["lo"], t["hi"]) for t in self.tasks
        ]
        limite = f" (limite: {fmt_secs(self.max_seconds)})" if self.max_seconds else ""
        self.log(f"Macro iniciada{limite}.")
        while not self.stop_event.is_set():
            if self.end_time and time.time() >= self.end_time:
                self.log("Tempo limite atingido. Macro parada.")
                break
            for i, t in enumerate(self.tasks):  # ordem da lista decide quem vai primeiro
                if self.stop_event.is_set():
                    break
                if time.time() >= self.next_run[i]:
                    cmd = random.choice(t["cmds"])
                    try:
                        send_command(cmd)
                        self.log(f"Enviado {cmd}")
                        if self.on_send:
                            self.on_send(cmd)
                    except subprocess.CalledProcessError as e:
                        self.log(f"Falha ao enviar {cmd}: {e}")
                    delay = random.uniform(t["lo"], t["hi"])
                    self.next_run[i] = time.time() + delay
                    nome = t["cmds"][0] if len(t["cmds"]) == 1 else "treino"
                    self.log(f"Próximo {nome} em {fmt_secs(delay)}")
                    self.stop_event.wait(3)
            self.stop_event.wait(1)
        self.stop_event.set()


def main() -> None:
    config = load_config()
    tasks = [t for t in config["tasks"] if t.get("enabled", True)]
    runner = Runner(tasks, config.get("max_seconds", 0))
    try:
        runner.run()
    except KeyboardInterrupt:
        default_log("Parado.")


if __name__ == "__main__":
    main()
