# -*- coding: utf-8 -*-
"""
瞄准控制器模块
负责计算鼠标移动和瞄准逻辑
"""
import math
import logging
from typing import Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AimResult:
    """瞄准计算结果"""
    move_x: int
    move_y: int
    remain_x: float
    remain_y: float
    target_x: Optional[float] = None
    target_y: Optional[float] = None


class AimController:
    """瞄准控制器 - 负责计算鼠标移动"""
    
    def __init__(
        self,
        smooth_factor: float = 8.0,
        lerp_factor: float = 0.8,
        min_move_threshold: float = 1.0
    ):
        """
        初始化瞄准控制器
        
        Args:
            smooth_factor: 平滑系数，值越大移动越平滑
            lerp_factor: 线性插值系数，控制移动比例
            min_move_threshold: 最小移动阈值，小于此值不移动
        """
        self.smooth_factor = smooth_factor
        self.lerp_factor = lerp_factor
        self.min_move_threshold = min_move_threshold
        
        # 余数累加器（解决微小位移被丢弃的问题）
        self.remain_x = 0.0
        self.remain_y = 0.0
    
    def reset_remainder(self) -> None:
        """重置余数累加器"""
        self.remain_x = 0.0
        self.remain_y = 0.0
    
    def calculate_move(
        self,
        target_local_x: float,
        target_local_y: float,
        center_x: float,
        center_y: float,
        smooth_factor: Optional[float] = None,
        lerp_factor: Optional[float] = None
    ) -> AimResult:
        """
        计算鼠标移动量
        
        Args:
            target_local_x: 目标在捕获区域的X坐标
            target_local_y: 目标在捕获区域的Y坐标
            center_x: 捕获区域中心X
            center_y: 捕获区域中心Y
            smooth_factor: 可选的平滑系数覆盖
            lerp_factor: 可选的插值系数覆盖
            
        Returns:
            AimResult: 包含移动量和余数的结果对象
        """
        smooth = smooth_factor if smooth_factor is not None else self.smooth_factor
        lerp = lerp_factor if lerp_factor is not None else self.lerp_factor
        
        # 计算偏移
        dx = target_local_x - center_x
        dy = target_local_y - center_y
        
        # 应用平滑和插值
        move_x_float = (dx * lerp) / smooth + self.remain_x
        move_y_float = (dy * lerp) / smooth + self.remain_y
        
        # 转换为整数移动量
        actual_move_x = int(move_x_float)
        actual_move_y = int(move_y_float)
        
        # 计算新余数
        new_remain_x = move_x_float - actual_move_x
        new_remain_y = move_y_float - actual_move_y
        
        # 更新余数
        self.remain_x = new_remain_x
        self.remain_y = new_remain_y
        
        return AimResult(
            move_x=actual_move_x,
            move_y=actual_move_y,
            remain_x=new_remain_x,
            remain_y=new_remain_y,
            target_x=target_local_x,
            target_y=target_local_y
        )
    
    def should_move(self, move_x: int, move_y: int) -> bool:
        """
        判断是否应该执行移动
        
        Args:
            move_x: X方向移动量
            move_y: Y方向移动量
            
        Returns:
            是否应该移动
        """
        return abs(move_x) >= self.min_move_threshold or abs(move_y) >= self.min_move_threshold
    
    @staticmethod
    def calculate_distance(x1: float, y1: float, x2: float, y2: float) -> float:
        """计算两点间距离"""
        return math.hypot(x2 - x1, y2 - y1)
    
    def update_params(self, smooth_factor: Optional[float] = None, lerp_factor: Optional[float] = None) -> None:
        """
        更新控制器参数
        
        Args:
            smooth_factor: 新的平滑系数
            lerp_factor: 新的插值系数
        """
        if smooth_factor is not None:
            self.smooth_factor = smooth_factor
        if lerp_factor is not None:
            self.lerp_factor = lerp_factor