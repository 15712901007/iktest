#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import subprocess
import datetime
import json
import traceback
import webbrowser
import pandas as pd
from typing import List, Dict, Any, Optional
import io
import threading
import time
import re

# 确保能找到当前目录下的模块
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QLabel,
    QMessageBox, QFileDialog, QTextEdit, QTreeWidget, QTreeWidgetItem,
    QCheckBox, QDialog, QFormLayout, QDialogButtonBox, QSpinBox, QListWidget,
    QTabWidget, QGroupBox, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter, QFrame, QButtonGroup, QRadioButton, QScrollArea,
    QProgressBar, QListWidgetItem
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QTimer, QObject
from PyQt5.QtGui import QTextCursor, QFont, QIcon

try:
    from test_framework import RouterTestConfig
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保 test_framework.py 文件在当前目录下")
    sys.exit(1)

class TestResult:
    """用于存储一次测试的结果和日志"""
    def __init__(self, test_id, test_name):
        self.test_id = test_id
        self.test_name = test_name
        self.start_time = None
        self.end_time = None
        self.status = "未执行"
        self.fail_steps = 0
        self.success_steps = 0
        self.execution_logs = []
        self.failure_logs = []
        self.test_steps = ""
        self.full_output = ""
        self.step_details = []

    def get_duration_seconds(self):
        """返回当前测试的执行时长(秒)"""
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            return delta.total_seconds()
        return 0.0

class ScriptModuleManager:
    """纯脚本模块管理器"""
    
    def __init__(self, modules_dir: str = "modules"):
        self.modules_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), modules_dir)
        
    def scan_modules(self) -> List[Dict]:
        """纯脚本模块扫描"""
        modules = []
        
        if not os.path.exists(self.modules_dir):
            os.makedirs(self.modules_dir)
            return modules
        
        print(f"扫描模块目录: {self.modules_dir}")
        
        for file in os.listdir(self.modules_dir):
            if file.endswith('_module.py') and not file.startswith('__'):
                print(f"发现脚本文件: {file}")
                module_info = self._create_module_info(file)
                modules.append(module_info)
                print(f"✅ 添加脚本: {module_info['info']['name']}")
        
        print(f"总共找到 {len(modules)} 个脚本")
        return sorted(modules, key=lambda x: x['info']['name'])
    
    def _create_module_info(self, filename: str) -> Dict:
        """创建脚本信息"""
        module_path = os.path.join(self.modules_dir, filename)
        module_name = filename[:-3]
        
        # 从文件名推断模块名称
        display_name = filename[:-10]  # 去掉_module.py
        if 'vlan' in filename.lower():
            display_name = "VLAN设置"
        elif 'l2tp' in filename.lower():
            display_name = "L2TP客户端"
        elif 'pptp' in filename.lower():
            display_name = "PPTP客户端"
        else:
            display_name = display_name.replace('_', ' ').title()
                
        module_info = {
            "name": display_name,
            "description": f"{display_name}自动化测试脚本",
            "version": "1.0"
        }
        
        return {
            'module_name': module_name,
            'module_path': module_path,
            'info': module_info,
            'file_name': filename
        }

