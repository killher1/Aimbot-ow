import ctypes
import time

# 默认假设 DLL 与本脚本/调用脚本同目录
DEFAULT_DLL_PATH = r".\IbInputSimulator.dll"


class SendType:
    AnyDriver = 0
    SendInput = 1
    Logitech = 2
    LogitechGHubNew = 6
    Razer = 3
    DD = 4
    MouClassInputInjection = 5


class MoveMode:
    Absolute = 0
    Relative = 1


class MouseButton:
    LeftDown = 0x02
    LeftUp = 0x04
    Left = LeftDown | LeftUp

    RightDown = 0x08
    RightUp = 0x10
    Right = RightDown | RightUp


class KeyboardModifiers(ctypes.Structure):
    _fields_ = [
        ("LCtrl", ctypes.c_uint8, 1),
        ("LShift", ctypes.c_uint8, 1),
        ("LAlt", ctypes.c_uint8, 1),
        ("LWin", ctypes.c_uint8, 1),
        ("RCtrl", ctypes.c_uint8, 1),
        ("RShift", ctypes.c_uint8, 1),
        ("RAlt", ctypes.c_uint8, 1),
        ("RWin", ctypes.c_uint8, 1),
    ]


def _load_dll(path: str) -> ctypes.WinDLL:
    try:
        ib = ctypes.WinDLL(path)
    except OSError as e:
        raise SystemExit(f"加载 IbInputSimulator DLL 失败: {e}\n请检查 DLL 路径是否正确: {path}")
    return ib


def _bind_functions(ib: ctypes.WinDLL):
    # Send::Error 实际是 uint32_t
    ib.IbSendInit.argtypes = (ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p)
    ib.IbSendInit.restype = ctypes.c_uint32

    ib.IbSendDestroy.argtypes = ()
    ib.IbSendDestroy.restype = None

    ib.IbSendMouseMove.argtypes = (
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_uint32,
    )
    ib.IbSendMouseMove.restype = ctypes.c_bool

    ib.IbSendMouseClick.argtypes = (ctypes.c_uint32,)
    ib.IbSendMouseClick.restype = ctypes.c_bool

    ib.IbSendMouseWheel.argtypes = (ctypes.c_int32,)
    ib.IbSendMouseWheel.restype = ctypes.c_bool

    ib.IbSendKeybdDown.argtypes = (ctypes.c_uint16,)
    ib.IbSendKeybdDown.restype = ctypes.c_bool

    ib.IbSendKeybdUp.argtypes = (ctypes.c_uint16,)
    ib.IbSendKeybdUp.restype = ctypes.c_bool

    ib.IbSendKeybdDownUp.argtypes = (ctypes.c_uint16, KeyboardModifiers)
    ib.IbSendKeybdDownUp.restype = ctypes.c_bool


class IbInput:
    """对 IbInputSimulator.dll 的简单封装，方便在任意文件中调用。"""

    def __init__(self, dll_path: str = DEFAULT_DLL_PATH, send_type: int = SendType.AnyDriver, flags: int = 1):
        self._dll_path = dll_path
        self._ib = _load_dll(dll_path)
        _bind_functions(self._ib)

        ret = self._ib.IbSendInit(send_type, flags, None)
        if ret != 0:
            raise RuntimeError(f"IbSendInit 失败，错误码: {ret}")

    def destroy(self):
        if self._ib is not None:
            self._ib.IbSendDestroy()
            self._ib = None

    # 让类可以用 with 语法自动清理
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.destroy()

    # ===== 对外封装一些常用操作 =====
    def mouse_move(self, x: int, y: int, mode: int = MoveMode.Absolute) -> bool:
        return bool(self._ib.IbSendMouseMove(x, y, mode))

    def mouse_click(self, button: int = MouseButton.Left) -> bool:
        return bool(self._ib.IbSendMouseClick(button))

    def key_down(self, vk: int) -> bool:
        return bool(self._ib.IbSendKeybdDown(vk))

    def key_up(self, vk: int) -> bool:
        return bool(self._ib.IbSendKeybdUp(vk))

    def key_down_up(self, vk: int, mods: KeyboardModifiers | None = None) -> bool:
        if mods is None:
            mods = KeyboardModifiers()
        return bool(self._ib.IbSendKeybdDownUp(vk, mods))


if __name__ == "__main__":
    # 简单自测：移动鼠标并点击、按一次 A
    with IbInput() as sim:
        sim.mouse_move(500, 500)
        time.sleep(0.5)
        sim.mouse_click()
        time.sleep(0.5)
        VK_A = 0x41
        sim.key_down(VK_A)
        sim.key_up(VK_A)


