# -*- coding: utf-8 -*-
"""
输入控制器模块
负责鼠标移动和输入模拟
"""
import ctypes
import os
import sys
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class InputController:
    """输入控制器 - 负责鼠标移动"""
    
    def __init__(self, config: dict):
        """
        初始化输入控制器
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.ib = None
        self.move_func = None
        self.driver_name = config.get("ib_driver", "AnyDriver")
        self._is_healthy = False
        
        self._init_driver()
    
    def _validate_dll_path(self, dll_path: str) -> Tuple[bool, str]:
        """
        验证DLL路径安全性
        
        Args:
            dll_path: DLL文件路径
            
        Returns:
            (是否安全, 完整路径或错误消息)
        """
        if not dll_path:
            return False, "DLL路径为空"
        
        # 防止路径遍历攻击
        if '..' in dll_path or '://' in dll_path:
            return False, f"不安全的DLL路径: {dll_path}"
        
        full_path = os.path.normpath(os.path.join(PROJECT_ROOT, dll_path))
        
        # 确保路径在项目目录内
        if not full_path.startswith(os.path.normpath(PROJECT_ROOT)):
            return False, f"DLL路径超出项目目录: {dll_path}"
        
        # 检查文件扩展名
        if not dll_path.lower().endswith('.dll'):
            return False, f"文件不是DLL: {dll_path}"
        
        if not os.path.exists(full_path):
            return False, f"DLL文件不存在: {full_path}"
        
        return True, full_path
    
    def _init_driver(self) -> None:
        """初始化输入驱动"""
        try:
            ib_dir = os.path.join(PROJECT_ROOT, "libs", "IbInputSimulator-master")
            if ib_dir not in sys.path:
                sys.path.append(ib_dir)
            
            from ib_input import IbInput, MoveMode, SendType
            
            # 驱动类型映射
            driver_map = {
                "AnyDriver": SendType.AnyDriver,
                "SendInput": SendType.SendInput,
                "Logitech": SendType.Logitech,
                "LogitechGHubNew": SendType.LogitechGHubNew,
                "Razer": SendType.Razer,
                "DD": SendType.DD,
                "MouClassInputInjection": SendType.MouClassInputInjection,
            }
            
            send_type = driver_map.get(self.driver_name, SendType.AnyDriver)
            
            # 验证DLL路径
            dll_path = self.config.get("ib_dll_path", "libs/IbInputSimulator.dll")
            is_safe, result = self._validate_dll_path(dll_path)
            
            if not is_safe:
                logger.warning(f"DLL路径验证失败: {result}，回退到系统鼠标移动")
                self._fallback_to_system()
                return
            
            self.ib = IbInput(
                dll_path=result,
                send_type=send_type,
                flags=1,
            )
            
            # 根据驱动类型选择移动函数
            if self.driver_name == "AnyDriver":
                def _move_impl(dx: int, dy: int, mode=MoveMode.Relative):
                    cur_x, cur_y = self.get_cursor_pos()
                    return self.ib.mouse_move(cur_x + dx, cur_y + dy, MoveMode.Absolute)
                self.move_func = _move_impl
            else:
                def _move_impl(dx: int, dy: int, mode=MoveMode.Relative):
                    return self.ib.mouse_move(dx, dy, mode)
                self.move_func = _move_impl
            
            self._is_healthy = True
            logger.info(f"IbInputSimulator 初始化成功（驱动: {self.driver_name})")
            
        except ImportError as e:
            logger.warning(f"IbInputSimulator 模块导入失败 ({e})，回退到系统鼠标移动")
            self._fallback_to_system()
        except Exception as e:
            logger.warning(f"IbInputSimulator 加载失败 ({e})，回退到系统鼠标移动")
            self._fallback_to_system()
    
    def _fallback_to_system(self) -> None:
        """回退到系统鼠标移动"""
        self.ib = None
        self._is_healthy = False
        self.move_func = self._system_move
        logger.info("使用系统 SetCursorPos 进行鼠标移动")
    
    def destroy(self) -> None:
        """释放底层驱动资源"""
        if self.ib is not None:
            try:
                self.ib.destroy()
                logger.info("IbInputSimulator 资源已释放")
            except Exception as e:
                logger.error(f"释放 IbInputSimulator 资源时出错: {e}")
            finally:
                self.ib = None
                self._is_healthy = False
    
    def _system_move(self, dx: int, dy: int, mode=None) -> None:
        """系统鼠标移动"""
        cur_x, cur_y = self.get_cursor_pos()
        ctypes.windll.user32.SetCursorPos(int(cur_x + dx), int(cur_y + dy))
    
    def get_cursor_pos(self) -> Tuple[int, int]:
        """
        获取当前鼠标位置
        
        Returns:
            (x, y) 鼠标坐标
        """
        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
        pt = POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        return pt.x, pt.y
    
    def move_mouse_relative(self, dx: int, dy: int) -> bool:
        """
        相对移动鼠标
        
        Args:
            dx: X方向移动量
            dy: Y方向移动量
            
        Returns:
            是否成功移动
        """
        if abs(dx) < 1 and abs(dy) < 1:
            return False
        
        try:
            self.move_func(int(dx), int(dy))
            return True
        except Exception as e:
            logger.error(f"鼠标移动失败: {e}")
            self._is_healthy = False
            return False
    
    def is_healthy(self) -> bool:
        """
        检查输入控制器健康状态
        
        Returns:
            是否健康
        """
        return self._is_healthy
    
    def check_health(self) -> Tuple[bool, str]:
        """
        执行健康检查
        
        Returns:
            (是否健康, 状态消息)
        """
        if self.ib is None:
            if self.move_func == self._system_move:
                return True, "使用系统鼠标移动"
            return False, "驱动未初始化"
        
        try:
            # 尝试获取鼠标位置来验证驱动是否正常
            x, y = self.get_cursor_pos()
            return True, f"驱动正常，鼠标位置: ({x}, {y})"
        except Exception as e:
            return False, f"驱动异常: {e}"