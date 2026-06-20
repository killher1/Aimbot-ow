# -*- coding: utf-8 -*-
"""
配置管理模块
负责加载、验证和管理配置
"""
import json
import os
import ctypes
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

# 使用项目根目录作为基准路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')

# 默认配置
DEFAULT_CONFIG: Dict[str, Any] = {
    "MODEL_PATH": "models/v11n5121.engine",
    "USE_TRT": True,
    "SMALL_WIN_SIZE": [400, 300],
    "FPS": 120,
    "DEVICE": 'cuda',
    "IMG_SIZE": 512,
    "CONF_THRESHOLD": 0.32,
    "aim_button": "x1",
    "y_offset_ratio": 0.12,        # 主模式：头部/脖子
    "y_offset_ratio_alt": 0.50,    # 副模式：身体中心
    "smooth_factor": 4.0,
    "lerp_factor": 0.9,
    "trigger_mode": "hold",
    "exit_key_combo": ["f12"],
    "resolution_preset": "auto",
    "capture_size": "small",
    "enable_preview": True,
    "ib_driver": "Logitech",
    "ib_dll_path": "libs/IbInputSimulator.dll",
    "lock_radius": 80,
    "target_switch_cooldown": 5,
}

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
    'aim_button': {'type': str, 'allowed': ['x1', 'x2', 'right', 'rshift']},
    'trigger_mode': {'type': str, 'allowed': ['hold', 'toggle']},
    'ib_driver': {'type': str, 'allowed': [
        'AnyDriver', 'SendInput', 'Logitech', 'LogitechGHubNew',
        'Razer', 'DD', 'MouClassInputInjection'
    ]},
}


def validate_config_value(key: str, value: Any) -> tuple[bool, str]:
    """
    验证单个配置值
    
    Args:
        key: 配置键名
        value: 配置值
        
    Returns:
        (是否有效, 错误消息)
    """
    if key not in CONFIG_RULES:
        return True, ""  # 没有规则的配置项跳过验证
    
    rules = CONFIG_RULES[key]
    
    # 类型检查
    expected_type = rules.get('type')
    if expected_type and not isinstance(value, expected_type):
        return False, f"类型错误: 期望 {expected_type}, 实际 {type(value).__name__}"
    
    # 范围检查
    if 'min' in rules and isinstance(value, (int, float)):
        if value < rules['min']:
            return False, f"值 {value} 小于最小值 {rules['min']}"
    if 'max' in rules and isinstance(value, (int, float)):
        if value > rules['max']:
            return False, f"值 {value} 大于最大值 {rules['max']}"
    
    # 允许值检查
    if 'allowed' in rules and value not in rules['allowed']:
        return False, f"值 '{value}' 不在允许列表中: {rules['allowed']}"
    
    return True, ""


def validate_config(config: Dict[str, Any]) -> tuple[bool, list[str]]:
    """
    验证配置参数的有效性
    
    Args:
        config: 配置字典
        
    Returns:
        (是否有效, 错误消息列表)
    """
    errors = []
    warnings = []
    
    # 验证每个配置项
    for key, rules in CONFIG_RULES.items():
        if key not in config:
            warnings.append(f"配置项 '{key}' 缺失，将使用默认值")
            continue
        
        value = config[key]
        is_valid, error_msg = validate_config_value(key, value)
        if not is_valid:
            errors.append(f"配置项 '{key}': {error_msg}")
    
    # 验证SMALL_WIN_SIZE
    if 'SMALL_WIN_SIZE' in config:
        size = config['SMALL_WIN_SIZE']
        if not isinstance(size, (list, tuple)) or len(size) != 2:
            errors.append("SMALL_WIN_SIZE 必须是包含2个元素的列表或元组")
        elif not all(isinstance(x, int) and x > 0 for x in size):
            errors.append("SMALL_WIN_SIZE 的元素必须是正整数")
    
    # 验证模型文件
    model_path = config.get('MODEL_PATH', '')
    if model_path:
        full_path = os.path.join(PROJECT_ROOT, model_path)
        if not os.path.exists(full_path):
            errors.append(f"模型文件不存在: {full_path}")
    
    # 验证DLL文件（仅警告）
    dll_path = config.get('ib_dll_path', 'libs/IbInputSimulator.dll')
    if dll_path:
        full_path = os.path.join(PROJECT_ROOT, dll_path)
        if not os.path.exists(full_path):
            warnings.append(f"DLL文件不存在: {full_path}，将使用系统鼠标移动")
    
    # 输出警告
    for warning in warnings:
        logger.warning(warning)
    
    # 输出错误
    for error in errors:
        logger.error(error)
    
    return len(errors) == 0, errors


def load_config() -> Dict[str, Any]:
    """
    加载配置文件
    
    Returns:
        配置字典
    """
    config = DEFAULT_CONFIG.copy()
    
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                config.update(user_config)
                logger.info(f"配置文件加载成功: {CONFIG_FILE}")
        else:
            logger.warning(f"配置文件不存在，使用默认配置: {CONFIG_FILE}")
            # 创建默认配置文件
            save_config(config)
    except json.JSONDecodeError as e:
        logger.error(f"配置文件JSON格式错误: {e}")
    except Exception as e:
        logger.error(f"配置加载失败: {e}")
    
    # 验证配置
    is_valid, errors = validate_config(config)
    if not is_valid:
        logger.error("配置验证失败，使用默认值覆盖无效配置项")
        # 对于无效配置项，使用默认值
        for key in DEFAULT_CONFIG:
            if key in config:
                is_valid, _ = validate_config_value(key, config[key])
                if not is_valid:
                    config[key] = DEFAULT_CONFIG[key]
                    logger.warning(f"配置项 '{key}' 已恢复为默认值: {DEFAULT_CONFIG[key]}")
    
    return config


def save_config(config: Dict[str, Any]) -> bool:
    """
    保存配置到文件
    
    Args:
        config: 配置字典
        
    Returns:
        是否保存成功
    """
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        logger.info(f"配置已保存到: {CONFIG_FILE}")
        return True
    except Exception as e:
        logger.error(f"配置保存失败: {e}")
        return False


def get_capture_region(config: Dict[str, Any]) -> Dict[str, int]:
    """
    根据配置计算捕获区域
    
    Args:
        config: 配置字典
        
    Returns:
        捕获区域字典 {'top', 'left', 'width', 'height'}
    """
    preset = config.get('resolution_preset', 'auto')
    user32 = ctypes.windll.user32
    sw, sh = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    
    # 预设分辨率对应的捕获区域
    if preset == '1920x1080':
        # 修正: top=200 导致中心偏上40像素，正确计算: (1080 - 600) / 2 = 240
        region = {'top': 240, 'left': 560, 'width': 800, 'height': 600}
    elif preset == '1440x1080':
        region = {'top': 240, 'left': 320, 'width': 800, 'height': 600}
    else:  # auto
        region = {
            'top': sh // 4,
            'left': (sw - 800) // 2,
            'width': 800,
            'height': 600
        }
    
    # 应用缩放
    scale_map = {'small': 0.75, 'large': 1.25}
    scale = scale_map.get(config.get('capture_size'), 1.0)
    
    if scale != 1.0:
        nw = int(region['width'] * scale)
        nh = int(region['height'] * scale)
        region['left'] += (region['width'] - nw) // 2
        region['top'] += (region['height'] - nh) // 2
        region['width'] = nw
        region['height'] = nh
    
    logger.debug(f"捕获区域: {region}")
    return region