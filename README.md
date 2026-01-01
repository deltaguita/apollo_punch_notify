# Auto Checkin Reminder

自動打卡提醒系統 - 透過 GitHub Actions 定時檢查 MayoHR 打卡狀態，並透過 Telegram Bot 發送提醒。

## Demo

![Telegram 通知截圖](assets/demo.png)

## 功能

- 🕐 早上 10:00 檢查上班打卡
- 🕖 晚上 19:00 檢查下班打卡（確保滿 9 小時工時）
  > 📝 作者最晚上班時間為 10:30，故設定 10:30 後打卡會直接以 10:30 為基準計算下班時間 19:30
- 📅 自動判斷台灣國定假日，假日不提醒
- 透過 Telegram 發送提醒，支援 `/pass` 指令跳過
- 未打卡時每分鐘持續提醒，直到打卡或回覆 `/pass`

## 設定

### 1. Fork 此專案

### 2. 設定 GitHub Secrets

在 Repository Settings → Secrets and variables → Actions → Secrets 新增：

| Secret | 說明 |
|--------|------|
| `COMPANY_CODE` | MayoHR 公司代碼 |
| `EMPLOYEE_NUMBER` | 員工編號 |
| `PASSWORD` | MayoHR 密碼 |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token |
| `TELEGRAM_CHAT_ID` | Telegram Chat ID |

### 3. 設定 GitHub Variables（可選）

在 Repository Settings → Secrets and variables → Actions → Variables 新增：

| Variable | 預設值 | 說明 |
|----------|--------|------|
| `CHECK_CHECKIN_TIME` | `10:00` | 上班檢查時間 |
| `CHECK_CHECKOUT_TIME` | `19:00` | 下班檢查時間 |
| `CHECK_INTERVAL` | `60` | 檢查間隔（秒）|

## 本地測試

```bash
# 安裝依賴
pip install -r requirements.txt
playwright install chromium

# 建立 .env 檔案
cp .env.example .env
# 編輯 .env 填入你的設定

# 執行早班檢查
python -m src.main morning

# 執行晚班檢查
python -m src.main evening

# 執行測試
pytest tests/ -v
```

## 專案結構

```
├── .github/workflows/
│   ├── morning.yml       # 早班排程 (UTC+8 10:00)
│   └── evening.yml       # 晚班排程 (UTC+8 19:00)
├── src/
│   ├── main.py           # 主程式入口
│   ├── calendar.py       # 假日判斷
│   ├── mayohr.py         # MayoHR 網站操作
│   └── telegram.py       # Telegram Bot
├── tests/
│   ├── test_calendar.py
│   └── test_mayohr.py
└── requirements.txt
```

## Acknowledgments

感謝 [@ruyut](https://github.com/ruyut) 提供的 [TaiwanCalendar](https://github.com/ruyut/TaiwanCalendar) 台灣行事曆 API。

## License

MIT
