#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
主程序入口文件
负责初始化日志和调用核心模块
"""

import sys
import os
import logging

# 添加项目根目录到Python路径
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.append(PROJECT_ROOT)


def setup_logging() -> None:
    """
    配置全局日志（仅在主入口调用一次）
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%H:%M:%S',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    # 降低第三方库的日志级别
    logging.getLogger('ultralytics').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)


def main() -> None:
    """
    主函数 - 程序入口点
    """
    # 配置日志（在导入其他模块之前）
    setup_logging()
    
    logger = logging.getLogger(__name__)
    logger.info("正在启动自瞄程序...")
    
    try:
        # 导入主应用类
        from core.aimbot_main import AimBotApp
        
        # 创建并运行应用
        app = AimBotApp()
        app.run()
        
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    except FileNotFoundError as e:
        logger.error(f"文件不存在: {e}")
    except ImportError as e:
        logger.error(f"模块导入失败: {e}")
        logger.error("请确保已安装所有依赖: pip install -r requirements.txt")
    except Exception as e:
        logger.error(f"程序运行出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        logger.info("程序已退出")


if __name__ == "__main__":
    main()