class TestConfigDialog(QDialog):
    """测试配置对话框"""
    
    def __init__(self, parent=None, config: RouterTestConfig = None):
        super().__init__(parent)
        self.setWindowTitle("测试配置")
        self.setModal(True)
        self.resize(650, 550)
        
        layout = QFormLayout(self)
        
        # 路由器IP地址
        ip_group = QGroupBox("路由器连接配置")
        ip_group.setStyleSheet("QGroupBox { font-size: 16px; font-weight: bold; }")
        ip_layout = QFormLayout(ip_group)
        
        self.router_ip_input = QLineEdit(self)
        if config and config.router_url:
            import re
            ip_match = re.search(r'://([^:/]+)', config.router_url)
            current_ip = ip_match.group(1) if ip_match else "10.66.0.40"
        else:
            current_ip = "10.66.0.40"
        
        self.router_ip_input.setText(current_ip)
        self.router_ip_input.setPlaceholderText("例如: 10.66.0.40 或 192.168.1.1")
        self.router_ip_input.setStyleSheet("QLineEdit { font-size: 18px; padding: 12px; }")
        
        ip_label = QLabel("路由器IP地址 *:")
        ip_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        ip_layout.addRow(ip_label, self.router_ip_input)
        
        ip_note = QLabel("请输入要测试的路由器IP地址（仅IP地址，无需协议和端口）")
        ip_note.setStyleSheet("color: #666; font-size: 15px;")
        ip_layout.addRow(ip_note)
        
        layout.addRow(ip_group)
        
        # 登录凭据
        auth_group = QGroupBox("登录凭据")
        auth_group.setStyleSheet("QGroupBox { font-size: 16px; font-weight: bold; }")
        auth_layout = QFormLayout(auth_group)
        
        username_label = QLabel("用户名:")
        username_label.setStyleSheet("font-size: 15px;")
        self.username_input = QLineEdit(self)
        self.username_input.setText(config.username if config else "admin")
        self.username_input.setStyleSheet("QLineEdit { font-size: 16px; padding: 10px; }")
        auth_layout.addRow(username_label, self.username_input)
        
        password_label = QLabel("密码:")
        password_label.setStyleSheet("font-size: 15px;")
        self.password_input = QLineEdit(self)
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setText(config.password if config else "admin123")
        self.password_input.setStyleSheet("QLineEdit { font-size: 16px; padding: 10px; }")
        auth_layout.addRow(password_label, self.password_input)
        
        layout.addRow(auth_group)
        
        # SSH配置
        ssh_group = QGroupBox("SSH配置")
        ssh_group.setStyleSheet("QGroupBox { font-size: 16px; font-weight: bold; }")
        ssh_layout = QFormLayout(ssh_group)
        
        ssh_user_label = QLabel("SSH用户名:")
        ssh_user_label.setStyleSheet("font-size: 15px;")
        self.ssh_user_input = QLineEdit(self)
        self.ssh_user_input.setText(config.ssh_user if config else "sshd")
        self.ssh_user_input.setStyleSheet("QLineEdit { font-size: 16px; padding: 10px; }")
        ssh_layout.addRow(ssh_user_label, self.ssh_user_input)
        
        ssh_pass_label = QLabel("SSH密码:")
        ssh_pass_label.setStyleSheet("font-size: 15px;")
        self.ssh_pass_input = QLineEdit(self)
        self.ssh_pass_input.setEchoMode(QLineEdit.Password)
        self.ssh_pass_input.setText(config.ssh_pass if config else "ikuai8.com")
        self.ssh_pass_input.setStyleSheet("QLineEdit { font-size: 16px; padding: 10px; }")
        ssh_layout.addRow(ssh_pass_label, self.ssh_pass_input)
        
        layout.addRow(ssh_group)
        
        # 按钮
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.setStyleSheet("QDialogButtonBox { font-size: 15px; }")
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        
        test_btn = QPushButton("🔗 测试连接", self)
        test_btn.setStyleSheet("QPushButton { font-size: 16px; padding: 12px; }")
        test_btn.clicked.connect(self.test_connection)
        layout.addRow(test_btn)
    
    def validate_and_accept(self):
        """验证输入并接受对话框"""
        router_ip = self.router_ip_input.text().strip()
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        
        if not router_ip:
            QMessageBox.warning(self, "输入错误", "请输入路由器IP地址")
            self.router_ip_input.setFocus()
            return
        
        if not username:
            QMessageBox.warning(self, "输入错误", "请输入用户名")
            self.username_input.setFocus()
            return
        
        if not password:
            QMessageBox.warning(self, "输入错误", "请输入密码")
            self.password_input.setFocus()
            return
        
        import re
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(ip_pattern, router_ip):
            reply = QMessageBox.question(
                self, 
                "IP格式警告", 
                f"输入的IP地址格式可能不正确: {router_ip}\n\n确定要继续吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                self.router_ip_input.setFocus()
                return
        
        self.accept()
    
    def test_connection(self):
        """测试连接到路由器"""
        router_ip = self.router_ip_input.text().strip()
        if not router_ip:
            QMessageBox.warning(self, "测试连接", "请先输入路由器IP地址")
            return
        
        import subprocess
        import platform
        
        try:
            param = "-n" if platform.system().lower() == "windows" else "-c"
            cmd = ["ping", param, "1", router_ip]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                QMessageBox.information(self, "连接测试", f"✅ 能够ping通 {router_ip}")
            else:
                QMessageBox.warning(self, "连接测试", f"❌ 无法ping通 {router_ip}\n\n请检查IP地址是否正确")
        except subprocess.TimeoutExpired:
            QMessageBox.warning(self, "连接测试", f"⏱️ 连接超时: {router_ip}")
        except Exception as e:
            QMessageBox.warning(self, "连接测试", f"测试连接时出错: {str(e)}")
    
    def get_config(self) -> RouterTestConfig:
        """获取配置"""
        router_ip = self.router_ip_input.text().strip()
        
        if not router_ip.startswith('http'):
            router_url = f"http://{router_ip}/login#/login"
        else:
            router_url = router_ip if router_ip.endswith('/login#/login') else f"{router_ip}/login#/login"
        
        return RouterTestConfig(
            router_url=router_url,
            username=self.username_input.text().strip(),
            password=self.password_input.text().strip(),
            ssh_user=self.ssh_user_input.text().strip(),
            ssh_pass=self.ssh_pass_input.text().strip()
        )

class ScriptExecutionThread(QThread):
    """纯脚本执行线程"""
    
    output_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, list)
    progress_signal = pyqtSignal(int, str)
    module_status_signal = pyqtSignal(int, str)
    report_ready = pyqtSignal(list, str, str)
    
    def __init__(self, config: RouterTestConfig, selected_modules: List[Dict], 
                 execution_mode: str = "sequential", continue_on_error: bool = True):
        super().__init__()
        self.config = config
        self.selected_modules = selected_modules
        self.execution_mode = execution_mode
        self.continue_on_error = continue_on_error
        self.is_cancelled = False
        self.test_results = []
        
    def run(self):
        """运行测试"""
        try:
            self.output_signal.emit("=" * 60)
            self.output_signal.emit("🚀 开始执行多脚本测试")
            self.output_signal.emit(f"📊 总共选择了 {len(self.selected_modules)} 个测试脚本")
            self.output_signal.emit(f"🔧 执行模式: {self.execution_mode}")
            self.output_signal.emit(f"🎯 目标路由器: {self.config.router_url}")
            self.output_signal.emit("=" * 60)
            
            if self.execution_mode == "sequential":
                self._execute_sequential()
            else:
                self._execute_parallel()
            
            if self.test_results:
                import re
                ip_match = re.search(r'://([^:/]+)', self.config.router_url)
                router_ip = ip_match.group(1) if ip_match else "未知"
                test_info = f"路由器IP: {router_ip}, 多脚本测试({len(self.test_results)}个脚本)"
                
                self.report_ready.emit(self.test_results, "测试用户", test_info)
            
            success = not self.is_cancelled and len([r for r in self.test_results if r.status == "成功"]) > 0
            self.finished_signal.emit(success, self.test_results)
                
        except Exception as e:
            error_msg = f"多脚本测试执行失败: {str(e)}\n{traceback.format_exc()}"
            self.output_signal.emit(error_msg)
            self.finished_signal.emit(False, self.test_results)
    
    def _execute_sequential(self):
        """顺序执行测试"""
        self.output_signal.emit("🔄 启动顺序执行模式...")
        
        for i, module_info in enumerate(self.selected_modules):
            if self.is_cancelled:
                self.output_signal.emit("⚠️ 测试被用户取消")
                break
            
            self.module_status_signal.emit(i, "running")
            
            progress = int((i / len(self.selected_modules)) * 100)
            self.progress_signal.emit(progress, f"执行脚本 {i+1}/{len(self.selected_modules)}: {module_info['info']['name']}")
            
            self.output_signal.emit(f"\n📦 开始执行脚本 {i+1}/{len(self.selected_modules)}: {module_info['info']['name']}")
            
            success = self._execute_single_script(module_info, i)
            
            self.module_status_signal.emit(i, "success" if success else "error")
            
            if not success and not self.continue_on_error:
                self.output_signal.emit(f"❌ 脚本 {module_info['info']['name']} 执行失败，停止后续测试")
                break
            
            if i < len(self.selected_modules) - 1 and not self.is_cancelled:
                self.output_signal.emit("⏳ 等待 2 秒后执行下一个脚本...")
                time.sleep(2)
        
        self.progress_signal.emit(100, "多脚本测试完成")
    
    def _execute_parallel(self):
        """并行执行测试"""
        self.output_signal.emit("🔄 启动并行执行模式...")
        
        import concurrent.futures
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(self.selected_modules), 4)) as executor:
            future_to_module = {}
            for i, module_info in enumerate(self.selected_modules):
                if self.is_cancelled:
                    break
                
                self.module_status_signal.emit(i, "running")
                
                future = executor.submit(self._execute_single_script, module_info, i)
                future_to_module[future] = (module_info, i)
            
            completed = 0
            for future in concurrent.futures.as_completed(future_to_module):
                module_info, index = future_to_module[future]
                completed += 1
                
                try:
                    success = future.result()
                    self.module_status_signal.emit(index, "success" if success else "error")
                except Exception as e:
                    self.output_signal.emit(f"❌ 脚本 {module_info['info']['name']} 执行异常: {str(e)}")
                    self.module_status_signal.emit(index, "error")
                
                progress = int((completed / len(self.selected_modules)) * 100)
                self.progress_signal.emit(progress, f"并行执行进度: {completed}/{len(self.selected_modules)}")
    
    def _execute_single_script(self, module_info: Dict, index: int) -> bool:
        """执行单个脚本"""
        test_result = TestResult(index + 1, module_info['info']['name'])
        test_result.start_time = datetime.datetime.now()
        test_result.status = "运行中"
        
        try:
            script_path = module_info['module_path']
            
            self.output_signal.emit(f"🔧 直接执行Python脚本...")
            self.output_signal.emit(f"📋 开始执行 {module_info['info']['name']} 脚本...")
            self.output_signal.emit("=" * 40)
            
            # 获取路由器IP
            router_ip = re.search(r'://([^:/]+)', self.config.router_url).group(1) if self.config.router_url else "10.66.0.40"
            
            # 设置环境变量传递配置
            env = os.environ.copy()
            env['ROUTER_URL'] = self.config.router_url
            env['ROUTER_IP'] = router_ip
            env['ROUTER_USERNAME'] = self.config.username
            env['ROUTER_PASSWORD'] = self.config.password
            env['SSH_USER'] = self.config.ssh_user
            env['SSH_PASS'] = self.config.ssh_pass
            
            # 解决Windows编码问题
            env['PYTHONIOENCODING'] = 'utf-8'
            env['PYTHONLEGACYWINDOWSSTDIO'] = '0'
            env['PYTHONUNBUFFERED'] = '1'
            
            # 添加调试信息
            self.output_signal.emit(f"📍 脚本路径: {script_path}")
            self.output_signal.emit(f"🌐 目标路由器URL: {env['ROUTER_URL']}")
            self.output_signal.emit(f"🔗 目标路由器IP: {env['ROUTER_IP']}")
            self.output_signal.emit(f"👤 用户名: {env['ROUTER_USERNAME']}")
            
            # 使用脚本原有的参数格式调用
            cmd = [
                sys.executable, '-u', script_path,
                '--ip', router_ip,
                '--username', self.config.username,
                '--password', self.config.password,
                '--ssh-user', self.config.ssh_user,
                '--ssh-pass', self.config.ssh_pass
            ]
            
            self.output_signal.emit(f"🚀 执行命令: {' '.join(cmd)}")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                env=env,
                cwd=os.path.dirname(script_path),
                bufsize=1,
                universal_newlines=True
            )
            
            # 实时读取输出
            output_lines = []
            self.output_signal.emit(f"🔄 开始读取脚本输出...")
            
            while True:
                if self.is_cancelled:
                    process.terminate()
                    break
                    
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                    
                if output:
                    line = output.rstrip()
                    if line:
                        self.output_signal.emit(f"[{module_info['info']['name']}] {line}")
                        output_lines.append(line)
            
            # 等待进程结束
            return_code = process.wait()
            
            test_result.full_output = '\n'.join(output_lines)
            test_result.execution_logs = output_lines.copy()
            
            self.output_signal.emit(f"🏁 脚本执行完毕，退出码: {return_code}")
            
            if return_code == 0:
                test_result.status = "成功"
                self.output_signal.emit("=" * 40)
                self.output_signal.emit(f"✅ 脚本 {module_info['info']['name']} 执行成功 (退出码: {return_code})")
            else:
                test_result.status = "失败"
                test_result.failure_logs.append(f"脚本执行失败，退出码: {return_code}")
                test_result.fail_steps += 1
                
                self.output_signal.emit("=" * 40)
                self.output_signal.emit(f"❌ 脚本 {module_info['info']['name']} 执行失败 (退出码: {return_code})")
                
        except Exception as e:
            test_result.status = "失败"
            test_result.failure_logs.append(f"脚本执行异常: {str(e)}")
            test_result.fail_steps += 1
            
            self.output_signal.emit("=" * 40)
            self.output_signal.emit(f"❌ 脚本 {module_info['info']['name']} 执行异常: {str(e)}")
            self.output_signal.emit(f"🔍 错误详情: {traceback.format_exc()}")
            
        finally:
            test_result.end_time = datetime.datetime.now()
        
        # 分析输出日志
        self._analyze_test_logs(test_result, test_result.full_output)
        self.test_results.append(test_result)
        
        return test_result.status == "成功"
    
    def _analyze_test_logs(self, test_result: TestResult, output: str):
        """分析测试日志 - 更精确的失败判断"""
        lines = output.split('\n')
        
        test_result.success_steps = 0
        test_result.fail_steps = 0
        test_result.failure_logs = []
        
        # 真正的失败关键词（排除误判）
        real_failure_keywords = [
            '测试失败', '执行失败', '连接失败', '登录失败', '创建失败', '删除失败', 
            'FAIL', 'failed', 'Exception', 'Traceback', 'Error:', '异常',
            '无法连接', '超时', 'timeout', '找不到元素', '元素不存在'
        ]
        
        # 成功关键词
        success_keywords = [
            '成功', '完成', '✅', 'SUCCESS', '已启用', '已停用', 
            '创建成功', 'passed', '测试通过', '验证成功', '连接成功',
            '删除成功', '配置成功', '保存成功'
        ]
        
        # 需要忽略的"错误"（这些不是真正的失败）
        ignore_patterns = [
            r'服务器地址/域名.*字段必填',
            r'字段必填',
            r'请输入',
            r'请选择',
            r'格式不正确',
            r'用户.*请求',
        ]
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 检查是否应该忽略的"错误"
            should_ignore = False
            for pattern in ignore_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    should_ignore = True
                    break
            
            if should_ignore:
                continue
            
            # 检查真正的失败
            is_failure = False
            for keyword in real_failure_keywords:
                if keyword.lower() in line.lower():
                    is_failure = True
                    break
            
            if is_failure:
                test_result.fail_steps += 1
                test_result.failure_logs.append(line)
            
            # 检查成功
            is_success = False
            for keyword in success_keywords:
                if keyword.lower() in line.lower():
                    is_success = True
                    break
            
            if is_success:
                test_result.success_steps += 1
        
        # 基于步骤数量和退出码判断状态
        if test_result.fail_steps > 0:
            if test_result.success_steps > test_result.fail_steps:
                test_result.status = "部分失败"
            else:
                test_result.status = "失败"
        elif test_result.success_steps > 0:
            test_result.status = "成功"
    
    def cancel(self):
        """取消测试"""
        self.is_cancelled = True

