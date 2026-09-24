# 露營小助手 Camping Agent Demo

用AI Agent回答台灣露營相關問題的展示專案：問「哪裡有露營地」、「那邊天氣如何」，AI會自動查詢露營地資料庫、串接即時天氣API，整理成一段回覆。

線上展示網址：`https://demo.yayjun.tw`（AI功能預設關閉）

## 功能

- 用自然語言問露營地推薦（依縣市、鄉鎮市區找最近的營地）
- 問天氣、要不要帶雨具、適不適合露營
- AI會自動判斷該該使用的工具，兩者可以串在同一次對話裡
- 簡單的多輪對話記憶（同一個session內記得上下文）

## 技術棧

- **後端**：FastAPI + SQLAlchemy（async）+ Pydantic
- **資料庫**：PostgreSQL（正式環境）／SQLite（本機開發用）
- **AI**：OpenAI Responses API（function calling 串接自家的露營地查詢、天氣查詢工具）
- **外部 API**：[Open-Meteo](https://open-meteo.com/) 免費天氣 API
- **前端**：Vanilla JS + HTML，由 FastAPI 用 `StaticFiles`
- **部署**：Railway

## 專案結構

```
app/
├── api/routes/       # FastAPI 路由（campsite/weather/agent）
├── core/config.py    # 環境變數設定（pydantic-settings）
├── db/database.py    # SQLAlchemy async engine/session
├── models/           # ORM 資料模型（campsite、district、county_alias）
├── schemas/          # Pydantic request/response schema
├── services/          # 商業邏輯（AI Agent、露營地查詢、天氣查詢）
└── main.py           # FastAPI app 進入點
local_tools/
├── docs/              # 原始資料（campsite.csv、position.json）
└── scripts/           # 一次性資料匯入腳本
tests/                 # pytest單元測試
web/index.html         # 前端聊天介面
```

## 環境變數

複製 `.env.example` 成 `.env`，填入實際值：

| 變數 | 說明 |
|---|---|
| `DATABASE_URL` | 資料庫連線字串，例如 `postgresql://user:pass@host:port/dbname` |
| `OPENAI_API_KEY` | OpenAI API 金鑰 |
| `OPENAI_MODEL` | 使用的模型名稱 |
| `AI_ENABLED` | 是否開放 `/api/chat` 這支AI對話API，預設關閉 |

## 本機開發

```bash
python -m venv myenv
source myenv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # 填入實際的環境變數

# 第一次跑，匯入基礎資料
python -m local_tools.scripts.import_district
python -m local_tools.scripts.import_campsite

uvicorn app.main:app --reload
```

打開 `http://127.0.0.1:8000/`

## 測試

```bash
pytest
```

## API

| Method | 路徑 | 說明 |
|---|---|---|
| GET | `/api/campsite/` | 取得全部露營地列表 |
| GET | `/api/campsite/county/{county}` | 依縣市篩選露營地 |
| GET | `/api/campsite/district/{district}` | 依鄉鎮市區篩選露營地 |
| GET | `/api/campsite/near?county=&district=` | 取得指定地點最近的5個露營地 |
| GET | `/api/weather/?lat=&lng=` | 查詢指定座標的即時天氣 |
| GET | `/api/chat/status` | 查詢AI對話功能目前是否開放 |
| POST | `/api/chat/` | 跟AI助手對話（`session_id`、`question`） |

完整的互動式文件可以在部署後打開 `/docs` 查看。

## 部署（Railway）

1. 用 GitHub Repository 方式連接 Railway
2. 額外建立一個 PostgreSQL 服務，並在 App 服務的環境變數設定 `DATABASE_URL=${{Postgres.DATABASE_URL}}`
3. 啟動指令見 `Procfile` / `railway.json`：`uvicorn app.main:app --host 0.0.0.0 --port $PORT`
