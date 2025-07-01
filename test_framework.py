# -*- coding: utf-8 -*-
from playwright.sync_api import sync_playwright, expect, Page
import time, os, json, re
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
import requests
from urllib.parse import parse_qs, urlparse

class RouterTestConfig:
    """路由器测试配置类"""
    def __init__(self, 
                 router_url: str = "http://10.66.0.40/login#/login",
                 username: str = "admin", 
                 password: str = "admin123",
                 ssh_user: str = "sshd",
                 ssh_pass: str = "ikuai8.com"):
        self.router_url = router_url
        self.username = username
        self.password = password
        self.ssh_user = ssh_user
        self.ssh_pass = ssh_pass

class BaseTestModule(ABC):
    """基础测试模块抽象类"""
    
    def __init__(self, config: RouterTestConfig):
        self.config = config
        self.page: Optional[Page] = None
        
    def setup(self, page: Page):
        """设置页面对象"""
        self.page = page
        
    @abstractmethod
    def get_module_info(self) -> Dict:
        """获取模块信息"""
        pass
        
    @abstractmethod
    def navigate_to_module(self):
        """导航到模块页面"""
        pass
        
    def login(self):
        """通用登录功能"""
        print(f"步骤1: 登录")
        self.page.goto(self.config.router_url)
        self.page.get_by_placeholder("用户名").fill(self.config.username)
        self.page.get_by_placeholder("密码").fill(self.config.password)
        self.page.get_by_role("button", name="登录").click()
        expect(self.page.locator('a:has-text("系统概况")')).to_be_visible(timeout=10000)
        print("登录成功")

class TableOperationsMixin:
    """表格操作混入类"""
    
    def select_all_configs(self, operation_name: str = "操作") -> bool:
        """通用的全选配置功能"""
        print(f"🔲 点击表头全选框，选中所有配置...")
        
        select_all_found = False
        
        # 方法1：直接点击表头最后一列的复选框
        try:
            last_header_checkbox = self.page.locator('th:last-child input[type="checkbox"]').first
            if last_header_checkbox.is_visible():
                last_header_checkbox.scroll_into_view_if_needed()
                last_header_checkbox.click()
                print("✅ 成功点击表头最后一列的全选框")
                select_all_found = True
        except Exception as e:
            print(f"方法1失败: {e}")
        
        # 方法2：使用chk_all类名
        if not select_all_found:
            try:
                chk_all = self.page.locator('input.chk_all').first
                if chk_all.is_visible():
                    chk_all.scroll_into_view_if_needed()
                    chk_all.click()
                    print("✅ 成功点击chk_all全选框")
                    select_all_found = True
            except Exception as e:
                print(f"方法2失败: {e}")
        
        # 方法3：备用方案
        if not select_all_found:
            try:
                last_header = self.page.locator('thead th:last-child, tr:first-child th:last-child').first
                if last_header.is_visible():
                    clickable_elements = last_header.locator('input, label, span').all()
                    for elem in clickable_elements:
                        try:
                            if elem.is_visible():
                                elem.click()
                                print("✅ 备用方案成功：点击了表头最后一列的元素")
                                select_all_found = True
                                break
                        except:
                            continue
            except Exception as e:
                print(f"备用方案失败: {e}")
        
        if not select_all_found:
            print(f"❌ 无法找到全选框，跳过{operation_name}")
            return False
        
        time.sleep(1)
        print("✅ 全选操作完成")
        return True
    
    def batch_operation(self, operation_type: str, button_selectors: List[str]) -> bool:
        """通用批量操作"""
        print(f"🔄 执行批量{operation_type}操作...")
        
        operation_button_found = False
        for selector in button_selectors:
            try:
                buttons = self.page.locator(selector)
                for i in range(buttons.count()):
                    button = buttons.nth(i)
                    if button.is_visible():
                        button.scroll_into_view_if_needed()
                        button.click()
                        print(f"✅ 成功点击批量{operation_type}按钮")
                        operation_button_found = True
                        break
                if operation_button_found:
                    break
            except Exception as e:
                continue
        
        if not operation_button_found:
            print(f"❌ 未找到批量{operation_type}按钮")
            return False
            
        time.sleep(2)
        print(f"✅ 批量{operation_type}操作执行完成")
        return True
    
    def batch_delete_all_configs(self, need_select_all: bool = True) -> bool:
        """批量删除所有配置"""
        print("🗑️ 执行批量删除所有配置...")
        
        if need_select_all:
            if not self.select_all_configs("批量删除"):
                return False
        else:
            print("🔲 全选框已选中，跳过全选步骤")
        
        # 点击删除按钮
        delete_selectors = [
            'a:has-text("删除")',
            'button:has-text("删除")',
            '.btn:has-text("删除")',
            'input[value="删除"]'
        ]
        
        if not self.batch_operation("删除", delete_selectors):
            return False
        
        # 处理确认弹窗
        time.sleep(1)
        try:
            confirm_modal_selectors = [
                'div.el-message-box',
                '.confirm-dialog',
                '.modal',
                '[role="dialog"]'
            ]
            
            modal_found = False
            for selector in confirm_modal_selectors:
                modals = self.page.locator(selector)
                if modals.count() > 0:
                    modal = modals.first
                    if modal.is_visible():
                        print(f"✅ 找到确认弹窗")
                        
                        confirm_selectors = [
                            'button:has-text("确定")',
                            'button:has-text("删除")',
                            'button.el-button--primary',
                            '.btn-primary'
                        ]
                        
                        for confirm_selector in confirm_selectors:
                            confirm_buttons = modal.locator(confirm_selector)
                            if confirm_buttons.count() > 0:
                                confirm_button = confirm_buttons.first
                                if confirm_button.is_visible():
                                    print(f"✅ 找到确定按钮")
                                    confirm_button.click()
                                    print(f"✅ 点击确定删除按钮")
                                    modal_found = True
                                    break
                        if modal_found:
                            break
            
            if not modal_found:
                print("❌ 未找到确认弹窗")
                return False
                
        except Exception as e:
            print(f"处理确认弹窗时出错: {e}")
            return False
        
        time.sleep(3)
        print("✅ 批量删除操作执行完成")
        
        # 检查删除结果
        try:
            rows = self.page.locator('table tr:not(:first-child)')
            row_count = 0
            
            for i in range(rows.count()):
                row = rows.nth(i)
                cells = row.locator('td')
                if cells.count() > 0:
                    config_name = cells.nth(0).text_content().strip()
                    if config_name and config_name not in ["拨号名称", "配置名称", "vlanID", "VLAN ID", ""]:
                        row_count += 1
            
            print(f"🔍 删除后剩余配置数量: {row_count}")
            
            if row_count == 0:
                print("✅ 所有配置已成功删除")
                return True
            else:
                print(f"⚠️  仍有 {row_count} 个配置未删除")
                return False
                
        except Exception as e:
            print(f"检查删除结果时出错: {e}")
            return False

