# -*- coding: utf-8 -*-
"""
配置菜单窗口模块
支持运行时调整参数（热加载）
"""
import tkinter as tk
from tkinter import ttk
import logging

logger = logging.getLogger(__name__)


class ConfigMenu:
    """配置菜单窗口 - 运行时调整参数"""
    
    def __init__(self, parent, config_callback):
        """
        初始化配置菜单
        
        Args:
            parent: 父窗口
            config_callback: 回调函数，用于更新配置
        """
        self.parent = parent
        self.config_callback = config_callback
        self.window = None
        self.values = {}  # 当前编辑的值
        self.entries = {}  # 输入框引用
        
    def _create_widgets(self, frame):
        """创建控件"""
        row = 0
        
        # 标题
        title_label = ttk.Label(frame, text="自瞄配置", font=("Microsoft YaHei", 14, "bold"))
        title_label.grid(row=row, column=0, columnspan=3, pady=(10, 15))
        row += 1
        
        # 主模式瞄准位置
        ttk.Label(frame, text="主模式瞄准位置").grid(row=row, column=0, sticky="w", padx=10)
        self.values['y_offset_ratio'] = tk.DoubleVar(value=self.config_callback('y_offset_ratio'))
        ttk.Scale(frame, from_=0.0, to=1.0, variable=self.values['y_offset_ratio'],
                  command=lambda x: self._on_slider_change('y_offset_ratio', is_float=True)).grid(row=row, column=1, sticky="we")
        entry = ttk.Entry(frame, width=8)
        entry.insert(0, f"{self.config_callback('y_offset_ratio'):.2f}")
        entry.bind('<FocusOut>', lambda e, k='y_offset_ratio': self._on_entry_change(k, entry, is_float=True, min_val=0.0, max_val=1.0))
        entry.grid(row=row, column=2, padx=10)
        self.entries['y_offset_ratio'] = entry
        row += 1
        
        # 副模式瞄准位置
        ttk.Label(frame, text="副模式瞄准位置").grid(row=row, column=0, sticky="w", padx=10)
        self.values['y_offset_ratio_alt'] = tk.DoubleVar(value=self.config_callback('y_offset_ratio_alt'))
        ttk.Scale(frame, from_=0.0, to=1.0, variable=self.values['y_offset_ratio_alt'],
                  command=lambda x: self._on_slider_change('y_offset_ratio_alt', is_float=True)).grid(row=row, column=1, sticky="we")
        entry = ttk.Entry(frame, width=8)
        entry.insert(0, f"{self.config_callback('y_offset_ratio_alt'):.2f}")
        entry.bind('<FocusOut>', lambda e, k='y_offset_ratio_alt': self._on_entry_change(k, entry, is_float=True, min_val=0.0, max_val=1.0))
        entry.grid(row=row, column=2, padx=10)
        self.entries['y_offset_ratio_alt'] = entry
        row += 1
        
        # 置信度阈值
        ttk.Label(frame, text="置信度阈值").grid(row=row, column=0, sticky="w", padx=10)
        self.values['CONF_THRESHOLD'] = tk.DoubleVar(value=self.config_callback('CONF_THRESHOLD'))
        ttk.Scale(frame, from_=0.0, to=1.0, variable=self.values['CONF_THRESHOLD'],
                  command=lambda x: self._on_slider_change('CONF_THRESHOLD', is_float=True)).grid(row=row, column=1, sticky="we")
        entry = ttk.Entry(frame, width=8)
        entry.insert(0, f"{self.config_callback('CONF_THRESHOLD'):.2f}")
        entry.bind('<FocusOut>', lambda e, k='CONF_THRESHOLD': self._on_entry_change(k, entry, is_float=True, min_val=0.0, max_val=1.0))
        entry.grid(row=row, column=2, padx=10)
        self.entries['CONF_THRESHOLD'] = entry
        row += 1
        
        # 平滑系数
        ttk.Label(frame, text="平滑系数").grid(row=row, column=0, sticky="w", padx=10)
        self.values['smooth_factor'] = tk.DoubleVar(value=self.config_callback('smooth_factor'))
        ttk.Scale(frame, from_=1.0, to=20.0, variable=self.values['smooth_factor'],
                  command=lambda x: self._on_slider_change('smooth_factor', is_float=True)).grid(row=row, column=1, sticky="we")
        entry = ttk.Entry(frame, width=8)
        entry.insert(0, f"{self.config_callback('smooth_factor'):.1f}")
        entry.bind('<FocusOut>', lambda e, k='smooth_factor': self._on_entry_change(k, entry, is_float=True, min_val=1.0, max_val=20.0))
        entry.grid(row=row, column=2, padx=10)
        self.entries['smooth_factor'] = entry
        row += 1
        
        # 辅助平滑度
        ttk.Label(frame, text="辅助平滑度").grid(row=row, column=0, sticky="w", padx=10)
        self.values['lerp_factor'] = tk.DoubleVar(value=self.config_callback('lerp_factor'))
        ttk.Scale(frame, from_=0.0, to=1.0, variable=self.values['lerp_factor'],
                  command=lambda x: self._on_slider_change('lerp_factor', is_float=True)).grid(row=row, column=1, sticky="we")
        entry = ttk.Entry(frame, width=8)
        entry.insert(0, f"{self.config_callback('lerp_factor'):.2f}")
        entry.bind('<FocusOut>', lambda e, k='lerp_factor': self._on_entry_change(k, entry, is_float=True, min_val=0.0, max_val=1.0))
        entry.grid(row=row, column=2, padx=10)
        self.entries['lerp_factor'] = entry
        row += 1
        
        # 锁敌半径
        ttk.Label(frame, text="锁敌半径").grid(row=row, column=0, sticky="w", padx=10)
        self.values['lock_radius'] = tk.IntVar(value=self.config_callback('lock_radius'))
        ttk.Scale(frame, from_=10, to=500, variable=self.values['lock_radius'],
                  command=lambda x: self._on_slider_change('lock_radius', is_float=False)).grid(row=row, column=1, sticky="we")
        entry = ttk.Entry(frame, width=8)
        entry.insert(0, str(self.config_callback('lock_radius')))
        entry.bind('<FocusOut>', lambda e, k='lock_radius': self._on_entry_change(k, entry, is_float=False, min_val=10, max_val=500))
        entry.grid(row=row, column=2, padx=10)
        self.entries['lock_radius'] = entry
        row += 1
        
        # 预览窗口开关
        self.values['enable_preview'] = tk.BooleanVar(value=self.config_callback('enable_preview'))
        preview_check = ttk.Checkbutton(frame, text="显示预览窗口", variable=self.values['enable_preview'])
        preview_check.grid(row=row, column=0, columnspan=3, pady=5)
        row += 1
        
        # 按钮
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=row, column=0, columnspan=3, pady=10)
        
        apply_btn = ttk.Button(button_frame, text="应用", command=self._apply_config)
        apply_btn.pack(side="left", padx=5)
        
        reset_btn = ttk.Button(button_frame, text="重置", command=self._reset_values)
        reset_btn.pack(side="left", padx=5)
        
        close_btn = ttk.Button(button_frame, text="关闭", command=self.close)
        close_btn.pack(side="left", padx=5)
        
        # 提示
        hint_label = ttk.Label(frame, text="提示：调整后点击应用即可生效", font=("Microsoft YaHei", 10), foreground="gray")
        hint_label.grid(row=row+1, column=0, columnspan=3, pady=(0, 10))
    
    def _on_slider_change(self, key, is_float=True):
        """滑块值变化处理 - 更新输入框显示"""
        value = self.values[key].get()
        # 四舍五入到合适的精度并更新输入框
        if is_float:
            if key == 'smooth_factor':
                value = round(value, 1)
                self.entries[key].delete(0, tk.END)
                self.entries[key].insert(0, f"{value:.1f}")
            else:
                value = round(value, 2)
                self.entries[key].delete(0, tk.END)
                self.entries[key].insert(0, f"{value:.2f}")
        else:
            self.entries[key].delete(0, tk.END)
            self.entries[key].insert(0, str(value))
        logger.debug(f"配置调整: {key} = {value}")
    
    def _on_entry_change(self, key, entry, is_float=True, min_val=0.0, max_val=1.0):
        """输入框值变化处理 - 更新滑块"""
        try:
            text = entry.get().strip()
            if not text:
                return
            
            if is_float:
                value = float(text)
                value = max(min(value, max_val), min_val)
                value = round(value, 1) if key == 'smooth_factor' else round(value, 2)
            else:
                value = int(text)
                value = max(min(value, max_val), min_val)
            
            # 更新滑块和变量
            self.values[key].set(value)
            
            # 更新输入框显示（格式化）
            entry.delete(0, tk.END)
            if is_float:
                if key == 'smooth_factor':
                    entry.insert(0, f"{value:.1f}")
                else:
                    entry.insert(0, f"{value:.2f}")
            else:
                entry.insert(0, str(value))
            
            logger.debug(f"输入调整: {key} = {value}")
        except ValueError:
            # 如果输入无效，重置为当前滑块值
            current_value = self.values[key].get()
            entry.delete(0, tk.END)
            if is_float:
                if key == 'smooth_factor':
                    entry.insert(0, f"{current_value:.1f}")
                else:
                    entry.insert(0, f"{current_value:.2f}")
            else:
                entry.insert(0, str(current_value))
    
    def _apply_config(self):
        """应用配置"""
        new_config = {}
        for key, var in self.values.items():
            value = var.get()
            if isinstance(value, float):
                value = round(value, 2)
            new_config[key] = value
        
        self.config_callback(None, new_config)
        logger.info(f"热加载配置: {new_config}")
    
    def _reset_values(self):
        """重置为当前值"""
        self.values['y_offset_ratio'].set(self.config_callback('y_offset_ratio'))
        self.values['y_offset_ratio_alt'].set(self.config_callback('y_offset_ratio_alt'))
        self.values['CONF_THRESHOLD'].set(self.config_callback('CONF_THRESHOLD'))
        self.values['smooth_factor'].set(self.config_callback('smooth_factor'))
        self.values['lerp_factor'].set(self.config_callback('lerp_factor'))
        self.values['lock_radius'].set(self.config_callback('lock_radius'))
    
    def show(self):
        """显示菜单"""
        if self.window is not None:
            self.window.destroy()
        
        self.window = tk.Toplevel(self.parent)
        self.window.title("自瞄配置")
        self.window.geometry("400x380")
        self.window.resizable(False, False)
        self.window.wm_attributes("-topmost", True)
        
        # 居中显示
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        x = (screen_width - 400) // 2
        y = (screen_height - 380) // 2
        self.window.geometry(f"400x380+{x}+{y}")
        
        frame = ttk.Frame(self.window, padding="10")
        frame.pack(fill="both", expand=True)
        
        self._create_widgets(frame)
        
        # 绑定关闭事件
        self.window.protocol("WM_DELETE_WINDOW", self.close)
    
    def close(self):
        """关闭菜单"""
        if self.window is not None:
            self.window.destroy()
            self.window = None
    
    def is_open(self):
        """检查菜单是否打开"""
        return self.window is not None