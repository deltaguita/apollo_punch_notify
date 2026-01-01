"""Calendar 模組測試"""

import os
import pytest
from hypothesis import given, strategies as st, settings

# 設定環境變數供測試使用
os.environ["taiwan_calendar_api"] = "https://cdn.jsdelivr.net/gh/ruyut/TaiwanCalendar/data/{year}.json"

from src.calendar import get_calendar_api_url


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
