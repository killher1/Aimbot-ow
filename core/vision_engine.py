# -*- coding: utf-8 -*-
"""
视觉引擎模块
负责目标检测和推理
"""
from ultralytics import YOLO
import os
import logging
from typing import Optional, Tuple, List, Any

logger = logging.getLogger(__name__)

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class VisionEngine:
    """视觉引擎 - 负责目标检测"""
    
    # 类别定义
    ENEMY_CLS = 0  # 敌人类别索引
    
    def __init__(self, config: dict):
        """
        初始化视觉引擎
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.model: Optional[YOLO] = None
        self._is_healthy = False
        self._init_model()
    
    def _init_model(self) -> None:
        """初始化模型"""
        model_path = os.path.join(PROJECT_ROOT, self.config['MODEL_PATH'])
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"模型文件不存在: {model_path}")
        
        try:
            use_trt = self.config.get('USE_TRT', False)
            if use_trt and model_path.endswith('.engine'):
                logger.info(f"正在加载 TensorRT 模型: {model_path}")
            else:
                logger.info(f"正在加载 PyTorch 模型: {model_path}")
            
            self.model = YOLO(model_path)
            self._is_healthy = True
            logger.info(f"模型加载成功: {model_path}")
            
        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            self._is_healthy = False
            raise
    
    def compute_target(
        self,
        box: Tuple[int, int, int, int],
        frame_h: int,
        y_offset_ratio: Optional[float] = None
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        计算目标瞄准点
        
        Args:
            box: 边界框 (x1, y1, x2, y2)
            frame_h: 帧高度
            y_offset_ratio: 垂直偏移比例，None时使用配置默认值
            
        Returns:
            (target_x, target_y) 目标坐标，失败返回 (None, None)
        """
        try:
            x1, y1, x2, y2 = box
            width = x2 - x1
            height = y2 - y1
            
            # 水平方向：锁定方框水平中心
            target_x = x1 + width / 2
            
            # 垂直方向：使用偏移比例
            if y_offset_ratio is None:
                ratio = self.config.get("y_offset_ratio", 0.15)
            else:
                ratio = y_offset_ratio
            
            target_y = y1 + (height * ratio)
            
            return float(target_x), float(target_y)
            
        except Exception as e:
            logger.error(f"计算目标点失败: {e}")
            return None, None
    
    def detect(self, frame: Any) -> Optional[Any]:
        """
        执行目标检测
        
        Args:
            frame: 输入帧
            
        Returns:
            检测结果，失败返回None
        """
        if self.model is None:
            logger.error("模型未初始化")
            return None
        
        try:
            results = self.model(
                frame,
                imgsz=self.config['IMG_SIZE'],
                conf=self.config['CONF_THRESHOLD'],
                device=self.config['DEVICE'],
                verbose=False
            )
            self._is_healthy = True
            return results
            
        except Exception as e:
            logger.error(f"推理异常: {e}")
            self._is_healthy = False
            return None
    
    def get_enemies_from_results(
        self,
        results: Any,
        frame: Any,
        y_offset_ratio: float
    ) -> List[Tuple[float, float, float, Tuple[int, int, int, int]]]:
        """
        从检测结果中提取敌人信息
        
        Args:
            results: YOLO检测结果
            frame: 输入帧（用于获取高度）
            y_offset_ratio: 垂直偏移比例
            
        Returns:
            敌人列表 [(x, y, confidence, box), ...]
        """
        enemies = []
        
        if results is None or len(results) == 0:
            return enemies
        
        if len(results[0].boxes) == 0:
            return enemies
        
        try:
            boxes = results[0].boxes
            frame_h = frame.shape[0]
            
            for box in boxes:
                coords = box.xyxy[0].cpu().numpy().astype(int)
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                
                # 只处理敌人类别
                if cls_id == self.ENEMY_CLS:
                    tx, ty = self.compute_target(coords, frame_h, y_offset_ratio)
                    if tx is not None and ty is not None:
                        enemies.append((tx, ty, conf, tuple(coords)))
                        
        except Exception as e:
            logger.error(f"提取敌人信息失败: {e}")
        
        return enemies
    
    def destroy(self) -> None:
        """释放模型资源"""
        try:
            if self.model is not None and not isinstance(self.model, str):
                if hasattr(self.model, 'predictor') and self.model.predictor is not None:
                    del self.model.predictor
                del self.model
                self.model = None
            self._is_healthy = False
            logger.info("视觉模型资源已释放")
            
        except Exception as e:
            logger.error(f"释放视觉模型资源时出错: {e}")
    
    def is_healthy(self) -> bool:
        """
        检查模型健康状态
        
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
        if self.model is None:
            return False, "模型未加载"
        
        try:
            # 检查模型是否可以访问
            _ = self.model.names
            return True, "模型正常"
        except Exception as e:
            return False, f"模型异常: {e}"