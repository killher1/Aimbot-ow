# -*- coding: utf-8 -*-
"""配置验证模块"""
import os
import logging
from typing import Any

logger = logging.getLogger(__name__)

# 配置验证规则
CONFIG_RULES = {
    'FPS': {'type': int, 'min': 30, 'max': 240},
    'IMG_SIZE': {'type': int, 'min': 256, 'max': 1024},
    'CONF_THRESHOLD': {'type': (int, float), 'min': 0.0, 'max': 1.0},
    'smooth_factor': {'type': (int, float), 'min': 1.0, 'max': 20.0},
    'lerp_factor': {'type': (int, float), 'min': 0.0, 'max': 1.0},
    'y_offset_ratio': {'type': (int, float), 'min': 0.0, 'max': 1.0},
    'y_offset_ratio_alt': {'type': (int, float), 'min': 0.0, 'max': 1.0},
    'lock_radius': {'type': int, 'min': 10, 'max': 500},
    'target_switch_cooldown': {'type': int, 'min': 0, 'max': 60},
    'SMALL_WIN_SIZE': {'type': tuple, 'length': 2},
    'aim_button': {'type': str, 'allowed': ['x1', 'x2', 'right', 'rshift']},
    'trigger_mode': {'type': str, 'allowed': ['hold', 'toggle']},
    'ib_driver': {'type': str, 'allowed': [
        'AnyDriver', 'SendInput', 'Logitech', 'LogitechGHubNew', 
        'Razer', 'DD', 'MouClassInputInjection'
    ]},
}


def validate_config(config: dict[str, Any]) -> tuple[bool, list[str]]:
    """
    验证配置参数的有效性
    
    Args:
        config: 配置字典
        
    Returns:
        (是否有效, 错误消息列表)
    """
    errors = []
    warnings = []
    
    for key, rules in CONFIG_RULES.items():
        if key not in config:
            warnings.append(f"配置项 '{key}' 缺失，将使用默认值")
            continue
            
        value = config[key]
        
        # 类型检查
        expected_type = rules.get('type')
        if expected_type and not isinstance(value, expected_type):
            errors.append(f"配置项 '{key}' 类型错误: 期望 {expected_type}, 实际 {type(value).__name__}")
            continue
        
        # 范围检查
        if 'min' in rules and isinstance(value, (int, float)):
            if value < rules['min']:
                errors.append(f"配置项 '{key}' 值 {value} 小于最小值 {rules['min']}")
        if 'max' in rules and isinstance(value, (int, float)):
            if value > rules['max']:
                errors.append(f"配置项 '{key}' 值 {value} 大于最大值 {rules['max']}")
        
        # 允许值检查
        if 'allowed' in rules and value not in rules['allowed']:
            errors.append(f"配置项 '{key}' 值 '{value}' 不在允许列表中: {rules['allowed']}")
        
        # 元组长度检查
        if 'length' in rules and hasattr(value, '__len__'):
            if len(value) != rules['length']:
                errors.append(f"配置项 '{key}' 长度错误: 期望 {rules['length']}, 实际 {len(value)}")
    
    # 模型文件检查
    model_path = config.get('MODEL_PATH', '')
    if model_path:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        full_path = os.path.join(base_dir, model_path)
        if not os.path.exists(full_path):
            errors.append(f"模型文件不存在: {full_path}")
    
    # DLL文件检查
    dll_path = config.get('ib_dll_path', 'IbInputSimulator.dll')
    if dll_path:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        full_path = os.path.join(base_dir, dll_path)
        if not os.path.exists(full_path):
            warnings.append(f"DLL文件不存在: {full_path}，将使用系统鼠标移动")
    
    # 输出警告
    for warning in warnings:
        logger.warning(warning)
    
    # 输出错误
    for error in errors:
        logger.error(error)
    
    return len(errors) == 0, errors


def validate_dll_path(dll_path: str) -> tuple[bool, str]:
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
    
    # 只允许相对路径或当前目录下的文件
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    full_path = os.path.normpath(os.path.join(base_dir, dll_path))
    
    # 确保路径在项目目录内
    if not full_path.startswith(os.path.normpath(base_dir)):
        return False, f"DLL路径超出项目目录: {dll_path}"
    
    # 检查文件扩展名
    if not dll_path.lower().endswith('.dll'):
        return False, f"文件不是DLL: {dll_path}"
    
    if not os.path.exists(full_path):
        return False, f"DLL文件不存在: {full_path}"
    
    return True, full_path