class SearchOperationsMixin:
    """搜索操作混入类"""
    
    def search_function_test(self, test_cases: List[Dict[str, str]], clear_after_each: bool = True):
        """通用搜索功能测试
        
        Args:
            test_cases: 搜索测试用例列表，每个用例包含 {'field': '字段名', 'value': '搜索值', 'description': '描述'}
            clear_after_each: 每次搜索后是否清空搜索框
        """
        print("🔍 开始搜索功能验证...")
        
        # 查找搜索框
        search_input = self._find_search_input()
        if not search_input:
            print("❌ 未找到搜索框，跳过搜索测试")
            return False
        
        all_passed = True
        
        for i, test_case in enumerate(test_cases, 1):
            field = test_case.get('field', '')
            value = test_case.get('value', '')
            description = test_case.get('description', f'测试用例{i}')
            
            print(f"\n🔍 搜索测试 {i}/{len(test_cases)}: {description}")
            print(f"   搜索字段: {field}, 搜索值: {value}")
            
            # 执行搜索
            search_result = self._perform_search(search_input, value)
            
            if search_result:
                # 验证搜索结果
                valid_results = self._verify_search_results(value, field)
                if valid_results:
                    print(f"✅ 搜索测试通过: 找到包含 '{value}' 的结果")
                else:
                    print(f"❌ 搜索测试失败: 结果中未找到包含 '{value}' 的内容")
                    all_passed = False
            else:
                print(f"❌ 搜索操作失败")
                all_passed = False
            
            # 清空搜索框（如果需要）
            if clear_after_each and i < len(test_cases):
                self._clear_search(search_input)
                time.sleep(1)
        
        # 最后清空搜索框，显示所有结果
        print(f"\n🧹 清空搜索框，显示所有结果...")
        self._clear_search(search_input)
        time.sleep(2)
        
        if all_passed:
            print("✅ 所有搜索测试都通过")
        else:
            print("⚠️  部分搜索测试失败")
        
        return all_passed
    
    def _find_search_input(self):
        """查找搜索输入框"""
        search_selectors = [
            'input[placeholder*="搜索"]',
            'input[placeholder*="查找"]',
            'input.search_inpt',
            'input[name="searchText"]',
            'input[type="text"].search',
            '.search input[type="text"]',
            '.search-box input',
            'input[class*="search"]'
        ]
        
        for selector in search_selectors:
            try:
                inputs = self.page.locator(selector)
                if inputs.count() > 0:
                    search_input = inputs.first
                    if search_input.is_visible():
                        print(f"✅ 找到搜索框: {selector}")
                        return search_input
            except Exception as e:
                continue
        
        print("❌ 未找到搜索输入框")
        return None
    
    def _perform_search(self, search_input, search_value: str) -> bool:
        """执行搜索操作"""
        try:
            # 清空并输入搜索值
            search_input.clear()
            search_input.fill(search_value)
            
            # 尝试触发搜索 - 按回车键
            search_input.press('Enter')
            time.sleep(2)
            
            # 如果按回车没有效果，尝试查找搜索按钮
            search_button_selectors = [
                'button:has-text("搜索")',
                'button:has-text("查找")',
                'input[value="搜索"]',
                '.search-btn',
                '.search_icon',
                'button[type="submit"]'
            ]
            
            for selector in search_button_selectors:
                try:
                    buttons = self.page.locator(selector)
                    if buttons.count() > 0:
                        button = buttons.first
                        if button.is_visible():
                            button.click()
                            print(f"✅ 点击搜索按钮")
                            break
                except:
                    continue
            
            time.sleep(2)
            return True
            
        except Exception as e:
            print(f"❌ 搜索操作失败: {e}")
            return False
    
    def _verify_search_results(self, search_value: str, target_field: str = "") -> bool:
        """验证搜索结果"""
        try:
            # 查找表格行
            table_rows = self.page.locator('table tr:not(:first-child)')
            
            if table_rows.count() == 0:
                print(f"⚠️  搜索结果为空")
                return False
            
            found_matching_results = False
            
            # 检查每一行是否包含搜索值
            for i in range(table_rows.count()):
                row = table_rows.nth(i)
                row_text = row.text_content().strip()
                
                # 跳过空行或提示行
                if not row_text or "暂无数据" in row_text or "没有找到" in row_text:
                    continue
                
                # 检查行内容是否包含搜索值
                if search_value.lower() in row_text.lower():
                    found_matching_results = True
                    print(f"   ✓ 找到匹配行: {row_text[:100]}...")
                else:
                    # 如果有不匹配的行，可能搜索有问题
                    print(f"   ⚠️  发现不匹配行: {row_text[:100]}...")
            
            return found_matching_results
            
        except Exception as e:
            print(f"❌ 验证搜索结果时出错: {e}")
            return False
    
    def _clear_search(self, search_input):
        """清空搜索框"""
        try:
            search_input.clear()
            search_input.press('Enter')
            print("🧹 已清空搜索框")
        except Exception as e:
            print(f"❌ 清空搜索框失败: {e}")

