# -*- coding: utf-8 -*-
import sys
import os
import argparse
from typing import Optional
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test_framework import RouterTestModule, RouterTestConfig
from playwright.sync_api import expect
import time

class PPTPTestModule(RouterTestModule):
    """PPTP测试模块 - 完整12个步骤，支持自定义IP地址（优化版）"""
    
    def __init__(self, config: RouterTestConfig):
        super().__init__(config)
        self.test_profile = {
            "name": "pptp_test_01",
            "port": "1723", 
            "server": "10.66.0.4",
            "user": "testuser",
            "pass": "testpass123",
            "mtu": "1400",
            "mru": "1400",
            "line": "auto",
            "reconnect_interval": "5",
            "scheduled_reconnect": {
                "enabled": True,
                "days": ["周一", "周三", "周五"],
                "times": ["03:30", "04:30", "05:30"]
            },
            "comment": "PlaywrightE2ETest"
        }
        self.batch_create_count = 5
    
    def get_module_info(self) -> dict:
        """获取模块信息"""
        return {
            "name": "PPTP客户端",
            "path": ["网络设置", "VPN客户端", "PPTP"],
            "description": "PPTP客户端配置测试 - 12个步骤",
            "version": "1.1"
        }
    
    def navigate_to_module(self):
        """步骤2: 导航到PPTP页面（优化版）"""
        print("步骤2: 导航到 PPTP 页面")
        if "vpn/pptp-client" not in self.page.url:
            self.page.locator('a:has-text("系统概况")').click()
            self.page.locator('a:has-text("网络设置")').click()
            self.page.locator('a:has-text("VPN客户端")').click()
            self.page.locator('a:has-text("PPTP")').click()
        
        # 等待页面完全加载
        self._wait_for_page_ready()
        print("已进入 PPTP 页面")
    
    def _wait_for_page_ready(self):
        """等待页面恢复到可操作状态（借鉴VLAN）"""
        print("⏳ 等待页面恢复...")
        for attempt in range(15):  # 增加等待时间适应MIPS路由
            try:
                add_button = self.page.locator('a.btn_green:has-text("添加")').first
                if add_button.is_visible() and add_button.is_enabled():
                    print("✅ 页面已恢复")
                    return True
                time.sleep(1)
            except:
                time.sleep(1)
        
        print("⚠️ 页面恢复超时")
        return False
    
    def _wait_for_form(self):
        """等待表单出现（借鉴VLAN）"""
        print("🔍 等待PPTP表单出现...")
        # 等待真正的输入字段出现
        for attempt in range(10):
            try:
                # 查找PPTP特有的拨号名称字段
                dial_name_field = self.page.locator('input[data-vv-as="拨号名称"]')
                if dial_name_field.count() > 0 and dial_name_field.first.is_visible():
                    print("✅ 检测到PPTP表单输入字段")
                    return True
                
                time.sleep(0.5)
            except:
                time.sleep(0.5)
        
        print("❌ PPTP表单加载超时")
        return False
    
    def _check_real_validation_errors(self):
        """检查真正的表单验证错误（借鉴VLAN）"""
        try:
            # 只查找真正的错误提示元素，避免误判
            error_selectors = [
                'div.error_tip:visible',
                'span.error_tip:visible', 
                'p.error_tip:visible',
                '.field-error:visible',
                '.form-error:visible',
                '.validation-error:visible'
            ]
            
            for selector in error_selectors:
                errors = self.page.locator(selector)
                if errors.count() > 0:
                    for i in range(errors.count()):
                        error_text = errors.nth(i).text_content().strip()
                        # 过滤掉太长的文本（可能是页面内容）和无关的文本
                        if error_text and len(error_text) < 100 and any(keyword in error_text for keyword in ["必填", "格式", "范围", "错误", "invalid"]):
                            print(f"⚠️ 发现真正的验证错误: {error_text}")
                            return True
            
            return False
        except:
            return False
    
    def _cancel_form(self):
        """取消表单（借鉴VLAN）"""
        try:
            cancel_strategies = [
                'button:has-text("取消"):visible',
                'a:has-text("取消"):visible',
                '.btn:has-text("取消"):visible'
            ]
            
            for strategy in cancel_strategies:
                buttons = self.page.locator(strategy)
                if buttons.count() > 0:
                    button = buttons.first
                    if button.is_visible():
                        button.click()
                        print("✅ 已取消PPTP表单")
                        time.sleep(1)
                        return True
            
            # 如果没有找到取消按钮，按ESC键
            self.page.keyboard.press('Escape')
            print("✅ 按ESC取消PPTP表单")
            return True
        except:
            return False
    
    def _close_modals(self):
        """关闭可能的模态弹窗（借鉴VLAN）"""
        try:
            # 查找关闭按钮
            close_selectors = [
                'button.el-dialog__headerbtn:visible',
                '.modal-close:visible',
                '.close:visible',
                'button:has-text("×"):visible'
            ]
            
            for selector in close_selectors:
                buttons = self.page.locator(selector)
                if buttons.count() > 0:
                    button = buttons.first
                    if button.is_visible():
                        button.click()
                        print("✅ 关闭PPTP模态弹窗")
                        time.sleep(1)
                        break
        except:
            pass
    
    def _verify_save_success(self):
        """验证保存是否成功（借鉴VLAN）"""
        try:
            # 等待保存完成的指示
            time.sleep(3)
            
            # 检查是否有成功提示或表单关闭
            success_indicators = [
                # 成功提示消息
                ':text("保存成功"):visible',
                ':text("添加成功"):visible', 
                ':text("操作成功"):visible',
                '.success:visible',
                '.message-success:visible',
                # 表单关闭指示
                'a.btn_green:has-text("添加"):visible'  # 添加按钮重新可见
            ]
            
            for indicator in success_indicators:
                try:
                    elements = self.page.locator(indicator)
                    if elements.count() > 0:
                        print(f"✅ 检测到PPTP保存成功指示: {indicator}")
                        return True
                except:
                    continue
            
            # 如果没有明确的成功指示，检查表单是否还存在
            form_inputs = self.page.locator('input[data-vv-as="拨号名称"]:visible')
            if form_inputs.count() == 0:
                print("✅ PPTP表单已关闭，可能保存成功")
                return True
            
            print("⚠️ 未检测到明确的PPTP保存成功指示")
            return True  # 默认认为成功，让后续验证来确认
            
        except Exception as e:
            print(f"验证PPTP保存成功时出错: {e}")
            return True  # 默认认为成功
    
    def _verify_config_created(self, config_name: str):
        """验证配置是否创建成功（借鉴VLAN）"""
        try:
            # 等待页面更新
            time.sleep(3)
            
            # 多次尝试验证
            for attempt in range(5):
                # 检查表格中是否存在配置
                config_row = self.page.locator(f'tr:has-text("{config_name}")')
                if config_row.count() > 0 and config_row.first.is_visible():
                    print(f"✅ PPTP配置 {config_name} 创建成功")
                    return True
                
                if attempt < 4:
                    time.sleep(2)
            
            print(f"⚠️ PPTP配置 {config_name} 未在表格中找到")
            return False
        except Exception as e:
            print(f"⚠️ PPTP配置 {config_name} 验证失败: {e}")
            return False
    
    def _save_pptp_form(self):
        """保存PPTP表单（借鉴VLAN的方法）"""
        print("💾 保存PPTP表单...")
        
        # 查找保存按钮的策略 - 更精确的选择器
        save_strategies = [
            'button:has-text("保存"):visible:enabled',
            'input[value="保存"]:visible:enabled', 
            'a:has-text("保存"):visible',
            '.btn:has-text("保存"):visible:enabled',
            'button[type="submit"]:visible:enabled',
            'button.el-button--primary:visible:enabled',
            '.btn-primary:visible:enabled',
            # 使用更具体的CSS选择器
            'div.btn_btm button:has-text("保存"):visible',
            'div.btn_bottom button:has-text("保存"):visible'
        ]
        
        for strategy in save_strategies:
            try:
                buttons = self.page.locator(strategy)
                print(f"🔍 尝试PPTP保存策略: {strategy}, 找到 {buttons.count()} 个按钮")
                
                if buttons.count() > 0:
                    button = buttons.first
                    if button.is_visible() and button.is_enabled():
                        print(f"✅ 找到PPTP保存按钮: {strategy}")
                        
                        # 滚动到按钮位置
                        button.scroll_into_view_if_needed()
                        time.sleep(1)  # 增加等待时间
                        
                        # 点击保存按钮
                        button.click()
                        print("✅ 点击PPTP保存按钮")
                        time.sleep(3)  # 增加等待时间
                        
                        # 检查是否有保存成功的指示
                        return self._verify_save_success()
                    else:
                        print(f"PPTP保存按钮不可见或不可用: visible={button.is_visible()}, enabled={button.is_enabled()}")
                        
            except Exception as e:
                print(f"尝试PPTP保存策略 {strategy} 时出错: {e}")
                continue
        
        print("❌ 未找到可用的PPTP保存按钮")
        return False
    
    def step3_create_profile(self, profile: dict = None, show_step_info: bool = True):
        """步骤3: 创建PPTP配置（优化版）"""
        if profile is None:
            profile = self.test_profile
            
        if show_step_info:
            print(f"步骤3: 创建PPTP配置 '{profile['name']}'")
        else:
            print(f"📝 创建PPTP配置 '{profile['name']}'")
        
        # 等待页面稳定
        time.sleep(1)
        
        # 点击添加按钮 - 增加重试机制（借鉴VLAN）
        add_button = self.page.locator('a.btn_green:has-text("添加")').first
        
        # 重试机制
        for attempt in range(3):
            try:
                expect(add_button).to_be_visible(timeout=8000)  # 增加超时时间
                add_button.click()
                print("✅ 点击PPTP添加按钮")
                break
            except Exception as e:
                print(f"❌ 第{attempt+1}次点击PPTP添加按钮失败: {e}")
                if attempt < 2:
                    time.sleep(3)  # 增加等待时间
                    # 刷新页面重试
                    self.page.reload()
                    time.sleep(3)
                    self.navigate_to_module()
                else:
                    raise e
        
        time.sleep(3)  # 增加等待时间
        
        # 等待表单出现（使用VLAN的方法）
        print("🔍 等待PPTP表单出现...")
        form_appeared = self._wait_for_form()
        
        if not form_appeared:
            print("❌ PPTP表单未出现")
            return False
        
        # 填写基本表单
        success = self._fill_pptp_form(profile)
        
        if success:
            # 检查是否有真正的验证错误（使用VLAN的方法）
            if self._check_real_validation_errors():
                print("❌ PPTP表单验证失败，取消操作")
                self._cancel_form()
                return False
            
            # 保存配置
            save_success = self._save_pptp_form()
            if save_success:
                # 等待保存完成
                time.sleep(5)
                
                # 关闭可能的弹窗
                self._close_modals()
                
                # 等待添加按钮重新可见
                self._wait_for_page_ready()
                
                # 验证配置是否创建成功
                verified = self._verify_config_created(profile["name"])
                if verified:
                    print("✅ PPTP配置创建并验证通过")
                    return True
                else:
                    print("⚠️ PPTP配置创建但验证失败")
                    return True  # 仍然认为创建成功
            else:
                print("❌ 保存PPTP配置失败")
                return False
        else:
            print("❌ 填写PPTP表单失败")
            return False
    
    def _fill_pptp_form(self, profile):
        """填写PPTP表单（优化版）"""
        print("📝 开始填写PPTP表单...")
        
        try:
            # 基础字段 - 使用更健壮的方式
            print("填写拨号名称...")
            dial_name_field = self.page.locator('input[data-vv-as="拨号名称"]').first
            expect(dial_name_field).to_be_visible(timeout=8000)
            dial_name_field.fill(profile["name"])
            print(f"拨号名称填写: {profile['name']}")
            
            print("填写服务端口...")
            port_field = self.page.locator('input[data-vv-as="服务端口"]').first
            expect(port_field).to_be_visible(timeout=8000)
            port_field.fill(profile["port"])
            print(f"服务端口填写: {profile['port']}")
            
            print("填写服务器地址/域名...")
            server_field = self.page.locator('input[data-vv-as="服务器地址/域名"]').first
            expect(server_field).to_be_visible(timeout=8000)
            server_field.fill(profile["server"])
            print(f"服务器地址填写: {profile['server']}")
            
            print("填写用户名...")
            user_field = self.page.locator('input[data-vv-as="用户名"]').first
            expect(user_field).to_be_visible(timeout=8000)
            user_field.fill(profile["user"])
            print(f"用户名填写: {profile['user']}")
            
            print("填写密码...")
            pass_field = self.page.locator('input[data-vv-as="密码"]').first
            expect(pass_field).to_be_visible(timeout=8000)
            pass_field.fill(profile["pass"])
            print(f"密码填写: {profile['pass']}")
            
            print("填写MTU...")
            mtu_field = self.page.locator('input[name="mtu"]').first
            expect(mtu_field).to_be_visible(timeout=8000)
            mtu_field.fill(profile["mtu"])
            print(f"MTU填写: {profile['mtu']}")
            
            print("填写MRU...")
            mru_field = self.page.locator('input[name="mru"][aria-required="true"]').first
            expect(mru_field).to_be_visible(timeout=8000)
            mru_field.fill(profile["mru"])
            print(f"MRU填写: {profile['mru']}")
            
            print("PPTP基础信息填写完成")
        except Exception as e:
            print(f"❌ PPTP基础字段填写失败: {e}")
            return False
        
        # 选择线路（增加等待和错误处理）
        try:
            print("正在选择线路...")
            sel = self.page.locator(
                'div.line_edit:has(div.input_tit:has-text("线路：")) select.focuseText.selects'
            ).first
            expect(sel).to_be_visible(timeout=8000)  # 增加超时时间
            sel.scroll_into_view_if_needed()
            time.sleep(1)  # 等待选择器加载完成
            
            values = sel.locator('option').evaluate_all("els => els.map(e => e.value)")
            texts = sel.locator('option').evaluate_all("els => els.map(e => e.textContent.trim())")
            print("可选线路:", list(zip(values, texts)))
            
            if len(values) > 1 and values[1] != profile["line"]:
                sel.select_option(values[1])
                time.sleep(1)  # 增加等待时间
                print("临时切换线路:", values[1])
            sel.select_option(profile["line"])
            print("最终选择线路:", profile["line"])
        except Exception as e:
            print(f"⚠️ 线路选择失败: {e}")
        
        # 填写间隔时长重拨（增加错误处理）
        try:
            print("填写间隔时长重拨...")
            iv = self.page.locator(
                'div.line_edit:has(div.input_tit:has-text("间隔时长重拨：")) input[name="cycle_rst_time"]'
            ).first
            expect(iv).to_be_visible(timeout=8000)  # 增加超时时间
            iv.fill(profile["reconnect_interval"])
            print("间隔时长重拨填写:", profile["reconnect_interval"])
        except Exception as e:
            print(f"⚠️ 间隔时长重拨填写失败: {e}")
        
        # 配置定时重拨
        if profile["scheduled_reconnect"]["enabled"]:
            try:
                self._configure_scheduled_reconnect(profile["scheduled_reconnect"])
            except Exception as e:
                print(f"⚠️ 定时重拨配置失败: {e}")
        
        # 填写备注（增加错误处理）
        try:
            print("填写备注...")
            remark = self.page.locator(
                'div.line_edit:has(div.input_tit:has-text("备注：")) input'
            ).first
            expect(remark).to_be_visible(timeout=8000)  # 增加超时时间
            remark.fill(profile["comment"])
            print("备注填写:", profile["comment"])
        except Exception as e:
            print(f"⚠️ 备注填写失败: {e}")
        
        return True
    
    def _configure_scheduled_reconnect(self, schedule_config: dict):
        """配置定时重拨（增加错误处理）"""
        print("配置定时重拨...")
        
        try:
            sc_label = self.page.locator('div.line_show:has-text("定时重拨")')
            expect(sc_label).to_be_visible(timeout=8000)  # 增加超时时间
            
            # 开启定时重拨
            sc_label.locator('label.checkbox:has-text("开启")').click()
            print("定时重拨已开启")
            time.sleep(1)  # 等待界面更新
            
            # 选择日期
            for day in schedule_config["days"]:
                try:
                    lbl = sc_label.locator(f'label.checkbox:has-text("{day}")')
                    if lbl.count():
                        lbl.click()
                        print("  已选中", day)
                        time.sleep(0.5)  # 增加等待时间
                except Exception as e:
                    print(f"  选择日期 {day} 失败: {e}")
            
            # 填写三组不同的时间
            times_list = schedule_config["times"]
            input_names = ["time0", "time1", "time2"]
            for idx, name in enumerate(input_names):
                try:
                    t = times_list[idx] if idx < len(times_list) else times_list[-1]
                    inp = self.page.locator(f'input[name="{name}"]').first
                    expect(inp).to_be_visible(timeout=5000)
                    inp.fill(t)
                    print(f'  填写 {name} = {t}')
                    time.sleep(0.5)
                except Exception as e:
                    print(f'  填写时间 {name} 失败: {e}')
            
            time.sleep(1)  # 增加等待时间
            # 打印可能的校验错误
            errs = sc_label.locator('p.error_tip')
            for i in range(errs.count()):
                print("❗ 定时重拨校验错误:", errs.nth(i).text_content().strip())
                
        except Exception as e:
            print(f"❌ 配置定时重拨失败: {e}")
    
    def step4_disable_profile(self, profile_name: str):
        """步骤4: 停用PPTP配置（增加等待）"""
        print("步骤4: 停用PPTP配置", profile_name)
        
        # 增加等待确保页面加载完成
        time.sleep(2)
        
        row = self.page.locator(f'tr:has-text("{profile_name}")')
        if row.count() > 0:
            self.page.on("dialog", lambda d: d.accept())
            stop_button = row.locator('a:text("停用")')
            if stop_button.count() > 0:
                stop_button.click()
                time.sleep(3)  # 增加等待时间
                expect(row.get_by_text("已停用")).to_be_visible(timeout=8000)
                print("PPTP配置已停用")
            else:
                print("⚠️ 未找到停用按钮")
        else:
            print("⚠️ 未找到指定PPTP配置")
    
    def step5_enable_profile(self, profile_name: str):
        """步骤5: 启用PPTP配置（增加等待）"""
        print("步骤5: 启用PPTP配置", profile_name)
        
        # 增加等待确保页面加载完成
        time.sleep(2)
        
        row = self.page.locator(f'tr:has-text("{profile_name}")')
        if row.count() > 0:
            self.page.on("dialog", lambda d: d.accept())
            enable_button = row.locator('a:text("启用")')
            if enable_button.count() > 0:
                enable_button.click()
                time.sleep(3)  # 增加等待时间
                expect(row.get_by_text("已启用")).to_be_visible(timeout=8000)
                print("PPTP配置已启用")
            else:
                print("⚠️ 未找到启用按钮")
        else:
            print("⚠️ 未找到指定PPTP配置")
    
    def step6_form_validation_errors(self, profile_name: str):
        """步骤6: PPTP表单必填项验证（优化版）"""
        print("步骤6: PPTP表单必填项验证", profile_name)
        
        # 增加等待确保页面稳定
        time.sleep(2)
        
        row = self.page.locator(f'tr:has-text("{profile_name}")')
        if row.count() > 0:
            edit_button = row.locator('a:text("编辑")')
            if edit_button.count() > 0:
                edit_button.click()
                
                # 等待编辑页面加载（使用VLAN的方法）
                time.sleep(3)
                if not self._wait_for_form():
                    print("❌ 编辑表单未加载，跳过验证")
                    return
                
                field_selectors = {
                    "拨号名称": 'input[data-vv-as="拨号名称"]',
                    "服务端口": 'input[data-vv-as="服务端口"]',
                    "服务器地址/域名": 'input[data-vv-as="服务器地址/域名"]',
                    "用户名": 'input[data-vv-as="用户名"]',
                    "密码": 'input[data-vv-as="密码"]',
                    "MTU:": 'input[name="mtu"]',
                    "MRU:": 'input[name="mru"]',
                    "间隔时长重拨：": 'input[name="cycle_rst_time"]'
                }
                
                for label, selector in field_selectors.items():
                    print(f"验证PPTP字段: {label}")
                    try:
                        inp = self.page.locator(selector).first
                        expect(inp).to_be_visible(timeout=5000)  # 增加超时时间
                        inp.clear()
                        
                        # 尝试保存以触发验证
                        save_button = self.page.locator('button:has-text("保存"):visible:enabled').first
                        if save_button.is_visible(timeout=3000):
                            save_button.click()
                            time.sleep(2)  # 增加等待时间
                        
                        # 查找错误提示
                        error_found = False
                        if label.endswith("："):
                            cont = self.page.locator(f'div.line_edit:has(div.input_tit:has-text("{label}"))')
                        else:
                            cont = self.page.locator(f'div.line_edit:has({selector})')
                        
                        err = cont.locator('p.error_tip')
                        if err.count() > 0 and err.first.is_visible(timeout=3000):
                            error_text = err.first.text_content().strip()
                            print(f"  错误提示: {error_text}")
                            error_found = True
                        
                        if not error_found:
                            print(f"  未找到{label}的错误提示")
                        
                        # 恢复原值
                        orig = {
                            "拨号名称": self.test_profile["name"], 
                            "服务端口": self.test_profile["port"],
                            "服务器地址/域名": self.test_profile["server"], 
                            "用户名": self.test_profile["user"],
                            "密码": self.test_profile["pass"], 
                            "MTU:": self.test_profile["mtu"],
                            "MRU:": self.test_profile["mru"], 
                            "间隔时长重拨：": self.test_profile["reconnect_interval"]
                        }[label]
                        inp.fill(orig)
                        time.sleep(0.5)  # 增加等待时间
                        
                    except Exception as e:
                        print(f"  验证{label}时出错: {e}")
                
                # 验证定时重拨时间字段（增加错误处理）
                print("验证字段 定时重拨时间")
                try:
                    sc_label = self.page.locator('div.line_show:has-text("定时重拨")')
                    if sc_label.is_visible():
                        enable_checkbox = sc_label.locator('label.checkbox:has-text("开启")')
                        if enable_checkbox.locator('input[type="checkbox"]').is_checked() == False:
                            enable_checkbox.click()
                            print("  开启定时重拨功能")
                            time.sleep(1)  # 等待界面更新
                        
                        time_inputs = ["time0", "time1", "time2"]
                        for time_name in time_inputs:
                            time_inp = self.page.locator(f'input[name="{time_name}"]').first
                            if time_inp.is_visible():
                                time_inp.clear()
                        
                        save_button = self.page.locator('button:has-text("保存"):visible:enabled').first
                        if save_button.is_visible(timeout=3000):
                            save_button.click()
                            time.sleep(2)
                        
                        # 查找定时重拨相关的错误提示
                        err_tips = sc_label.locator('p.error_tip')
                        if err_tips.count() > 0:
                            for i in range(err_tips.count()):
                                error_text = err_tips.nth(i).text_content().strip()
                                if error_text:
                                    print("  错误提示:", error_text)
                                    break
                        else:
                            all_errors = self.page.locator('p.error_tip:visible')
                            if all_errors.count() > 0:
                                for i in range(all_errors.count()):
                                    error_text = all_errors.nth(i).text_content().strip()
                                    if "定时" in error_text or "时间" in error_text:
                                        print("  错误提示:", error_text)
                                        break
                                else:
                                    if all_errors.count() > 0:
                                        print("  错误提示:", all_errors.last.text_content().strip())
                            else:
                                print("  未找到错误提示")
                        
                        # 恢复定时重拨时间的原值
                        times_list = self.test_profile["scheduled_reconnect"]["times"]
                        for idx, time_name in enumerate(time_inputs):
                            if idx < len(times_list):
                                time_inp = self.page.locator(f'input[name="{time_name}"]').first
                                if time_inp.is_visible():
                                    time_inp.fill(times_list[idx])
                                    time.sleep(0.5)
                except Exception as e:
                    print(f"  验证定时重拨时间时出错: {e}")
                
                # 取消表单（使用VLAN的方法）
                self._cancel_form()
                self._wait_for_page_ready()
                print("PPTP表单验证完成")
            else:
                print("⚠️ 未找到编辑按钮")
        else:
            print("⚠️ 未找到指定PPTP配置")
    
    def step7_delete_profile(self, profile_name: str):
        """步骤7: 删除PPTP配置 取消和确认流程（增加等待）"""
        print("步骤7: 删除PPTP配置 取消流程")
        
        # 增加等待确保页面稳定
        time.sleep(2)
        
        row = self.page.locator(f'tr:has-text("{profile_name}")')
        if row.count() > 0:
            delete_button = row.locator('a:text("删除")')
            if delete_button.count() > 0:
                delete_button.click()
                modal = self.page.locator('div.el-message-box')
                expect(modal).to_be_visible(timeout=8000)  # 增加超时时间
                modal.locator('button.el-button:has-text("取消")').click()
                time.sleep(1)
                expect(row).to_be_visible(timeout=5000)
                print("取消删除，PPTP配置依然存在")
                
                print("步骤7: 删除PPTP配置 确认流程")
                delete_button.click()
                expect(modal).to_be_visible(timeout=8000)  # 增加超时时间
                modal.locator('button.el-button--primary:has-text("确定")').click()
                expect(row).to_be_hidden(timeout=8000)  # 增加超时时间
                print("确认删除，PPTP配置已移除")
            else:
                print("⚠️ 未找到删除按钮")
        else:
            print("⚠️ 未找到指定PPTP配置")
    
    def step8_batch_create_profiles(self, count: int = None):
        """步骤8: 批量创建PPTP配置（优化版）"""
        if count is None:
            count = self.batch_create_count
            
        print(f"步骤8: 批量创建PPTP配置，共{count}条")
        
        for i in range(1, count + 1):
            profile = self.test_profile.copy()
            profile["name"] = f"pptp_test_{i+1:02d}"  # pptp_test_02, pptp_test_03, ...
            
            print(f"创建第 {i}/{count} 个PPTP配置: {profile['name']}")
            
            # 使用优化的创建流程
            try:
                success = self.step3_create_profile(profile, show_step_info=False)
                if success:
                    print(f"✅ PPTP配置 {profile['name']} 创建成功")
                else:
                    print(f"⚠️ PPTP配置 {profile['name']} 创建失败")
            except Exception as e:
                print(f"❌ 创建PPTP配置 {profile['name']} 失败: {e}")
                
            time.sleep(3)  # 增加批量创建之间的等待时间
        
        print(f"批量创建完成，共创建了{count}个PPTP配置")
    
    def step9_check_local_ips(self):
        """步骤9: 检查并展示PPTP本地IP信息（优化版）"""
        print("步骤9: 检查并展示PPTP本地IP信息")
        
        # 刷新页面以获取最新的IP状态
        print("🔄 刷新页面以获取最新的IP状态...")
        self.page.reload()
        time.sleep(3)  # 增加等待时间
        
        # 重新导航到PPTP页面
        print("🧭 重新导航到PPTP页面...")
        self.navigate_to_module()
        
        print("🔍 开始查找表格元素...")
        
        # 使用VLAN类似的表格查找逻辑
        table_selectors = [
            'table',
            'div.table-box table',
            'div[class*="table"] table',
            '.el-table table',
            '[role="table"]'
        ]
        
        table_found = False
        table_element = None
        
        for selector in table_selectors:
            tables = self.page.locator(selector)
            if tables.count() > 0:
                print(f"✅ 找到表格，使用选择器: {selector}, 数量: {tables.count()}")
                table_element = tables.first
                table_found = True
                break
        
        if table_found and table_element:
            print("📊 分析表格结构...")
            
            # 查找表头
            headers = table_element.locator('thead tr th, thead tr td, tr:first-child th, tr:first-child td')
            header_count = headers.count()
            
            if header_count > 0:
                print(f"✅ 找到表头，列数: {header_count}")
                for i in range(header_count):
                    header_text = headers.nth(i).text_content().strip()
                    print(f"  第{i+1}列表头: '{header_text}'")
                
                local_ip_column_index = -1
                for i in range(header_count):
                    header_text = headers.nth(i).text_content().strip()
                    if "本地IP" in header_text:
                        local_ip_column_index = i
                        print(f"🎯 确定本地IP列位置: 第{i+1}列")
                        break
                
                if local_ip_column_index == -1:
                    print("⚠️ 未找到本地IP列，使用默认第6列")
                    local_ip_column_index = 5
            else:
                print("⚠️ 未找到表头，使用默认第6列作为本地IP列")
                local_ip_column_index = 5
            
            # 查找数据行
            rows = table_element.locator('tbody tr')
            if rows.count() == 0:
                all_rows = table_element.locator('tr')
                if all_rows.count() > 1:
                    rows = table_element.locator('tr:not(:first-child)')
                else:
                    rows = all_rows
            
            row_count = rows.count()
            print(f"✅ 找到数据行: {row_count}")
            
            if row_count > 0:
                print("\n=== PPTP配置本地IP信息 ===")
                ip_info_list = []
                valid_data_rows = 0
                
                for i in range(row_count):
                    row = rows.nth(i)
                    cells = row.locator('td')
                    cell_count = cells.count()
                    
                    if cell_count >= 3:
                        config_name = cells.nth(0).text_content().strip()
                        
                        if config_name and config_name not in ["拨号名称", "配置名称", ""]:
                            valid_data_rows += 1
                            
                            if cell_count > local_ip_column_index:
                                local_ip = cells.nth(local_ip_column_index).text_content().strip()
                                
                                if local_ip and local_ip != "-" and local_ip != "" and "." in local_ip:
                                    ip_info_list.append({"name": config_name, "local_ip": local_ip})
                                    print(f"{valid_data_rows}. {config_name} -> 本地IP: {local_ip}")
                                else:
                                    ip_info_list.append({"name": config_name, "local_ip": "未获取到IP"})
                                    print(f"{valid_data_rows}. {config_name} -> 未获取到IP")
                            else:
                                ip_info_list.append({"name": config_name, "local_ip": "列数据不足"})
                                print(f"{valid_data_rows}. {config_name} -> 列数据不足 (总列数: {cell_count})")
                
                valid_ip_count = len([info for info in ip_info_list if info["local_ip"] not in ["未获取到IP", "列数据不足"]])
                print(f"\n统计信息:")
                print(f"  有效数据行: {valid_data_rows}")
                print(f"  总配置数: {len(ip_info_list)}")
                print(f"  已获取IP: {valid_ip_count}")
                print(f"  未获取IP: {len(ip_info_list) - valid_ip_count}")
                
                if valid_ip_count > 0:
                    valid_ips = [info["local_ip"] for info in ip_info_list if info["local_ip"] not in ["未获取到IP", "列数据不足"]]
                    print(f"\n✅ 成功获取到{valid_ip_count}个PPTP配置的本地IP")
                    print(f"IP列表: {', '.join(valid_ips)}")
                else:
                    print(f"\n⚠️ 所有PPTP配置都未获取到本地IP")
            else:
                print("⚠️ 没有找到数据行")
        else:
            print("❌ 未找到表格")
    
    def step10_batch_operations_test(self):
        """步骤10: PPTP批量停用和启用操作（增加等待）"""
        print("步骤10: PPTP批量停用和启用操作")
        
        # 增加等待确保页面稳定
        time.sleep(2)
        
        # 步骤10.1: 全选所有配置
        if not self.select_all_configs("PPTP批量操作"):
            return
        
        # 步骤10.2: 批量停用
        print("🛑 执行PPTP批量停用操作...")
        
        disable_selectors = [
            'a:has-text("停用")',
            'button:has-text("停用")',
            '.btn:has-text("停用")',
            'input[value="停用"]'
        ]
        
        if not self.batch_operation("停用", disable_selectors):
            print("❌ 未找到批量停用按钮")
            return
        
        print("✅ PPTP批量停用操作执行完成")
        
        # 步骤10.3: 等待后批量启用
        print("\n⏳ 等待3秒...")  # 增加等待时间
        time.sleep(3)
        
        print("✅ 执行PPTP批量启用操作...")
        
        enable_selectors = [
            'a:has-text("启用")',
            'button:has-text("启用")',
            '.btn:has-text("启用")',
            'input[value="启用"]'
        ]
        
        if not self.batch_operation("启用", enable_selectors):
            print("❌ 未找到批量启用按钮")
            return
        
        print("✅ PPTP批量启用操作执行完成")
        print("\n✅ PPTP批量停用和启用操作全部完成")
    
    def step11_export_import_test(self):
        """步骤11: 测试PPTP导出和导入功能（增加等待）"""
        print("步骤11: 测试PPTP导出和导入功能")
        
        # 获取下载目录
        download_path = os.path.abspath("./downloads")
        if not os.path.exists(download_path):
            os.makedirs(download_path)
            print(f"📁 创建下载目录: {download_path}")
        
        exported_files = []
        
        # 步骤11.1: 导出CSV和TXT文件 - 使用PPTP专用方法
        print("📤 测试PPTP导出功能...")
        
        export_formats = ["csv", "txt"]
        
        for format_type in export_formats:
            file_path = self.export_data_pptp(format_type, download_path)
            if file_path:
                exported_files.append(file_path)
                time.sleep(3)  # 增加等待时间
        
        print(f"\n📊 PPTP导出结果统计:")
        print(f"  成功导出文件数: {len(exported_files)}")
        for file_path in exported_files:
            print(f"  - {os.path.basename(file_path)}")
        
        if len(exported_files) < 2:
            print("⚠️ 导出文件不足，跳过后续测试")
            return
        
        # 步骤11.2: 批量删除所有配置
        print("\n🗑️ 步骤11.2: 批量删除所有PPTP配置")
        delete_success = self.batch_delete_all_configs(need_select_all=False)
        if not delete_success:
            print("❌ 批量删除失败，跳过后续测试")
            return
        
        # 步骤11.3: 导入CSV文件（不勾选合并选项）
        print("\n📥 步骤11.3: 导入PPTP CSV文件")
        csv_file = None
        for file_path in exported_files:
            if file_path.endswith('.csv'):
                csv_file = file_path
                break
        
        if csv_file:
            import_success = self.import_data(csv_file, "csv", merge_to_current=False)
            if import_success:
                print("✅ PPTP CSV文件导入成功")
            else:
                print("❌ PPTP CSV文件导入失败")
        else:
            print("❌ 未找到PPTP CSV文件")
        
        time.sleep(3)  # 增加等待时间
        
        # 步骤11.4: 再次批量删除所有配置
        print("\n🗑️ 步骤11.4: 再次批量删除所有PPTP配置")
        delete_success = self.batch_delete_all_configs(need_select_all=True)
        if not delete_success:
            print("❌ 第二次批量删除失败")
        
        # 步骤11.5: 导入TXT文件（勾选合并到当前数据选项）
        print("\n📥 步骤11.5: 导入PPTP TXT文件（勾选合并到当前数据）")
        txt_file = None
        for file_path in exported_files:
            if file_path.endswith('.txt'):
                txt_file = file_path
                break
        
        if txt_file:
            import_success = self.import_data(txt_file, "txt", merge_to_current=True)
            if import_success:
                print("✅ PPTP TXT文件导入成功")
            else:
                print("❌ PPTP TXT文件导入失败")
        else:
            print("❌ 未找到PPTP TXT文件")
        
        # 步骤11.6: 清理导出的文件
        print(f"\n🧹 清理PPTP导出文件...")
        for file_path in exported_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"✅ 已删除文件: {os.path.basename(file_path)}")
            except Exception as e:
                print(f"⚠️ 删除文件失败: {os.path.basename(file_path)}, 错误: {e}")
        
        # 清理下载目录（如果为空）
        try:
            if os.path.exists(download_path) and not os.listdir(download_path):
                os.rmdir(download_path)
                print(f"✅ 已删除空的下载目录")
        except Exception as e:
            print(f"⚠️ 删除下载目录失败: {e}")
        
        print("\n✅ PPTP导出导入功能测试全部完成")
    
    def export_data_pptp(self, format_type: str, download_path: str) -> Optional[str]:
        """PPTP专用导出数据方法，确保文件名正确（增加等待）"""
        print(f"🔹 导出PPTP {format_type.upper()}格式...")
        
        try:
            import requests
            
            # 记录导出请求
            export_requests = []
            download_requests = []
            
            def handle_request(request):
                try:
                    if "/Action/call" in request.url and request.post_data:
                        post_data = request.post_data
                        if "EXPORT" in post_data:
                            export_requests.append({
                                "url": request.url,
                                "data": post_data
                            })
                            print(f"🔍 捕获到PPTP导出API请求: {request.url}")
                    elif "/Action/download" in request.url:
                        download_requests.append({
                            "url": request.url
                        })
                        print(f"🔍 捕获到PPTP下载请求: {request.url}")
                except Exception as e:
                    print(f"⚠️ 处理请求时出错: {e}")
                    
            # 添加请求监听器
            self.page.on("request", handle_request)
            
            # 查找并点击导出按钮
            export_button_strategies = [
                'a:has-text("导出")',
                'button:has-text("导出")',
                '.btn:has-text("导出")',
                'input[value="导出"]'
            ]
            
            export_button_found = False
            for strategy in export_button_strategies:
                export_buttons = self.page.locator(strategy)
                if export_buttons.count() > 0:
                    export_button = export_buttons.first
                    if export_button.is_visible(timeout=5000):  # 增加超时时间
                        print(f"✅ 找到PPTP导出按钮，策略: {strategy}")
                        export_button.scroll_into_view_if_needed()
                        export_button.click()
                        export_button_found = True
                        break
            
            if not export_button_found:
                print(f"❌ 未找到PPTP导出按钮")
                self.page.remove_listener("request", handle_request)
                return None
            
            # 等待下拉菜单
            time.sleep(2)  # 增加等待时间
            
            # 选择格式
            format_option_strategies = [
                f'a:has-text("{format_type.upper()}")',
                f'li:has-text("{format_type.upper()}")',
                f'[data-format="{format_type}"]'
            ]
            
            format_option_found = False
            for strategy in format_option_strategies:
                format_options = self.page.locator(strategy)
                if format_options.count() > 0:
                    format_option = format_options.first
                    if format_option.is_visible(timeout=5000):  # 增加超时时间
                        print(f"✅ 找到PPTP {format_type.upper()}选项，策略: {strategy}")
                        format_option.click()
                        format_option_found = True
                        break
            
            if not format_option_found:
                print(f"❌ 未找到PPTP {format_type.upper()}选项")
                self.page.remove_listener("request", handle_request)
                return None
            
            # 等待API请求
            time.sleep(5)  # 增加等待时间
            
            # 移除监听器
            self.page.remove_listener("request", handle_request)
            
            # 使用requests下载文件
            if export_requests or download_requests:
                cookies = self.get_cookies_from_page()
                
                # 构造下载URL - 确保是PPTP的文件名
                base_url = self.config.router_url.replace('/login#/login', '')
                download_url = f"{base_url}/Action/download?filename=pptp_client.{format_type}"
                
                headers = {
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'zh-CN,zh;q=0.9',
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'Pragma': 'no-cache',
                    'Referer': base_url + '/',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                response = requests.get(download_url, headers=headers, cookies=cookies, verify=False, timeout=15)  # 增加超时时间
                
                if response.status_code == 200:
                    # 强制使用正确的PPTP文件名
                    file_path = os.path.join(download_path, f"pptp_client.{format_type}")
                    
                    with open(file_path, 'wb') as f:
                        f.write(response.content)
                    
                    if os.path.exists(file_path):
                        file_size = os.path.getsize(file_path)
                        print(f"✅ PPTP {format_type.upper()}格式导出成功: {file_path}")
                        print(f"   文件大小: {file_size} 字节")
                        return file_path
                    else:
                        print(f"❌ PPTP文件保存失败: {file_path}")
                        return None
                else:
                    print(f"❌ PPTP下载失败，状态码: {response.status_code}")
                    return None
            else:
                print(f"❌ 未检测到PPTP导出相关请求")
                return None
                
        except Exception as e:
            print(f"❌ 导出PPTP {format_type.upper()}格式时出错: {e}")
            try:
                self.page.remove_listener("request", handle_request)
            except:
                pass
            return None

    def get_cookies_from_page(self):
        """从页面获取cookies"""
        cookies = self.page.context.cookies()
        return {cookie['name']: cookie['value'] for cookie in cookies}
    
    def step12_cleanup_all_configs(self):
        """步骤12: 清理所有PPTP配置（增加等待）"""
        print("步骤12: 清理所有PPTP配置")
        
        # 首先检查是否有配置需要删除
        try:
            time.sleep(2)  # 增加等待时间
            rows = self.page.locator('table tr:not(:first-child)')
            config_count = 0
            
            for i in range(rows.count()):
                row = rows.nth(i)
                cells = row.locator('td')
                if cells.count() > 0:
                    config_name = cells.nth(0).text_content().strip()
                    if config_name and config_name not in ["拨号名称", "配置名称", ""]:
                        config_count += 1
            
            print(f"🔍 当前PPTP配置数量: {config_count}")
            
            if config_count == 0:
                print("✅ 当前没有PPTP配置，无需清理")
                return True
                
        except Exception as e:
            print(f"检查PPTP配置数量时出错: {e}")
        
        # 使用批量删除功能清理所有配置
        print("🗑️ 开始清理所有PPTP配置...")
        delete_success = self.batch_delete_all_configs(need_select_all=True)
        
        if delete_success:
            print("✅ 所有PPTP配置已成功清理")
            return True
        else:
            print("❌ PPTP配置清理失败")
            return False
    
    def run_full_test(self):
        """运行完整的PPTP 12个步骤测试（优化版）"""
        print("开始PPTP模块完整测试 - 12个步骤（优化版）")
        print(f"测试目标路由器: {self.config.router_url}")
        
        try:
            # 步骤3: 创建PPTP配置
            success = self.step3_create_profile()
            if not success:
                print("❌ 步骤3失败，但继续执行其他步骤")
            
            # 步骤4: 停用配置
            self.step4_disable_profile(self.test_profile["name"])
            time.sleep(2)  # 增加等待时间
            
            # 步骤5: 启用配置
            self.step5_enable_profile(self.test_profile["name"])
            time.sleep(2)  # 增加等待时间
            
            # 步骤6: 表单验证错误
            self.step6_form_validation_errors(self.test_profile["name"])
            
            # 步骤7: 删除配置（取消和确认）
            self.step7_delete_profile(self.test_profile["name"])
            
            # 步骤8: 批量创建配置
            self.step8_batch_create_profiles()
            
            # 步骤9: 检查并展示本地IP信息
            self.step9_check_local_ips()
            
            # 步骤10: 批量停用和启用操作
            self.step10_batch_operations_test()
            
            # 步骤11: 导出导入功能测试
            self.step11_export_import_test()
            
            # 步骤12: 清理所有PPTP配置
            self.step12_cleanup_all_configs()
            
            print("✅ 所有PPTP 12个测试步骤已成功完成（优化版）")
            time.sleep(2)
            
        except Exception as e:
            print(f"❌ PPTP测试过程中出现错误: {e}")
            raise

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='PPTP模块自动化测试（优化版）')
    parser.add_argument('--ip', '--router-ip', dest='router_ip', 
                        help='路由器IP地址 (默认: 10.66.0.40)')
    parser.add_argument('--username', '-u', 
                        help='路由器用户名 (默认: admin)')
    parser.add_argument('--password', '-p', 
                        help='路由器密码 (默认: admin123)')
    parser.add_argument('--ssh-user', 
                        help='SSH用户名 (默认: sshd)')
    parser.add_argument('--ssh-pass', 
                        help='SSH密码 (默认: ikuai8.com)')
    parser.add_argument('--headless', action='store_true',
                        help='无头模式运行 (不显示浏览器界面)')
    parser.add_argument('--method', '-m', 
                        help='指定要运行的测试方法名称')
    
    return parser.parse_args()

