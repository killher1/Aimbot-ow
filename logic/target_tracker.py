# -*- coding: utf-8 -*-
"""
目标跟踪器模块
负责目标选择和跟踪逻辑
"""
import math
import logging
from typing import Optional, List, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DetectedEnemy:
    """检测到的敌人信息"""
    x: float  # 目标X坐标（捕获区域内）
    y: float  # 目标Y坐标（捕获区域内）
    confidence: float  # 置信度
    box: Tuple[int, int, int, int]  # 边界框 (x1, y1, x2, y2)


@dataclass
class TrackingResult:
    """跟踪结果"""
    target: Optional[DetectedEnemy] = None
    is_new_target: bool = False
    miss_count: int = 0
    should_clear_target: bool = False


class TargetTracker:
    """目标跟踪器 - 负责目标选择和锁定"""
    
    def __init__(
        self,
        lock_radius: int = 80,
        search_radius: int = 400,
        switch_cooldown_frames: int = 5
    ):
        """
        初始化目标跟踪器
        
        Args:
            lock_radius: 锁定半径，在此范围内优先锁定上次目标
            search_radius: 搜索半径，在此范围内搜索新目标
            switch_cooldown_frames: 目标切换冷却帧数
        """
        self.lock_radius = lock_radius
        self.search_radius = search_radius
        self.switch_cooldown_frames = switch_cooldown_frames
        
        # 跟踪状态
        self.last_target: Optional[Tuple[float, float]] = None
        self.miss_count: int = 0
    
    def reset(self) -> None:
        """重置跟踪状态"""
        self.last_target = None
        self.miss_count = 0
    
    def update_params(
        self,
        lock_radius: Optional[int] = None,
        search_radius: Optional[int] = None,
        switch_cooldown_frames: Optional[int] = None
    ) -> None:
        """更新跟踪参数"""
        if lock_radius is not None:
            self.lock_radius = lock_radius
        if search_radius is not None:
            self.search_radius = search_radius
        if switch_cooldown_frames is not None:
            self.switch_cooldown_frames = switch_cooldown_frames
    
    def select_target(
        self,
        enemies: List[DetectedEnemy],
        center_x: float,
        center_y: float,
        reg_left: int,
        reg_top: int
    ) -> TrackingResult:
        """
        选择最佳目标
        
        Args:
            enemies: 检测到的敌人列表
            center_x: 捕获区域中心X
            center_y: 捕获区域中心Y
            reg_left: 捕获区域左边距
            reg_top: 捕获区域上边距
            
        Returns:
            TrackingResult: 跟踪结果
        """
        if not enemies:
            # 没有检测到敌人
            if self.last_target is not None:
                self.miss_count += 1
                if self.miss_count > self.switch_cooldown_frames:
                    # 目标丢失超过冷却时间，清除目标
                    result = TrackingResult(
                        target=None,
                        is_new_target=False,
                        miss_count=0,
                        should_clear_target=True
                    )
                    self.last_target = None
                    self.miss_count = 0
                    return result
                return TrackingResult(
                    target=None,
                    is_new_target=False,
                    miss_count=self.miss_count,
                    should_clear_target=False
                )
            return TrackingResult(target=None)
        
        # 策略A：优先锁定上一次的目标
        if self.last_target is not None:
            last_x, last_y = self.last_target
            # 转换为捕获区域坐标
            local_last_x = last_x - reg_left
            local_last_y = last_y - reg_top
            
            nearest_in_lock = None
            min_dist = float('inf')
            
            for enemy in enemies:
                dist = math.hypot(enemy.x - local_last_x, enemy.y - local_last_y)
                if dist <= self.lock_radius and dist < min_dist:
                    min_dist = dist
                    nearest_in_lock = enemy
            
            if nearest_in_lock is not None:
                # 在锁定范围内找到上次目标
                self.miss_count = 0
                return TrackingResult(
                    target=nearest_in_lock,
                    is_new_target=False,
                    miss_count=0
                )
            else:
                # 上次目标不在锁定范围内
                self.miss_count += 1
                if self.miss_count <= self.switch_cooldown_frames:
                    # 还在冷却期内，保持上次目标
                    return TrackingResult(
                        target=None,
                        is_new_target=False,
                        miss_count=self.miss_count,
                        should_clear_target=False
                    )
                # 冷却期结束，清除上次目标，继续搜索新目标
        
        # 策略B：没有锁定目标或已确认丢失，找离屏幕中心最近的
        nearest_to_center = None
        min_dist = float('inf')
        
        for enemy in enemies:
            dist = math.hypot(enemy.x - center_x, enemy.y - center_y)
            # 移除搜索半径限制，允许锁定任何检测到的目标
            if dist < min_dist:
                min_dist = dist
                nearest_to_center = enemy
        
        if nearest_to_center is not None:
            # 找到新目标
            self.last_target = (nearest_to_center.x + reg_left, nearest_to_center.y + reg_top)
            self.miss_count = 0
            return TrackingResult(
                target=nearest_to_center,
                is_new_target=True,
                miss_count=0
            )
        
        # 搜索范围内没有目标
        return TrackingResult(target=None)
    
    def force_clear_target(self) -> None:
        """强制清除当前目标"""
        self.last_target = None
        self.miss_count = 0