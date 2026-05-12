#!/usr/bin/env python3
"""Simple GUI frontend for KeyMouse2Pad."""

from __future__ import annotations

import argparse
import json
import math
import os
import queue
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


BUTTON_BITS = {
    "A": 1 << 0,
    "B": 1 << 1,
    "X": 1 << 2,
    "Y": 1 << 3,
    "LB": 1 << 4,
    "RB": 1 << 5,
    "Back": 1 << 6,
    "Start": 1 << 7,
    "LS": 1 << 8,
    "RS": 1 << 9,
    "DUp": 1 << 10,
    "DDown": 1 << 11,
    "DLeft": 1 << 12,
    "DRight": 1 << 13,
}

X360_BUTTON_NAMES = {
    "A": "XUSB_GAMEPAD_A",
    "B": "XUSB_GAMEPAD_B",
    "X": "XUSB_GAMEPAD_X",
    "Y": "XUSB_GAMEPAD_Y",
    "LB": "XUSB_GAMEPAD_LEFT_SHOULDER",
    "RB": "XUSB_GAMEPAD_RIGHT_SHOULDER",
    "Back": "XUSB_GAMEPAD_BACK",
    "Start": "XUSB_GAMEPAD_START",
    "LS": "XUSB_GAMEPAD_LEFT_THUMB",
    "RS": "XUSB_GAMEPAD_RIGHT_THUMB",
    "DUp": "XUSB_GAMEPAD_DPAD_UP",
    "DDown": "XUSB_GAMEPAD_DPAD_DOWN",
    "DLeft": "XUSB_GAMEPAD_DPAD_LEFT",
    "DRight": "XUSB_GAMEPAD_DPAD_RIGHT",
}

APP_NAME = "KeyMouse2Pad"
CONFIG_DIR = Path(os.getenv("LOCALAPPDATA", Path.home())) / APP_NAME
CONFIG_PATH = CONFIG_DIR / "profile.json"

DEFAULT_PROFILE = {
    "buttons": {
        "A": ["space"],
        "B": ["control_l"],
        "X": ["e"],
        "Y": ["r"],
        "LB": ["q", "button4"],
        "RB": ["f", "button5"],
        "Back": ["tab"],
        "Start": ["return"],
        "LS": ["shift_l"],
        "RS": ["button2"],
        "DUp": ["up"],
        "DDown": ["down"],
        "DLeft": ["left"],
        "DRight": ["right"],
    },
    "triggers": {
        "LT": ["button3", "k"],
        "RT": ["button1", "j"],
    },
    "leftStick": {
        "left": ["a"],
        "right": ["d"],
        "down": ["s"],
        "up": ["w"],
    },
}


@dataclass
class GamepadState:
    left_x: int = 0
    left_y: int = 0
    right_x: int = 0
    right_y: int = 0
    left_trigger: int = 0
    right_trigger: int = 0
    buttons: int = 0

    def pressed(self, name: str) -> bool:
        return bool(self.buttons & BUTTON_BITS[name])

    def set_button(self, name: str, pressed: bool) -> None:
        if pressed:
            self.buttons |= BUTTON_BITS[name]
        else:
            self.buttons &= ~BUTTON_BITS[name]


@dataclass
class InputSnapshot:
    keys: set[str] = field(default_factory=set)
    mouse_buttons: set[str] = field(default_factory=set)
    mouse_dx: int = 0
    mouse_dy: int = 0


@dataclass
class AnalogSettings:
    deadzone: float = 0.05
    left_ramp_up_per_second: float = 18.0
    left_ramp_down_per_second: float = 24.0
    mouse_sensitivity: float = 0.018
    mouse_smoothing: float = 0.35
    mouse_recenter_per_second: float = 7.5


def normalize_input_name(value: str) -> str:
    token = value.strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "ctrl": "control_l",
        "control": "control_l",
        "leftctrl": "control_l",
        "left_ctrl": "control_l",
        "shift": "shift_l",
        "leftshift": "shift_l",
        "left_shift": "shift_l",
        "enter": "return",
        "esc": "escape",
        "mouse_left": "button1",
        "left_click": "button1",
        "lbutton": "button1",
        "mouse_middle": "button2",
        "middle_click": "button2",
        "mbutton": "button2",
        "mouse_right": "button3",
        "right_click": "button3",
        "rbutton": "button3",
        "mouse4": "button4",
        "x1": "button4",
        "mouse5": "button5",
        "x2": "button5",
    }
    return aliases.get(token, token)


def parse_inputs(value: str | list[str] | set[str]) -> set[str]:
    if isinstance(value, str):
        raw_values = value.split(",")
    else:
        raw_values = list(value)
    return {normalize_input_name(item) for item in raw_values if normalize_input_name(item)}


def format_inputs(values: set[str] | list[str]) -> str:
    return ", ".join(sorted(values))


def input_active(input_state: InputSnapshot, inputs: set[str]) -> bool:
    return bool(inputs & input_state.keys) or bool(inputs & input_state.mouse_buttons)


@dataclass
class MappingProfile:
    button_inputs: dict[str, set[str]]
    left_trigger_inputs: set[str]
    right_trigger_inputs: set[str]
    left_stick: dict[str, set[str]]

    @classmethod
    def defaults(cls) -> "MappingProfile":
        return cls.from_dict(DEFAULT_PROFILE)

    @classmethod
    def from_dict(cls, data: dict) -> "MappingProfile":
        buttons = data.get("buttons", {})
        triggers = data.get("triggers", {})
        left_stick = data.get("leftStick", {})
        return cls(
            button_inputs={
                button: parse_inputs(buttons.get(button, DEFAULT_PROFILE["buttons"].get(button, [])))
                for button in BUTTON_BITS
            },
            left_trigger_inputs=parse_inputs(triggers.get("LT", DEFAULT_PROFILE["triggers"]["LT"])),
            right_trigger_inputs=parse_inputs(triggers.get("RT", DEFAULT_PROFILE["triggers"]["RT"])),
            left_stick={
                direction: parse_inputs(left_stick.get(direction, DEFAULT_PROFILE["leftStick"][direction]))
                for direction in ("left", "right", "down", "up")
            },
        )

    def to_dict(self) -> dict:
        return {
            "buttons": {button: sorted(values) for button, values in self.button_inputs.items()},
            "triggers": {
                "LT": sorted(self.left_trigger_inputs),
                "RT": sorted(self.right_trigger_inputs),
            },
            "leftStick": {direction: sorted(values) for direction, values in self.left_stick.items()},
        }

    def mapped_inputs(self) -> set[str]:
        inputs: set[str] = set()
        for values in self.button_inputs.values():
            inputs.update(values)
        inputs.update(self.left_trigger_inputs)
        inputs.update(self.right_trigger_inputs)
        for values in self.left_stick.values():
            inputs.update(values)
        return inputs


