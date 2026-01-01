"""主程式入口 - 自動打卡提醒系統"""

import os
import sys
import time
from datetime import datetime
from dotenv import load_dotenv

from src.calendar import is_holiday, CalendarAPIError
from src.telegram import TelegramBot
from src.mayohr import MayoHRClient, calculate_checkout_time, should_start_checkout_check

load_dotenv()


def get_check_interval() -> int:
    """取得檢查間隔秒數"""
    return int(os.getenv("check_interval", "60"))


MAX_CONSECUTIVE_FAILURES = 3  # 連續失敗次數上限


def run_morning():
    """
    早班流程
    
    1. 檢查假日 → 假日發送放假訊息並結束
    2. 工作日 → 登入檢查上班卡 → 未打卡則提醒並循環檢查
    3. 處理 pass callback
    """
    bot = TelegramBot()
    check_interval = get_check_interval()
    
    try:
        # 檢查是否為假日
        if is_holiday():
            bot.send_message("🎉 今天放假！")
            print("今天是假日，結束執行")
            return
    except CalendarAPIError as e:
        bot.send_message(f"❌ 行事曆 API 錯誤: {e}")
        print(f"行事曆 API 錯誤: {e}")
        sys.exit(1)
    
    # 工作日流程
    client = MayoHRClient(headless=True)
    last_message_id = None
    
    try:
        # 登入 MayoHR
        if not client.login():
            bot.send_message("❌ MayoHR 登入失敗，請檢查帳號密碼")
            print("MayoHR 登入失敗")
            sys.exit(1)
        
        while True:
            # 取得打卡紀錄
            records = client.get_checkin_records()
            
            if records.checkin_time:
                # 已打上班卡
                print(f"已打上班卡: {records.checkin_time}")
                if last_message_id:
                    bot.send_message(f"✅ 已偵測到上班打卡: {records.checkin_time}")
                return
            
            # 未打卡，發送提醒（早上未打卡是正常情況，需要提醒）
            print("未偵測到上班打卡，發送提醒")
            message_id = bot.send_message(
                "⏰ 提醒：尚未打上班卡！\n請記得打卡，或回覆 /pass 跳過提醒。"
            )
            if message_id:
                last_message_id = message_id
            
            # 等待並檢查 /pass 指令
            time.sleep(check_interval)
            
            if last_message_id and bot.check_pass_command(last_message_id):
                print("收到 Pass 指令，結束執行")
                bot.send_message("✅ 已收到 Pass 指令，停止上班打卡提醒")
                return
    
    finally:
        client.close()


def run_evening():
    """
    晚班流程
    
    1. 檢查假日 → 假日則結束
    2. 工作日 → 登入取得上班時間 → 計算下班時間 → 等待或立即檢查
    3. 未打卡則提醒並循環檢查
    4. 處理 pass callback
    """
    bot = TelegramBot()
    check_interval = get_check_interval()
    
    try:
        # 檢查是否為假日
        if is_holiday():
            print("今天是假日，結束執行")
            return
    except CalendarAPIError as e:
        bot.send_message(f"❌ 行事曆 API 錯誤: {e}")
        print(f"行事曆 API 錯誤: {e}")
        sys.exit(1)
    
    # 工作日流程
    client = MayoHRClient(headless=True)
    last_message_id = None
    consecutive_failures = 0
    
    try:
        # 登入 MayoHR
        if not client.login():
            bot.send_message("❌ MayoHR 登入失敗，請檢查帳號密碼")
            print("MayoHR 登入失敗")
            sys.exit(1)
        
        # 取得上班打卡時間
        records = client.get_checkin_records()
        
        if not records.checkin_time:
            # 沒有上班打卡紀錄，可能早上已經 pass 了
            print("沒有上班打卡紀錄，結束執行")
            return
        
        # 計算下班時間
        checkout_time = calculate_checkout_time(records.checkin_time)
        print(f"上班時間: {records.checkin_time}, 預計下班時間: {checkout_time}")
        
        # 等待直到下班時間
        while not should_start_checkout_check(checkout_time):
            current = datetime.now().strftime("%H:%M")
            print(f"當前時間 {current}，等待下班時間 {checkout_time}")
            time.sleep(check_interval)
        
        # 開始檢查下班打卡
        while True:
            # 重新取得打卡紀錄
            records = client.get_checkin_records()
            
            # 檢查是否連續取得紀錄失敗
            if records.checkin_time is None and records.checkout_time is None:
                consecutive_failures += 1
                print(f"取得打卡紀錄失敗 ({consecutive_failures}/{MAX_CONSECUTIVE_FAILURES})")
                
                if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                    bot.send_message(f"❌ 連續 {MAX_CONSECUTIVE_FAILURES} 次取得打卡紀錄失敗，請檢查 MayoHR 連線狀態")
                    print("連續取得紀錄失敗，中斷執行")
                    sys.exit(1)
                
                time.sleep(check_interval)
                continue
            
            consecutive_failures = 0  # 重置失敗計數
            
            if records.checkout_time:
                # 檢查下班時間是否 >= 上班時間 + 9 小時
                if records.checkout_time >= checkout_time:
                    print(f"已打下班卡: {records.checkout_time} (滿 9 小時)")
                    if last_message_id:
                        bot.send_message(f"✅ 已偵測到下班打卡: {records.checkout_time}")
                    return
                else:
                    # 下班卡打太早，還沒滿 9 小時
                    print(f"下班卡 {records.checkout_time} 未滿 9 小時，需等到 {checkout_time}")
            
            # 未打卡或未滿 9 小時，發送提醒
            print("未偵測到有效下班打卡，發送提醒")
            message_id = bot.send_message(
                f"⏰ 提醒：已過下班時間 {checkout_time}，尚未打下班卡！\n請記得打卡，或回覆 /pass 跳過提醒。"
            )
            if message_id:
                last_message_id = message_id
            
            # 等待並檢查 /pass 指令
            time.sleep(check_interval)
            
            if last_message_id and bot.check_pass_command(last_message_id):
                print("收到 Pass 指令，結束執行")
                bot.send_message("✅ 已收到 Pass 指令，停止下班打卡提醒")
                return
    
    finally:
        client.close()


def main(mode: str) -> None:
    """
    主程式入口
    
    Args:
        mode: "morning" 或 "evening"
    """
    print(f"啟動自動打卡提醒系統 - 模式: {mode}")
    print(f"當前時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if mode == "morning":
        run_morning()
    elif mode == "evening":
        run_evening()
    else:
        print(f"未知的模式: {mode}")
        print("使用方式: python -m src.main [morning|evening]")
        sys.exit(1)
    
    print("執行完成")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("使用方式: python -m src.main [morning|evening]")
        sys.exit(1)
    
    main(sys.argv[1])