class FormOperationsMixin:
    """表单操作混入类"""
    
    def fill_form_field(self, field_selector: str, value: str, field_name: str = ""):
        """填写表单字段"""
        try:
            field = self.page.locator(field_selector).first
            expect(field).to_be_visible(timeout=5000)
            field.fill(value)
            if field_name:
                print(f"{field_name}填写: {value}")
        except Exception as e:
            print(f"填写字段 {field_name} 失败: {e}")
            raise
    
    def select_option(self, select_selector: str, option_value: str, field_name: str = ""):
        """选择下拉框选项"""
        try:
            select = self.page.locator(select_selector).first
            expect(select).to_be_visible(timeout=5000)
            select.select_option(option_value)
            if field_name:
                print(f"{field_name}选择: {option_value}")
        except Exception as e:
            print(f"选择 {field_name} 失败: {e}")
            raise
    
    def click_checkbox(self, checkbox_selector: str, field_name: str = ""):
        """点击复选框"""
        try:
            checkbox = self.page.locator(checkbox_selector).first
            expect(checkbox).to_be_visible(timeout=5000)
            checkbox.click()
            if field_name:
                print(f"{field_name}已点击")
        except Exception as e:
            print(f"点击 {field_name} 失败: {e}")
            raise
    
    def save_form(self, save_button_text: str = "保存"):
        """保存表单"""
        try:
            save_button = self.page.get_by_role("button", name=save_button_text)
            save_button.click()
            print(f"表单已保存")
        except Exception as e:
            print(f"保存表单失败: {e}")
            raise

