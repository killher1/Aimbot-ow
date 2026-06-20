# -*- coding: utf-8 -*-
"""
预览窗口模块
负责显示捕获区域的实时预览
"""
import cv2
import logging
from typing import Optional, Tuple
from tkinter import Toplevel, Label
from PIL import Image, ImageTk

logger = logging.getLogger(__name__)


class PreviewWindow:
    """预览窗口 - 显示捕获区域的实时画面"""
    
    def __init__(
        self,
        parent,
        size: Tuple[int, int] = (400, 300),
        initial_position: Tuple[int, int] = (100, 100)
    ):
        """
        初始化预览窗口
        
        Args:
            parent: 父窗口
            size: 窗口尺寸 (宽, 高)
            initial_position: 初始位置 (x, y)
        """
        self.size = size
        self.window: Optional[Toplevel] = None
        self.label: Optional[Label] = None
        self.is_dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        self._photo_image = None  # 保持引用防止GC
        
        self._create_window(parent, initial_position)
    
    def _create_window(self, parent, position: Tuple[int, int]) -> None:
        """创建窗口"""
        self.window = Toplevel(parent)
        self.window.overrideredirect(True)  # 无边框
        self.window.geometry(f"{self.size[0]}x{self.size[1]}+{position[0]}+{position[1]}")
        self.window.wm_attributes("-topmost", True)
        
        self.label = Label(self.window)
        self.label.pack(fill="both", expand=True)
        
        # 绑定拖动事件
        self.window.bind("<Button-1>", self._on_drag_start)
        self.window.bind("<B1-Motion>", self._on_drag)
        self.window.bind("<ButtonRelease-1>", self._on_drag_end)
        
        logger.debug(f"预览窗口已创建: {self.size}, 位置: {position}")
    
    def _on_drag_start(self, event) -> None:
        """开始拖动"""
        self.is_dragging = True
        self.drag_start_x = event.x
        self.drag_start_y = event.y
    
    def _on_drag(self, event) -> None:
        """拖动中"""
        if self.is_dragging and self.window:
            dx = event.x - self.drag_start_x
            dy = event.y - self.drag_start_y
            x = self.window.winfo_x() + dx
            y = self.window.winfo_y() + dy
            self.window.geometry(f"+{x}+{y}")
    
    def _on_drag_end(self, event) -> None:
        """结束拖动"""
        self.is_dragging = False
    
    def update_frame(self, frame) -> None:
        """
        更新显示的帧
        
        Args:
            frame: BGR格式的帧数据
        """
        if self.label is None or self.window is None:
            return
        
        try:
            # 缩放到窗口大小
            small = cv2.resize(frame, self.size)
            # BGR转RGB
            small_rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
            # 转换为PIL图像
            pil_img = Image.fromarray(small_rgb)
            # 转换为Tk图像
            tk_img = ImageTk.PhotoImage(pil_img)
            
            # 保持引用防止被GC
            self._photo_image = tk_img
            
            # 更新标签
            self.label.config(image=tk_img)
        except Exception as e:
            logger.error(f"更新预览帧失败: {e}")
    
    def set_topmost(self) -> None:
        """设置窗口置顶"""
        if self.window:
            try:
                import ctypes
                hwnd = self.window.winfo_id()
                ctypes.windll.user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0002)
            except Exception as e:
                logger.debug(f"设置预览窗口置顶失败: {e}")
    
    @property
    def dragging(self) -> bool:
        """是否正在拖动"""
        return self.is_dragging
    
    def destroy(self) -> None:
        """销毁窗口"""
        if self.window:
            try:
                self.window.destroy()
            except Exception:
                pass
            self.window = None
            self.label = None
            self._photo_image = None
            logger.debug("预览窗口已销毁")