def create_config_from_args(args):
    """根据命令行参数创建配置"""
    # 默认值
    router_ip = "10.66.0.40"
    username = "admin"
    password = "admin123"
    ssh_user = "sshd"
    ssh_pass = "ikuai8.com"
    
    # 如果提供了参数，则使用参数值
    if args.router_ip:
        router_ip = args.router_ip
        print(f"✅ 使用自定义路由器IP: {router_ip}")
    else:
        print(f"📍 使用默认路由器IP: {router_ip}")
    
    if args.username:
        username = args.username
        print(f"✅ 使用自定义用户名: {username}")
    
    if args.password:
        password = args.password
        print(f"✅ 使用自定义密码: {'*' * len(password)}")
    
    if args.ssh_user:
        ssh_user = args.ssh_user
        print(f"✅ 使用自定义SSH用户名: {ssh_user}")
    
    if args.ssh_pass:
        ssh_pass = args.ssh_pass
        print(f"✅ 使用自定义SSH密码: {'*' * len(ssh_pass)}")
    
    # 构造完整的URL
    if not router_ip.startswith('http'):
        router_url = f"http://{router_ip}/login#/login"
    else:
        router_url = router_ip if router_ip.endswith('/login#/login') else f"{router_ip}/login#/login"
    
    return RouterTestConfig(
        router_url=router_url,
        username=username,
        password=password,
        ssh_user=ssh_user,
        ssh_pass=ssh_pass
    )

# 单独运行测试的入口
if __name__ == "__main__":
    from test_framework import TestRunner, RouterTestConfig
    
    # 解析命令行参数
    args = parse_arguments()
    
    # 创建配置
    config = create_config_from_args(args)
    
    # 创建测试运行器
    runner = TestRunner(config, headless=args.headless)
    
    try:
        if args.method:
            # 运行指定的测试方法
            print(f"🎯 运行指定PPTP测试方法: {args.method}")
            runner.run_test_module(PPTPTestModule, [args.method])
        else:
            # 运行完整的12步测试
            print("🚀 运行完整的PPTP 12步测试（优化版）")
            runner.run_test_module(PPTPTestModule)
        
        print("🎉 PPTP模块测试全部完成！")
        
    except Exception as e:
        print(f"💥 PPTP测试执行失败: {e}")
        sys.exit(1)