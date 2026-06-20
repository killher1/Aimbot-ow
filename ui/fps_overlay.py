# -*- coding: utf-8 -*-
"""
FPS叠加层模块
负责显示FPS和当前模式信息
"""
import ctypes
import logging
from typing import Optional
from tkinter import Toplevel, Label

logger = logging.getLogger(__name__)


class FPSOverlay:
    """FPS叠加层 - 显示FPS和模式信息"""
    
    def __init__(self, parent):
        """
        初始化FPS叠加层
        
        Args:
            parent: 父窗口
        """
        self.window: Optional[Toplevel] = None
        self.fps_label: Optional[Label] = None
        self.mode_label: Optional[Label] = None
        
        self._create_window(parent)
    
    def _create_window(self, parent) -> None:
        """创建窗口"""
        self.window = Toplevel(parent)
        self.window.overrideredirect(True)
        self.window.wm_attributes("-topmost", True)
        self.window.wm_attributes("-transparentcolor", "black")
        self.window.config(bg="black")
        self.window.attributes("-alpha", 0.7)
        
        # FPS标签
        self.fps_label = Label(
            self.window,
            text="FPS: 计算中...",
            fg="white",
            bg="black",
            font=("Microsoft YaHei", 14, "bold"),
            padx=10,
            pady=5
        )
        self.fps_label.pack()
        
        # 模式标签
        self.mode_label = Label(
            self.window,
            text="模式：主",
            fg="cyan",
            bg="black",
            font=("Microsoft YaHei", 12, "bold"),
            padx=10,
            pady=2
        )
        self.mode_label.pack()
    
    def update_position(self) -> None:
        """更新窗口位置到屏幕右上角"""
        if self.window:
            self.window.update_idletasks()
            screen_width = ctypes.windll.user32.GetSystemMetrics(0)
            win_width = self.window.winfo_width()
            x = screen_width - win_width - 10
            y = 10
            self.window.geometry(f"+{x}+{y}")
    
    def update_fps(self, fps_text: str) -> None:
        """
        更新FPS显示
        
        Args:
            fps_text: FPS文本
        """
        if self.fps_label:
            self.fps_label.config(text=fps_text)
    
    def update_mode(self, mode_index: int, mode_value: float) -> None:
        """
        更新模式显示
        
        Args:
            mode_index: 模式索引 (0=主模式, 1=副模式)
            mode_value: 偏移值
        """
        if self.mode_label:
            if mode_index == 0:
                text = f"模式：主 ({mode_value:.2f} 头)"
                self.mode_label.config(fg="cyan")
            else:
                text = f"模式：副 ({mode_value:.2f} 身体)"
                self.mode_label.config(fg="orange")
            self.mode_label.config(text=text)
    
    def set_topmost(self) -> None:
        """设置窗口置顶"""
        if self.window:
            try:
                hwnd = self.window.winfo_id()
                ctypes.windll.user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002)
            except Exception as e:
                logger.debug(f"设置FPS窗口置顶失败: {e}")
    
    def set_visible(self, visible: bool) -> None:
        """
        设置窗口可见性
        
        Args:
            visible: 是否可见
        """
        if self.window:
            if visible:
                self.window.deiconify()
            else:
                self.window.withdraw()
    
    def destroy(self) -> None:
        """销毁窗口"""
        if self.window:
            try:
                self.window.destroy()
            except Exception:
                pass
            self.window = None
            self.fps_label = None
            self.mode_label = None
            logger.debug("FPS叠加层已销毁")