def load_profile() -> MappingProfile:
    try:
        if CONFIG_PATH.exists():
            return MappingProfile.from_dict(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
    except Exception:
        pass
    return MappingProfile.defaults()


def save_profile(profile: MappingProfile) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(profile.to_dict(), indent=2), encoding="utf-8")


class MappingEngine:
    def __init__(self, profile: MappingProfile | None = None) -> None:
        self.analog = AnalogSettings()
        self.profile = profile or MappingProfile.defaults()
        self.left_x = 0.0
        self.left_y = 0.0
        self.right_x = 0.0
        self.right_y = 0.0

    def update(self, input_state: InputSnapshot, delta_seconds: float) -> GamepadState:
        delta_seconds = max(0.0, delta_seconds)
        state = GamepadState()

        for button, inputs in self.profile.button_inputs.items():
            state.set_button(button, input_active(input_state, inputs))

        state.left_trigger = 255 if input_active(input_state, self.profile.left_trigger_inputs) else 0
        state.right_trigger = 255 if input_active(input_state, self.profile.right_trigger_inputs) else 0

        target_left_x = self._axis(input_state, self.profile.left_stick["left"], self.profile.left_stick["right"])
        target_left_y = self._axis(input_state, self.profile.left_stick["down"], self.profile.left_stick["up"])
        if target_left_x and target_left_y:
            target_left_x *= math.sqrt(0.5)
            target_left_y *= math.sqrt(0.5)

        ramp_x = (
            self.analog.left_ramp_up_per_second
            if abs(target_left_x) > abs(self.left_x)
            else self.analog.left_ramp_down_per_second
        )
        ramp_y = (
            self.analog.left_ramp_up_per_second
            if abs(target_left_y) > abs(self.left_y)
            else self.analog.left_ramp_down_per_second
        )
        self.left_x = self._move_towards(self.left_x, target_left_x, ramp_x * delta_seconds)
        self.left_y = self._move_towards(self.left_y, target_left_y, ramp_y * delta_seconds)

        mouse_target_x = self._clamp(input_state.mouse_dx * self.analog.mouse_sensitivity)
        mouse_target_y = self._clamp(-input_state.mouse_dy * self.analog.mouse_sensitivity)
        smoothing = min(1.0, max(0.0, self.analog.mouse_smoothing))

        if input_state.mouse_dx or input_state.mouse_dy:
            self.right_x = self._clamp(self.right_x * smoothing + mouse_target_x * (1.0 - smoothing))
            self.right_y = self._clamp(self.right_y * smoothing + mouse_target_y * (1.0 - smoothing))
        else:
            recenter = self.analog.mouse_recenter_per_second * delta_seconds
            self.right_x = self._move_towards(self.right_x, 0.0, recenter)
            self.right_y = self._move_towards(self.right_y, 0.0, recenter)

        state.left_x = self._to_stick(self._apply_deadzone(self.left_x))
        state.left_y = self._to_stick(self._apply_deadzone(self.left_y))
        state.right_x = self._to_stick(self._apply_deadzone(self.right_x))
        state.right_y = self._to_stick(self._apply_deadzone(self.right_y))
        return state

    @staticmethod
    def _axis(input_state: InputSnapshot, negative: set[str], positive: set[str]) -> float:
        value = 0.0
        if input_active(input_state, negative):
            value -= 1.0
        if input_active(input_state, positive):
            value += 1.0
        return value

    @staticmethod
    def _move_towards(current: float, target: float, max_delta: float) -> float:
        if current < target:
            return min(current + max_delta, target)
        return max(current - max_delta, target)

    @staticmethod
    def _clamp(value: float) -> float:
        return min(1.0, max(-1.0, value))

    def _apply_deadzone(self, value: float) -> float:
        deadzone = min(0.95, max(0.0, self.analog.deadzone))
        if abs(value) < deadzone:
            return 0.0
        sign = -1.0 if value < 0.0 else 1.0
        return sign * ((abs(value) - deadzone) / (1.0 - deadzone))

    @staticmethod
    def _to_stick(value: float) -> int:
        value = min(1.0, max(-1.0, value))
        return round(value * (32767 if value >= 0 else 32768))


class WindowsControllerOutput:
    def __init__(self) -> None:
        self.available = False
        self.status = "Controller output: unavailable"
        self._gamepad = None
        self._button_map = {}

        try:
            import vgamepad

            self._gamepad = vgamepad.VX360Gamepad()
            self._button_map = {
                button: getattr(vgamepad.XUSB_BUTTON, xusb_name)
                for button, xusb_name in X360_BUTTON_NAMES.items()
            }
            self.available = True
            self.status = "Controller output: Xbox 360 active"
        except Exception as exc:
            self.status = f"Controller output: unavailable ({exc})"

    def submit(self, state: GamepadState) -> None:
        if not self.available or self._gamepad is None:
            return

        self._gamepad.left_joystick(x_value=state.left_x, y_value=state.left_y)
        self._gamepad.right_joystick(x_value=state.right_x, y_value=state.right_y)
        self._gamepad.left_trigger(value=state.left_trigger)
        self._gamepad.right_trigger(value=state.right_trigger)

        for button, xusb_button in self._button_map.items():
            if state.pressed(button):
                self._gamepad.press_button(button=xusb_button)
            else:
                self._gamepad.release_button(button=xusb_button)
        self._gamepad.update()

    def debug_buttons_value(self) -> int:
        if not self.available or self._gamepad is None:
            return 0
        return int(self._gamepad.report.wButtons)

    def reset(self) -> None:
        if not self.available or self._gamepad is None:
            return
        self._gamepad.reset()
        self._gamepad.update()


