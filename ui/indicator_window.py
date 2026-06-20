# -*- coding: utf-8 -*-
"""
指示器窗口模块
负责显示捕获区域边框和瞄准状态
"""
import ctypes
import logging
from typing import Optional, Tuple
from tkinter import Toplevel, Canvas

logger = logging.getLogger(__name__)


class IndicatorWindow:
    """指示器窗口 - 显示捕获区域边框和瞄准状态"""
    
    # 边框颜色
    COLOR_IDLE = "cyan"      # 空闲状态
    COLOR_AIMING = "red"     # 瞄准状态
    
    def __init__(
        self,
        parent,
        region: dict,
        border_width: int = 4
    ):
        """
        初始化指示器窗口
        
        Args:
            parent: 父窗口
            region: 捕获区域 {'left', 'top', 'width', 'height'}
            border_width: 边框宽度
        """
        self.region = region
        self.border_width = border_width
        self.window: Optional[Toplevel] = None
        self.canvas: Optional[Canvas] = None
        self.border_item = None
        self._is_aiming = False
        
        self._create_window(parent)
    
    def _create_window(self, parent) -> None:
        """创建窗口"""
        left = self.region['left']
        top = self.region['top']
        width = self.region['width']
        height = self.region['height']
        
        self.window = Toplevel(parent)
        self.window.overrideredirect(True)  # 无边框
        self.window.geometry(f"{width}x{height}+{left}+{top}")
        self.window.wm_attributes("-topmost", True)
        self.window.attributes("-transparentcolor", "magenta")
        self.window.config(bg="magenta")
        
        self.canvas = Canvas(
            self.window,
            bg="magenta",
            highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True)
        
        # 创建边框
        self.border_item = self.canvas.create_rectangle(
            0, 0, width - 1, height - 1,
            outline=self.COLOR_IDLE,
            width=self.border_width
        )
        
        logger.debug(f"指示器窗口已创建: {width}x{height} at ({left}, {top})")
    
    def set_aiming(self, is_aiming: bool) -> None:
        """
        设置瞄准状态
        
        Args:
            is_aiming: 是否正在瞄准
        """
        if self._is_aiming != is_aiming:
            self._is_aiming = is_aiming
            color = self.COLOR_AIMING if is_aiming else self.COLOR_IDLE
            if self.canvas and self.border_item is not None:
                self.canvas.itemconfig(self.border_item, outline=color)
    
    def set_topmost(self) -> None:
        """设置窗口置顶"""
        if self.window:
            try:
                hwnd = self.window.winfo_id()
                ctypes.windll.user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002)
            except Exception as e:
                logger.debug(f"设置指示器窗口置顶失败: {e}")
    
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
            self.canvas = None
            self.border_item = None
            logger.debug("指示器窗口已销毁")