class ImprovedTestGUI(QWidget):
    """改进的测试GUI - 纯脚本执行版"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("路由器自动化测试平台 v5.4 - 最小修改版")
        self.setGeometry(100, 100, 1600, 1100)
        
        self.module_manager = ScriptModuleManager()
        self.test_config = RouterTestConfig()
        self.test_thread = None
        self.modules = []
        self.selected_modules = []
        
        self.is_testing = False
        
        self.init_ui()
        self.load_modules()
        
    def init_ui(self):
        """初始化UI"""
        main_layout = QHBoxLayout(self)
        
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        splitter.setSizes([500, 1100])
    
    def create_left_panel(self) -> QWidget:
        """创建左侧面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # 配置区域
        config_group = QGroupBox("测试配置")
        config_group.setStyleSheet("QGroupBox { font-size: 17px; font-weight: bold; }")
        config_layout = QVBoxLayout(config_group)
        
        config_btn = QPushButton("⚙️ 配置测试参数", self)
        config_btn.clicked.connect(self.open_config_dialog)
        config_btn.setStyleSheet("QPushButton { font-size: 18px; padding: 14px; }")
        config_layout.addWidget(config_btn)
        
        self.config_label = QLabel("当前配置:\n" + self._format_config())
        self.config_label.setStyleSheet("""
            QLabel {
                background-color: #f0f0f0; 
                padding: 14px; 
                border: 1px solid #ccc; 
                border-radius: 5px;
                font-size: 15px;
            }
        """)
        config_layout.addWidget(self.config_label)
        
        layout.addWidget(config_group)
        
        # 脚本选择区域
        module_group = QGroupBox("测试脚本选择 (支持多选)")
        module_group.setStyleSheet("QGroupBox { font-size: 17px; font-weight: bold; }")
        module_layout = QVBoxLayout(module_group)
        
        # 模块状态和控制按钮
        module_header_layout = QHBoxLayout()
        
        self.module_status_label = QLabel("脚本状态: 正在加载...")
        self.module_status_label.setStyleSheet("font-weight: bold; color: #333; font-size: 15px;")
        module_header_layout.addWidget(self.module_status_label)
        
        module_header_layout.addStretch()
        
        refresh_btn = QPushButton("🔄")
        refresh_btn.setToolTip("刷新脚本列表")
        refresh_btn.setMaximumWidth(45)
        refresh_btn.setStyleSheet("QPushButton { font-size: 18px; padding: 10px; }")
        refresh_btn.clicked.connect(self.load_modules)
        module_header_layout.addWidget(refresh_btn)
        
        module_layout.addLayout(module_header_layout)
        
        # 选择控制按钮
        select_control_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("✅ 全选")
        select_all_btn.setStyleSheet("QPushButton { font-size: 14px; padding: 8px; }")
        select_all_btn.clicked.connect(self.select_all_modules)
        select_control_layout.addWidget(select_all_btn)
        
        select_none_btn = QPushButton("❌ 全不选")
        select_none_btn.setStyleSheet("QPushButton { font-size: 14px; padding: 8px; }")
        select_none_btn.clicked.connect(self.select_none_modules)
        select_control_layout.addWidget(select_none_btn)
        
        select_recommended_btn = QPushButton("⭐ 推荐")
        select_recommended_btn.setStyleSheet("QPushButton { font-size: 14px; padding: 8px; }")
        select_recommended_btn.clicked.connect(self.select_recommended_modules)
        select_control_layout.addWidget(select_recommended_btn)
        
        select_control_layout.addStretch()
        
        module_layout.addLayout(select_control_layout)
        
        # 已选择数量显示
        self.selected_count_label = QLabel("已选择 0 个脚本")
        self.selected_count_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2196F3; padding: 8px;")
        module_layout.addWidget(self.selected_count_label)
        
        # 脚本列表
        self.module_list = QListWidget()
        self.module_list.setSelectionMode(QListWidget.MultiSelection)
        self.module_list.setStyleSheet("""
            QListWidget {
                font-size: 14px;
                border: 2px solid #ccc;
                border-radius: 5px;
                background-color: white;
            }
            QListWidget::item {
                padding: 12px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background-color: #2196F3;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #f0f0f0;
            }
        """)
        self.module_list.itemSelectionChanged.connect(self.on_module_selection_changed)
        module_layout.addWidget(self.module_list)
        
        layout.addWidget(module_group)
        
        # 执行模式选择
        mode_group = QGroupBox("执行模式")
        mode_group.setStyleSheet("QGroupBox { font-size: 17px; font-weight: bold; }")
        mode_layout = QVBoxLayout(mode_group)
        
        self.execution_mode_group = QButtonGroup()
        
        self.sequential_radio = QRadioButton("🔄 顺序执行 (推荐)")
        self.sequential_radio.setChecked(True)
        self.sequential_radio.setStyleSheet("font-size: 15px; font-weight: bold;")
        self.execution_mode_group.addButton(self.sequential_radio, 0)
        mode_layout.addWidget(self.sequential_radio)
        
        sequential_desc = QLabel("按顺序逐个执行测试脚本，可靠性高")
        sequential_desc.setStyleSheet("color: #666; font-size: 13px; margin-left: 20px;")
        mode_layout.addWidget(sequential_desc)
        
        self.parallel_radio = QRadioButton("⚡ 并行执行 (快速)")
        self.parallel_radio.setStyleSheet("font-size: 15px;")
        self.execution_mode_group.addButton(self.parallel_radio, 1)
        mode_layout.addWidget(self.parallel_radio)
        
        parallel_desc = QLabel("同时执行多个测试脚本，速度快但资源占用高")
        parallel_desc.setStyleSheet("color: #666; font-size: 13px; margin-left: 20px;")
        mode_layout.addWidget(parallel_desc)
        
        layout.addWidget(mode_group)
        
        # 执行控制区域
        control_group = QGroupBox("执行控制")
        control_group.setStyleSheet("QGroupBox { font-size: 17px; font-weight: bold; }")
        control_layout = QVBoxLayout(control_group)
        
        options_layout = QVBoxLayout()
        
        self.continue_on_error_checkbox = QCheckBox("⚠️ 出错后继续执行")
        self.continue_on_error_checkbox.setChecked(True)
        self.continue_on_error_checkbox.setStyleSheet("font-size: 15px;")
        options_layout.addWidget(self.continue_on_error_checkbox)
        
        control_layout.addLayout(options_layout)
        
        # 执行按钮
        button_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("🚀 开始测试")
        self.start_btn.clicked.connect(self.start_test)
        self.start_btn.setStyleSheet("QPushButton { font-size: 20px; padding: 16px; background-color: #4CAF50; color: white; font-weight: bold; }")
        button_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹️ 停止测试")
        self.stop_btn.clicked.connect(self.stop_test)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("QPushButton { font-size: 20px; padding: 16px; background-color: #f44336; color: white; font-weight: bold; }")
        button_layout.addWidget(self.stop_btn)
        
        control_layout.addLayout(button_layout)
        
        # 进度显示
        self.progress_label = QLabel("就绪")
        self.progress_label.setStyleSheet("font-weight: bold; color: #333; font-size: 17px; padding: 10px;")
        control_layout.addWidget(self.progress_label)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("QProgressBar { font-size: 15px; }")
        control_layout.addWidget(self.progress_bar)
        
        layout.addWidget(control_group)
        
        layout.addStretch()
        
        return panel
    
    def create_right_panel(self) -> QWidget:
        """创建右侧面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        tab_widget = QTabWidget()
        tab_widget.setStyleSheet("QTabWidget::pane { font-size: 18px; }")
        
        # 测试输出标签页
        output_tab = QWidget()
        output_layout = QVBoxLayout(output_tab)
        
        output_title = QLabel("实时测试输出:")
        output_title.setStyleSheet("font-size: 20px; font-weight: bold;")
        output_layout.addWidget(output_title)
        
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont("Consolas", 18))
        self.output_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 2px solid #ccc;
                font-size: 18px;
                line-height: 1.8;
                padding: 12px;
            }
        """)
        output_layout.addWidget(self.output_text)
        
        # 输出控制按钮
        output_control_layout = QHBoxLayout()
        
        clear_btn = QPushButton("🗑️ 清空输出")
        clear_btn.setStyleSheet("QPushButton { font-size: 16px; padding: 10px; }")
        clear_btn.clicked.connect(self.output_text.clear)
        output_control_layout.addWidget(clear_btn)
        
        self.auto_scroll_checkbox = QCheckBox("自动滚动")
        self.auto_scroll_checkbox.setChecked(True)
        self.auto_scroll_checkbox.setStyleSheet("font-size: 15px;")
        output_control_layout.addWidget(self.auto_scroll_checkbox)
        
        output_control_layout.addStretch()
        
        output_layout.addLayout(output_control_layout)
        
        tab_widget.addTab(output_tab, "测试输出")
        
        # 测试报告标签页
        report_tab = QWidget()
        report_layout = QVBoxLayout(report_tab)
        
        report_title = QLabel("测试报告:")
        report_title.setStyleSheet("font-size: 20px; font-weight: bold;")
        report_layout.addWidget(report_title)
        
        self.report_list = QListWidget()
        self.report_list.setStyleSheet("QListWidget { font-size: 15px; }")
        self.report_list.itemDoubleClicked.connect(self.open_selected_report)
        report_layout.addWidget(self.report_list)
        
        # 报告操作按钮
        report_btn_layout = QHBoxLayout()
        
        refresh_report_btn = QPushButton("🔄 刷新报告列表")
        refresh_report_btn.setStyleSheet("QPushButton { font-size: 16px; padding: 10px; }")
        refresh_report_btn.clicked.connect(self.refresh_reports)
        report_btn_layout.addWidget(refresh_report_btn)
        
        open_report_btn = QPushButton("📖 打开选中报告")
        open_report_btn.setStyleSheet("QPushButton { font-size: 16px; padding: 10px; }")
        open_report_btn.clicked.connect(self.open_selected_report)
        report_btn_layout.addWidget(open_report_btn)
        
        open_folder_btn = QPushButton("📁 打开报告文件夹")
        open_folder_btn.setStyleSheet("QPushButton { font-size: 16px; padding: 10px; }")
        open_folder_btn.clicked.connect(self.open_report_folder)
        report_btn_layout.addWidget(open_folder_btn)
        
        report_btn_layout.addStretch()
        
        report_layout.addLayout(report_btn_layout)
        
        tab_widget.addTab(report_tab, "测试报告")
        
        layout.addWidget(tab_widget)
        
        return panel
    
    def _format_config(self) -> str:
        """格式化配置显示"""
        import re
        ip_match = re.search(r'://([^:/]+)', self.test_config.router_url)
        router_ip = ip_match.group(1) if ip_match else "未知"
        
        return f"""路由器IP: {router_ip}
用户名: {self.test_config.username}
SSH用户: {self.test_config.ssh_user}"""
    
    def open_config_dialog(self):
        """打开配置对话框"""
        dialog = TestConfigDialog(self, self.test_config)
        if dialog.exec_() == QDialog.Accepted:
            self.test_config = dialog.get_config()
            self.config_label.setText("当前配置:\n" + self._format_config())
            
            import re
            ip_match = re.search(r'://([^:/]+)', self.test_config.router_url)
            router_ip = ip_match.group(1) if ip_match else "未知"
            self.output_text.append(f"✅ 配置已更新，目标路由器: {router_ip}")
    
    def load_modules(self):
        """加载测试脚本"""
        try:
            self.output_text.append("正在扫描测试脚本...")
            self.module_status_label.setText("脚本状态: 正在扫描...")
            
            self.module_list.clear()
            
            self.modules = self.module_manager.scan_modules()
            
            if len(self.modules) > 0:
                for i, module in enumerate(self.modules):
                    module_info = module['info']
                    
                    item_text = f"{module_info['name']}\n📁 {module['file_name']} | 📝 {module_info.get('description', '无描述')}"
                    item = QListWidgetItem(item_text)
                    item.setData(Qt.UserRole, i)
                    
                    is_recommended = module_info['name'] in ['PPTP客户端', 'L2TP客户端', 'VLAN设置']
                    if is_recommended:
                        item.setToolTip("⭐ 推荐测试脚本")
                    
                    self.module_list.addItem(item)
                
                self.module_status_label.setText(f"已找到 {len(self.modules)} 个脚本")
                self.output_text.append(f"✅ 发现 {len(self.modules)} 个测试脚本:")
                
                for i, module in enumerate(self.modules):
                    self.output_text.append(f"  {i+1}. {module['info']['name']} - {module['file_name']}")
                
                self.start_btn.setEnabled(True)
                self.module_list.setEnabled(True)
                
                self.select_recommended_modules()
                    
            else:
                self.module_status_label.setText("未找到任何脚本")
                self.output_text.append("❌ 未找到任何测试脚本")
                self.output_text.append("💡 请检查modules目录下是否有*_module.py文件")
                
                self.start_btn.setEnabled(False)
                self.module_list.setEnabled(False)
            
        except Exception as e:
            error_msg = f"加载测试脚本失败: {str(e)}"
            self.output_text.append(error_msg)
            self.module_status_label.setText("脚本状态: 加载失败")
    
    def select_all_modules(self):
        """全选所有脚本"""
        for i in range(self.module_list.count()):
            item = self.module_list.item(i)
            item.setSelected(True)
        self.on_module_selection_changed()
    
    def select_none_modules(self):
        """全不选"""
        self.module_list.clearSelection()
        self.on_module_selection_changed()
    
    def select_recommended_modules(self):
        """选择推荐脚本"""
        self.module_list.clearSelection()
        
        recommended_names = ['PPTP客户端', 'L2TP客户端', 'VLAN设置']
        
        for i in range(self.module_list.count()):
            item = self.module_list.item(i)
            module_index = item.data(Qt.UserRole)
            if module_index < len(self.modules):
                module_name = self.modules[module_index]['info']['name']
                if any(rec in module_name for rec in recommended_names):
                    item.setSelected(True)
        
        self.on_module_selection_changed()
    
    def on_module_selection_changed(self):
        """脚本选择改变"""
        selected_items = self.module_list.selectedItems()
        self.selected_modules = []
        
        for item in selected_items:
            module_index = item.data(Qt.UserRole)
            if module_index < len(self.modules):
                self.selected_modules.append(self.modules[module_index])
        
        count = len(self.selected_modules)
        self.selected_count_label.setText(f"已选择 {count} 个脚本")
        
        self.start_btn.setEnabled(count > 0 and not self.is_testing)
        
        if count > 0:
            module_names = [m['info']['name'] for m in self.selected_modules]
            self.output_text.append(f"📦 已选择 {count} 个测试脚本: {', '.join(module_names)}")
    
    def start_test(self):
        """开始测试"""
        if self.is_testing:
            return
        
        if not self.selected_modules:
            QMessageBox.warning(self, "无法开始测试", "请至少选择一个测试脚本")
            return
        
        self.output_text.clear()
        
        import re
        ip_match = re.search(r'://([^:/]+)', self.test_config.router_url)
        router_ip = ip_match.group(1) if ip_match else "未知"
        
        execution_mode = "sequential" if self.sequential_radio.isChecked() else "parallel"
        
        self.test_thread = ScriptExecutionThread(
            self.test_config,
            self.selected_modules,
            execution_mode,
            self.continue_on_error_checkbox.isChecked()
        )
        
        self.test_thread.output_signal.connect(self.append_output)
        self.test_thread.finished_signal.connect(self.on_test_finished)
        self.test_thread.progress_signal.connect(self.update_progress)
        self.test_thread.module_status_signal.connect(self.update_module_status)
        self.test_thread.report_ready.connect(self.on_report_ready)
        
        self.is_testing = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        for i in range(len(self.selected_modules)):
            self.update_module_status(i, "pending")
        
        self.test_thread.start()
        
        mode_name = "顺序执行" if execution_mode == "sequential" else "并行执行"
        
        self.output_text.append(f"🚀 开始执行多脚本测试 (最小修改版)")
        self.output_text.append(f"🎯 目标路由器: {router_ip}")
        self.output_text.append(f"📊 选择脚本数: {len(self.selected_modules)}")
        self.output_text.append(f"🔧 执行模式: {mode_name}")
        self.output_text.append(f"⚙️ 测试设置: {'出错继续' if self.continue_on_error_checkbox.isChecked() else '出错停止'}")
        self.output_text.append(f"⏰ 开始时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.output_text.append("=" * 60)
    
    def update_module_status(self, module_index: int, status: str):
        """更新脚本状态显示"""
        if module_index < len(self.selected_modules):
            for i in range(self.module_list.count()):
                item = self.module_list.item(i)
                item_module_index = item.data(Qt.UserRole)
                
                for j, selected_module in enumerate(self.selected_modules):
                    if item_module_index < len(self.modules) and self.modules[item_module_index] == selected_module and j == module_index:
                        module_info = selected_module['info']
                        status_emoji = {
                            "pending": "⏳",
                            "running": "🔄",
                            "success": "✅", 
                            "error": "❌"
                        }.get(status, "⏳")
                        
                        item_text = f"{status_emoji} {module_info['name']}\n📁 {selected_module['file_name']} | 📝 {module_info.get('description', '无描述')}"
                        item.setText(item_text)
                        break
    
    def stop_test(self):
        """停止测试"""
        if self.test_thread and self.test_thread.isRunning():
            self.output_text.append("⚠️ 用户请求停止测试...")
            self.test_thread.cancel()
            self.test_thread.wait(5000)
            if self.test_thread.isRunning():
                self.test_thread.terminate()
                self.test_thread.wait()
        
        self.on_test_finished(False, [])
    
    def on_test_finished(self, success: bool, test_results):
        """测试完成"""
        self.is_testing = False
        self.start_btn.setEnabled(len(self.selected_modules) > 0)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        
        end_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if test_results:
            success_count = len([r for r in test_results if r.status == "成功"])
            fail_count = len([r for r in test_results if r.status in ["失败", "部分失败"]])
            total_count = len(test_results)
            
            self.output_text.append("=" * 60)
            self.output_text.append(f"🎉 多脚本测试执行完成！")
            self.output_text.append(f"📊 测试统计:")
            self.output_text.append(f"   总脚本数: {total_count}")
            self.output_text.append(f"   成功: {success_count}")
            self.output_text.append(f"   失败: {fail_count}")
            self.output_text.append(f"   成功率: {(success_count/total_count*100):.1f}%")
            self.output_text.append(f"⏰ 结束时间: {end_time}")
            
            if success_count > 0:
                self.progress_label.setText(f"✅ 测试完成 ({success_count}/{total_count} 成功)")
            else:
                self.progress_label.setText("❌ 测试失败")
        else:
            self.progress_label.setText("❌ 测试失败或被取消")
            self.output_text.append("=" * 60)
            self.output_text.append(f"💥 测试失败或被取消")
            self.output_text.append(f"⏰ 结束时间: {end_time}")
        
        QTimer.singleShot(1000, self.refresh_reports)
    
    def update_progress(self, value: int, description: str):
        """更新进度"""
        self.progress_label.setText(f"⏳ {description} ({value}%)")
        self.progress_bar.setValue(value)
    
    def append_output(self, text: str):
        """添加输出"""
        self.output_text.append(text)
        
        if self.auto_scroll_checkbox.isChecked():
            cursor = self.output_text.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.output_text.setTextCursor(cursor)
    
    def on_report_ready(self, test_results, tester_name: str, test_info: str):
        """处理测试报告就绪信号"""
        try:
            report_file = self.generate_html_report(test_results, tester_name, test_info)
            
            if report_file:
                self.output_text.append(f"📄 测试报告已生成: {os.path.basename(report_file)}")
                
                self.refresh_reports()
                
                reply = QMessageBox.question(
                    self, 
                    "测试报告", 
                    f"多脚本测试报告已生成完成！\n\n文件位置: {report_file}\n\n是否现在打开报告？",
                    QMessageBox.Yes | QMessageBox.No, 
                    QMessageBox.Yes
                )
                
                if reply == QMessageBox.Yes:
                    self.open_report_file(report_file)
                    
        except Exception as e:
            error_msg = f"生成测试报告时出错: {str(e)}\n{traceback.format_exc()}"
            self.output_text.append(error_msg)
            QMessageBox.critical(self, "错误", f"生成测试报告时出错: {str(e)}")
    
    def generate_html_report(self, test_results, tester_name: str, test_info: str) -> str:
        """生成HTML测试报告"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(os.getcwd(), f"test_report_{timestamp}.html")
        
        total_count = len(test_results)
        success_count = sum(1 for r in test_results if r.status == "成功")
        fail_count = sum(1 for r in test_results if r.status in ["失败", "部分失败"])
        
        summary_html = f"""
        <h2>多脚本测试结果汇总</h2>
        <table border='1' cellpadding='10' cellspacing='0' style='border-collapse: collapse; width: 100%; font-size: 16px;'>
          <tr><td style='background-color: #f2f2f2; font-weight: bold; width: 25%;'>测试人员</td><td>{tester_name}</td></tr>
          <tr><td style='background-color: #f2f2f2; font-weight: bold;'>测试信息</td><td>{test_info}</td></tr>
          <tr><td style='background-color: #f2f2f2; font-weight: bold;'>脚本总数</td><td>{total_count}</td></tr>
          <tr style='background-color: #d4edda;'><td style='background-color: #f2f2f2; font-weight: bold;'>成功脚本</td><td style='color: green; font-weight: bold; font-size: 18px;'>{success_count}</td></tr>
          <tr style='background-color: #f8d7da;'><td style='background-color: #f2f2f2; font-weight: bold;'>失败脚本</td><td style='color: red; font-weight: bold; font-size: 18px;'>{fail_count}</td></tr>
          <tr><td style='background-color: #f2f2f2; font-weight: bold;'>成功率</td><td style='font-weight: bold; font-size: 18px;'>{(success_count/total_count*100):.1f}%</td></tr>
        </table>
        """
        
        detail_html = """
        <h3>详细脚本执行信息</h3>
        <table border='1' cellpadding='10' cellspacing='0' style='border-collapse: collapse; width: 100%; font-size: 15px;'>
          <tr style='background-color: #f8f9fa;'>
            <th style='font-size: 16px;'>编号</th>
            <th style='font-size: 16px;'>测试脚本</th>
            <th style='font-size: 16px;'>开始时间</th>
            <th style='font-size: 16px;'>结束时间</th>
            <th style='font-size: 16px;'>执行时长(s)</th>
            <th style='font-size: 16px;'>执行结果</th>
            <th style='font-size: 16px;'>成功步骤</th>
            <th style='font-size: 16px;'>失败步骤</th>
            <th style='font-size: 16px;'>完整执行日志</th>
          </tr>
        """
        
        for i, result in enumerate(test_results):
            status_color = "#28a745" if result.status == "成功" else "#dc3545"
            
            execution_details_html = (
                f"<details><summary style='cursor: pointer; color: blue; font-size: 14px; font-weight: bold;'>"
                f"点击查看完整执行日志</summary>"
                f"<div style='max-height: 600px; overflow-y: auto; background-color: #f8f9fa; padding: 15px; border-radius: 4px; border: 1px solid #ddd; margin: 10px 0;'>"
                f"<pre style='white-space: pre-wrap; font-size: 13px; font-family: Consolas, monospace; margin: 0; line-height: 1.4;'>"
                + result.full_output
                + "</pre></div></details>"
            )
            
            detail_html += f"""
            <tr style='border-bottom: 1px solid #dee2e6;'>
              <td style='text-align: center; font-weight: bold;'>{i+1}</td>
              <td style='font-weight: bold;'>{result.test_name}</td>
              <td>{result.start_time.strftime("%Y-%m-%d %H:%M:%S") if result.start_time else "未知"}</td>
              <td>{result.end_time.strftime("%Y-%m-%d %H:%M:%S") if result.end_time else "未知"}</td>
              <td style='text-align: center; font-weight: bold;'>{result.get_duration_seconds():.1f}</td>
              <td style='color: {status_color}; font-weight: bold; text-align: center; font-size: 16px;'>{result.status}</td>
              <td style='text-align: center; color: green; font-weight: bold;'>{result.success_steps}</td>
              <td style='text-align: center; color: red; font-weight: bold;'>{result.fail_steps}</td>
              <td>{execution_details_html}</td>
            </tr>
            """
        
        detail_html += "</table>"
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
          <meta charset="utf-8"/>
          <title>多脚本自动化测试报告 - {test_info}</title>
          <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
                line-height: 1.6;
                max-width: 95%;
                margin: 0 auto;
                padding: 20px;
                background-color: #ffffff;
                color: #333333;
                font-size: 16px;
            }}
            h1 {{
                color: #2c3e50;
                text-align: center;
                border-bottom: 3px solid #3498db;
                padding-bottom: 10px;
                margin-bottom: 30px;
                font-size: 28px;
            }}
            h2, h3 {{
                color: #34495e;
                border-bottom: 2px solid #ecf0f1;
                padding-bottom: 8px;
                margin-top: 30px;
                font-size: 22px;
            }}
            table {{
                border-collapse: collapse;
                width: 100%;
                margin-bottom: 25px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            th, td {{
                padding: 15px;
                text-align: left;
                border: 1px solid #ddd;
                font-size: 15px;
                word-wrap: break-word;
                max-width: 300px;
            }}
            th {{
                background-color: #f8f9fa;
                font-weight: bold;
                color: #495057;
            }}
            tr:nth-child(even) {{
                background-color: #f8f9fa;
            }}
            details {{
                margin: 8px 0;
            }}
            summary {{
                cursor: pointer;
                padding: 10px;
                background-color: #e9ecef;
                border-radius: 4px;
                outline: none;
                font-weight: bold;
            }}
            pre {{
                background-color: #f8f9fa;
                padding: 15px;
                border-radius: 6px;
                overflow-x: auto;
                border: 1px solid #e9ecef;
                font-family: monospace;
                font-size: 13px;
                margin: 10px 0;
                line-height: 1.4;
                white-space: pre-wrap;
            }}
          </style>
        </head>
        <body>
          <h1>🔬 多脚本自动化测试报告 (v5.4 最小修改版)</h1>
          
          <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 30px;">
            <p><strong>📊 报告生成时间:</strong> {datetime.datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")}</p>
            <p><strong>🎯 测试范围:</strong> 路由器多脚本自动化功能测试</p>
            <p><strong>⚡ 特性:</strong> 使用脚本原有参数格式，最小化修改</p>
          </div>
          
          {summary_html}
          
          <hr style="border: none; border-top: 2px solid #ecf0f1; margin: 40px 0;">
          
          {detail_html}
          
          <footer style="margin-top: 50px; text-align: center; color: #6c757d; font-size: 15px;">
            <p>🚀 平台版本: v5.4 最小修改版 | 📦 支持多脚本批量测试</p>
          </footer>
        </body>
        </html>
        """
        
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        return report_file
    
    def refresh_reports(self):
        """刷新报告列表"""
        try:
            self.report_list.clear()
            
            current_dir = os.getcwd()
            report_files = []
            
            for file in os.listdir(current_dir):
                if file.startswith("test_report") and file.endswith(".html"):
                    file_path = os.path.join(current_dir, file)
                    file_time = os.path.getmtime(file_path)
                    file_size = os.path.getsize(file_path)
                    report_files.append((file, file_time, file_size))
            
            report_files.sort(key=lambda x: x[1], reverse=True)
            
            for file_name, file_time, file_size in report_files:
                time_str = datetime.datetime.fromtimestamp(file_time).strftime('%Y-%m-%d %H:%M:%S')
                size_str = f"{file_size / 1024:.1f} KB"
                display_name = f"{file_name} ({time_str}, {size_str})"
                
                item = QListWidgetItem(display_name)
                item.setData(Qt.UserRole, file_name)
                self.report_list.addItem(item)
                
        except Exception as e:
            print(f"刷新报告列表失败: {e}")
    
    def open_selected_report(self):
        """打开选中的报告"""
        current_item = self.report_list.currentItem()
        if not current_item:
            QMessageBox.information(self, "提示", "请先选择一个报告文件")
            return
        
        file_name = current_item.data(Qt.UserRole)
        if not file_name:
            display_text = current_item.text()
            file_name = display_text.split(" (")[0]
        
        report_path = os.path.join(os.getcwd(), file_name)
        self.open_report_file(report_path)
    
    def open_report_file(self, report_path: str):
        """打开指定的报告文件"""
        if os.path.exists(report_path):
            try:
                if sys.platform == "win32":
                    os.startfile(report_path)
                elif sys.platform == "darwin":
                    subprocess.run(["open", report_path])
                else:
                    subprocess.run(["xdg-open", report_path])
                
                self.output_text.append(f"📖 已打开测试报告: {os.path.basename(report_path)}")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"打开报告失败: {str(e)}")
        else:
            QMessageBox.warning(self, "错误", f"报告文件不存在: {report_path}")
    
    def open_report_folder(self):
        """打开报告文件夹"""
        folder_path = os.getcwd()
        try:
            if sys.platform == "win32":
                os.startfile(folder_path)
            elif sys.platform == "darwin":
                subprocess.run(["open", folder_path])
            else:
                subprocess.run(["xdg-open", folder_path])
            
            self.output_text.append(f"📁 已打开报告文件夹: {folder_path}")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"打开文件夹失败: {str(e)}")

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("路由器自动化测试平台")
    
    window = ImprovedTestGUI()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()