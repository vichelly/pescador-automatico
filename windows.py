"""Parte do macro específica do Windows: teclas, tela acordada e som.

Usa só a biblioteca padrão (ctypes e winsound). As teclas vão por SendInput como
caracteres Unicode, então não dependem do layout do teclado nem da área de
transferência.
"""
from __future__ import annotations

import ctypes
import time
import winsound
from ctypes import wintypes
from pathlib import Path

DISCORD_EXES = {"discord.exe", "discordptb.exe", "discordcanary.exe"}

SW_RESTORE = 9
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
VK_RETURN = 0x0D
VK_CONTROL = 0x11
VK_K = 0x4B
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002
ES_CONTINUOUS = 0x80000000


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class MOUSEINPUT(ctypes.Structure):  # só para o union ter o tamanho que o Windows espera
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]


WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
user32.GetForegroundWindow.restype = wintypes.HWND
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.IsIconic.argtypes = [wintypes.HWND]
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
user32.SendInput.restype = wintypes.UINT
kernel32.GetCurrentThreadId.restype = wintypes.DWORD
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.LPWSTR,
    ctypes.POINTER(wintypes.DWORD),
]
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.SetThreadExecutionState.argtypes = [wintypes.DWORD]
kernel32.SetThreadExecutionState.restype = wintypes.DWORD


def exe_name(hwnd: int) -> str:
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    if not handle:
        return ""
    try:
        buffer = ctypes.create_unicode_buffer(1024)
        size = wintypes.DWORD(len(buffer))
        if not kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return ""
        return Path(buffer.value).name.lower()
    finally:
        kernel32.CloseHandle(handle)


def window_title(hwnd: int) -> str:
    buffer = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(hwnd, buffer, len(buffer))
    return buffer.value


def find_discord() -> int:
    found: list[int] = []

    @WNDENUMPROC
    def check(hwnd, _param):
        if (
            user32.IsWindowVisible(hwnd)
            and window_title(hwnd).endswith("Discord")
            and exe_name(hwnd) in DISCORD_EXES
        ):
            found.append(hwnd)
            return False
        return True

    user32.EnumWindows(check, 0)
    if not found:
        raise OSError("Janela do Discord não encontrada (ele está aberto e fora da bandeja?).")
    return found[0]


def focus(hwnd: int) -> None:
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)
    # O Windows só deixa trocar o foco quem está ligado à thread da janela em foco.
    current = kernel32.GetCurrentThreadId()
    foreground = user32.GetForegroundWindow()
    fg_thread = user32.GetWindowThreadProcessId(foreground, None) if foreground else 0
    attached = bool(fg_thread and fg_thread != current and user32.AttachThreadInput(current, fg_thread, True))
    try:
        user32.SetForegroundWindow(hwnd)
    finally:
        if attached:
            user32.AttachThreadInput(current, fg_thread, False)


def key(vk: int, up: bool = False) -> INPUT:
    flags = KEYEVENTF_KEYUP if up else 0
    return INPUT(type=INPUT_KEYBOARD, u=_INPUTUNION(ki=KEYBDINPUT(wVk=vk, dwFlags=flags)))


def char(unit: int, up: bool = False) -> INPUT:
    flags = KEYEVENTF_UNICODE | (KEYEVENTF_KEYUP if up else 0)
    return INPUT(type=INPUT_KEYBOARD, u=_INPUTUNION(ki=KEYBDINPUT(wScan=unit, dwFlags=flags)))


def send_keys(hwnd: int, *inputs: INPUT) -> None:
    """Só envia com a janela em foco, para nunca digitar em outro programa."""
    if user32.GetForegroundWindow() != hwnd:
        raise OSError("O Discord perdeu o foco; envio cancelado.")
    array = (INPUT * len(inputs))(*inputs)
    if user32.SendInput(len(inputs), array, ctypes.sizeof(INPUT)) != len(inputs):
        raise ctypes.WinError(ctypes.get_last_error())


def type_text(hwnd: int, text: str) -> None:
    data = text.encode("utf-16-le")
    for i in range(0, len(data), 2):
        unit = int.from_bytes(data[i:i + 2], "little")
        send_keys(hwnd, char(unit), char(unit, up=True))
        time.sleep(0.02)


def press_enter(hwnd: int) -> None:
    send_keys(hwnd, key(VK_RETURN), key(VK_RETURN, up=True))


def send_command(cmd: str, query: str) -> None:
    previous = user32.GetForegroundWindow()
    hwnd = find_discord()
    focus(hwnd)
    try:
        time.sleep(1.0)
        send_keys(hwnd, key(VK_CONTROL), key(VK_K), key(VK_K, up=True), key(VK_CONTROL, up=True))
        time.sleep(0.6)
        type_text(hwnd, query)
        time.sleep(1.0)
        press_enter(hwnd)
        time.sleep(1.2)
        type_text(hwnd, cmd)
        time.sleep(0.6)
        press_enter(hwnd)
        time.sleep(0.5)
    finally:
        if previous and previous != hwnd:
            focus(previous)


def keep_awake(on: bool) -> None:
    """Vale para a thread que chamou, que precisa continuar viva enquanto o macro roda."""
    flags = ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED if on else 0
    kernel32.SetThreadExecutionState(ES_CONTINUOUS | flags)


def play_sound() -> None:
    winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS | winsound.SND_ASYNC)