class ImportExportMixin:
    """导入导出操作混入类"""
    
    def get_cookies_from_page(self):
        """从页面获取cookies"""
        cookies = self.page.context.cookies()
        return {cookie['name']: cookie['value'] for cookie in cookies}

    def get_filename_from_headers(self, headers):
        """从响应头中提取文件名"""
        content_disposition = headers.get('Content-Disposition', '')
        if content_disposition:
            match = re.search(r'filename="([^"]+)"', content_disposition)
            if match:
                return match.group(1)
        return None
    
    def get_filename_from_url(self, url):
        """从URL中提取文件名"""
        try:
            parsed_url = urlparse(url)
            params = parse_qs(parsed_url.query)
            if 'filename' in params:
                return params['filename'][0]
        except Exception as e:
            print(f"从URL提取文件名时出错: {e}")
        return None
    
    def export_data(self, format_type: str, download_path: str) -> Optional[str]:
        """导出数据"""
        print(f"🔹 导出{format_type.upper()}格式...")
        
        try:
            # 记录导出请求
            export_requests = []
            download_requests = []
            actual_filename = None
            
            def handle_request(request):
                try:
                    if "/Action/call" in request.url and request.post_data:
                        post_data = request.post_data
                        if "EXPORT" in post_data:
                            export_requests.append({
                                "url": request.url,
                                "data": post_data
                            })
                            print(f"🔍 捕获到导出API请求: {request.url}")
                    elif "/Action/download" in request.url:
                        # 从URL中提取实际的文件名
                        filename = self.get_filename_from_url(request.url)
                        if filename:
                            nonlocal actual_filename
                            actual_filename = filename
                        download_requests.append({
                            "url": request.url,
                            "filename": filename
                        })
                        print(f"🔍 捕获到下载请求: {request.url}")
                        if filename:
                            print(f"🔍 提取到实际文件名: {filename}")
                except Exception as e:
                    print(f"⚠️  处理请求时出错: {e}")
                    
            # 添加请求监听器
            self.page.on("request", handle_request)
            
            # 查找并点击导出按钮
            export_button_selectors = [
                'a:has-text("导出")',
                'button:has-text("导出")',
                '.btn:has-text("导出")',
                'input[value="导出"]'
            ]
            
            export_button_found = False
            for selector in export_button_selectors:
                export_buttons = self.page.locator(selector)
                if export_buttons.count() > 0:
                    export_button = export_buttons.first
                    if export_button.is_visible():
                        print(f"✅ 找到可见的导出按钮")
                        export_button.scroll_into_view_if_needed()
                        export_button.click()
                        export_button_found = True
                        break
            
            if not export_button_found:
                print(f"❌ 未找到导出按钮")
                self.page.remove_listener("request", handle_request)
                return None
            
            # 等待下拉菜单
            time.sleep(1)
            
            # 选择格式
            format_option_selectors = [
                f'a:has-text("{format_type.upper()}")',
                f'li:has-text("{format_type.upper()}")',
                f'[data-format="{format_type}"]'
            ]
            
            format_option_found = False
            for selector in format_option_selectors:
                format_options = self.page.locator(selector)
                if format_options.count() > 0:
                    format_option = format_options.first
                    if format_option.is_visible():
                        print(f"✅ 找到{format_type.upper()}选项")
                        format_option.click()
                        format_option_found = True
                        break
            
            if not format_option_found:
                print(f"❌ 未找到{format_type.upper()}选项")
                self.page.remove_listener("request", handle_request)
                return None
            
            # 等待API请求
            time.sleep(3)
            
            # 移除监听器
            self.page.remove_listener("request", handle_request)
            
            # 使用requests下载文件
            if export_requests or download_requests:
                cookies = self.get_cookies_from_page()
                
                # 构造下载URL - 使用实际捕获到的文件名或默认文件名
                base_url = self.config.router_url.replace('/login#/login', '')
                
                if actual_filename:
                    download_url = f"{base_url}/Action/download?filename={actual_filename}"
                    expected_filename = actual_filename
                else:
                    # 尝试常见的文件名模式
                    possible_filenames = [
                        f"vlan_config.{format_type}",
                        f"pptp_client.{format_type}",
                        f"export.{format_type}"
                    ]
                    expected_filename = possible_filenames[0]
                    download_url = f"{base_url}/Action/download?filename={expected_filename}"
                
                headers = {
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'zh-CN,zh;q=0.9',
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'Pragma': 'no-cache',
                    'Referer': base_url + '/',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                response = requests.get(download_url, headers=headers, cookies=cookies, verify=False, timeout=10)
                
                if response.status_code == 200:
                    # 优先使用响应头中的文件名
                    real_filename = self.get_filename_from_headers(dict(response.headers))
                    
                    if real_filename:
                        final_filename = real_filename
                    elif actual_filename:
                        final_filename = actual_filename
                    else:
                        final_filename = expected_filename
                    
                    file_path = os.path.join(download_path, final_filename)
                    
                    with open(file_path, 'wb') as f:
                        f.write(response.content)
                    
                    if os.path.exists(file_path):
                        file_size = os.path.getsize(file_path)
                        print(f"✅ {format_type.upper()}格式导出成功: {file_path}")
                        print(f"   文件大小: {file_size} 字节")
                        return file_path
                    else:
                        print(f"❌ 文件保存失败: {file_path}")
                        return None
                else:
                    print(f"❌ 下载失败，状态码: {response.status_code}")
                    return None
            else:
                print(f"❌ 未检测到导出相关请求")
                return None
                
        except Exception as e:
            print(f"❌ 导出{format_type.upper()}格式时出错: {e}")
            try:
                self.page.remove_listener("request", handle_request)
            except:
                pass
            return None
    
    def import_data(self, file_path: str, file_type: str, merge_to_current: bool = False) -> bool:
        """导入数据"""
        print(f"📥 导入{file_type.upper()}文件: {os.path.basename(file_path)}")
        if merge_to_current:
            print("🔀 将勾选'合并到当前数据'选项")
        
        try:
            # 查找导入按钮
            import_button_selectors = [
                'a:has-text("导入")',
                'button:has-text("导入")',
                '.btn:has-text("导入")',
                'input[value="导入"]'
            ]
            
            import_button_found = False
            for selector in import_button_selectors:
                import_buttons = self.page.locator(selector)
                if import_buttons.count() > 0:
                    import_button = import_buttons.first
                    if import_button.is_visible():
                        import_button.scroll_into_view_if_needed()
                        import_button.click()
                        import_button_found = True
                        break
            
            if not import_button_found:
                print("❌ 未找到导入按钮")
                return False
            
            # 等待导入弹窗
            time.sleep(2)
            
            # 查找文件选择框
            file_input_selectors = [
                'input[type="file"]',
                'input[accept*="csv"]',
                'input[accept*="txt"]',
                '.type_file_file input',
                '[class*="file"] input[type="file"]',
                'input[class*="fileField"]'
            ]
            
            file_input_found = False
            for selector in file_input_selectors:
                file_inputs = self.page.locator(selector)
                if file_inputs.count() > 0:
                    for i in range(file_inputs.count()):
                        file_input = file_inputs.nth(i)
                        try:
                            file_input.set_input_files(file_path)
                            print(f"✅ 成功选择文件: {os.path.basename(file_path)}")
                            file_input_found = True
                            break
                        except:
                            continue
                if file_input_found:
                    break
            
            if not file_input_found:
                print("❌ 所有文件输入框都无法使用")
                return False
            
            time.sleep(2)
            
            # 如果需要勾选合并选项
            if merge_to_current:
                self._check_merge_option()
            
            # 点击确定导入
            confirm_button_selectors = [
                'button:has-text("确定导入")',
                'button:has-text("确定")',
                'button:has-text("导入")',
                '.btn:has-text("确定导入")',
                '.btn:has-text("确定")',
                '.btn_green:has-text("确定")',
                '.el-button--primary:has-text("确定")'
            ]
            
            confirm_button_found = False
            for selector in confirm_button_selectors:
                confirm_buttons = self.page.locator(selector)
                if confirm_buttons.count() > 0:
                    for i in range(confirm_buttons.count()):
                        confirm_button = confirm_buttons.nth(i)
                        if confirm_button.is_visible():
                            confirm_button.scroll_into_view_if_needed()
                            confirm_button.click()
                            confirm_button_found = True
                            break
                if confirm_button_found:
                    break
            
            if not confirm_button_found:
                print("❌ 未找到确定导入按钮")
                return False
            
            time.sleep(5)
            print("✅ 导入操作执行完成")
            
            # 检查导入结果
            try:
                rows = self.page.locator('table tr:not(:first-child)')
                imported_count = 0
                
                for i in range(rows.count()):
                    row = rows.nth(i)
                    cells = row.locator('td')
                    if cells.count() > 0:
                        config_name = cells.nth(0).text_content().strip()
                        if config_name and config_name not in ["拨号名称", "配置名称", "vlanID", "VLAN ID", ""]:
                            imported_count += 1
                
                print(f"🔍 导入后配置数量: {imported_count}")
                
                if imported_count > 0:
                    print(f"✅ 成功导入 {imported_count} 个{file_type.upper()}配置")
                    return True
                else:
                    print(f"⚠️  未检测到导入的配置")
                    return False
                    
            except Exception as e:
                print(f"检查导入结果时出错: {e}")
                return False
            
        except Exception as e:
            print(f"❌ 导入{file_type.upper()}文件时出错: {e}")
            return False
    
    def _check_merge_option(self):
        """勾选合并到当前数据选项"""
        print("🔍 查找'合并到当前数据'选项...")
        
        merge_option_selectors = [
            'input[type="checkbox"]:near(:text("合并到当前数据"))',
            'label:has-text("合并到当前数据") input[type="checkbox"]',
            'label:has-text("合并到当前数据")',
            ':text("合并到当前数据")',
            'input[type="checkbox"]'
        ]
        
        merge_option_found = False
        for selector in merge_option_selectors:
            try:
                merge_options = self.page.locator(selector)
                for i in range(merge_options.count()):
                    option = merge_options.nth(i)
                    if option.is_visible():
                        if selector == 'input[type="checkbox"]':
                            parent = option.locator('..')
                            parent_text = parent.text_content()
                            if "合并到当前数据" in parent_text:
                                if not option.is_checked():
                                    option.click()
                                    print("✅ 已勾选'合并到当前数据'选项")
                                else:
                                    print("✅ '合并到当前数据'选项已经勾选")
                                merge_option_found = True
                                break
                        else:
                            option.click()
                            print("✅ 已勾选'合并到当前数据'选项")
                            merge_option_found = True
                            break
                if merge_option_found:
                    break
            except Exception as e:
                continue
        
        if not merge_option_found:
            print("⚠️  未找到'合并到当前数据'选项，继续执行导入")

class RouterTestModule(BaseTestModule, TableOperationsMixin, SearchOperationsMixin, FormOperationsMixin, ImportExportMixin):
    """路由器测试模块基类，组合所有功能"""
    pass

class TestRunner:
    """测试运行器"""
    
    def __init__(self, config: RouterTestConfig, headless: bool = False):
        self.config = config
        self.headless = headless
        self.browser = None
        self.page = None
        
    def run_test_module(self, module_class, test_methods: List[str] = None):
        """运行测试模块"""
        with sync_playwright() as p:
            self.browser = p.chromium.launch(headless=self.headless, slow_mo=100)
            self.page = self.browser.new_page()
            
            try:
                # 创建测试模块实例
                module = module_class(self.config)
                module.setup(self.page)
                
                # 登录
                module.login()
                
                # 导航到模块页面
                module.navigate_to_module()
                
                # 运行指定的测试方法
                if test_methods:
                    for method_name in test_methods:
                        if hasattr(module, method_name):
                            print(f"\n=== 运行测试方法: {method_name} ===")
                            method = getattr(module, method_name)
                            method()
                        else:
                            print(f"警告: 测试模块中不存在方法 {method_name}")
                else:
                    # 运行默认的完整测试
                    if hasattr(module, 'run_full_test'):
                        module.run_full_test()
                    else:
                        print("警告: 测试模块中没有 run_full_test 方法")
                
                print("\n✅ 所有测试完成")
                
            except Exception as e:
                print(f"❌ 测试失败: {e}")
                # 截图保存错误
                error_screenshot = f"error_{module_class.__name__}.png"
                self.page.screenshot(path=error_screenshot)
                print(f"错误截图已保存: {error_screenshot}")
                raise
            finally:
                self.browser.close()