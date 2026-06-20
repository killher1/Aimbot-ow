# ========================================
# 配置面板模块 - 参数配置界面
# ========================================
import sys
import json
import os
import logging
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSlider,
    QPushButton,
    QComboBox,
    QButtonGroup,
    QRadioButton,
    QFormLayout,
    QMessageBox,
    QDoubleSpinBox,
    QCheckBox,
    QSpinBox,
)
from PyQt5.QtCore import Qt

logger = logging.getLogger(__name__)

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(PROJECT_ROOT, 'config', 'config.json')

class ConfigPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.load_config_to_ui()
        self.detect_and_set_resolution()
        self.update_model_options()

    def initUI(self):
        self.setWindowTitle('自瞄程序 - 参数配置')
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(['自动检测', '1920x1080 (全屏)', '1440x1080 (全屏)', '自定义'])
        form_layout.addRow(QLabel("分辨率预设:"), self.resolution_combo)

        self.capture_size_combo = QComboBox()
        self.capture_size_combo.addItems(['小范围', '中等(默认)', '大范围'])
        form_layout.addRow(QLabel("识别范围大小:"), self.capture_size_combo)

        self.use_trt_checkbox = QCheckBox("使用TensorRT模型(.engine)")
        form_layout.addRow(QLabel("模型类型:"), self.use_trt_checkbox)
        self.use_trt_checkbox.stateChanged.connect(self.update_model_options)

        self.model_combo = QComboBox()
        form_layout.addRow(QLabel("检测模型:"), self.model_combo)

        self.aim_button_combo = QComboBox()
        self.aim_button_combo.addItems([
            '鼠标侧键 1 (后退)', 
            '键盘右 Shift'
        ])
        form_layout.addRow(QLabel("自瞄按键:"), self.aim_button_combo)

        self.trigger_mode_group = QButtonGroup()
        self.hold_radio = QRadioButton("按住生效")
        self.toggle_radio = QRadioButton("按下切换")
        self.trigger_mode_group.addButton(self.hold_radio, 0)
        self.trigger_mode_group.addButton(self.toggle_radio, 1)
        trigger_layout = QHBoxLayout()
        trigger_layout.addWidget(self.hold_radio)
        trigger_layout.addWidget(self.toggle_radio)
        form_layout.addRow(QLabel("触发模式:"), trigger_layout)

        self.preview_checkbox = QCheckBox("启用右下角预览小窗")
        self.preview_checkbox.setChecked(True)
        form_layout.addRow(QLabel("预览小窗:"), self.preview_checkbox)
        
        # 垂直偏移比例滑动条（替代原来的部位选择）
        self.y_offset_spin = QDoubleSpinBox()
        self.y_offset_spin.setRange(0.0, 1.0)  # 范围 0~1
        self.y_offset_spin.setSingleStep(0.01)
        self.y_offset_spin.setDecimals(2)
        self.y_offset_spin.setValue(0.12)
        self.y_offset_spin.setSuffix(" (0=头顶，1=脚底)")
        form_layout.addRow(QLabel("垂直瞄准位置 (主):"), self.y_offset_spin)
        
        # 垂直偏移比例（副模式）滑动条
        self.y_offset_alt_spin = QDoubleSpinBox()
        self.y_offset_alt_spin.setRange(0.0, 1.0)  # 范围 0~1
        self.y_offset_alt_spin.setSingleStep(0.01)
        self.y_offset_alt_spin.setDecimals(2)
        self.y_offset_alt_spin.setValue(0.50)  # 默认 0.50
        self.y_offset_alt_spin.setSuffix(" (副模式)")
        form_layout.addRow(QLabel("垂直瞄准位置 (副):"), self.y_offset_alt_spin)
        
        self.lerp_slider = QSlider(Qt.Horizontal)
        self.lerp_slider.setRange(10, 100)
        self.lerp_slider.setValue(80)
        
        self.lerp_spinbox = QDoubleSpinBox()
        self.lerp_spinbox.setRange(0.1, 1.0)
        self.lerp_spinbox.setSingleStep(0.01)
        self.lerp_spinbox.setDecimals(2)
        self.lerp_spinbox.setValue(0.80)
        
        self.lerp_slider.valueChanged.connect(lambda v: self.lerp_spinbox.setValue(v / 100.0))
        self.lerp_spinbox.valueChanged.connect(lambda v: self.lerp_slider.setValue(int(v * 100)))

        lerp_layout = QHBoxLayout()
        lerp_layout.addWidget(self.lerp_slider)
        lerp_layout.addWidget(self.lerp_spinbox)
        form_layout.addRow(QLabel("自瞄平滑度 (辅助):"), lerp_layout)

        self.conf_slider = QSlider(Qt.Horizontal)
        self.conf_slider.setRange(1, 99)
        self.conf_slider.setValue(50)

        self.conf_spinbox = QDoubleSpinBox()
        self.conf_spinbox.setRange(0.01, 0.99)
        self.conf_spinbox.setSingleStep(0.01)
        self.conf_spinbox.setDecimals(2)
        self.conf_spinbox.setValue(0.50)

        self.conf_slider.valueChanged.connect(lambda v: self.conf_spinbox.setValue(v / 100.0))
        self.conf_spinbox.valueChanged.connect(lambda v: self.conf_slider.setValue(int(v * 100)))
        
        conf_layout = QHBoxLayout()
        conf_layout.addWidget(self.conf_slider)
        conf_layout.addWidget(self.conf_spinbox)
        form_layout.addRow(QLabel("AI置信度阈值:"), conf_layout)
        
        self.exit_key_combo = QComboBox()
        self.exit_key_combo.addItems(['Shift + L', 'Ctrl + Q', 'F12'])
        form_layout.addRow(QLabel("退出热键:"), self.exit_key_combo)

        self.ib_driver_combo = QComboBox()
        self.ib_driver_combo.addItems(['AnyDriver', 'Logitech', 'LogitechGHubNew', 'Razer', 'DD', 'MouClassInputInjection'])
        form_layout.addRow(QLabel("注入驱动类型:"), self.ib_driver_combo)

        # 修改这里：最小值改为 1.0
        self.smooth_factor_spin = QDoubleSpinBox()
        self.smooth_factor_spin.setRange(1.0, 20.0)          # 最低改为 1.0
        self.smooth_factor_spin.setSingleStep(0.5)
        self.smooth_factor_spin.setValue(8.0)
        form_layout.addRow(QLabel("自瞄平滑度 (速度主控):"), self.smooth_factor_spin)

        # 目标锁定半径配置
        self.lock_radius_spin = QSpinBox()
        self.lock_radius_spin.setRange(30, 200)
        self.lock_radius_spin.setSingleStep(5)
        self.lock_radius_spin.setValue(80)
        self.lock_radius_spin.setSuffix(" 像素")
        form_layout.addRow(QLabel("目标锁定半径 (正常):"), self.lock_radius_spin)
        
        self.target_switch_cooldown_spin = QSpinBox()
        self.target_switch_cooldown_spin.setRange(0, 20)
        self.target_switch_cooldown_spin.setSingleStep(1)
        self.target_switch_cooldown_spin.setValue(5)
        self.target_switch_cooldown_spin.setSuffix(" 帧")
        form_layout.addRow(QLabel("目标切换冷却时间:"), self.target_switch_cooldown_spin)

        main_layout.addLayout(form_layout)
        self.save_button = QPushButton("保存配置并退出")
        self.save_button.clicked.connect(self.save_config)
        main_layout.addWidget(self.save_button)

        self.setLayout(main_layout)

        # 在所有控件创建完成后，安全地设置默认值
        self.use_trt_checkbox.setChecked(True)        # 默认启用 TensorRT
        self.update_model_options()                   # 手动调用一次，加载 .engine 文件列表

    def update_model_options(self):
        self.model_combo.clear()
        use_trt = self.use_trt_checkbox.isChecked()
        
        if use_trt:
            # 查找models目录中的engine文件
            models_dir = os.path.join(PROJECT_ROOT, "models")
            if os.path.exists(models_dir):
                engine_files = [f for f in os.listdir(models_dir) if f.endswith('.engine')]
                if engine_files:
                    # 按文件名排序，便于找到常用模型
                    engine_files.sort()
                    self.model_combo.addItems(engine_files)
                else:
                    self.model_combo.addItem("未找到.engine文件")
            else:
                self.model_combo.addItem("models目录不存在")
        else:
            # 你已放弃pt模型，这里直接禁用或提示
            self.model_combo.addItem("已禁用 PyTorch (.pt) 模型")
            self.model_combo.setEnabled(False)  # 禁用下拉框，避免误选

    def detect_and_set_resolution(self):
        try:
            desktop = QApplication.desktop()
            screen_rect = desktop.screenGeometry()
            screen_width = screen_rect.width()
            screen_height = screen_rect.height()
            
            if screen_width == 1920 and screen_height == 1080:
                self.resolution_combo.setCurrentText("1920x1080 (全屏)")
            elif screen_width == 2560 and screen_height == 1080:
                self.resolution_combo.setCurrentText("1440x1080 (全屏)")
            elif screen_width == 1440 and screen_height == 1080:
                self.resolution_combo.setCurrentText("1440x1080 (全屏)")
            else:
                self.resolution_combo.setCurrentText("自动检测")
        except:
            self.resolution_combo.setCurrentText("自动检测")

    def load_config_to_ui(self):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
            
            preset_map = {'auto': '自动检测', '1920x1080': '1920x1080 (全屏)', '1440x1080': '1440x1080 (全屏)'}
            self.resolution_combo.setCurrentText(preset_map.get(config.get('resolution_preset', 'auto'), '自动检测'))

            self.use_trt_checkbox.setChecked(config.get('USE_TRT', False))
            self.update_model_options()

            # 强制使用TRT
            self.use_trt_checkbox.setChecked(True)
            self.update_model_options()
            
            model_path = config.get('MODEL_PATH', 'models/yolo11m-pose.engine')
            # 只获取文件名部分，去除路径前缀
            model_filename = os.path.basename(model_path)
            index = self.model_combo.findText(model_filename)
            if index != -1:
                self.model_combo.setCurrentIndex(index)

            size_map = {'small': '小范围', 'normal': '中等(默认)', 'large': '大范围'}
            self.capture_size_combo.setCurrentText(size_map.get(config.get('capture_size', 'normal'), '中等(默认)'))

            aim_button_map = {'x1': 0, 'rshift': 1}
            current = config.get('aim_button', 'x1')
            index = aim_button_map.get(current, 0)
            self.aim_button_combo.setCurrentIndex(index)

            if config.get('trigger_mode', 'hold') == 'toggle':
                self.toggle_radio.setChecked(True)
            else:
                self.hold_radio.setChecked(True)

            self.lerp_spinbox.setValue(config.get('lerp_factor', 0.8))
            self.conf_spinbox.setValue(config.get('CONF_THRESHOLD', 0.5))
            self.preview_checkbox.setChecked(config.get('enable_preview', True))

            # 修改：加载垂直偏移比例
            self.y_offset_spin.setValue(config.get('y_offset_ratio', 0.12))
            
            # 加载垂直偏移比例（副模式）
            self.y_offset_alt_spin.setValue(config.get('y_offset_ratio_alt', 0.50))

            exit_key_str = '+'.join(config.get('exit_key_combo', ['shift', 'l'])).title()
            index = self.exit_key_combo.findText(exit_key_str)
            if index != -1:
                self.exit_key_combo.setCurrentIndex(index)

            self.ib_driver_combo.setCurrentText(config.get('ib_driver', 'Logitech'))

            self.smooth_factor_spin.setValue(config.get('smooth_factor', 4.0))
            
            # 【新增】加载目标锁定相关配置
            self.lock_radius_spin.setValue(config.get('lock_radius', 80))
            self.target_switch_cooldown_spin.setValue(config.get('target_switch_cooldown', 5))

        except FileNotFoundError:
            logger.info(f"配置文件 {CONFIG_FILE} 未找到，使用默认值。")
        except json.JSONDecodeError:
            logger.warning("配置文件格式错误，使用默认值。")

    def save_config(self):
        config = {}
        
        preset_map_inv = {'自动检测': 'auto', '1920x1080 (全屏)': '1920x1080', '1440x1080 (全屏)': '1440x1080', '自定义': 'custom'}
        config['resolution_preset'] = preset_map_inv.get(self.resolution_combo.currentText(), 'auto')

        use_trt = self.use_trt_checkbox.isChecked()
        config['USE_TRT'] = use_trt
        
        if use_trt:
            # 保存时加上models/路径前缀
            config['MODEL_PATH'] = "models/" + self.model_combo.currentText()
        else:
            model_text = self.model_combo.currentText().split()[0]
            config['MODEL_PATH'] = model_text

        size_map_inv = {'小范围': 'small', '中等(默认)': 'normal', '大范围': 'large'}
        config['capture_size'] = size_map_inv.get(self.capture_size_combo.currentText(), 'normal')

        aim_button_map = {0: 'x1', 1: 'rshift'}
        config['aim_button'] = aim_button_map[self.aim_button_combo.currentIndex()]

        config['trigger_mode'] = 'toggle' if self.toggle_radio.isChecked() else 'hold'
        
        config['lerp_factor'] = self.lerp_spinbox.value()
        config['CONF_THRESHOLD'] = self.conf_spinbox.value()
        config['enable_preview'] = self.preview_checkbox.isChecked()

        # 修改：保存垂直偏移比例
        config['y_offset_ratio'] = self.y_offset_spin.value()
        
        # 保存垂直偏移比例（副模式）
        config['y_offset_ratio_alt'] = self.y_offset_alt_spin.value()

        exit_key_str = self.exit_key_combo.currentText()
        if exit_key_str == 'F12':
            config['exit_key_combo'] = ['f12']
        else:
            config['exit_key_combo'] = exit_key_str.lower().split(' + ')

        config['ib_driver'] = self.ib_driver_combo.currentText()

        config['smooth_factor'] = self.smooth_factor_spin.value()
        
        # 【新增】保存目标锁定相关配置
        config['lock_radius'] = self.lock_radius_spin.value()
        config['target_switch_cooldown'] = self.target_switch_cooldown_spin.value()

        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            
            QMessageBox.information(self, "成功", "配置已保存！\n重启自瞄程序后生效。")
            QApplication.quit()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {e}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    panel = ConfigPanel()
    panel.show()
    sys.exit(app.exec_())