class GlobalInputCapture:
    def __init__(self) -> None:
        self.available = sys.platform == "win32"
        self.active = False
        self.block_original_input = False
        self.status = "Global capture: unavailable"
        self._input_state = InputSnapshot()
        self._hotkeys_down: set[str] = set()
        self._hotkeys: queue.SimpleQueue[str] = queue.SimpleQueue()
        self._lock = threading.RLock()
        self._blocked_key_names: set[str] = set()
        self._blocked_mouse_buttons: set[str] = {"button1", "button2", "button3", "button4", "button5"}
        self._last_mouse_pos: tuple[int, int] | None = None
        self._key_poll_map: dict[str, int] = {}
        self._vk_key_names: dict[int, str] = {}
        self._keyboard_hook = None
        self._mouse_hook = None
        self._keyboard_proc = None
        self._mouse_proc = None
        self._raw_mouse_active = False
        self._raw_mouse_thread: threading.Thread | None = None
        self._raw_mouse_thread_id = 0
        self._raw_mouse_hwnd = None
        self._raw_mouse_wndproc = None

        if not self.available:
            self.status = "Global capture: Windows only"

    def start(self) -> bool:
        if not self.available:
            return False

        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.WinDLL("user32", use_last_error=True)
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

            WH_KEYBOARD_LL = 13
            WH_MOUSE_LL = 14
            WM_KEYDOWN = 0x0100
            WM_KEYUP = 0x0101
            WM_SYSKEYDOWN = 0x0104
            WM_SYSKEYUP = 0x0105
            WM_MOUSEMOVE = 0x0200
            WM_LBUTTONDOWN = 0x0201
            WM_LBUTTONUP = 0x0202
            WM_RBUTTONDOWN = 0x0204
            WM_RBUTTONUP = 0x0205
            WM_MBUTTONDOWN = 0x0207
            WM_MBUTTONUP = 0x0208
            WM_MOUSEWHEEL = 0x020A
            WM_XBUTTONDOWN = 0x020B
            WM_XBUTTONUP = 0x020C
            WM_MOUSEHWHEEL = 0x020E

            mouse_message_buttons = {
                WM_LBUTTONDOWN: "button1",
                WM_LBUTTONUP: "button1",
                WM_RBUTTONDOWN: "button3",
                WM_RBUTTONUP: "button3",
                WM_MBUTTONDOWN: "button2",
                WM_MBUTTONUP: "button2",
            }

            key_names = {
                0x08: "backspace",
                0x09: "tab",
                0x0D: "return",
                0x10: "shift_l",
                0x11: "control_l",
                0x20: "space",
                0x25: "left",
                0x26: "up",
                0x27: "right",
                0x28: "down",
                0x77: "f8",
                0x78: "f9",
                0xA0: "shift_l",
                0xA1: "shift_l",
                0xA2: "control_l",
                0xA3: "control_l",
            }
            key_names.update({vk: chr(vk).lower() for vk in range(0x30, 0x3A)})
            key_names.update({vk: chr(vk).lower() for vk in range(0x41, 0x5B)})
            self._vk_key_names = dict(key_names)
            self._key_poll_map = {name: vk for vk, name in key_names.items() if not name.startswith("button")}

            class POINT(ctypes.Structure):
                _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

            class KBDLLHOOKSTRUCT(ctypes.Structure):
                _fields_ = [
                    ("vkCode", wintypes.DWORD),
                    ("scanCode", wintypes.DWORD),
                    ("flags", wintypes.DWORD),
                    ("time", wintypes.DWORD),
                    ("dwExtraInfo", ctypes.c_void_p),
                ]

            class MSLLHOOKSTRUCT(ctypes.Structure):
                _fields_ = [
                    ("pt", POINT),
                    ("mouseData", wintypes.DWORD),
                    ("flags", wintypes.DWORD),
                    ("time", wintypes.DWORD),
                    ("dwExtraInfo", ctypes.c_void_p),
                ]

            HOOKPROC = ctypes.WINFUNCTYPE(wintypes.LPARAM, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

            user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD]
            user32.SetWindowsHookExW.restype = wintypes.HANDLE
            user32.CallNextHookEx.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
            user32.CallNextHookEx.restype = wintypes.LPARAM
            user32.UnhookWindowsHookEx.argtypes = [wintypes.HANDLE]
            user32.UnhookWindowsHookEx.restype = wintypes.BOOL
            kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
            kernel32.GetModuleHandleW.restype = wintypes.HMODULE

            def keyboard_callback(code, w_param, l_param):
                should_block = False
                if code >= 0:
                    event = ctypes.cast(l_param, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                    key_name = key_names.get(event.vkCode)
                    if key_name:
                        with self._lock:
                            if w_param in (WM_KEYDOWN, WM_SYSKEYDOWN):
                                self._input_state.keys.add(key_name)
                                if key_name in ("f8", "f9") and key_name not in self._hotkeys_down:
                                    self._hotkeys_down.add(key_name)
                                    self._hotkeys.put(key_name)
                            elif w_param in (WM_KEYUP, WM_SYSKEYUP):
                                self._input_state.keys.discard(key_name)
                                self._hotkeys_down.discard(key_name)
                        should_block = self.block_original_input
                        if key_name in ("f8", "f9"):
                            should_block = True
                if should_block:
                    return 1
                return user32.CallNextHookEx(self._keyboard_hook, code, w_param, l_param)

            def mouse_callback(code, w_param, l_param):
                should_block = False
                if code >= 0:
                    event = ctypes.cast(l_param, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
                    pos = (int(event.pt.x), int(event.pt.y))
                    with self._lock:
                        if w_param == WM_MOUSEMOVE and not self._raw_mouse_active:
                            if self._last_mouse_pos is not None:
                                self._input_state.mouse_dx += pos[0] - self._last_mouse_pos[0]
                                self._input_state.mouse_dy += pos[1] - self._last_mouse_pos[1]
                            self._last_mouse_pos = pos
                        elif w_param == WM_MOUSEMOVE:
                            self._last_mouse_pos = pos
                        elif w_param == WM_LBUTTONDOWN:
                            self._input_state.mouse_buttons.add("button1")
                        elif w_param == WM_LBUTTONUP:
                            self._input_state.mouse_buttons.discard("button1")
                        elif w_param == WM_RBUTTONDOWN:
                            self._input_state.mouse_buttons.add("button3")
                        elif w_param == WM_RBUTTONUP:
                            self._input_state.mouse_buttons.discard("button3")
                        elif w_param == WM_MBUTTONDOWN:
                            self._input_state.mouse_buttons.add("button2")
                        elif w_param == WM_MBUTTONUP:
                            self._input_state.mouse_buttons.discard("button2")
                        elif w_param in (WM_XBUTTONDOWN, WM_XBUTTONUP):
                            x_button = (event.mouseData >> 16) & 0xFFFF
                            button_name = "button4" if x_button == 1 else "button5"
                            if w_param == WM_XBUTTONDOWN:
                                self._input_state.mouse_buttons.add(button_name)
                            else:
                                self._input_state.mouse_buttons.discard(button_name)
                    blocked_mouse_buttons = self._blocked_mouse_buttons
                    if w_param == WM_MOUSEMOVE:
                        should_block = self.block_original_input
                    elif w_param in mouse_message_buttons:
                        should_block = self.block_original_input
                    elif w_param in (WM_XBUTTONDOWN, WM_XBUTTONUP):
                        should_block = self.block_original_input
                    elif w_param in (WM_MOUSEWHEEL, WM_MOUSEHWHEEL):
                        should_block = self.block_original_input
                if should_block:
                    return 1
                return user32.CallNextHookEx(self._mouse_hook, code, w_param, l_param)

            self._keyboard_proc = HOOKPROC(keyboard_callback)
            self._mouse_proc = HOOKPROC(mouse_callback)
            module_handle = kernel32.GetModuleHandleW(None)
            self._keyboard_hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._keyboard_proc, module_handle, 0)
            self._mouse_hook = user32.SetWindowsHookExW(WH_MOUSE_LL, self._mouse_proc, module_handle, 0)

            if not self._keyboard_hook or not self._mouse_hook:
                error = ctypes.get_last_error()
                self.stop()
                self.status = f"Global capture: hook install failed ({error})"
                return False

            self.active = True
            self.status = "Global capture: active"
            self._start_raw_mouse_thread()
            return True
        except Exception as exc:
            self.status = f"Global capture: unavailable ({exc})"
            self.stop()
            return False

    def stop(self) -> None:
        if not self.available:
            return
        try:
            import ctypes

            user32 = ctypes.windll.user32
            if self._keyboard_hook:
                user32.UnhookWindowsHookEx(self._keyboard_hook)
            if self._mouse_hook:
                user32.UnhookWindowsHookEx(self._mouse_hook)
            if self._raw_mouse_thread_id:
                user32.PostThreadMessageW(self._raw_mouse_thread_id, 0x0012, 0, 0)
        finally:
            self._keyboard_hook = None
            self._mouse_hook = None
            self._raw_mouse_active = False
            self.active = False
            if self.available:
                self.status = "Global capture: stopped"

    def _start_raw_mouse_thread(self) -> None:
        if self._raw_mouse_thread and self._raw_mouse_thread.is_alive():
            return
        self._raw_mouse_thread = threading.Thread(target=self._raw_mouse_loop, daemon=True)
        self._raw_mouse_thread.start()

    def _raw_mouse_loop(self) -> None:
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.WinDLL("user32", use_last_error=True)
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

            WM_INPUT = 0x00FF
            WM_DESTROY = 0x0002
            WM_QUIT = 0x0012
            HWND_MESSAGE = wintypes.HWND(-3)
            RID_INPUT = 0x10000003
            RIM_TYPEMOUSE = 0
            RIM_TYPEKEYBOARD = 1
            RIDEV_INPUTSINK = 0x00000100
            WM_KEYDOWN = 0x0100
            WM_KEYUP = 0x0101
            WM_SYSKEYDOWN = 0x0104
            WM_SYSKEYUP = 0x0105

            class WNDCLASS(ctypes.Structure):
                _fields_ = [
                    ("style", wintypes.UINT),
                    ("lpfnWndProc", ctypes.c_void_p),
                    ("cbClsExtra", ctypes.c_int),
                    ("cbWndExtra", ctypes.c_int),
                    ("hInstance", wintypes.HINSTANCE),
                    ("hIcon", wintypes.HICON),
                    ("hCursor", wintypes.HCURSOR),
                    ("hbrBackground", wintypes.HBRUSH),
                    ("lpszMenuName", wintypes.LPCWSTR),
                    ("lpszClassName", wintypes.LPCWSTR),
                ]

            class RAWINPUTDEVICE(ctypes.Structure):
                _fields_ = [
                    ("usUsagePage", wintypes.USHORT),
                    ("usUsage", wintypes.USHORT),
                    ("dwFlags", wintypes.DWORD),
                    ("hwndTarget", wintypes.HWND),
                ]

            class RAWINPUTHEADER(ctypes.Structure):
                _fields_ = [
                    ("dwType", wintypes.DWORD),
                    ("dwSize", wintypes.DWORD),
                    ("hDevice", wintypes.HANDLE),
                    ("wParam", wintypes.WPARAM),
                ]

            class RAWMOUSE_BUTTONS_STRUCT(ctypes.Structure):
                _fields_ = [("usButtonFlags", wintypes.USHORT), ("usButtonData", wintypes.USHORT)]

            class RAWMOUSE_BUTTONS(ctypes.Union):
                _fields_ = [("ulButtons", wintypes.ULONG), ("buttons", RAWMOUSE_BUTTONS_STRUCT)]

            class RAWMOUSE(ctypes.Structure):
                _fields_ = [
                    ("usFlags", wintypes.USHORT),
                    ("buttons", RAWMOUSE_BUTTONS),
                    ("ulRawButtons", wintypes.ULONG),
                    ("lLastX", wintypes.LONG),
                    ("lLastY", wintypes.LONG),
                    ("ulExtraInformation", wintypes.ULONG),
                ]

            class RAWKEYBOARD(ctypes.Structure):
                _fields_ = [
                    ("MakeCode", wintypes.USHORT),
                    ("Flags", wintypes.USHORT),
                    ("Reserved", wintypes.USHORT),
                    ("VKey", wintypes.USHORT),
                    ("Message", wintypes.UINT),
                    ("ExtraInformation", wintypes.ULONG),
                ]

            class RAWINPUTDATA(ctypes.Union):
                _fields_ = [("mouse", RAWMOUSE), ("keyboard", RAWKEYBOARD)]

            class RAWINPUT(ctypes.Structure):
                _fields_ = [("header", RAWINPUTHEADER), ("data", RAWINPUTDATA)]

            class MSG(ctypes.Structure):
                _fields_ = [
                    ("hwnd", wintypes.HWND),
                    ("message", wintypes.UINT),
                    ("wParam", wintypes.WPARAM),
                    ("lParam", wintypes.LPARAM),
                    ("time", wintypes.DWORD),
                    ("pt", wintypes.POINT),
                ]

            WNDPROC = ctypes.WINFUNCTYPE(wintypes.LPARAM, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

            user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASS)]
            user32.RegisterClassW.restype = wintypes.ATOM
            user32.CreateWindowExW.argtypes = [
                wintypes.DWORD,
                wintypes.LPCWSTR,
                wintypes.LPCWSTR,
                wintypes.DWORD,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_int,
                wintypes.HWND,
                wintypes.HMENU,
                wintypes.HINSTANCE,
                ctypes.c_void_p,
            ]
            user32.CreateWindowExW.restype = wintypes.HWND
            user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
            user32.DefWindowProcW.restype = wintypes.LPARAM
            user32.RegisterRawInputDevices.argtypes = [ctypes.POINTER(RAWINPUTDEVICE), wintypes.UINT, wintypes.UINT]
            user32.RegisterRawInputDevices.restype = wintypes.BOOL
            user32.GetRawInputData.argtypes = [wintypes.HANDLE, wintypes.UINT, ctypes.c_void_p, ctypes.POINTER(wintypes.UINT), wintypes.UINT]
            user32.GetRawInputData.restype = wintypes.UINT
            user32.GetMessageW.argtypes = [ctypes.POINTER(MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
            user32.GetMessageW.restype = wintypes.BOOL
            user32.TranslateMessage.argtypes = [ctypes.POINTER(MSG)]
            user32.DispatchMessageW.argtypes = [ctypes.POINTER(MSG)]
            user32.DestroyWindow.argtypes = [wintypes.HWND]
            kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
            kernel32.GetModuleHandleW.restype = wintypes.HMODULE
            kernel32.GetCurrentThreadId.restype = wintypes.DWORD

            def wndproc(hwnd, msg, w_param, l_param):
                if msg == WM_INPUT:
                    size = wintypes.UINT(0)
                    header_size = ctypes.sizeof(RAWINPUTHEADER)
                    user32.GetRawInputData(l_param, RID_INPUT, None, ctypes.byref(size), header_size)
                    if size.value:
                        buffer = ctypes.create_string_buffer(size.value)
                        result = user32.GetRawInputData(l_param, RID_INPUT, buffer, ctypes.byref(size), header_size)
                        if result != 0xFFFFFFFF:
                            raw = ctypes.cast(buffer, ctypes.POINTER(RAWINPUT)).contents
                            if raw.header.dwType == RIM_TYPEMOUSE:
                                with self._lock:
                                    self._input_state.mouse_dx += int(raw.data.mouse.lLastX)
                                    self._input_state.mouse_dy += int(raw.data.mouse.lLastY)
                            elif raw.header.dwType == RIM_TYPEKEYBOARD:
                                key_name = self._vk_key_names.get(int(raw.data.keyboard.VKey))
                                if key_name:
                                    with self._lock:
                                        if raw.data.keyboard.Message in (WM_KEYDOWN, WM_SYSKEYDOWN):
                                            self._input_state.keys.add(key_name)
                                        elif raw.data.keyboard.Message in (WM_KEYUP, WM_SYSKEYUP):
                                            self._input_state.keys.discard(key_name)
                    return 0
                if msg == WM_DESTROY:
                    return 0
                return user32.DefWindowProcW(hwnd, msg, w_param, l_param)

            self._raw_mouse_thread_id = int(kernel32.GetCurrentThreadId())
            self._raw_mouse_wndproc = WNDPROC(wndproc)
            instance = kernel32.GetModuleHandleW(None)
            class_name = "KeyMouse2PadRawInputWindow"
            wndclass = WNDCLASS(
                style=0,
                lpfnWndProc=ctypes.cast(self._raw_mouse_wndproc, ctypes.c_void_p).value,
                cbClsExtra=0,
                cbWndExtra=0,
                hInstance=instance,
                hIcon=None,
                hCursor=None,
                hbrBackground=None,
                lpszMenuName=None,
                lpszClassName=class_name,
            )
            user32.RegisterClassW(ctypes.byref(wndclass))
            hwnd = user32.CreateWindowExW(0, class_name, class_name, 0, 0, 0, 0, 0, HWND_MESSAGE, None, instance, None)
            if not hwnd:
                return
            self._raw_mouse_hwnd = hwnd

            devices = (RAWINPUTDEVICE * 2)(
                RAWINPUTDEVICE(usUsagePage=0x01, usUsage=0x02, dwFlags=RIDEV_INPUTSINK, hwndTarget=hwnd),
                RAWINPUTDEVICE(usUsagePage=0x01, usUsage=0x06, dwFlags=RIDEV_INPUTSINK, hwndTarget=hwnd),
            )
            if not user32.RegisterRawInputDevices(devices, 2, ctypes.sizeof(RAWINPUTDEVICE)):
                return

            self._raw_mouse_active = True
            msg = MSG()
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0):
                if msg.message == WM_QUIT:
                    break
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
            self._raw_mouse_active = False
            if self._raw_mouse_hwnd:
                user32.DestroyWindow(self._raw_mouse_hwnd)
                self._raw_mouse_hwnd = None
        except Exception:
            self._raw_mouse_active = False

    def reset(self) -> None:
        with self._lock:
            self._input_state = InputSnapshot()
            self._last_mouse_pos = None

    def set_blocked_inputs(self, inputs: set[str]) -> None:
        with self._lock:
            self._blocked_key_names = {value for value in inputs if not value.startswith("button")}
            self._blocked_mouse_buttons = {value for value in inputs if value.startswith("button")}

    def snapshot(self) -> InputSnapshot:
        with self._lock:
            self._poll_keyboard_state_locked()
            snapshot = InputSnapshot(
                keys=set(self._input_state.keys),
                mouse_buttons=set(self._input_state.mouse_buttons),
                mouse_dx=self._input_state.mouse_dx,
                mouse_dy=self._input_state.mouse_dy,
            )
            self._input_state.mouse_dx = 0
            self._input_state.mouse_dy = 0
        return snapshot

    def _poll_keyboard_state_locked(self) -> None:
        if not self.available or not self._key_poll_map:
            return
        if self.block_original_input:
            return
        try:
            import ctypes

            user32 = ctypes.windll.user32
            for key_name, vk_code in self._key_poll_map.items():
                if user32.GetAsyncKeyState(vk_code) & 0x8000:
                    self._input_state.keys.add(key_name)
                else:
                    self._input_state.keys.discard(key_name)
        except Exception:
            return

    def pop_hotkeys(self) -> list[str]:
        hotkeys: list[str] = []
        while True:
            try:
                hotkeys.append(self._hotkeys.get_nowait())
            except queue.Empty:
                return hotkeys


class ConverterGui:
    def __init__(self) -> None:
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.ttk = ttk
        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.geometry("1160x720")
        self.root.minsize(1040, 640)

        self.profile = load_profile()
        self.engine = MappingEngine(self.profile)
        self.input_state = InputSnapshot()
        self.running = tk.BooleanVar(value=True)
        self.output_enabled = tk.BooleanVar(value=True)
        self.global_capture_enabled = tk.BooleanVar(value=True)
        self.block_original_input = tk.BooleanVar(value=False)
        self.last_time = time.monotonic()
        self.last_render_time = 0.0
        self._resizing = False
        self._resize_after_id: str | None = None
        self._render_pending = True
        self._last_render_signature: tuple[object, ...] | None = None
        self.last_mouse_pos: tuple[int, int] | None = None
        self.state = GamepadState()
        self.output = WindowsControllerOutput()
        self.global_capture = GlobalInputCapture()
        self.global_capture.set_blocked_inputs(self.profile.mapped_inputs())
        if self.global_capture.available:
            self.global_capture.start()

        self.status_text = tk.StringVar(value="Ready")
        self.state_text = tk.StringVar(value="")
        self.input_text = tk.StringVar(value="")
        self.driver_text = tk.StringVar(value=self.output.status)
        self.capture_text = tk.StringVar(value=self.global_capture.status)
        self.deadzone_var = tk.DoubleVar(value=self.engine.analog.deadzone)
        self.sensitivity_var = tk.DoubleVar(value=self.engine.analog.mouse_sensitivity)
        self.smoothing_var = tk.DoubleVar(value=self.engine.analog.mouse_smoothing)
        self.mapping_vars: dict[str, object] = {}

        self._build_ui()
        self._bind_events()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._tick()

    def run(self) -> None:
        self.root.mainloop()

    def _build_ui(self) -> None:
        tk = self.tk
        ttk = self.ttk

        root = self.root
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)

        toolbar = ttk.Frame(root, padding=10)
        toolbar.grid(row=0, column=0, sticky="ew")
        toolbar.columnconfigure(6, weight=1)

        ttk.Checkbutton(toolbar, text="Running", variable=self.running).grid(row=0, column=0, padx=(0, 12))
        ttk.Checkbutton(toolbar, text="Send to Windows", variable=self.output_enabled).grid(
            row=0, column=1, padx=(0, 12)
        )
        ttk.Checkbutton(toolbar, text="Global capture", variable=self.global_capture_enabled).grid(
            row=0, column=2, padx=(0, 12)
        )
        ttk.Checkbutton(
            toolbar,
            text="Exclusive pad mode",
            variable=self.block_original_input,
            command=self._on_exclusive_checkbox,
        ).grid(
            row=0, column=3, padx=(0, 12)
        )
        ttk.Label(toolbar, textvariable=self.driver_text).grid(row=0, column=4, padx=(0, 12))
        ttk.Button(toolbar, text="Reset", command=self._reset).grid(row=0, column=5)
        ttk.Label(toolbar, textvariable=self.status_text, anchor="e").grid(row=0, column=6, sticky="ew")

        main = ttk.Frame(root, padding=(10, 0, 10, 10))
        main.grid(row=1, column=0, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        pad = ttk.LabelFrame(main, text="Virtual Pad", padding=12)
        pad.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        pad.columnconfigure(0, weight=1)
        pad.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(pad, background="#171a21", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        ttk.Label(pad, textvariable=self.state_text, font=("TkFixedFont", 10)).grid(
            row=1, column=0, sticky="ew", pady=(10, 0)
        )
        ttk.Label(pad, textvariable=self.input_text, font=("TkFixedFont", 9)).grid(
            row=2, column=0, sticky="ew", pady=(6, 0)
        )

        side = ttk.Frame(main)
        side.grid(row=0, column=1, sticky="nsew")
        side.columnconfigure(0, weight=1)
        side.rowconfigure(1, weight=1)

        controls = ttk.LabelFrame(side, text="Analog Tuning", padding=12)
        controls.grid(row=0, column=0, sticky="ew")
        controls.columnconfigure(1, weight=1)
        self._slider(controls, 0, "Deadzone", self.deadzone_var, 0.0, 0.4, self._update_settings)
        self._slider(controls, 1, "Mouse Sens", self.sensitivity_var, 0.001, 0.06, self._update_settings)
        self._slider(controls, 2, "Smoothing", self.smoothing_var, 0.0, 0.95, self._update_settings)

        self._build_mapping_editor(side)

        capture = ttk.LabelFrame(side, text="Input Capture", padding=12)
        capture.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        ttk.Label(
            capture,
            text="F8 toggles Running. F9 toggles Exclusive pad mode, where keyboard and mouse drive only the controller output.",
            wraplength=300,
            justify="left",
        ).grid(row=0, column=0, sticky="ew")
        ttk.Label(capture, textvariable=self.capture_text, justify="left").grid(row=1, column=0, sticky="ew", pady=(8, 0))

    def _build_mapping_editor(self, parent) -> None:
        ttk = self.ttk
        mapping = ttk.LabelFrame(parent, text="Mapping", padding=12)
        mapping.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        mapping.columnconfigure(1, weight=1)
        mapping.columnconfigure(3, weight=1)

        rows = [
            ("Pad A", "button:A"),
            ("Pad B", "button:B"),
            ("Pad X", "button:X"),
            ("Pad Y", "button:Y"),
            ("LB", "button:LB"),
            ("RB", "button:RB"),
            ("LT", "trigger:LT"),
            ("RT", "trigger:RT"),
            ("Start", "button:Start"),
            ("Back", "button:Back"),
            ("LStick Left", "stick:left"),
            ("LStick Right", "stick:right"),
            ("LStick Up", "stick:up"),
            ("LStick Down", "stick:down"),
        ]

        split_at = (len(rows) + 1) // 2
        for index, (label, key) in enumerate(rows):
            row = index if index < split_at else index - split_at
            column = 0 if index < split_at else 2
            variable = self.tk.StringVar(value=self._mapping_value(key))
            self.mapping_vars[key] = variable
            ttk.Label(mapping, text=label).grid(row=row, column=column, sticky="w", pady=2, padx=(0, 6))
            ttk.Entry(mapping, textvariable=variable, width=20).grid(row=row, column=column + 1, sticky="ew", pady=2, padx=(0, 12))

        buttons = ttk.Frame(mapping)
        buttons.grid(row=split_at, column=0, columnspan=4, sticky="ew", pady=(10, 0))
        buttons.columnconfigure(0, weight=1)
        buttons.columnconfigure(1, weight=1)
        buttons.columnconfigure(2, weight=1)
        ttk.Button(buttons, text="Apply", command=self._apply_mapping_from_ui).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(buttons, text="Save", command=self._save_mapping_from_ui).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(buttons, text="Defaults", command=self._restore_default_mapping).grid(row=0, column=2, sticky="ew", padx=(4, 0))

    def _mapping_value(self, key: str) -> str:
        kind, name = key.split(":", 1)
        if kind == "button":
            return format_inputs(self.profile.button_inputs[name])
        if kind == "trigger" and name == "LT":
            return format_inputs(self.profile.left_trigger_inputs)
        if kind == "trigger" and name == "RT":
            return format_inputs(self.profile.right_trigger_inputs)
        if kind == "stick":
            return format_inputs(self.profile.left_stick[name])
        return ""

    def _slider(
        self,
        parent,
        row: int,
        label: str,
        variable,
        minimum: float,
        maximum: float,
        command: Callable[[str], None],
    ) -> None:
        ttk = self.ttk
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=4)
        ttk.Scale(parent, variable=variable, from_=minimum, to=maximum, command=command).grid(
            row=row, column=1, sticky="ew", padx=(10, 0), pady=4
        )

    def _bind_events(self) -> None:
        self.root.bind("<KeyPress>", self._on_key_press)
        self.root.bind("<KeyRelease>", self._on_key_release)
        self.canvas.bind("<Motion>", self._on_mouse_motion)
        self.canvas.bind("<ButtonPress>", self._on_mouse_press)
        self.canvas.bind("<ButtonRelease>", self._on_mouse_release)
        self.canvas.bind("<Leave>", self._on_mouse_leave)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

    def _on_canvas_configure(self, _event) -> None:
        self._resizing = True
        self._render_pending = True
        if self._resize_after_id is not None:
            self.root.after_cancel(self._resize_after_id)
        self._resize_after_id = self.root.after(140, self._finish_resize)

    def _finish_resize(self) -> None:
        self._resize_after_id = None
        self._resizing = False
        self._render_pending = True

    def _on_key_press(self, event) -> None:
        self.input_state.keys.add(event.keysym.lower())

    def _on_key_release(self, event) -> None:
        self.input_state.keys.discard(event.keysym.lower())

    def _on_mouse_motion(self, event) -> None:
        if self.last_mouse_pos is not None:
            self.input_state.mouse_dx += event.x - self.last_mouse_pos[0]
            self.input_state.mouse_dy += event.y - self.last_mouse_pos[1]
        self.last_mouse_pos = (event.x, event.y)

    def _on_mouse_press(self, event) -> None:
        self.input_state.mouse_buttons.add(f"button{event.num}")

    def _on_mouse_release(self, event) -> None:
        self.input_state.mouse_buttons.discard(f"button{event.num}")

    def _on_mouse_leave(self, _event) -> None:
        self.last_mouse_pos = None

    def _update_settings(self, _value: str = "") -> None:
        self.engine.analog.deadzone = float(self.deadzone_var.get())
        self.engine.analog.mouse_sensitivity = float(self.sensitivity_var.get())
        self.engine.analog.mouse_smoothing = float(self.smoothing_var.get())

    def _profile_from_ui(self) -> MappingProfile:
        profile = MappingProfile.defaults()
        for key, variable in self.mapping_vars.items():
            kind, name = key.split(":", 1)
            values = parse_inputs(variable.get())
            if kind == "button":
                profile.button_inputs[name] = values
            elif kind == "trigger" and name == "LT":
                profile.left_trigger_inputs = values
            elif kind == "trigger" and name == "RT":
                profile.right_trigger_inputs = values
            elif kind == "stick":
                profile.left_stick[name] = values
        return profile

    def _apply_profile(self, profile: MappingProfile) -> None:
        self.profile = profile
        old_analog = self.engine.analog
        self.engine = MappingEngine(self.profile)
        self.engine.analog = old_analog
        self.global_capture.set_blocked_inputs(self.profile.mapped_inputs())
        self.global_capture.reset()

    def _apply_mapping_from_ui(self) -> None:
        self._apply_profile(self._profile_from_ui())
        self.status_text.set("Mapping applied")

    def _save_mapping_from_ui(self) -> None:
        self._apply_mapping_from_ui()
        save_profile(self.profile)
        self.status_text.set(f"Mapping saved: {CONFIG_PATH}")

    def _restore_default_mapping(self) -> None:
        self.profile = MappingProfile.defaults()
        for key, variable in self.mapping_vars.items():
            variable.set(self._mapping_value(key))
        self._apply_profile(self.profile)
        self.status_text.set("Default mapping restored")

    def _reset(self) -> None:
        old_analog = self.engine.analog
        self.engine = MappingEngine(self.profile)
        self.engine.analog = old_analog
        self.input_state = InputSnapshot()
        self.global_capture.reset()
        self.output.reset()
        self.deadzone_var.set(self.engine.analog.deadzone)
        self.sensitivity_var.set(self.engine.analog.mouse_sensitivity)
        self.smoothing_var.set(self.engine.analog.mouse_smoothing)

    def _toggle_running_hotkey(self) -> None:
        self.running.set(not self.running.get())
        self._set_text(self.status_text, "Running toggled by F8")

    def _toggle_blocking_hotkey(self) -> None:
        if self.block_original_input.get():
            self.block_original_input.set(False)
            self.global_capture.block_original_input = False
            self._set_text(self.status_text, "Exclusive pad mode off")
        else:
            self._enable_exclusive_mode()

    def _on_exclusive_checkbox(self) -> None:
        if self.block_original_input.get():
            self._enable_exclusive_mode()
        else:
            self.global_capture.block_original_input = False
            self._set_text(self.status_text, "Exclusive pad mode off")

    def _enable_exclusive_mode(self) -> None:
        self.running.set(True)
        self.output_enabled.set(True)
        self.global_capture_enabled.set(True)

        if self.global_capture.available and not self.global_capture.active:
            self.global_capture.start()

        if not self.output.available:
            self.block_original_input.set(False)
            self.global_capture.block_original_input = False
            self._set_text(self.status_text, "Controller output unavailable; exclusive mode was not enabled")
            return

        if not self.global_capture.active:
            self.block_original_input.set(False)
            self.global_capture.block_original_input = False
            self._set_text(self.status_text, "Global capture unavailable; exclusive mode was not enabled")
            return

        self.block_original_input.set(True)
        self._set_text(self.status_text, "Exclusive pad mode on")

    def _tick(self) -> None:
        now = time.monotonic()
        delta = min(0.05, now - self.last_time)
        self.last_time = now
        self._process_hotkeys()
        exclusive_ready = (
            self.running.get()
            and self.output_enabled.get()
            and self.global_capture_enabled.get()
            and self.block_original_input.get()
            and self.output.available
            and self.global_capture.active
        )
        self.global_capture.block_original_input = exclusive_ready
        input_state = self._current_input_snapshot()

        if self.running.get():
            self.state = self.engine.update(input_state, delta)
            if self.output_enabled.get() and self.output.available:
                self.output.submit(self.state)
            if exclusive_ready:
                self._set_text(self.status_text, "Exclusive pad mode active")
            else:
                self._set_text(self.status_text, "Capturing input")
        else:
            self.output.reset()
            self._set_text(self.status_text, "Paused")

        if not self._using_global_capture():
            self.input_state.mouse_dx = 0
            self.input_state.mouse_dy = 0
        should_render = self._render_pending or now - self.last_render_time >= 0.10
        if should_render and not self._resizing:
            self._render_pending = False
            self.last_render_time = now
            render_signature = self._render_signature(input_state)
            if render_signature != self._last_render_signature:
                self._last_render_signature = render_signature
                self._set_text(self.capture_text, self.global_capture.status)
                self._draw_pad()
                self._update_state_text(input_state)
        self.root.after(33, self._tick)

    def _process_hotkeys(self) -> None:
        for hotkey in self.global_capture.pop_hotkeys():
            if hotkey == "f8":
                self._toggle_running_hotkey()
            elif hotkey == "f9":
                self._toggle_blocking_hotkey()

    def _using_global_capture(self) -> bool:
        return self.global_capture_enabled.get() and self.global_capture.active

    def _current_input_snapshot(self) -> InputSnapshot:
        if self._using_global_capture():
            return self.global_capture.snapshot()
        return self.input_state

    def _on_close(self) -> None:
        if self._resize_after_id is not None:
            self.root.after_cancel(self._resize_after_id)
            self._resize_after_id = None
        self.output.reset()
        self.global_capture.stop()
        self.root.destroy()

    @staticmethod
    def _set_text(variable, value: str) -> None:
        if variable.get() != value:
            variable.set(value)

    def _render_signature(self, input_state: InputSnapshot) -> tuple[object, ...]:
        return (
            self.canvas.winfo_width(),
            self.canvas.winfo_height(),
            self.state.left_x,
            self.state.left_y,
            self.state.right_x,
            self.state.right_y,
            self.state.left_trigger,
            self.state.right_trigger,
            self.state.buttons,
            tuple(sorted(input_state.keys)),
            tuple(sorted(input_state.mouse_buttons)),
            self.global_capture.status,
        )

    def _draw_pad(self) -> None:
        canvas = self.canvas
        canvas.delete("all")
        width = max(1, canvas.winfo_width())
        height = max(1, canvas.winfo_height())

        canvas.create_rectangle(0, 0, width, height, fill="#171a21", outline="")
        self._draw_stick(canvas, width * 0.28, height * 0.48, self.state.left_x, -self.state.left_y, "L")
        self._draw_stick(canvas, width * 0.72, height * 0.48, self.state.right_x, -self.state.right_y, "R")

        self._draw_trigger(canvas, width * 0.18, 30, self.state.left_trigger, "LT")
        self._draw_trigger(canvas, width * 0.82, 30, self.state.right_trigger, "RT")

        labels = ["Y", "X", "B", "A"]
        positions = [
            (width * 0.78, height * 0.68),
            (width * 0.72, height * 0.76),
            (width * 0.84, height * 0.76),
            (width * 0.78, height * 0.84),
        ]
        for label, pos in zip(labels, positions):
            self._draw_button(canvas, pos[0], pos[1], label, self.state.pressed(label))

        dpad_positions = {
            "DUp": (width * 0.22, height * 0.68, "U"),
            "DLeft": (width * 0.16, height * 0.76, "L"),
            "DRight": (width * 0.28, height * 0.76, "R"),
            "DDown": (width * 0.22, height * 0.84, "D"),
        }
        for button, (x, y, text) in dpad_positions.items():
            self._draw_button(canvas, x, y, text, self.state.pressed(button))

    def _draw_stick(self, canvas, cx: float, cy: float, raw_x: int, raw_y: int, label: str) -> None:
        radius = 58
        knob_radius = 18
        nx = raw_x / 32767.0
        ny = raw_y / 32767.0
        canvas.create_oval(cx - radius, cy - radius, cx + radius, cy + radius, outline="#6f7b8f", width=2)
        canvas.create_line(cx - radius, cy, cx + radius, cy, fill="#343b49")
        canvas.create_line(cx, cy - radius, cx, cy + radius, fill="#343b49")
        kx = cx + nx * (radius - knob_radius)
        ky = cy + ny * (radius - knob_radius)
        canvas.create_oval(kx - knob_radius, ky - knob_radius, kx + knob_radius, ky + knob_radius, fill="#47d7ac", outline="")
        canvas.create_text(cx, cy + radius + 22, text=label, fill="#d6dde8", font=("TkDefaultFont", 12, "bold"))

    def _draw_trigger(self, canvas, cx: float, y: float, value: int, label: str) -> None:
        width = 110
        height = 18
        fill_width = width * (value / 255.0)
        canvas.create_rectangle(cx - width / 2, y, cx + width / 2, y + height, outline="#6f7b8f")
        canvas.create_rectangle(cx - width / 2, y, cx - width / 2 + fill_width, y + height, fill="#e7c65a", outline="")
        canvas.create_text(cx, y + height + 16, text=label, fill="#d6dde8")

    def _draw_button(self, canvas, x: float, y: float, label: str, active: bool) -> None:
        fill = "#e85d75" if active else "#2a303b"
        outline = "#f7a7b5" if active else "#6f7b8f"
        canvas.create_oval(x - 19, y - 19, x + 19, y + 19, fill=fill, outline=outline, width=2)
        canvas.create_text(x, y, text=label, fill="#ffffff", font=("TkDefaultFont", 10, "bold"))

    def _update_state_text(self, input_state: InputSnapshot) -> None:
        active_buttons = [name for name in BUTTON_BITS if self.state.pressed(name)]
        self._set_text(
            self.state_text,
            f"LX={self.state.left_x:6d} LY={self.state.left_y:6d} "
            f"RX={self.state.right_x:6d} RY={self.state.right_y:6d}\n"
            f"LT={self.state.left_trigger:3d} RT={self.state.right_trigger:3d} "
            f"Buttons={','.join(active_buttons) if active_buttons else '-'}",
        )
        active_inputs = sorted(input_state.keys | input_state.mouse_buttons)
        self._set_text(self.input_text, f"Inputs={','.join(active_inputs[:12]) if active_inputs else '-'}")


def self_test() -> None:
    engine = MappingEngine()
    input_state = InputSnapshot(keys={"w", "d", "space"}, mouse_dx=30, mouse_dy=-10)
    state = engine.update(input_state, 1.0 / 60.0)
    assert state.left_x > 0
    assert state.left_y > 0
    assert state.right_x > 0
    assert state.right_y > 0
    assert state.pressed("A")
    assert not MappingEngine().update(InputSnapshot(keys={"a"}), 1.0 / 60.0).pressed("A")
    trigger_state = MappingEngine().update(InputSnapshot(keys={"j", "k"}), 1.0 / 60.0)
    assert trigger_state.right_trigger == 255
    assert trigger_state.left_trigger == 255
    print("converter_gui self-test passed")


def controller_self_test() -> None:
    output = WindowsControllerOutput()
    if not output.available:
        raise RuntimeError(output.status)

    state = GamepadState(left_x=12000, left_y=12000, right_trigger=255)
    state.set_button("A", True)
    output.submit(state)
    assert output.debug_buttons_value() & 0x1000
    time.sleep(0.15)
    output.reset()
    print(output.status)


def global_hook_self_test() -> None:
    capture = GlobalInputCapture()
    if not capture.available:
        print(capture.status)
        return
    if not capture.start():
        raise RuntimeError(capture.status)
    capture.block_original_input = True
    assert capture.block_original_input
    capture.stop()
    print("global hook self-test passed")


def main() -> None:
    parser = argparse.ArgumentParser(description="KeyMouse2Pad GUI")
    parser.add_argument("--self-test", action="store_true", help="run a no-display smoke test")
    parser.add_argument("--controller-self-test", action="store_true", help="create and update the Windows controller")
    parser.add_argument("--global-hook-self-test", action="store_true", help="install and remove global input hooks")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return
    if args.controller_self_test:
        controller_self_test()
        return
    if args.global_hook_self_test:
        global_hook_self_test()
        return

    ConverterGui().run()


if __name__ == "__main__":
    main()
