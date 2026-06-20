import ctypes
import time

# 按你的实际路径改，如果 dll 与本脚本同目录，可以只写文件名
DLL_PATH = r".\IbInputSimulator.dll"


def load_dll(path: str) -> ctypes.WinDLL:
    try:
        ib = ctypes.WinDLL(path)
    except OSError as e:
        raise SystemExit(f"加载 DLL 失败: {e}\n请检查 DLL 路径是否正确: {path}")
    return ib


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


def bind_functions(ib: ctypes.WinDLL):
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


def main():
    ib = load_dll(DLL_PATH)
    bind_functions(ib)

    # 初始化，使用 AnyDriver，flags=1，argument=null
    ret = ib.IbSendInit(SendType.AnyDriver, 1, None)
    if ret != 0:
        raise SystemExit(f"IbSendInit 失败，错误码: {ret}")
    print("IbSendInit 成功")

    try:
        # 鼠标移动到 (500, 500)
        ok_move = ib.IbSendMouseMove(500, 500, MoveMode.Absolute)
        print("鼠标移动结果:", ok_move)
        time.sleep(0.5)

        # 鼠标左键点击
        ok_click = ib.IbSendMouseClick(MouseButton.Left)
        print("鼠标左键点击结果:", ok_click)
        time.sleep(0.5)

        # 键盘输入 A（虚拟键码 0x41）
        VK_A = 0x41
        ok_down = ib.IbSendKeybdDown(VK_A)
        ok_up = ib.IbSendKeybdUp(VK_A)
        print("键盘 A 按下结果:", ok_down, "抬起结果:", ok_up)

    finally:
        ib.IbSendDestroy()
        print("已调用 IbSendDestroy")


if __name__ == "__main__":
    main()


