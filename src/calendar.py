"""假日判斷模組 - 使用台灣行事曆 API 判斷當日是否為假日"""

import os
import datetime
import requests
from dotenv import load_dotenv

load_dotenv()


class CalendarAPIError(Exception):
    """Taiwan Calendar API 呼叫失敗時拋出的例外"""
    pass


def get_calendar_api_url(year: int = None) -> str:
    """
    取得當年度的 Taiwan Calendar API URL
    
    Args:
        year: 指定年份，預設為當前年份
    
    Returns:
        完整的 API URL
    """
    if year is None:
        year = datetime.datetime.now().year
    
    api_template = os.getenv("taiwan_calendar_api", "")
    return api_template.format(year=year)


def is_holiday(date: datetime.date = None) -> bool:
    """
    判斷指定日期是否為假日
    
    Args:
        date: 要判斷的日期，預設為今天
    
    Returns:
        True: 假日, False: 工作日
    
    Raises:
        CalendarAPIError: API 呼叫失敗或回傳錯誤
    """
    if date is None:
        date = datetime.date.today()
    
    url = get_calendar_api_url(date.year)
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        raise CalendarAPIError(f"Taiwan Calendar API 呼叫失敗: {e}")
    except ValueError as e:
        raise CalendarAPIError(f"Taiwan Calendar API 回傳格式錯誤: {e}")
    
    # 格式化日期為 YYYYMMDD
    date_str = date.strftime("%Y%m%d")
    
    # 搜尋該日期的資料
    for day_info in data:
        if day_info.get("date") == date_str:
            return day_info.get("isHoliday") is True
    
    # 如果找不到該日期，根據星期判斷（週六日為假日）
    return date.weekday() >= 5
