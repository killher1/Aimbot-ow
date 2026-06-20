# -*- coding: utf-8 -*-
"""线程工具和状态封装"""
import threading
import dataclasses
from dataclasses import dataclass, field
from typing import Optional
import copy


@dataclass
class AimState:
    """瞄准状态数据类 - 封装所有共享状态"""
    # 瞄准状态
    is_aiming: bool = False
    current_mode_index: int = 0
    is_paused: bool = False  # 暂停状态
    
    # 目标跟踪
    last_target: Optional[tuple[int, int]] = None
    target_miss_count: int = 0
    
    # 配置参数（运行时可调整）
    lock_radius: int = 80
    search_radius: int = 400
    smooth_factor: float = 8.0
    lerp_factor: float = 0.8
    
    # 余数累加器
    remain_x: float = 0.0
    remain_y: float = 0.0
    
    # 模式偏移
    y_offset_modes: list[float] = field(default_factory=lambda: [0.12, 0.50])
    
    # 区域信息
    reg_left: int = 0
    reg_top: int = 0
    reg_width: int = 800
    reg_height: int = 600
    
    # UI状态
    is_dragging: bool = False
    
    # 按键状态
    trigger_button_pressed: bool = False
    left_button_pressed: bool = False
    
    # 目标切换冷却
    target_switch_cooldown: int = 5


class ThreadSafeState:
    """线程安全的状态管理器"""
    
    def __init__(self, initial_state: Optional[AimState] = None):
        self._state = initial_state or AimState()
        self._lock = threading.Lock()
    
    def get_snapshot(self) -> AimState:
        """获取状态的线程安全快照"""
        with self._lock:
            return dataclasses.replace(self._state)
    
    def update(self, **kwargs) -> None:
        """更新状态的线程安全方法"""
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self._state, key):
                    setattr(self._state, key, value)
                else:
                    raise AttributeError(f"AimState 没有属性 '{key}'")
    
    def get(self, key: str, default=None):
        """获取单个状态值"""
        with self._lock:
            return getattr(self._state, key, default)
    
    def set(self, key: str, value) -> None:
        """设置单个状态值"""
        with self._lock:
            if hasattr(self._state, key):
                setattr(self._state, key, value)
            else:
                raise AttributeError(f"AimState 没有属性 '{key}'")
    
    @property
    def lock(self) -> threading.Lock:
        """获取锁对象（用于复杂操作）"""
        return self._lock
    
    @property
    def raw_state(self) -> AimState:
        """获取原始状态对象（必须在锁内使用）"""
        return self._state


class FPSCounter:
    """FPS计数器"""
    
    def __init__(self):
        self._frame_count = 0
        self._start_time = 0.0
        self._current_fps = 0.0
        self._lock = threading.Lock()
    
    def tick(self, current_time: float) -> Optional[float]:
        """
        记录一帧，如果超过1秒则返回新的FPS值
        
        Args:
            current_time: 当前时间戳
            
        Returns:
            如果计算了新的FPS则返回FPS值，否则返回None
        """
        with self._lock:
            if self._start_time == 0.0:
                self._start_time = current_time
            
            self._frame_count += 1
            elapsed = current_time - self._start_time
            
            if elapsed >= 1.0:
                self._current_fps = self._frame_count / elapsed
                self._frame_count = 0
                self._start_time = current_time
                return self._current_fps
            return None
    
    @property
    def fps(self) -> float:
        """获取当前FPS"""
        with self._lock:
            return self._current_fps


class HealthChecker:
    """健康检查器"""
    
    def __init__(self):
        self._camera_healthy = True
        self._model_healthy = True
        self._input_healthy = True
        self._last_check_time = 0.0
        self._lock = threading.Lock()
    
    def update_camera_status(self, healthy: bool) -> None:
        with self._lock:
            self._camera_healthy = healthy
    
    def update_model_status(self, healthy: bool) -> None:
        with self._lock:
            self._model_healthy = healthy
    
    def update_input_status(self, healthy: bool) -> None:
        with self._lock:
            self._input_healthy = healthy
    
    def is_healthy(self) -> tuple[bool, list[str]]:
        """
        检查系统健康状态
        
        Returns:
            (是否全部健康, 问题列表)
        """
        with self._lock:
            issues = []
            if not self._camera_healthy:
                issues.append("摄像头捕获异常")
            if not self._model_healthy:
                issues.append("模型推理异常")
            if not self._input_healthy:
                issues.append("输入驱动异常")
            return len(issues) == 0, issues