# OW 自瞄程序

基于 YOLO 视觉检测的自瞄程序，支持多种输入驱动和自定义配置。

## 项目结构

```
.
├── main.py                 # 程序入口
├── README.md               # 说明文档
│
├── config/                 # 配置模块
│   ├── __init__.py
│   ├── config.json         # 配置文件
│   ├── config_manager.py  # 配置管理
│   ├── botsort.yaml       # 跟踪配置
│   └── bytetrack.yaml      # 跟踪配置
│
├── core/                   # 核心模块
│   ├── __init__.py
│   ├── aimbot_main.py      # 主程序逻辑（多线程架构）
│   ├── input_handler.py    # 输入控制
│   └── vision_engine.py    # 视觉检测
│
├── logic/                  # 业务逻辑
│   ├── aim_controller.py   # 瞄准控制
│   └── target_tracker.py   # 目标跟踪
│
├── ui/                     # 用户界面
│   ├── config_menu.py       # 热更新菜单（运行时调整）
│   ├── config_panel.py      # PyQt5配置面板
│   ├── fps_overlay.py       # FPS叠加显示
│   ├── indicator_window.py  # 区域指示窗口
│   └── preview_window.py    # 预览窗口
│
├── utils/                  # 工具模块
│   ├── thread_utils.py     # 线程工具
│   └── validators.py       # 配置验证
│
├── models/                 # YOLO模型目录
│
└── libs/                   # 第三方库
    ├── IbInputSimulator.dll
    └── IbInputSimulator-master/
```

## 依赖环境

- Python 3.8+
- PyQt5
- OpenCV (cv2)
- NumPy
- Ultralytics (YOLO)
- pynput
- bettercam

安装依赖：
```bash
pip install PyQt5 opencv-python numpy ultralytics pynput bettercam
```

## 快速开始

1. 确保已安装所有依赖
2. 配置 `config/config.json` 或运行 `ui/config_panel.py` 图形界面进行配置
3. 运行程序：
```bash
python main.py
```

## 配置说明

### 基础配置（config/config.json）

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `MODEL_PATH` | YOLO模型路径（相对于项目根目录） | `models/v11n5121.engine` |
| `USE_TRT` | 是否使用TensorRT加速 | `true` |
| `FPS` | 捕获帧率 | `120` |
| `DEVICE` | 运行设备 | `cuda` |
| `IMG_SIZE` | 模型输入尺寸 | `512` |
| `CONF_THRESHOLD` | 检测置信度阈值 | `0.51` |
| `aim_button` | 自瞄触发按键 | `x1`（鼠标侧键） |
| `trigger_mode` | 触发模式：`hold`按住生效 / `toggle`切换 | `hold` |
| `smooth_factor` | 自瞄平滑系数 | `4.0` |
| `lerp_factor` | 辅助平滑系数 | `0.9` |
| `y_offset_ratio` | 主模式垂直瞄准偏移（0=头顶，1=脚底） | `0.17` |
| `y_offset_ratio_alt` | 副模式垂直瞄准偏移 | `0.54` |
| `lock_radius` | 目标锁定半径（像素） | `80` |
| `target_switch_cooldown` | 目标切换冷却帧数 | `5` |
| `ib_driver` | 输入驱动类型 | `Logitech` |
| `ib_dll_path` | DLL路径 | `libs/IbInputSimulator.dll` |
| `resolution_preset` | 分辨率预设 | `1920x1080` |
| `capture_size` | 捕获范围大小：`small`/`large` | `small` |
| `enable_preview` | 启用预览窗口 | `true` |

### 输入驱动

支持以下输入驱动：
- `Logitech` - 罗技驱动
- `LogitechGHubNew` - 新版罗技G HUB
- `Razer` - 雷云
- `DD` - DD虚拟鼠标
- `MouClassInputInjection` - MouClass注入
- `AnyDriver` - 自动选择可用驱动

### 按键说明

- **自瞄按键**：默认鼠标侧键（X1/后退键）
- **退出按键**：按 `Delete` 键退出程序
- **模式切换**：鼠标前进键（X2）切换主/副瞄准模式
- **热更新**：按 `Insert` 打开配置菜单（运行时调整参数）

## 架构说明

程序采用多线程架构：

1. **主线程**：GUI事件循环、状态管理
2. **抓帧线程**：持续捕获屏幕画面
3. **推理线程**：YOLO目标检测 + 鼠标移动控制

线程间通过队列通信：
- `frame_queue`：抓帧线程 → 推理线程
- `annotated_queue`：推理线程 → 主线程（预览用）

## 热更新配置

运行时按 `Insert` 打开配置菜单，可实时调整以下参数：
- 主/副模式瞄准位置
- 置信度阈值
- 平滑系数
- 辅助平滑度
- 锁敌半径
- 预览窗口开关

调整后点击「应用」即可生效，无需重启程序。

## 预览窗口

程序会创建以下辅助窗口：
- **预览小窗**：可拖动，显示检测画面
- **识别框指示窗**：显示捕获区域边界
- **FPS信息窗**：显示实时帧率和当前模式

## 注意事项

1. 部分输入驱动（如Logitech）需要安装对应软件才能使用
2. TensorRT模型（.engine）需要与GPU计算能力匹配
3. 目标切换冷却时间用于防止目标跳动
4. 垂直偏移比例：0.0 = 头顶，1.0 = 脚底
5. 配置文件位于 `config/` 目录
6. 模型文件放在 `models/` 目录
7. 第三方库放在 `libs/` 目录
