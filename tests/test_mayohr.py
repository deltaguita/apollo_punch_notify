"""MayoHR 模組測試"""

from datetime import datetime, timedelta
import pytest
from hypothesis import given, strategies as st, settings

from src.mayohr import calculate_checkout_time, should_start_checkout_check


# 產生 <= 10:30 的上班時間策略（正常上班）
normal_checkin_time = st.builds(
    lambda h, m: f"{h:02d}:{m:02d}",
    st.integers(min_value=0, max_value=10),
    st.integers(min_value=0, max_value=59)
).filter(lambda t: t <= "10:30")

# 產生 > 10:30 的上班時間策略（遲到/請假）
late_checkin_time = st.builds(
    lambda h, m: f"{h:02d}:{m:02d}",
    st.integers(min_value=10, max_value=14),
    st.integers(min_value=0, max_value=59)
).filter(lambda t: t > "10:30")

# 產生任意有效時間字串策略
any_valid_time = st.builds(
    lambda h, m: f"{h:02d}:{m:02d}",
    st.integers(min_value=0, max_value=23),
    st.integers(min_value=0, max_value=59)
)


class TestCheckoutTimeCalculation:
    """
    Property 2: 下班時間計算正確性
    **Validates: Requirements 3.4**
    
    規則：
    - 如果上班時間 <= 10:30，下班時間 = 上班時間 + 9 小時
    - 如果上班時間 > 10:30（遲到/請假），下班時間 = 19:30（以 10:30 為基準）
    """
    
    @given(normal_checkin_time)
    @settings(max_examples=100)
    def test_normal_checkin_checkout_is_plus_9_hours(self, checkin_time: str):
        """
        Feature: auto-checkin-reminder, Property 2a: 正常上班下班時間計算
        
        *For any* 上班時間 <= 10:30，下班時間應為上班時間 + 9 小時。
        """
        checkout_time = calculate_checkout_time(checkin_time)
        
        checkin = datetime.strptime(checkin_time, "%H:%M")
        checkout = datetime.strptime(checkout_time, "%H:%M")
        expected_checkout = checkin + timedelta(hours=9)
        
        assert checkout.hour == expected_checkout.hour, \
            f"Expected hour {expected_checkout.hour}, got {checkout.hour}"
        assert checkout.minute == expected_checkout.minute, \
            f"Expected minute {expected_checkout.minute}, got {checkout.minute}"
    
    @given(late_checkin_time)
    @settings(max_examples=100)
    def test_late_checkin_checkout_is_fixed_1930(self, checkin_time: str):
        """
        Feature: auto-checkin-reminder, Property 2b: 遲到/請假下班時間計算
        
        *For any* 上班時間 > 10:30（遲到或請假），下班時間固定為 19:30。
        """
        checkout_time = calculate_checkout_time(checkin_time)
        
        assert checkout_time == "19:30", \
            f"For late checkin {checkin_time}, expected 19:30, got {checkout_time}"


class TestCheckoutTimeComparison:
    """
    Property 3: 下班時間比較邏輯
    **Validates: Requirements 3.5**
    """
    
    @given(any_valid_time, any_valid_time)
    @settings(max_examples=100)
    def test_should_start_checkout_check_logic(self, checkout_time: str, current_time: str):
        """
        Feature: auto-checkin-reminder, Property 3: 下班時間比較邏輯
        
        *For any* 計算出的下班時間 D 和當前時間 N：
        - 若 N >= D，則 `should_start_checkout_check()` 返回 True
        - 若 N < D，則 `should_start_checkout_check()` 返回 False
        """
        result = should_start_checkout_check(checkout_time, current_time)
        
        checkout = datetime.strptime(checkout_time, "%H:%M")
        current = datetime.strptime(current_time, "%H:%M")
        
        expected = current >= checkout
        
        assert result == expected, \
            f"For checkout={checkout_time}, current={current_time}: expected {expected}, got {result}"


class TestCheckoutTimeValidation:
    """
    Property 4: 下班打卡時間驗證邏輯
    驗證下班打卡時間是否滿足工時要求
    
    規則：
    - 正常上班 (<= 10:30)：下班時間 >= 上班時間 + 9 小時
    - 遲到/請假 (> 10:30)：下班時間 >= 19:30
    """
    
    @given(normal_checkin_time, any_valid_time)
    @settings(max_examples=100)
    def test_normal_checkout_validation(self, checkin_time: str, actual_checkout: str):
        """
        Feature: auto-checkin-reminder, Property 4a: 正常上班下班驗證
        
        *For any* 正常上班時間 (<= 10:30) 和實際下班打卡時間：
        - 若實際下班時間 >= 上班時間 + 9 小時，則視為有效下班
        """
        required_checkout = calculate_checkout_time(checkin_time)
        
        is_valid = actual_checkout >= required_checkout
        
        checkin = datetime.strptime(checkin_time, "%H:%M")
        expected_checkout = checkin + timedelta(hours=9)
        actual = datetime.strptime(actual_checkout, "%H:%M")
        
        expected_valid = actual >= expected_checkout
        
        assert is_valid == expected_valid, \
            f"checkin={checkin_time}, actual={actual_checkout}, required={required_checkout}"
    
    @given(late_checkin_time, any_valid_time)
    @settings(max_examples=100)
    def test_late_checkout_validation(self, checkin_time: str, actual_checkout: str):
        """
        Feature: auto-checkin-reminder, Property 4b: 遲到/請假下班驗證
        
        *For any* 遲到/請假上班時間 (> 10:30) 和實際下班打卡時間：
        - 下班時間固定為 19:30，實際下班 >= 19:30 即為有效
        """
        required_checkout = calculate_checkout_time(checkin_time)
        
        assert required_checkout == "19:30", \
            f"Late checkin should require 19:30, got {required_checkout}"
        
        is_valid = actual_checkout >= required_checkout
        expected_valid = actual_checkout >= "19:30"
        
        assert is_valid == expected_valid, \
            f"checkin={checkin_time}, actual={actual_checkout}: expected {expected_valid}, got {is_valid}"
