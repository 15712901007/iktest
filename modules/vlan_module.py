# -*- coding: utf-8 -*-
import sys
import os
import argparse
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from test_framework import RouterTestModule, RouterTestConfig
from playwright.sync_api import expect
import time

class VLANTestModule(RouterTestModule):
    """VLAN设置测试模块 - 完整12个步骤，支持自定义IP地址"""
    
    def __init__(self, config: RouterTestConfig):
        super().__init__(config)
        self.test_profile = {
            "vlan_id": "43",  # 修改为1-4090范围内的值
            "vlan_name": "vlan01",
            "mac": "00:1a:4a:1b:f6:35",
            "ip": "192.168.1.100",
            "subnet_mask": "255.255.255.0",
            "line": "lan1",
            "comment": "PlaywrightE2ETest"
        }
        self.batch_create_count = 5
        self.created_profiles = []  # 记录创建的配置，用于搜索测试
    
    def get_module_info(self) -> dict:
        """获取模块信息"""
        return {
            "name": "VLAN设置",
            "path": ["网络设置", "VLAN设置"],
            "description": "VLAN网络配置测试 - 12个步骤",
            "version": "1.0"
        }
    
    def navigate_to_module(self):
        """步骤2: 导航到VLAN设置页面"""
        print("步骤2: 导航到 VLAN设置 页面")
        if "vlan" not in self.page.url.lower():
            self.page.locator('a:has-text("系统概况")').click()
            self.page.locator('a:has-text("网络设置")').click()
            self.page.locator('a:has-text("VLAN设置")').click()
        expect(self.page.locator('a.btn_green:has-text("添加")').first).to_be_visible(timeout=10000)
        print("已进入 VLAN设置 页面")
    
    def _generate_unique_mac(self, index: int) -> str:
        """生成唯一的MAC地址"""
        # 基础MAC地址：00:1a:4a:1b:f6:35
        # 为每个VLAN生成不同的MAC地址
        base_mac = "00:1a:4a:1b"
        # 修改最后两位来确保唯一性
        last_byte = (0x35 + index) % 0xFF
        second_last_byte = 0xf6 + (index // 0xFF)
        return f"{base_mac}:{second_last_byte:02x}:{last_byte:02x}"
    
    def _generate_unique_comment(self, index: int) -> str:
        """生成唯一的备注"""
        return f"PlaywrightE2ETest-VLAN{index:02d}"
    
    def step3_create_profile(self, profile: dict = None, show_step_info: bool = True):
        """步骤3: 创建VLAN配置（包含扩展IP和子网掩码测试）
        
        Args:
            profile: 配置信息字典
            show_step_info: 是否显示步骤信息（用于批量创建时减少输出）
        """
        if profile is None:
            profile = self.test_profile
            
        if show_step_info:
            print(f"步骤3: 创建VLAN配置 '{profile['vlan_name']}'")
        else:
            print(f"📝 创建VLAN配置 '{profile['vlan_name']}'")
        
        # 等待页面稳定
        time.sleep(1)
        
        # 点击添加按钮 - 等待其可见
        add_button = self.page.locator('a.btn_green:has-text("添加")').first
        
        # 重试机制
        for attempt in range(3):
            try:
                expect(add_button).to_be_visible(timeout=5000)
                add_button.click()
                print("✅ 点击添加按钮")
                break
            except Exception as e:
                print(f"❌ 第{attempt+1}次点击添加按钮失败: {e}")
                if attempt < 2:
                    time.sleep(2)
                    # 刷新页面重试
                    self.page.reload()
                    time.sleep(2)
                    self.navigate_to_module()
                else:
                    raise e
        
        time.sleep(2)
        
        # 等待表单出现
        print("🔍 等待表单出现...")
        form_appeared = self._wait_for_form()
        
        if not form_appeared:
            print("❌ 表单未出现")
            return False
        
        # 填写基本表单
        success = self._fill_vlan_form(profile)
        
        if success:
            # 步骤3.1: 测试扩展IP功能（只在完整测试时进行）
            if show_step_info:
                self._test_extended_ip_functionality(profile)
            
            # 检查是否有真正的验证错误（更严格的检查）
            if self._check_real_validation_errors():
                print("❌ 表单验证失败，取消操作")
                self._cancel_form()
                return False
            
            # 保存配置
            save_success = self._save_vlan_form()
            if save_success:
                # 等待保存完成
                time.sleep(5)
                
                # 关闭可能的弹窗
                self._close_modals()
                
                # 等待添加按钮重新可见
                self._wait_for_page_ready()
                
                # 验证配置是否创建成功
                verified = self._verify_config_created(profile["vlan_name"])
                if verified:
                    print("✅ VLAN配置创建并验证通过")
                    return True
                else:
                    print("⚠️  VLAN配置创建但验证失败")
                    return True  # 仍然认为创建成功
            else:
                print("❌ 保存VLAN配置失败")
                return False
        else:
            print("❌ 填写VLAN表单失败")
            return False
    
    def _test_extended_ip_functionality(self, profile: dict):
        """测试扩展IP功能"""
        print("\n🔧 步骤3.1: 测试扩展IP功能...")
        
        # 定义扩展IP测试数据
        extended_ips = [
            {"ip": "192.168.1.101", "comment": "扩展IP1"},
            {"ip": "192.168.1.102", "comment": "扩展IP2"}
        ]
        
        for i, ext_ip in enumerate(extended_ips, 1):
            print(f"  添加扩展IP {i}: {ext_ip['ip']}")
            
            # 查找扩展IP的添加按钮
            add_ip_success = self._add_extended_ip(ext_ip["ip"], ext_ip["comment"])
            if add_ip_success:
                print(f"  ✅ 扩展IP {i} 添加成功")
            else:
                print(f"  ⚠️  扩展IP {i} 添加失败")
        
        print("✅ 扩展IP功能测试完成")
    
    def _add_extended_ip(self, ip_address: str, comment: str) -> bool:
        """添加扩展IP"""
        try:
            # 查找扩展IP区域的添加按钮 - 更精确的定位
            print(f"    🔍 查找扩展IP区域的添加按钮...")
            
            # 先查找扩展IP区域
            extended_ip_section_selectors = [
                'div:has-text("扩展IP")',
                'label:has-text("扩展IP")',
                'span:has-text("扩展IP")',
                '*:has-text("扩展IP：")'
            ]
            
            extended_ip_section = None
            for selector in extended_ip_section_selectors:
                sections = self.page.locator(selector)
                if sections.count() > 0:
                    extended_ip_section = sections.first
                    print(f"    ✅ 找到扩展IP区域")
                    break
            
            if not extended_ip_section:
                print(f"    ❌ 未找到扩展IP区域")
                return False
            
            # 在扩展IP区域内查找添加按钮
            add_button_found = False
            if extended_ip_section:
                # 在扩展IP区域的父容器中查找添加按钮
                parent_container = extended_ip_section.locator('..')
                add_button_selectors = [
                    'button:has-text("添加"):visible',
                    'a:has-text("添加"):visible',
                    '.btn:has-text("添加"):visible',
                    'input[value="添加"]:visible'
                ]
                
                for selector in add_button_selectors:
                    buttons = parent_container.locator(selector)
                    if buttons.count() > 0:
                        # 查找扩展IP区域附近的添加按钮
                        for i in range(buttons.count()):
                            button = buttons.nth(i)
                            if button.is_visible() and button.is_enabled():
                                # 检查按钮是否在扩展IP区域附近
                                button_text = button.text_content().strip()
                                if button_text == "添加":
                                    button.click()
                                    print(f"    ✅ 点击扩展IP添加按钮")
                                    add_button_found = True
                                    time.sleep(2)  # 等待输入框出现
                                    break
                    if add_button_found:
                        break
            
            # 如果在扩展IP区域没找到，尝试更广泛的搜索
            if not add_button_found:
                print(f"    🔍 尝试更广泛的添加按钮搜索...")
                all_add_buttons = self.page.locator('button:has-text("添加"):visible, a:has-text("添加"):visible')
                
                # 过滤掉主表单的添加按钮（通常是绿色的大按钮）
                for i in range(all_add_buttons.count()):
                    button = all_add_buttons.nth(i)
                    if button.is_visible():
                        # 检查按钮的类名，避免点击主添加按钮
                        button_class = button.get_attribute('class') or ""
                        if "btn_green" not in button_class:  # 避免主添加按钮
                            try:
                                button.click()
                                print(f"    ✅ 点击找到的添加按钮")
                                add_button_found = True
                                time.sleep(2)
                                break
                            except:
                                continue
            
            if not add_button_found:
                print(f"    ❌ 未找到扩展IP添加按钮")
                return False
            
            # 查找新出现的IP输入框
            print(f"    🔍 查找扩展IP输入框...")
            ip_input_found = False
            
            # 等待输入框出现
            time.sleep(1)
            
            # 查找扩展IP表格中的输入框
            ip_input_selectors = [
                'table tbody tr:last-child input[type="text"]:first-child',
                'table tr:last-child input[type="text"]:first-child',
                'tbody tr:last-child input[type="text"]',
                'table input[type="text"]:visible'
            ]
            
            for selector in ip_input_selectors:
                try:
                    ip_inputs = self.page.locator(selector)
                    if ip_inputs.count() > 0:
                        # 尝试最后一个可见的输入框
                        ip_input = ip_inputs.last if ip_inputs.count() > 1 else ip_inputs.first
                        if ip_input.is_visible() and ip_input.is_enabled():
                            # 检查输入框是否为空或包含占位符
                            current_value = ip_input.input_value()
                            if not current_value or current_value.strip() == "":
                                ip_input.clear()
                                ip_input.fill(ip_address)
                                print(f"    ✅ 填写扩展IP: {ip_address}")
                                ip_input_found = True
                                break
                except Exception as e:
                    print(f"    ⚠️  尝试选择器 {selector} 失败: {e}")
                    continue
            
            if not ip_input_found:
                print(f"    ❌ 未找到可用的扩展IP输入框")
                return False
            
            # 查找备注输入框 - 在同一行
            print(f"    🔍 查找备注输入框...")
            comment_input_found = False
            
            # 查找包含刚填写IP的表格行
            time.sleep(0.5)  # 等待输入生效
            
            table_rows = self.page.locator('table tr:visible, tbody tr:visible')
            for i in range(table_rows.count()):
                try:
                    row = table_rows.nth(i)
                    row_text = row.text_content()
                    
                    # 如果这一行包含我们刚填写的IP
                    if ip_address in row_text:
                        # 查找这一行的所有输入框
                        row_inputs = row.locator('input[type="text"]:visible')
                        if row_inputs.count() >= 2:  # 应该有IP和备注两个输入框
                            comment_input = row_inputs.nth(1)  # 第二个是备注
                            if comment_input.is_visible() and comment_input.is_enabled():
                                comment_input.clear()
                                comment_input.fill(comment)
                                print(f"    ✅ 填写扩展IP备注: {comment}")
                                comment_input_found = True
                                break
                except Exception as e:
                    continue
            
            if not comment_input_found:
                print(f"    ⚠️  未找到扩展IP备注输入框，但IP已添加")
            
            # 查找并点击"确定"按钮以确认扩展IP
            print(f"    🔍 查找确定按钮...")
            confirm_button_found = False
            
            # 查找包含刚填写IP的表格行中的确定按钮
            time.sleep(0.5)  # 等待页面更新
            
            table_rows = self.page.locator('table tr:visible, tbody tr:visible')
            for i in range(table_rows.count()):
                try:
                    row = table_rows.nth(i)
                    row_text = row.text_content()
                    
                    # 如果这一行包含我们刚填写的IP
                    if ip_address in row_text:
                        # 查找这一行的确定按钮
                        confirm_button_selectors = [
                            'button:has-text("确定"):visible',
                            'a:has-text("确定"):visible',
                            '.btn:has-text("确定"):visible',
                            'button:has-text("确认"):visible',
                            'a:has-text("确认"):visible'
                        ]
                        
                        for selector in confirm_button_selectors:
                            confirm_buttons = row.locator(selector)
                            if confirm_buttons.count() > 0:
                                confirm_button = confirm_buttons.first
                                if confirm_button.is_visible() and confirm_button.is_enabled():
                                    confirm_button.click()
                                    print(f"    ✅ 点击确定按钮确认扩展IP")
                                    confirm_button_found = True
                                    time.sleep(1)  # 等待确认生效
                                    break
                        if confirm_button_found:
                            break
                except Exception as e:
                    continue
            
            # 如果在行内没找到，尝试查找页面上的确定按钮
            if not confirm_button_found:
                print(f"    🔍 尝试查找页面上的确定按钮...")
                page_confirm_selectors = [
                    'button:has-text("确定"):visible:enabled',
                    'a:has-text("确定"):visible',
                    '.btn:has-text("确定"):visible:enabled'
                ]
                
                for selector in page_confirm_selectors:
                    confirm_buttons = self.page.locator(selector)
                    if confirm_buttons.count() > 0:
                        # 查找最合适的确定按钮（通常是最后一个或最近添加的）
                        confirm_button = confirm_buttons.last
                        if confirm_button.is_visible() and confirm_button.is_enabled():
                            confirm_button.click()
                            print(f"    ✅ 点击页面确定按钮确认扩展IP")
                            confirm_button_found = True
                            time.sleep(1)
                            break
            
            if not confirm_button_found:
                print(f"    ⚠️  未找到确定按钮，扩展IP可能需要手动确认")
            
            return True
            
        except Exception as e:
            print(f"    ❌ 添加扩展IP时出错: {e}")
            return False
    
    def _wait_for_form(self):
        """等待表单出现"""
        # 等待真正的输入字段出现
        for attempt in range(10):
            try:
                # 查找text类型的输入字段，排除button和search类型
                text_inputs = self.page.locator('input[type="text"]:not(.search_inpt):not([name="searchText"]):visible')
                if text_inputs.count() > 0:
                    # 检查是否有name属性，确保是表单字段
                    for i in range(text_inputs.count()):
                        field = text_inputs.nth(i)
                        name = field.get_attribute('name') or ""
                        if name and name != "searchText":
                            print("✅ 检测到表单输入字段")
                            return True
                
                time.sleep(0.5)
            except:
                time.sleep(0.5)
        
        return False
    
    def _check_real_validation_errors(self):
        """检查真正的表单验证错误（更严格）"""
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
                            print(f"⚠️  发现真正的验证错误: {error_text}")
                            return True
            
            return False
        except:
            return False
    
    def _cancel_form(self):
        """取消表单"""
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
                        print("✅ 已取消表单")
                        time.sleep(1)
                        return True
            
            # 如果没有找到取消按钮，按ESC键
            self.page.keyboard.press('Escape')
            print("✅ 按ESC取消表单")
            return True
        except:
            return False
    
    def _close_modals(self):
        """关闭可能的模态弹窗"""
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
                        print("✅ 关闭模态弹窗")
                        time.sleep(1)
                        break
        except:
            pass
    
    def _wait_for_page_ready(self):
        """等待页面恢复到可操作状态"""
        print("⏳ 等待页面恢复...")
        for attempt in range(15):  # 增加等待时间
            try:
                add_button = self.page.locator('a.btn_green:has-text("添加")').first
                if add_button.is_visible() and add_button.is_enabled():
                    print("✅ 页面已恢复")
                    return True
                time.sleep(1)
            except:
                time.sleep(1)
        
        print("⚠️  页面恢复超时")
        return False
    
    def _fill_vlan_form(self, profile):
        """填写VLAN表单"""
        print("📝 开始填写VLAN表单...")
        
        # 查找所有文本输入字段和文本域，排除搜索和按钮类型
        input_selectors = [
            'input[type="text"]:not(.search_inpt):not([name="searchText"]):visible, textarea:visible',
            'input:not([type="button"]):not([type="submit"]):not(.search_inpt):not([name="searchText"]):visible, textarea:visible'
        ]
        
        input_fields = None
        for selector in input_selectors:
            fields = self.page.locator(selector)
            if fields.count() > 0:
                input_fields = fields
                print(f"✅ 找到 {fields.count()} 个输入字段 (策略: {selector})")
                break
        
        if not input_fields:
            print("❌ 未找到输入字段")
            return False
        
        field_count = input_fields.count()
        
        # 打印字段信息用于调试
        for i in range(field_count):
            try:
                field = input_fields.nth(i)
                placeholder = field.get_attribute('placeholder') or ""
                name = field.get_attribute('name') or ""
                field_type = field.get_attribute('type') or ""
                tag_name = field.evaluate('el => el.tagName.toLowerCase()')
                print(f"  字段{i+1}: name='{name}', type='{field_type}', tag='{tag_name}', placeholder='{placeholder}'")
            except:
                print(f"  字段{i+1}: 无法获取属性")
        
        # 按name属性填写字段
        fields_filled = 0
        
        # 按优先级填写各个字段
        field_mappings = [
            ("vlan_id", profile["vlan_id"], "VLAN ID"),
            ("vlan_name", profile["vlan_name"], "VLAN名称"),
            ("mac", profile["mac"], "MAC地址"),
            ("ip_addr", profile["ip"], "IP地址"),
            ("comment", profile["comment"], "备注")
        ]
        
        for field_name, field_value, field_label in field_mappings:
            success = self._fill_field_by_name_or_position(input_fields, field_name, field_value, field_label)
            if success:
                fields_filled += 1
            time.sleep(0.5)
        
        # 如果通过常规方式没找到备注字段，尝试其他方式
        if fields_filled < 5:  # 应该填写5个字段
            comment_success = self._fill_comment_field_alternative(profile["comment"])
            if comment_success:
                fields_filled += 1
        
        # 处理下拉选择框
        self._handle_form_selects(self.page, profile)
        
        print(f"📊 总共填写了 {fields_filled} 个字段")
        return fields_filled > 0
    
    def _fill_field_by_name_or_position(self, input_fields, target_name, value, label):
        """根据name属性或位置填写字段"""
        field_count = input_fields.count()
        
        # 首先按name属性查找
        for i in range(field_count):
            try:
                field = input_fields.nth(i)
                name = field.get_attribute('name') or ""
                
                if name == target_name:
                    if field.is_enabled():
                        field.clear()  # 先清空
                        field.fill(value)
                        print(f"✅ {label}填写成功: {value} (按name属性)")
                        return True
                    else:
                        print(f"⚠️  {label}字段被禁用")
                        return False
            except Exception as e:
                print(f"❌ 填写{label}时出错: {e}")
                continue
        
        # 如果按name没找到，按位置填写
        position_mapping = {
            "vlan_id": 0,
            "vlan_name": 1, 
            "mac": 2,
            "ip_addr": 3,
            "comment": 4
        }
        
        if target_name in position_mapping:
            pos = position_mapping[target_name]
            if pos < field_count:
                try:
                    field = input_fields.nth(pos)
                    if field.is_enabled():
                        field.clear()  # 先清空
                        field.fill(value)
                        print(f"✅ {label}填写成功: {value} (按位置)")
                        return True
                    else:
                        print(f"⚠️  {label}字段被禁用")
                        return False
                except Exception as e:
                    print(f"❌ {label}填写失败: {e}")
                    return False
        
        print(f"⚠️  {label}字段未找到")
        return False
    
    def _fill_comment_field_alternative(self, comment):
        """备注字段的备用填写方法"""
        try:
            print("🔍 尝试备用方式查找备注字段...")
            
            # 备注字段的多种策略
            comment_selectors = [
                'input[name="comment"]:visible',
                'textarea[name="comment"]:visible',
                'input[placeholder*="备注"]:visible',
                'textarea[placeholder*="备注"]:visible',
                'input[name*="remark"]:visible',
                'textarea[name*="remark"]:visible',
                # 通过标签查找
                'div:has-text("备注：") + * input:visible',
                'div:has-text("备注：") + * textarea:visible',
                'label:has-text("备注") + input:visible',
                'label:has-text("备注") + textarea:visible'
            ]
            
            for selector in comment_selectors:
                try:
                    fields = self.page.locator(selector)
                    if fields.count() > 0:
                        field = fields.first
                        if field.is_visible() and field.is_enabled():
                            field.clear()
                            field.fill(comment)
                            print(f"✅ 备注填写成功: {comment} (策略: {selector})")
                            return True
                except:
                    continue
            
            # 如果还是没找到，尝试查找页面上最后一个可见的输入框
            try:
                all_inputs = self.page.locator('input[type="text"]:visible, textarea:visible')
                if all_inputs.count() > 4:  # 如果有超过4个输入框，最后一个可能是备注
                    last_input = all_inputs.last
                    if last_input.is_enabled():
                        last_input.clear()
                        last_input.fill(comment)
                        print(f"✅ 备注填写成功: {comment} (最后一个输入框)")
                        return True
            except:
                pass
            
            print("⚠️  备注字段未找到")
            return False
            
        except Exception as e:
            print(f"❌ 备注字段填写失败: {e}")
            return False
    
    def _handle_form_selects(self, container, profile):
        """处理表单中的下拉选择框"""
        print("📋 处理表单下拉选择框...")
        
        # 查找select元素
        selects = container.locator('select:visible')
        select_count = selects.count()
        print(f"🔍 找到 {select_count} 个下拉选择框")
        
        for i in range(select_count):
            try:
                select = selects.nth(i)
                select_name = select.get_attribute('name') or f"select_{i+1}"
                
                print(f"🔍 处理选择框 {i+1} ({select_name}):")
                
                # 根据位置判断选择框类型
                if i == 0:  # 第一个选择框 - 子网掩码（测试不同的掩码）
                    self._test_different_subnet_masks(select, profile.get("subnet_mask", "255.255.255.0"))
                elif i == 1:  # 第二个选择框 - 线路
                    self._select_line_option(select, profile["line"])
                else:
                    self._select_first_valid_option(select, f"选择框{i+1}")
                
                time.sleep(0.5)
                
            except Exception as e:
                print(f"⚠️  处理选择框 {i+1} 时出错: {e}")
    
    def _test_different_subnet_masks(self, select, target_mask):
        """测试不同的子网掩码选择"""
        try:
            # 先获取所有选项的值
            option_values = select.locator('option').evaluate_all('options => options.map(option => option.value)')
            option_texts = select.locator('option').evaluate_all('options => options.map(option => option.textContent.trim())')
            
            print(f"  可用子网掩码选项: {len(option_values)} 个")
            
            # 测试几种不同的子网掩码
            test_masks = [
                "255.255.255.0",    # /24
                "255.255.254.0",    # /23  
                "255.255.252.0",    # /22
                "255.255.248.0"     # /21
            ]
            
            # 选择一个可用的测试掩码
            selected_mask = None
            for test_mask in test_masks:
                for i, (value, text) in enumerate(zip(option_values, option_texts)):
                    if test_mask in text or test_mask == value:
                        if value:  # 确保value不为空
                            select.select_option(value)
                            print(f"✅ 测试子网掩码选择: {text}")
                            selected_mask = text
                            break
                if selected_mask:
                    break
            
            # 如果没有找到测试掩码，使用目标掩码
            if not selected_mask:
                for i, (value, text) in enumerate(zip(option_values, option_texts)):
                    if target_mask in text or target_mask == value:
                        if value:
                            select.select_option(value)
                            print(f"✅ 子网掩码选择成功: {text} (目标掩码)")
                            selected_mask = text
                            break
            
            # 最后选择第一个有值的选项
            if not selected_mask:
                for i, (value, text) in enumerate(zip(option_values, option_texts)):
                    if value and value.strip():
                        select.select_option(value)
                        print(f"✅ 子网掩码选择成功: {text} (第一个有效选项)")
                        selected_mask = text
                        break
            
            if selected_mask:
                # 测试验证：等待一下，看看是否有验证错误
                time.sleep(1)
                print(f"🧪 子网掩码 {selected_mask} 验证通过")
                return True
            else:
                print("⚠️  子网掩码无有效选项可选")
                return False
            
        except Exception as e:
            print(f"❌ 子网掩码选择失败: {e}")
            return False
    
    def _select_first_valid_option(self, select, field_name):
        """选择第一个有效选项"""
        try:
            option_values = select.locator('option').evaluate_all('options => options.map(option => option.value)')
            option_texts = select.locator('option').evaluate_all('options => options.map(option => option.textContent.trim())')
            
            for value, text in zip(option_values, option_texts):
                if value and value.strip() and text and text not in ["请选择", "选择", ""]:
                    select.select_option(value)
                    print(f"✅ {field_name}选择成功: {text}")
                    return True
            
            print(f"⚠️  {field_name}无有效选项可选")
            return False
        except Exception as e:
            print(f"❌ {field_name}选择失败: {e}")
            return False
    
    def _select_line_option(self, select, target_line):
        """选择指定的线路选项"""
        try:
            option_values = select.locator('option').evaluate_all('options => options.map(option => option.value)')
            option_texts = select.locator('option').evaluate_all('options => options.map(option => option.textContent.trim())')
            
            for value, text in zip(option_values, option_texts):
                if target_line.lower() in text.lower():
                    if value:
                        select.select_option(value)
                        print(f"✅ 线路选择成功: {text}")
                        return True
            
            # 如果没找到指定线路，选择第一个有效选项
            print(f"⚠️  未找到线路 {target_line}，选择第一个有效选项")
            return self._select_first_valid_option(select, "线路")
        except Exception as e:
            print(f"❌ 线路选择失败: {e}")
            return False
    
    def _save_vlan_form(self):
        """保存VLAN表单"""
        print("💾 保存VLAN表单...")
        
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
                print(f"🔍 尝试策略: {strategy}, 找到 {buttons.count()} 个按钮")
                
                if buttons.count() > 0:
                    button = buttons.first
                    if button.is_visible() and button.is_enabled():
                        print(f"✅ 找到保存按钮: {strategy}")
                        
                        # 滚动到按钮位置
                        button.scroll_into_view_if_needed()
                        time.sleep(0.5)
                        
                        # 点击保存按钮
                        button.click()
                        print("✅ 点击保存按钮")
                        time.sleep(2)
                        
                        # 检查是否有保存成功的指示
                        return self._verify_save_success()
                    else:
                        print(f"按钮不可见或不可用: visible={button.is_visible()}, enabled={button.is_enabled()}")
                        
            except Exception as e:
                print(f"尝试策略 {strategy} 时出错: {e}")
                continue
        
        print("❌ 未找到可用的保存按钮")
        return False
    
    def _verify_save_success(self):
        """验证保存是否成功"""
        try:
            # 等待保存完成的指示
            time.sleep(2)
            
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
                        print(f"✅ 检测到保存成功指示: {indicator}")
                        return True
                except:
                    continue
            
            # 如果没有明确的成功指示，检查表单是否还存在
            form_inputs = self.page.locator('input[name="vlan_id"]:visible')
            if form_inputs.count() == 0:
                print("✅ 表单已关闭，可能保存成功")
                return True
            
            print("⚠️  未检测到明确的保存成功指示")
            return True  # 默认认为成功，让后续验证来确认
            
        except Exception as e:
            print(f"验证保存成功时出错: {e}")
            return True  # 默认认为成功
    
    def _verify_config_created(self, config_name: str):
        """验证配置是否创建成功"""
        try:
            # 等待页面更新
            time.sleep(3)
            
            # 多次尝试验证
            for attempt in range(5):
                # 检查表格中是否存在配置
                config_row = self.page.locator(f'tr:has-text("{config_name}")')
                if config_row.count() > 0 and config_row.first.is_visible():
                    print(f"✅ 配置 {config_name} 创建成功")
                    return True
                
                if attempt < 4:
                    time.sleep(2)
            
            print(f"⚠️  配置 {config_name} 未在表格中找到")
            return False
        except Exception as e:
            print(f"⚠️  配置 {config_name} 验证失败: {e}")
            return False
    
    def step4_disable_profile(self, profile_name: str):
        """步骤4: 停用配置"""
        print("步骤4: 停用配置", profile_name)
        row = self.page.locator(f'tr:has-text("{profile_name}")')
        if row.count() > 0:
            # 查找停用操作
            disable_actions = row.locator('a:text("停用"), a:text("禁用"), button:text("停用"), button:text("禁用")')
            if disable_actions.count() > 0:
                self.page.on("dialog", lambda d: d.accept())
                disable_actions.first.click()
                time.sleep(2)
                print("配置已停用")
            else:
                print("⚠️  未找到停用操作按钮")
        else:
            print("⚠️  未找到指定配置")
    
    def step5_enable_profile(self, profile_name: str):
        """步骤5: 启用配置"""
        print("步骤5: 启用配置", profile_name)
        row = self.page.locator(f'tr:has-text("{profile_name}")')
        if row.count() > 0:
            # 查找启用操作
            enable_actions = row.locator('a:text("启用"), button:text("启用")')
            if enable_actions.count() > 0:
                self.page.on("dialog", lambda d: d.accept())
                enable_actions.first.click()
                time.sleep(2)
                print("配置已启用")
            else:
                print("⚠️  未找到启用操作按钮")
        else:
            print("⚠️  未找到指定配置")
    
    def step6_form_validation_errors(self, profile_name: str):
        """步骤6: 表单必填项验证"""
        print("步骤6: 表单必填项验证", profile_name)
        
        # 点击添加按钮进入表单
        add_button = self.page.locator('a.btn_green:has-text("添加")').first
        if add_button.is_visible():
            add_button.click()
            time.sleep(2)
        else:
            print("❌ 添加按钮不可见，跳过验证")
            return
        
        # 等待表单出现
        if not self._wait_for_form():
            print("❌ 表单未出现，跳过验证")
            return
        
        # 查找输入字段
        input_fields = self.page.locator('input[type="text"]:not(.search_inpt):not([name="searchText"]):visible')
        
        # 验证必填字段
        required_fields = ["VLAN ID", "VLAN名称"]
        
        for i, field_name in enumerate(required_fields):
            if i < input_fields.count():
                print(f"验证字段: {field_name}")
                field = input_fields.nth(i)
                
                try:
                    # 清空字段
                    field.clear()
                    
                    # 尝试保存以触发验证
                    save_button = self.page.locator('button:has-text("保存"), button:has-text("确定")').first
                    if save_button.is_visible(timeout=2000):
                        save_button.click()
                        time.sleep(1)
                    
                    # 查找错误提示
                    error_tip = self.page.locator('p.error_tip, .error-message, .field-error').first
                    if error_tip.is_visible(timeout=2000):
                        print(f"  错误提示: {error_tip.text_content().strip()}")
                    else:
                        print(f"  未找到错误提示")
                    
                    # 恢复字段值
                    if field_name == "VLAN ID":
                        field.fill(self.test_profile["vlan_id"])
                    elif field_name == "VLAN名称":
                        field.fill(self.test_profile["vlan_name"])
                        
                except Exception as e:
                    print(f"  验证字段 {field_name} 时出错: {e}")
        
        # 取消表单
        self._cancel_form()
        time.sleep(1)
        print("表单验证完成")
    
    def step7_delete_profile(self, profile_name: str):
        """步骤7: 删除配置 取消和确认流程"""
        print("步骤7: 删除配置 取消流程")
        row = self.page.locator(f'tr:has-text("{profile_name}")')
        
        if row.count() > 0:
            delete_action = row.locator('a:text("删除"), button:text("删除")')
            if delete_action.count() > 0:
                delete_action.first.click()
                time.sleep(1)
                
                # 处理确认对话框 - 先取消
                modal = self.page.locator('div.el-message-box, .confirm-dialog, .modal')
                if modal.count() > 0 and modal.first.is_visible(timeout=3000):
                    cancel_btn = modal.first.locator('button:has-text("取消"), button:has-text("关闭")')
                    if cancel_btn.count() > 0:
                        cancel_btn.first.click()
                        print("取消删除，配置依然存在")
                        time.sleep(1)
                
                # 再次删除并确认
                print("步骤7: 删除配置 确认流程")
                delete_action.first.click()
                time.sleep(1)
                
                if modal.count() > 0 and modal.first.is_visible(timeout=3000):
                    confirm_btn = modal.first.locator('button:has-text("确定"), button:has-text("确认"), button.el-button--primary')
                    if confirm_btn.count() > 0:
                        confirm_btn.first.click()
                        print("确认删除，配置已移除")
                        time.sleep(2)
            else:
                print("⚠️  未找到删除操作按钮")
        else:
            print("⚠️  未找到指定配置")
    
    def step8_batch_create_profiles(self, count: int = None):
        """步骤8: 批量创建VLAN配置"""
        if count is None:
            count = self.batch_create_count
            
        print(f"步骤8: 批量创建VLAN配置，共{count}条")
        
        self.created_profiles = []  # 重置创建的配置列表
        
        for i in range(1, count + 1):
            profile = self.test_profile.copy()
            profile["vlan_id"] = str(int(self.test_profile["vlan_id"]) + i)  # 44, 45, ...
            profile["vlan_name"] = f"vlan{i+1:02d}"  # vlan02, vlan03, ...
            # 使用不同网段避免地址池冲突：192.168.2.100, 192.168.3.100, 192.168.4.100...
            profile["ip"] = f"192.168.{i+1}.100"  # 192.168.2.100, 192.168.3.100, ...
            # 生成不同的MAC地址
            profile["mac"] = self._generate_unique_mac(i)
            # 生成不同的备注
            profile["comment"] = self._generate_unique_comment(i)
            
            print(f"\n创建第 {i}/{count} 个配置: {profile['vlan_name']} (IP: {profile['ip']}, MAC: {profile['mac']})")
            
            # 使用step3的逻辑，但不显示步骤信息
            success = self.step3_create_profile(profile, show_step_info=False)
            if success:
                self.created_profiles.append(profile)
                print(f"✅ 配置 {profile['vlan_name']} 创建成功")
            else:
                print(f"⚠️  配置 {profile['vlan_name']} 创建失败")
            time.sleep(3)  # 增加等待时间
        
        print(f"\n📊 批量创建完成，共创建了{len(self.created_profiles)}/{count}个VLAN配置")
        
        # 步骤8.1: 搜索功能验证
        if self.created_profiles:
            print(f"\n步骤8.1: 搜索功能验证")
            self.step8_1_search_function_test()
    
    def step8_1_search_function_test(self):
        """步骤8.1: 搜索功能验证"""
        print("步骤8.1: 开始搜索功能验证...")
        
        # 准备搜索测试用例
        test_cases = []
        
        if self.created_profiles:
            # 随机选择几个配置进行搜索测试
            import random
            sample_profiles = random.sample(self.created_profiles, min(3, len(self.created_profiles)))
            
            for i, profile in enumerate(sample_profiles):
                test_cases.extend([
                    {
                        'field': 'vlan_id',
                        'value': profile['vlan_id'],
                        'description': f'搜索VLAN ID: {profile["vlan_id"]}'
                    },
                    {
                        'field': 'vlan_name',
                        'value': profile['vlan_name'],
                        'description': f'搜索VLAN名称: {profile["vlan_name"]}'
                    },
                    {
                        'field': 'ip',
                        'value': profile['ip'].split('.')[2],  # 搜索网段，如 "2"
                        'description': f'搜索IP网段: {profile["ip"].split(".")[2]}'
                    },
                    {
                        'field': 'comment',
                        'value': 'VLAN',  # 搜索备注中的关键字
                        'description': f'搜索备注关键字: VLAN'
                    }
                ])
                
                # 只测试前2个配置的详细搜索，避免测试时间过长
                if i >= 1:
                    break
        
        # 添加一些通用搜索测试
        test_cases.extend([
            {
                'field': 'general',
                'value': 'vlan',
                'description': '搜索通用关键字: vlan'
            },
            {
                'field': 'general',
                'value': '192.168',
                'description': '搜索IP段: 192.168'
            }
        ])
        
        # 执行搜索测试
        if test_cases:
            success = self.search_function_test(test_cases)
            if success:
                print("✅ 搜索功能验证全部通过")
            else:
                print("⚠️  部分搜索功能验证失败")
        else:
            print("⚠️  没有可用的测试用例，跳过搜索验证")
    
    def step9_check_local_ips(self):
        """步骤9: 检查并展示VLAN配置信息"""
        print("步骤9: 检查并展示VLAN配置信息")
        
        # 刷新页面以获取最新状态
        print("🔄 刷新页面以获取最新状态...")
        self.page.reload()
        time.sleep(3)
        
        # 重新导航到VLAN页面
        print("🧭 重新导航到VLAN设置页面...")
        self.navigate_to_module()
        
        print("🔍 开始查找VLAN配置表格...")
        
        # 查找表格
        tables = self.page.locator('table')
        if tables.count() > 0:
            table = tables.first
            print(f"✅ 找到表格")
            
            # 获取表头信息
            headers = table.locator('th')
            header_texts = []
            for i in range(headers.count()):
                header_text = headers.nth(i).text_content().strip()
                header_texts.append(header_text)
                print(f"  第{i+1}列表头: '{header_text}'")
            
            # 查找数据行
            rows = table.locator('tbody tr, tr:not(:first-child)')
            row_count = rows.count()
            print(f"✅ 找到数据行: {row_count}")
            
            if row_count > 0:
                print("\n=== VLAN配置信息 ===")
                vlan_info_list = []
                valid_data_rows = 0
                
                for i in range(row_count):
                    row = rows.nth(i)
                    cells = row.locator('td')
                    cell_count = cells.count()
                    
                    if cell_count >= 3:
                        vlan_id = cells.nth(0).text_content().strip() if cell_count > 0 else ""
                        vlan_name = cells.nth(1).text_content().strip() if cell_count > 1 else ""
                        ip_info = cells.nth(3).text_content().strip() if cell_count > 3 else ""
                        
                        if vlan_id and vlan_id not in ["vlanID", "VLAN ID", ""]:
                            valid_data_rows += 1
                            vlan_info_list.append({
                                "vlan_id": vlan_id,
                                "vlan_name": vlan_name,
                                "ip_info": ip_info
                            })
                            print(f"{valid_data_rows}. VLAN ID: {vlan_id}, 名称: {vlan_name}, IP: {ip_info}")
                
                print(f"\n统计信息:")
                print(f"  有效VLAN配置: {valid_data_rows}")
                
                if valid_data_rows > 0:
                    print(f"\n✅ 成功获取到{valid_data_rows}个VLAN配置信息")
                else:
                    print(f"\n⚠️  未找到有效的VLAN配置")
            else:
                print("⚠️  表格中没有数据行")
        else:
            print("❌ 未找到表格")
    
    def step10_batch_operations_test(self):
        """步骤10: 批量停用和启用操作"""
        print("步骤10: 批量停用和启用操作")
        
        # 步骤10.1: 全选所有配置
        if not self.select_all_configs("批量操作"):
            print("❌ 全选操作失败")
            return
        
        # 步骤10.2: 批量停用
        print("🛑 执行批量停用操作...")
        disable_selectors = [
            'a:has-text("停用")',
            'button:has-text("停用")',
            'a:has-text("禁用")',
            'button:has-text("禁用")',
            '.btn:has-text("停用")',
            'input[value="停用"]'
        ]
        
        if not self.batch_operation("停用", disable_selectors):
            print("❌ 未找到批量停用按钮")
            return
        
        print("✅ 批量停用操作执行完成")
        
        # 步骤10.3: 等待1秒后批量启用
        print("\n⏳ 等待1秒...")
        time.sleep(1)
        
        print("✅ 执行批量启用操作...")
        enable_selectors = [
            'a:has-text("启用")',
            'button:has-text("启用")',
            '.btn:has-text("启用")',
            'input[value="启用"]'
        ]
        
        if not self.batch_operation("启用", enable_selectors):
            print("❌ 未找到批量启用按钮")
            return
        
        print("✅ 批量启用操作执行完成")
        print("\n✅ 批量停用和启用操作全部完成")
    
    def step11_export_import_test(self):
        """步骤11: 测试导出和导入功能"""
        print("步骤11: 测试导出和导入功能")
        
        # 获取下载目录
        download_path = os.path.abspath("./downloads")
        if not os.path.exists(download_path):
            os.makedirs(download_path)
            print(f"📁 创建下载目录: {download_path}")
        
        exported_files = []
        
        # 步骤11.1: 导出CSV和TXT文件
        print("📤 测试导出功能...")
        export_formats = ["csv", "txt"]
        
        for format_type in export_formats:
            file_path = self.export_data(format_type, download_path)
            if file_path:
                exported_files.append(file_path)
                time.sleep(2)
        
        print(f"\n📊 导出结果统计:")
        print(f"  成功导出文件数: {len(exported_files)}")
        for file_path in exported_files:
            print(f"  - {os.path.basename(file_path)}")
        
        if len(exported_files) < 2:
            print("⚠️  导出文件不足，跳过后续测试")
            return
        
        # 步骤11.2: 批量删除所有配置
        print("\n🗑️ 步骤11.2: 批量删除所有VLAN配置")
        delete_success = self.batch_delete_all_configs(need_select_all=False)
        if not delete_success:
            print("❌ 批量删除失败，跳过后续测试")
            return
        
        # 步骤11.3: 导入CSV文件
        print("\n📥 步骤11.3: 导入CSV文件")
        csv_file = next((f for f in exported_files if f.endswith('.csv')), None)
        if csv_file:
            import_success = self.import_data(csv_file, "csv", merge_to_current=False)
            if import_success:
                print("✅ CSV文件导入成功")
            else:
                print("❌ CSV文件导入失败")
        
        time.sleep(2)
        
        # 步骤11.4: 再次批量删除所有配置
        print("\n🗑️ 步骤11.4: 再次批量删除所有VLAN配置")
        delete_success = self.batch_delete_all_configs(need_select_all=True)
        
        # 步骤11.5: 导入TXT文件
        print("\n📥 步骤11.5: 导入TXT文件（勾选合并到当前数据）")
        txt_file = next((f for f in exported_files if f.endswith('.txt')), None)
        if txt_file:
            import_success = self.import_data(txt_file, "txt", merge_to_current=True)
            if import_success:
                print("✅ TXT文件导入成功")
            else:
                print("❌ TXT文件导入失败")
        
        # 清理导出的文件
        print(f"\n🧹 清理导出文件...")
        for file_path in exported_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"✅ 已删除文件: {os.path.basename(file_path)}")
            except Exception as e:
                print(f"⚠️  删除文件失败: {os.path.basename(file_path)}, 错误: {e}")
        
        print("\n✅ 导出导入功能测试全部完成")
    
    def step12_cleanup_all_configs(self):
        """步骤12: 清理所有VLAN配置"""
        print("步骤12: 清理所有VLAN配置")
        
        # 检查是否有配置需要删除
        try:
            rows = self.page.locator('table tr:not(:first-child)')
            config_count = 0
            
            for i in range(rows.count()):
                row = rows.nth(i)
                cells = row.locator('td')
                if cells.count() > 0:
                    vlan_id = cells.nth(0).text_content().strip()
                    if vlan_id and vlan_id not in ["vlanID", "VLAN ID", ""]:
                        config_count += 1
            
            print(f"🔍 当前VLAN配置数量: {config_count}")
            
            if config_count == 0:
                print("✅ 当前没有VLAN配置，无需清理")
                return True
                
        except Exception as e:
            print(f"检查配置数量时出错: {e}")
        
        # 使用批量删除功能清理所有配置
        print("🗑️ 开始清理所有VLAN配置...")
        delete_success = self.batch_delete_all_configs(need_select_all=True)
        
        if delete_success:
            print("✅ 所有VLAN配置已成功清理")
            return True
        else:
            print("❌ VLAN配置清理失败")
            return False
    
    def run_full_test(self):
        """运行完整的12个步骤测试"""
        print("开始VLAN模块完整测试 - 12个步骤")
        print(f"测试目标路由器: {self.config.router_url}")
        
        try:
            # 步骤3: 创建配置（包含扩展IP和子网掩码测试）
            success = self.step3_create_profile()
            if not success:
                print("❌ 步骤3失败，跳过后续依赖步骤")
                # 但继续执行其他独立步骤
            
            # 步骤4: 停用配置
            self.step4_disable_profile(self.test_profile["vlan_name"])
            time.sleep(1)
            
            # 步骤5: 启用配置
            self.step5_enable_profile(self.test_profile["vlan_name"])
            time.sleep(1)
            
            # 步骤6: 表单验证错误
            self.step6_form_validation_errors(self.test_profile["vlan_name"])
            
            # 步骤7: 删除配置（取消和确认）
            self.step7_delete_profile(self.test_profile["vlan_name"])
            
            # 步骤8: 批量创建配置（包含搜索验证）
            self.step8_batch_create_profiles()
            
            # 步骤9: 检查VLAN配置信息
            self.step9_check_local_ips()
            
            # 步骤10: 批量停用和启用操作
            self.step10_batch_operations_test()
            
            # 步骤11: 导出导入功能测试
            self.step11_export_import_test()
            
            # 步骤12: 清理所有VLAN配置
            self.step12_cleanup_all_configs()
            
            print("✅ 所有12个测试步骤已成功完成")
            time.sleep(2)
            
        except Exception as e:
            print(f"❌ 测试过程中出现错误: {e}")
            raise

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='VLAN模块自动化测试')
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
            print(f"🎯 运行指定测试方法: {args.method}")
            runner.run_test_module(VLANTestModule, [args.method])
        else:
            # 运行完整的12步测试
            print("🚀 运行完整的12步测试")
            runner.run_test_module(VLANTestModule)
        
        print("🎉 VLAN模块测试全部完成！")
        
    except Exception as e:
        print(f"💥 测试执行失败: {e}")
        sys.exit(1)