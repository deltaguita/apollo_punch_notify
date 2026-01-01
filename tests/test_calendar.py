"""Calendar 模組測試"""

import os
import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import patch

# 設定環境變數供測試使用
os.environ["taiwan_calendar_api"] = "https://cdn.jsdelivr.net/gh/ruyut/TaiwanCalendar/data/{year}.json"

from src.calendar import get_calendar_api_url, is_holiday
import datetime


class TestCalendarAPIURL:
    """
    Property 1: Calendar API URL 年份自動更新
    **Validates: Requirements 1.2**
    """
    
    @given(st.integers(min_value=2000, max_value=2100))
    @settings(max_examples=100)
    def test_calendar_api_url_contains_year(self, year: int):
        """
        Feature: auto-checkin-reminder, Property 1: Calendar API URL 年份自動更新
        
        *For any* 年份 Y，`get_calendar_api_url()` 產生的 URL 應包含該年份字串。
        """
        url = get_calendar_api_url(year)
        assert str(year) in url, f"URL should contain year {year}, got {url}"


class TestIsHoliday:
    """
    測試假日判斷邏輯
    **Validates: Requirements 1.1**
    """
    
    def test_is_holiday_with_boolean_true(self):
        """測試 API 回傳布林值 true 的情況"""
        mock_response = [
            {"date": "20260101", "isHoliday": True, "description": "開國紀念日"}
        ]
        
        with patch('src.calendar.requests.get') as mock_get:
            mock_get.return_value.json.return_value = mock_response
            mock_get.return_value.raise_for_status = lambda: None
            
            result = is_holiday(datetime.date(2026, 1, 1))
            assert result is True
    
    def test_is_holiday_with_boolean_false(self):
        """測試 API 回傳布林值 false 的情況"""
        mock_response = [
            {"date": "20260102", "isHoliday": False, "description": ""}
        ]
        
        with patch('src.calendar.requests.get') as mock_get:
            mock_get.return_value.json.return_value = mock_response
            mock_get.return_value.raise_for_status = lambda: None
            
            result = is_holiday(datetime.date(2026, 1, 2))
            assert result is False
