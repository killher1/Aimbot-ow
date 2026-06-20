# -*- coding: utf-8 -*-
"""
主程序模块 - 自瞄应用（重构版）
使用模块化架构，包含健康检查机制
"""
import sys
import os
import cv2
import numpy as np
import ctypes
import time
import threading
import queue
import logging
import math
from typing import Optional, Dict, Any
from tkinter import Tk

from pynput import mouse, keyboard
import bettercam

# 获取项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 导入配置模块
from config.config_manager import load_config, get_capture_region

# 导入核心模块
from core.input_handler import InputController
from core.vision_engine import VisionEngine

# 导入逻辑模块
from logic.aim_controller import AimController, AimResult
from logic.target_tracker import TargetTracker, DetectedEnemy, TrackingResult

# 导入UI模块
from ui.preview_window import PreviewWindow
from ui.indicator_window import IndicatorWindow
from ui.fps_overlay import FPSOverlay
from ui.config_menu import ConfigMenu

# 导入工具模块
from utils.thread_utils import FPSCounter, HealthChecker, ThreadSafeState, AimState

logger = logging.getLogger(__name__)


class AimBotApp:
    """自瞄应用主类 - 多线程架构"""
    
    def __init__(self):
        """初始化自瞄应用"""
        logger.info("=" * 50)
        logger.info("自瞄程序启动（模块化重构版）")
        logger.info("=" * 50)
        
        self.running = True
        self._initialized = False
        
        # 加载配置
        self.cfg = load_config()
        self.reg = get_capture_region(self.cfg)
        
        # 初始化健康检查器
        self.health_checker = HealthChecker()
        
        # 初始化FPS计数器
        self.fps_counter = FPSCounter()
        
        # 初始化线程安全状态
        self.state = ThreadSafeState(AimState(
            lock_radius=self.cfg.get('lock_radius', 80),
            # 搜索半径设为捕获区域对角线的一半，确保覆盖整个区域
            search_radius=int(math.hypot(self.reg['width'], self.reg['height']) / 2),
            smooth_factor=self.cfg.get('smooth_factor', 8.0),
            lerp_factor=self.cfg.get('lerp_factor', 0.8),
            y_offset_modes=[
                self.cfg.get('y_offset_ratio', 0.12),
                self.cfg.get('y_offset_ratio_alt', 0.50)
            ],
            reg_left=self.reg['left'],
            reg_top=self.reg['top'],
            reg_width=self.reg['width'],
            reg_height=self.reg['height'],
            target_switch_cooldown=self.cfg.get('target_switch_cooldown', 5)
        ))
        
        # 初始化核心组件
        self._init_components()
        
        # 初始化UI
        self._init_ui()
        
        # 初始化输入监听
        self._init_input_listeners()
        
        # 初始化线程通信队列
        self.frame_queue = queue.Queue(maxsize=2)
        self.annotated_queue = queue.Queue(maxsize=2)
        
        # 启动工作线程
        self._start_threads()
        
        self._initialized = True
        logger.info("自瞄程序已启动，现在可以使用!")
        logger.info("FPS信息将显示在屏幕右上角")
        logger.info("按 Insert 打开配置菜单（热加载）")
        logger.info("按 Home 暂停/恢复自瞄")
        logger.info("按 Delete 退出程序")
    
    def _init_components(self) -> None:
        """初始化核心组件"""
        # 初始化摄像头
        left = self.reg['left']
        top = self.reg['top']
        right = left + self.reg['width']
        bottom = top + self.reg['height']
        
        try:
            self.camera = bettercam.create(
                region=(left, top, right, bottom),
                output_color="BGR"
            )
            self.camera.start(target_fps=self.cfg['FPS'], video_mode=True)
            
            # 验证捕获是否正常（管理员权限下可能需要等待）
            import time
            time.sleep(0.5)
            test_frame = self.camera.get_latest_frame()
            if test_frame is None:
                logger.warning("屏幕捕获初始化延迟，等待帧数据...")
                for _ in range(10):
                    time.sleep(0.1)
                    test_frame = self.camera.get_latest_frame()
                    if test_frame is not None:
                        break
            
            self.health_checker.update_camera_status(True)
            logger.info(f"摄像头初始化成功: {self.reg['width']}x{self.reg['height']} at ({left}, {top})")
        except Exception as e:
            logger.error(f"摄像头初始化失败: {e}")
            self.health_checker.update_camera_status(False)
            raise
        
        # 初始化输入控制器
        try:
            self.input = InputController(self.cfg)
            is_healthy, msg = self.input.check_health()
            self.health_checker.update_input_status(is_healthy)
            logger.info(f"输入控制器: {msg}")
        except Exception as e:
            logger.warning(f"输入控制器初始化异常: {e}")
            self.health_checker.update_input_status(False)
        
        # 初始化视觉引擎
        try:
            self.vision = VisionEngine(self.cfg)
            is_healthy, msg = self.vision.check_health()
            self.health_checker.update_model_status(is_healthy)
            logger.info(f"视觉引擎: {msg}")
        except Exception as e:
            logger.error(f"视觉引擎初始化失败: {e}")
            self.health_checker.update_model_status(False)
            raise
        
        # 初始化瞄准控制器
        self.aim_controller = AimController(
            smooth_factor=self.cfg.get('smooth_factor', 8.0),
            lerp_factor=self.cfg.get('lerp_factor', 0.8)
        )
        
        # 初始化目标跟踪器
        self.target_tracker = TargetTracker(
            lock_radius=self.cfg.get('lock_radius', 80),
            search_radius=min(self.reg['width'], self.reg['height']) // 2,
            switch_cooldown_frames=self.cfg.get('target_switch_cooldown', 5)
        )
        
        # 打印配置信息
        logger.info(f"当前配置:")
        logger.info(f"  - 瞄准位置：主模式 {self.cfg.get('y_offset_ratio', 0.12):.2f}, 副模式 {self.cfg.get('y_offset_ratio_alt', 0.50):.2f}")
        logger.info(f"  - 置信度阈值：{self.cfg['CONF_THRESHOLD']}")
        logger.info(f"  - 平滑系数：{self.cfg['smooth_factor']}")
        logger.info(f"  - 辅助平滑度：{self.cfg['lerp_factor']}")
        logger.info(f"  - 触发模式：{self.cfg['trigger_mode']}")
        logger.info(f"  - 自瞄按键：{self.cfg['aim_button']}")
    
    def _init_ui(self) -> None:
        """初始化UI组件"""
        self.root = Tk()
        self.root.withdraw()
        
        # 预览窗口
        enable_preview = self.cfg.get('enable_preview', True)
        if enable_preview:
            self.preview_window = PreviewWindow(
                self.root,
                size=tuple(self.cfg['SMALL_WIN_SIZE']),
                initial_position=(100, 100)
            )
        else:
            self.preview_window = None
        
        # 指示器窗口
        self.indicator_window = IndicatorWindow(
            self.root,
            region=self.reg
        )
        
        # FPS叠加层
        self.fps_overlay = FPSOverlay(self.root)
        self.fps_overlay.update_position()
        
        # 配置菜单（热加载）
        self.config_menu = ConfigMenu(self.root, self._get_or_update_config)
        
        # 启动窗口置顶定时器
        self.root.after(100, self._force_topmost_all)
    
    def _get_or_update_config(self, key=None, new_config=None):
        """
        获取或更新配置（用于热加载）
        
        Args:
            key: 配置键名，None表示更新配置
            new_config: 新配置字典，用于更新
        
        Returns:
            指定键的值或None
        """
        if new_config is not None:
            # 更新配置
            self.cfg.update(new_config)
            
            # 更新瞄准控制器参数
            if 'smooth_factor' in new_config:
                self.aim_controller.update_params(smooth_factor=new_config['smooth_factor'])
                self.state.update(smooth_factor=new_config['smooth_factor'])
            if 'lerp_factor' in new_config:
                self.aim_controller.update_params(lerp_factor=new_config['lerp_factor'])
                self.state.update(lerp_factor=new_config['lerp_factor'])
            
            # 更新目标跟踪器参数
            if 'lock_radius' in new_config:
                self.target_tracker.update_params(lock_radius=new_config['lock_radius'])
                self.state.update(lock_radius=new_config['lock_radius'])
            
            # 更新垂直偏移模式
            if 'y_offset_ratio' in new_config:
                modes = self.state.get('y_offset_modes')
                modes[0] = new_config['y_offset_ratio']
                self.state.update(y_offset_modes=modes)
            if 'y_offset_ratio_alt' in new_config:
                modes = self.state.get('y_offset_modes')
                modes[1] = new_config['y_offset_ratio_alt']
                self.state.update(y_offset_modes=modes)
            
            # 处理预览窗口开关
            if 'enable_preview' in new_config:
                enable = new_config['enable_preview']
                if enable and self.preview_window is None:
                    # 创建预览窗口
                    self.preview_window = PreviewWindow(
                        self.root,
                        size=tuple(self.cfg['SMALL_WIN_SIZE']),
                        initial_position=(100, 100)
                    )
                    logger.info("预览窗口已启用")
                elif not enable and self.preview_window is not None:
                    # 销毁预览窗口
                    self.preview_window.destroy()
                    self.preview_window = None
                    logger.info("预览窗口已禁用")
            
            return None
        
        # 获取配置值
        return self.cfg.get(key, 0)
    
    def _init_input_listeners(self) -> None:
        """初始化输入监听器"""
        self._pressed_keys = set()
        self.aim_button = self.cfg.get('aim_button', 'x1')
        self.is_rshift_aim = self.aim_button == 'rshift'
        
        # 鼠标监听器
        self.mouse_listener = mouse.Listener(on_click=self._on_click)
        self.mouse_listener.start()
        
        # 键盘监听器
        self.keyboard_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release
        )
        self.keyboard_listener.start()
        
        logger.info(f"按鼠标侧键 (X2) 切换瞄准模式")
    
    def _start_threads(self) -> None:
        """启动工作线程"""
        threading.Thread(target=self._capture_thread, daemon=True, name="CaptureThread").start()
        threading.Thread(target=self._inference_thread, daemon=True, name="InferenceThread").start()
    
    def _force_topmost_all(self) -> None:
        """强制所有窗口置顶"""
        if not self.running:
            return
        
        if self.preview_window:
            self.preview_window.set_topmost()
        self.indicator_window.set_topmost()
        self.fps_overlay.set_topmost()
        
        self.root.after(50, self._force_topmost_all)
    
    # ================================
    # 输入事件处理
    # ================================
    
    def _on_click(self, x: int, y: int, button: mouse.Button, pressed: bool) -> None:
        """鼠标点击事件处理"""
        # 侧键前进 (X2) 切换模式
        if button == mouse.Button.x2:
            if pressed:
                current_mode = self.state.get('current_mode_index')
                new_mode = 1 - current_mode
                self.state.update(current_mode_index=new_mode)
                mode_name = "主模式" if new_mode == 0 else "副模式"
                mode_val = self.state.raw_state.y_offset_modes[new_mode]
                logger.info(f"已切换至：{mode_name} (垂直偏移：{mode_val:.2f})")
            return
        
        # 处理自瞄按键
        button_map = {
            'right': mouse.Button.right,
            'x1': mouse.Button.x1,
        }
        aim_btn = button_map.get(self.aim_button)
        
        # 左键处理
        if button == mouse.Button.left:
            self.state.update(left_button_pressed=pressed)
            self._update_aiming_state()
            return
        
        # 自瞄按键处理
        if aim_btn and button == aim_btn:
            if self.cfg['trigger_mode'] == 'hold':
                self.state.update(trigger_button_pressed=pressed)
            elif pressed:
                current = self.state.get('trigger_button_pressed')
                self.state.update(trigger_button_pressed=not current)
            self._update_aiming_state()
    
    def _on_key_press(self, key: keyboard.Key) -> None:
        """键盘按下事件处理"""
        try:
            self._pressed_keys.add(key)
            
            # 右Shift自瞄
            if self.is_rshift_aim and key == keyboard.Key.shift_r:
                if self.cfg['trigger_mode'] == 'hold':
                    self.state.update(trigger_button_pressed=True)
                else:
                    current = self.state.get('trigger_button_pressed')
                    self.state.update(trigger_button_pressed=not current)
                self._update_aiming_state()
                return
            
            # Insert键打开配置菜单（热加载）
            if key == keyboard.Key.insert:
                if self.config_menu.is_open():
                    self.config_menu.close()
                else:
                    self.config_menu.show()
                    logger.info("配置菜单已打开")
                return
            
            # Home键暂停/恢复
            if key == keyboard.Key.home:
                self._toggle_pause()
                return
            
            # 检查退出组合键
            self._check_exit_combo()
            
        except Exception as e:
            logger.error(f"键盘按下事件异常: {e}")
    
    def _on_key_release(self, key: keyboard.Key) -> None:
        """键盘释放事件处理"""
        try:
            self._pressed_keys.discard(key)
            
            if self.is_rshift_aim and key == keyboard.Key.shift_r:
                if self.cfg['trigger_mode'] == 'hold':
                    self.state.update(trigger_button_pressed=False)
                    self._update_aiming_state()
                    
        except Exception as e:
            logger.error(f"键盘释放事件异常: {e}")
    
    def _check_exit_combo(self) -> None:
        """检查退出键 (固定为 Delete)"""
        for k in self._pressed_keys:
            if hasattr(k, 'name') and k.name.lower() == 'delete':
                logger.info("检测到退出键 (Delete)，程序即将退出...")
                self.shutdown()
                break
    
    def _update_aiming_state(self) -> None:
        """更新瞄准状态"""
        trigger_pressed = self.state.get('trigger_button_pressed')
        left_pressed = self.state.get('left_button_pressed')
        
        if self.cfg['trigger_mode'] == 'hold':
            is_aiming = trigger_pressed or left_pressed
        else:
            is_aiming = trigger_pressed
        
        self.state.update(is_aiming=is_aiming)
        self.indicator_window.set_aiming(is_aiming)
    
    def _toggle_pause(self) -> None:
        """暂停/恢复自瞄功能，隐藏/显示UI"""
        current_paused = self.state.get('is_paused')
        new_paused = not current_paused
        
        self.state.update(is_paused=new_paused)
        
        # 隐藏/显示预览窗口
        if self.preview_window and self.preview_window.window:
            if new_paused:
                self.preview_window.window.withdraw()
            else:
                self.preview_window.window.deiconify()
        
        # 隐藏/显示指示器窗口
        self.indicator_window.set_visible(not new_paused)
        
        # 隐藏/显示FPS叠加层
        self.fps_overlay.set_visible(not new_paused)
        
        if new_paused:
            logger.info("自瞄已暂停，按 Home 恢复")
        else:
            logger.info("自瞄已恢复")
    
    # ================================
    # 工作线程
    # ================================
    
    def _capture_thread(self) -> None:
        """抓帧线程"""
        logger.debug("抓帧线程启动")
        
        while self.running:
            try:
                frame = self.camera.get_latest_frame()
                if frame is not None:
                    try:
                        self.frame_queue.put_nowait(frame)
                    except queue.Full:
                        # 丢弃旧帧，放入新帧
                        try:
                            self.frame_queue.get_nowait()
                        except queue.Empty:
                            pass
                        self.frame_queue.put_nowait(frame)
                        self.health_checker.update_camera_status(True)
                else:
                    self.health_checker.update_camera_status(False)
                    
            except Exception as e:
                logger.error(f"抓帧异常: {e}")
                self.health_checker.update_camera_status(False)
                
            time.sleep(0.001)
        
        logger.debug("抓帧线程退出")
    
    def _inference_thread(self) -> None:
        """推理线程"""
        logger.debug("推理线程启动")
        skip_counter = 0
        
        while self.running:
            try:
                frame = self.frame_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            
            # FPS计数
            fps_result = self.fps_counter.tick(time.time())
            if fps_result is not None:
                fps_text = f"FPS: {fps_result:.1f}"
                self.fps_overlay.update_fps(fps_text)
            
            # 获取状态快照
            state_snapshot = self.state.get_snapshot()
            
            annotated_frame = None
            target_x = target_y = None
            
            # 检查是否正在拖动预览窗口
            is_dragging = self.preview_window and self.preview_window.dragging
            
            # 检查是否暂停
            is_paused = state_snapshot.is_paused
            
            if is_paused:
                # 暂停模式：跳过推理，只更新预览
                annotated_frame = frame.copy()
                mode_idx = state_snapshot.current_mode_index
                mode_val = state_snapshot.y_offset_modes[mode_idx]
                self.fps_overlay.update_mode(mode_idx, mode_val)
                
                if annotated_frame is not None:
                    try:
                        self.annotated_queue.put_nowait(annotated_frame)
                    except queue.Full:
                        try:
                            self.annotated_queue.get_nowait()
                        except queue.Empty:
                            pass
                        self.annotated_queue.put_nowait(annotated_frame)
                continue
            
            if state_snapshot.is_aiming and not is_dragging:
                # 瞄准模式：执行推理
                annotated_frame = frame.copy()
                skip_counter = 0
                
                results = self.vision.detect(frame)
                
                if results is None:
                    # 推理失败
                    self.target_tracker.force_clear_target()
                    self.health_checker.update_model_status(False)
                elif len(results[0].boxes) > 0:
                    # 有检测结果
                    self.health_checker.update_model_status(True)
                    
                    # 提取敌人信息
                    y_offset = state_snapshot.y_offset_modes[state_snapshot.current_mode_index]
                    enemies_data = self.vision.get_enemies_from_results(results, frame, y_offset)
                    
                    # 转换为DetectedEnemy对象
                    enemies = [
                        DetectedEnemy(x=e[0], y=e[1], confidence=e[2], box=e[3])
                        for e in enemies_data
                    ]
                    
                    # 绘制检测框
                    for enemy in enemies:
                        x1, y1, x2, y2 = enemy.box
                        cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                        cv2.putText(
                            annotated_frame,
                            f"Enemy {enemy.confidence:.2f}",
                            (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1
                        )
                        cv2.drawMarker(
                            annotated_frame,
                            (int(enemy.x), int(enemy.y)),
                            (255, 255, 255),
                            markerType=cv2.MARKER_CROSS,
                            markerSize=10, thickness=2
                        )
                    
                    # 目标选择
                    center_x = state_snapshot.reg_width / 2
                    center_y = state_snapshot.reg_height / 2
                    
                    tracking_result = self.target_tracker.select_target(
                        enemies,
                        center_x,
                        center_y,
                        state_snapshot.reg_left,
                        state_snapshot.reg_top
                    )
                    
                    if tracking_result.target:
                        target = tracking_result.target
                        target_x = target.x + state_snapshot.reg_left
                        target_y = target.y + state_snapshot.reg_top
                        
                        # 绘制目标点
                        cv2.circle(annotated_frame, (int(target.x), int(target.y)), 8, (0, 255, 255), -1)
                        
                        # 计算鼠标移动
                        aim_result = self.aim_controller.calculate_move(
                            target.x,
                            target.y,
                            center_x,
                            center_y,
                            state_snapshot.smooth_factor,
                            state_snapshot.lerp_factor
                        )
                        
                        # 执行移动
                        if self.aim_controller.should_move(aim_result.move_x, aim_result.move_y):
                            self.input.move_mouse_relative(aim_result.move_x, aim_result.move_y)
                    else:
                        # 没有目标
                        if tracking_result.should_clear_target:
                            self.aim_controller.reset_remainder()
                else:
                    # 推理成功但无检测结果（正常情况）
                    self.health_checker.update_model_status(True)
                    self.target_tracker.force_clear_target()
                    
            else:
                # 非瞄准模式：降低推理频率，但保持预览更新
                self.target_tracker.reset()
                self.aim_controller.reset_remainder()
                
                skip_counter += 1
                if skip_counter % 4 != 0:
                    # 跳过推理，但仍更新预览
                    annotated_frame = frame.copy()
                    # 直接跳到预览更新部分
                    mode_idx = state_snapshot.current_mode_index
                    mode_val = state_snapshot.y_offset_modes[mode_idx]
                    self.fps_overlay.update_mode(mode_idx, mode_val)
                    
                    if annotated_frame is not None:
                        try:
                            self.annotated_queue.put_nowait(annotated_frame)
                        except queue.Full:
                            try:
                                self.annotated_queue.get_nowait()
                            except queue.Empty:
                                pass
                            self.annotated_queue.put_nowait(annotated_frame)
                    continue
                    
                annotated_frame = frame.copy()
            
            # 更新模式显示
            mode_idx = state_snapshot.current_mode_index
            mode_val = state_snapshot.y_offset_modes[mode_idx]
            self.fps_overlay.update_mode(mode_idx, mode_val)
            
            # 发送标注帧到UI队列
            if annotated_frame is not None:
                try:
                    self.annotated_queue.put_nowait(annotated_frame)
                except queue.Full:
                    try:
                        self.annotated_queue.get_nowait()
                    except queue.Empty:
                        pass
                    self.annotated_queue.put_nowait(annotated_frame)
        
        logger.debug("推理线程退出")
    
    # ================================
    # UI更新和健康检查
    # ================================
    
    def _update_ui(self) -> None:
        """更新UI"""
        if not self.running:
            return
        
        # 更新预览窗口
        if self.preview_window:
            annotated_frame = None
            while True:
                try:
                    annotated_frame = self.annotated_queue.get_nowait()
                except queue.Empty:
                    break
            
            if annotated_frame is not None:
                self.preview_window.update_frame(annotated_frame)
        
        # 定期健康检查
        is_healthy, issues = self.health_checker.is_healthy()
        if not is_healthy:
            logger.warning(f"健康检查发现问题: {', '.join(issues)}")
        
        self.root.after(16, self._update_ui)  # ~60Hz
    
    def run(self) -> None:
        """运行应用"""
        try:
            self._update_ui()
            self.root.mainloop()
        finally:
            self.shutdown()
    
    def shutdown(self) -> None:
        """关闭应用"""
        if not self.running:
            return
        
        logger.info("正在关闭自瞄程序...")
        self.running = False
        
        # 停止摄像头
        try:
            self.camera.stop()
            logger.info("摄像头已停止")
        except Exception as e:
            logger.error(f"停止摄像头时出错: {e}")
        
        # 停止监听器
        try:
            self.mouse_listener.stop()
        except Exception as e:
            logger.error(f"停止鼠标监听时出错: {e}")
        
        try:
            self.keyboard_listener.stop()
        except Exception as e:
            logger.error(f"停止键盘监听时出错: {e}")
        
        # 释放组件资源
        try:
            self.input.destroy()
        except Exception as e:
            logger.error(f"释放输入驱动资源时出错: {e}")
        
        try:
            self.vision.destroy()
        except Exception as e:
            logger.error(f"释放视觉模型资源时出错: {e}")
        
        # 销毁UI
        try:
            if self.preview_window:
                self.preview_window.destroy()
            self.indicator_window.destroy()
            self.fps_overlay.destroy()
            self.root.quit()
        except Exception:
            pass
        
        logger.info("自瞄程序已退出")


if __name__ == '__main__':
    try:
        app = AimBotApp()
        app.run()
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"程序异常: {e}")
    finally:
        if 'app' in locals():
            app.shutdown()