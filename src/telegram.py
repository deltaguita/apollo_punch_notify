"""Telegram Bot 模組 - 發送通知和處理用戶回應"""

import os
import requests
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class TelegramBot:
    """Telegram Bot 用於發送打卡提醒和接收用戶回應"""
    
    def __init__(self, token: str = None, chat_id: str = None):
        """
        初始化 Telegram Bot
        
        Args:
            token: Bot Token，預設從環境變數讀取
            chat_id: Chat ID，預設從環境變數讀取
        """
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self._last_update_id = 0
    
    def send_message(self, text: str) -> Optional[int]:
        """
        發送訊息
        
        Args:
            text: 訊息內容
        
        Returns:
            message_id 或 None（發送失敗時）
        """
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()
            if result.get("ok"):
                return result["result"]["message_id"]
            return None
        except requests.RequestException as e:
            print(f"Telegram 發送訊息失敗: {e}")
            return None
    
    def check_pass_command(self, since_message_id: int = 0) -> bool:
        """
        輪詢檢查是否有 /pass 指令
        
        Args:
            since_message_id: 從哪個 message_id 之後開始檢查
        
        Returns:
            True: 收到 /pass, False: 未收到
        """
        url = f"{self.base_url}/getUpdates"
        params = {
            "offset": self._last_update_id + 1,
            "timeout": 1,
            "allowed_updates": ["message"]
        }
        
        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            result = response.json()
            
            if not result.get("ok"):
                return False
            
            for update in result.get("result", []):
                self._last_update_id = update["update_id"]
                
                message = update.get("message")
                if message:
                    text = message.get("text", "")
                    message_id = message.get("message_id", 0)
                    chat_id = str(message.get("chat", {}).get("id", ""))
                    
                    # 檢查是否為 /pass 指令且來自正確的 chat
                    if text.strip().lower() == "/pass" and chat_id == self.chat_id and message_id > since_message_id:
                        return True
            
            return False
        except requests.RequestException as e:
            print(f"Telegram 輪詢失敗: {e}")
            return False
