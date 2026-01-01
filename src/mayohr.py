"""MayoHR 網站操作模組 - 使用 Playwright 登入並取得打卡紀錄"""

import os
import re
import time
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class CheckinRecord:
    """打卡紀錄結構"""
    checkin_time: Optional[str] = None   # "HH:MM" 格式或 None
    checkout_time: Optional[str] = None  # "HH:MM" 格式或 None


class MayoHRClient:
    """MayoHR 網站操作客戶端"""
    
    def __init__(self, headless: bool = True):
        """
        初始化 Playwright Chromium 無頭瀏覽器
        
        Args:
            headless: 是否使用無頭模式
        """
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None
        self._playwright = None
    
    def _init_browser(self):
        """初始化瀏覽器"""
        from playwright.sync_api import sync_playwright
        
        self._playwright = sync_playwright().start()
        self.browser = self._playwright.chromium.launch(headless=self.headless)
        
        # 偽裝為一般瀏覽器
        self.context = self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="zh-TW"
        )
        self.page = self.context.new_page()
    
    def login(self, company_code: str = None, employee_id: str = None, password: str = None) -> bool:
        """
        登入 MayoHR
        
        Args:
            company_code: 公司代碼，預設從環境變數讀取
            employee_id: 員工編號，預設從環境變數讀取
            password: 密碼，預設從環境變數讀取
        
        Returns:
            True: 登入成功, False: 登入失敗
        """
        if self.page is None:
            self._init_browser()
        
        company_code = company_code or os.getenv("company_code")
        employee_id = employee_id or os.getenv("employee_number")
        password = password or os.getenv("password")
        login_url = os.getenv("login_url")
        
        try:
            self.page.goto(login_url)
            
            # 等待登入表單載入
            self.page.wait_for_selector('input[name="companyCode"]', timeout=15000)
            
            # 填寫登入表單
            self.page.fill('input[name="companyCode"]', company_code)
            self.page.fill('input[name="employeeNo"]', employee_id)
            self.page.fill('input[name="password"]', password)
            
            # 點擊登入按鈕
            self.page.click('button[type="submit"]')
            
            # 等待登入完成
            self.page.wait_for_load_state("networkidle")
            
            # 檢查是否登入成功（URL 應該改變）
            return "Login" not in self.page.url
        except Exception as e:
            print(f"MayoHR 登入失敗: {e}")
            return False
    
    def get_checkin_records(self) -> CheckinRecord:
        """
        取得當日打卡紀錄
        
        Returns:
            CheckinRecord 包含上班和下班時間
        """
        checkinrecord_url = os.getenv("checkinrecord_url")
        
        try:
            self.page.goto(checkinrecord_url)
            
            # 等待表格載入
            self.page.wait_for_selector("table", timeout=15000)
            time.sleep(2)  # 額外等待確保資料載入完成
            
            # 取得今天的日期
            today_str = datetime.now().strftime("%Y/%m/%d")
            
            # 尋找今天的紀錄行
            rows = self.page.query_selector_all("tr")
            
            checkin_time = None
            checkout_time = None
            
            for row in rows:
                row_text = row.inner_text()
                if today_str in row_text:
                    # 解析時間 (格式是 HH:MM/地點，例如 19:43/TNLMG)
                    times = re.findall(r'(\d{2}:\d{2})/\w+', row_text)
                    if len(times) >= 1:
                        checkin_time = times[0]
                    if len(times) >= 2:
                        checkout_time = times[1]
                    break
            
            return CheckinRecord(checkin_time=checkin_time, checkout_time=checkout_time)
        except Exception as e:
            print(f"取得打卡紀錄失敗: {e}")
            return CheckinRecord()
    
    def close(self) -> None:
        """關閉瀏覽器"""
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self._playwright:
            self._playwright.stop()


def calculate_checkout_time(checkin_time: str) -> str:
    """
    計算下班時間
    
    規則：
    - 如果上班時間 <= 10:30，下班時間 = 上班時間 + 9 小時
    - 如果上班時間 > 10:30（遲到/請假），下班時間 = 19:30（以 10:30 為基準）
    
    Args:
        checkin_time: 上班時間，格式 "HH:MM"
    
    Returns:
        下班時間，格式 "HH:MM"
    """
    checkin = datetime.strptime(checkin_time, "%H:%M")
    base_time = datetime.strptime("10:30", "%H:%M")
    
    if checkin > base_time:
        # 遲到或請假，以 10:30 為基準
        checkout = base_time + timedelta(hours=9)
    else:
        checkout = checkin + timedelta(hours=9)
    
    return checkout.strftime("%H:%M")


def should_start_checkout_check(checkout_time: str, current_time: str = None) -> bool:
    """
    判斷是否應該開始檢查下班打卡
    
    Args:
        checkout_time: 計算出的下班時間，格式 "HH:MM"
        current_time: 當前時間，格式 "HH:MM"，預設為現在
    
    Returns:
        True: 應該開始檢查, False: 還不需要
    """
    if current_time is None:
        current_time = datetime.now().strftime("%H:%M")
    
    checkout = datetime.strptime(checkout_time, "%H:%M")
    current = datetime.strptime(current_time, "%H:%M")
    
    return current >= checkout
