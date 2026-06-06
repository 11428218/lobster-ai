import logging
import sqlite3
from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    filters,
    ContextTypes
)

try:
    import google.generativeai as genai
except Exception:
    try:
        import google.genai as genai
    except Exception:
        genai = None
from secrets_config import get_credentials
import os
import requests
import random
import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN, API_KEY = get_credentials()
DB_FILE = "lobster.db"
MEMORY_FILE = "memory.txt"

UNITY_PROJECT_PATH = r"D:\tmy\My project"


def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS memories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS core_memories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT NOT NULL,
        status TEXT DEFAULT 'todo',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        done_at TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS research_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic TEXT NOT NULL,
        summary TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

if not TOKEN or not API_KEY:
    raise RuntimeError("BOT_TOKEN 或 GEMINI_API_KEY 尚未設定")

genai.configure(api_key=API_KEY)

model = genai.GenerativeModel("gemini-2.5-flash")

CHAT_ID = None
TOPICS = [
    "unity inventory system",
    "unity dialogue system",
    "unity save system",
    "unity 2d rpg",
    "unity enemy ai",
    "unity quest system",
    "godot inventory system",
    "pixel art game development",
    "game design patterns",
    "procedural generation game"
]
async def send_long_message(update, text):
    max_length = 4000

    for i in range(0, len(text), max_length):
        await update.message.reply_text(
            text[i:i + max_length]
        )


def add_memory(content):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO memories(content) VALUES(?)",
        (content,)
    )

    conn.commit()
    conn.close()


def get_memories():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, content, created_at FROM memories ORDER BY id DESC"
    )

    rows = cursor.fetchall()
    conn.close()

    return rows


def get_memory_text():
    memories = get_memories()
    text = ""

    for memory_id, content, created_at in memories:
        text += f"{memory_id}. {content}\n"

    return text


def add_core_memory(content):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO core_memories(content) VALUES(?)",
        (content,)
    )

    conn.commit()
    conn.close()


def get_core_memories():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, content
        FROM core_memories
        ORDER BY id DESC
        """
    )

    rows = cursor.fetchall()
    conn.close()

    return rows


def delete_memory(memory_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM memories WHERE id=?",
        (memory_id,)
    )

    changed = cursor.rowcount

    conn.commit()
    conn.close()

    return changed > 0


def save_research(topic, summary):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO research_reports
        (topic, summary)
        VALUES (?, ?)
        """,
        (topic, summary)
    )


def add_task(content):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO tasks(content, status) VALUES(?, 'todo')",
        (content,)
    )

    conn.commit()
    conn.close()


def get_todo_tasks():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, content FROM tasks WHERE status='todo' ORDER BY id ASC"
    )

    rows = cursor.fetchall()
    conn.close()

    return rows


def get_done_tasks():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, content, done_at FROM tasks WHERE status='done' ORDER BY done_at DESC"
    )

    rows = cursor.fetchall()
    conn.close()

    return rows


def save_research(topic, summary):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO research_reports
        (topic, summary)
        VALUES (?, ?)
        """,
        (topic, summary)
    )

    conn.commit()
    conn.close()


def get_research_reports(limit=10):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT topic, summary, created_at
        FROM research_reports
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,)
    )

    rows = cursor.fetchall()
    conn.close()

    return rows


def get_recent_topics(limit=20):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT topic
        FROM research_reports
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,)
    )

    rows = cursor.fetchall()
    conn.close()

    return [row[0] for row in rows]


def scan_project():

    assets_path = os.path.join(
        UNITY_PROJECT_PATH,
        "Assets"
    )

    result = []

    for root, dirs, files in os.walk(
        assets_path
    ):

        for file in files:

            if file.endswith(
                (
                    ".cs",
                    ".unity",
                    ".prefab"
                )
            ):

                result.append(file)

    return result


def choose_research_topic():
    recent_topics = get_recent_topics()

    available_topics = [
        topic for topic in TOPICS
        if topic not in recent_topics
    ]

    if not available_topics:
        return random.choice(TOPICS)

    return random.choice(available_topics)


def finish_task(task_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE tasks SET status='done', done_at=CURRENT_TIMESTAMP WHERE id=? AND status='todo'",
        (task_id,)
    )

    changed = cursor.rowcount

    conn.commit()
    conn.close()

    return changed > 0


async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not getattr(update.message, "text", None):
        return
    user_text = update.message.text

    global CHAT_ID
    CHAT_ID = update.effective_chat.id

    if not user_text.startswith("/"):
        keywords = [
            "我喜歡",
            "我正在",
            "我的目標",
            "我想做",
            "我想開發",
            "我討厭",
            "我希望"
        ]

        for keyword in keywords:
            if keyword in user_text:

                add_memory("[自動記憶] " + user_text)

                break

    if user_text.startswith("/help"):
        help_text = """
🦞 龍蝦AI 指令列表

/story 主題
產生遊戲故事企劃

/character 角色概念
產生角色設定

/code 功能需求
產生 Unity C# 程式

/idea
產生今天的遊戲靈感

/quest
產生今日遊戲開發任務

/remember 內容
讓龍蝦AI記住一件事

/memory
查看目前記憶

/forget 編號
刪除指定記憶

/core
查看核心記憶

/addcore 內容
新增核心記憶

/addtask 任務內容
新增遊戲開發任務

/tasks
查看目前任務

/donetask 編號
完成指定任務

/donehistory
查看已完成任務紀錄

/project
整理目前遊戲專案總覽

/github 關鍵字
搜尋 GitHub 遊戲開發相關專案

/learn 關鍵字
搜尋 GitHub 並請龍蝦AI整理學習重點

/whatilearned
查看最近學到的知識

/testdaily
立刻測試每日 GitHub 推播

/help
查看指令列表
"""
        await update.message.reply_text(help_text)
        return

    if user_text.startswith("/remember"):
        new_memory = user_text.replace("/remember", "").strip()

        if not new_memory:
            await update.message.reply_text(
                "請在 /remember 後面輸入要記住的內容。"
            )
            return

        add_memory(new_memory)

        await update.message.reply_text(
            "🦞 已經記住了。"
        )
        return

    if user_text.startswith("/memory"):
        memories = get_memories()

        if not memories:
            await update.message.reply_text("目前還沒有記憶。")
            return

        text = "🧠 目前記憶：\n\n"

        for memory_id, content, created_at in memories:
            text += f"{memory_id}. {content}\n"

        await send_long_message(update, text)
        return

    if user_text.startswith("/core"):
        memories = get_core_memories()

        if not memories:
            await update.message.reply_text(
                "目前沒有核心記憶。"
            )
            return

        text = "🦞 核心記憶：\n\n"

        for memory_id, content in memories:
            text += f"{memory_id}. {content}\n"

        await send_long_message(
            update,
            text
        )

        return

    if user_text.startswith("/addcore"):
        content = (
            user_text
            .replace("/addcore", "")
            .strip()
        )

        if not content:
            await update.message.reply_text(
                "請輸入核心記憶。"
            )
            return

        add_core_memory(content)

        await update.message.reply_text(
            "🦞 已加入核心記憶。"
        )
        return

    if user_text.startswith("/forget"):
        number_text = user_text.replace("/forget", "").strip()

        if not number_text.isdigit():
            await update.message.reply_text(
                "請輸入要刪除的記憶編號，例如：/forget 5"
            )
            return

        memory_id = int(number_text)

        success = delete_memory(memory_id)

        if not success:
            await update.message.reply_text("找不到這個記憶編號。")
            return

        await update.message.reply_text(
            f"🗑 已刪除記憶 ID：{memory_id}"
        )
        return

    if user_text.startswith("/addtask"):
        task = user_text.replace("/addtask", "").strip()

        if not task:
            await update.message.reply_text(
                "請輸入任務，例如：/addtask 製作2D角色移動"
            )
            return

        add_task(task)

        await update.message.reply_text(
            "🦞 已新增任務。"
        )
        return

    if user_text.startswith("/tasks"):
        tasks = get_todo_tasks()

        if not tasks:
            await update.message.reply_text("目前沒有任務。")
            return

        text = "📋 目前任務：\n\n"

        for task_id, task in tasks:
            text += f"{task_id}. □ {task}\n"

        await send_long_message(update, text)
        return

    if user_text.startswith("/donetask"):
        number_text = user_text.replace("/donetask", "").strip()

        if not number_text.isdigit():
            await update.message.reply_text(
                "請輸入任務編號，例如：/donetask 1"
            )
            return

        task_id = int(number_text)

        success = finish_task(task_id)

        if not success:
            await update.message.reply_text("找不到這個任務編號。")
            return

        await update.message.reply_text(
            f"✅ 已完成任務 ID：{task_id}"
        )
        return


    if user_text.startswith("/whatilearned"):

        reports = get_research_reports()

        if not reports:
            await update.message.reply_text(
                "目前還沒有學習紀錄。"
            )
            return

        text = "🦞 最近學到：\n\n"

        for topic, summary, created_at in reports:

            text += f"""
📚 {topic}
🕒 {created_at}

{summary}

----------------
"""

    await send_long_message(
        update,
        text
    )

    return


    if user_text.startswith("/donehistory"):

        done_tasks = get_done_tasks()

        if not done_tasks:
            await update.message.reply_text(
                "目前還沒有完成紀錄。"
            )
            return

        text = "🏆 已完成任務紀錄：\n\n"

        for task_id, task, done_at in done_tasks:
            text += f"{task_id}. ✅ {task}\n"

        await send_long_message(update, text)
        return


    if user_text.startswith("/whatilearned"):

        reports = get_research_reports()

        if not reports:
            await update.message.reply_text(
                "目前還沒有學習紀錄。"
            )
            return

        text = "🦞 最近學到：\n\n"

        for topic, summary, created_at in reports:
            text += f"""
📚 {topic}
🕒 {created_at}

{summary}

----------------

"""

        await send_long_message(update, text)
        return


    if user_text.startswith("/scanproject"):

        files = scan_project()

        if not files:
            await update.message.reply_text(
                "找不到 Unity 專案。"
            )
            return

        text = "🎮 Unity 專案內容\n\n"

        for file in files[:50]:
            text += f"{file}\n"

        await send_long_message(update, text)
        return


    if user_text.startswith("/testdaily"):
        await daily_github_report(context.application)
        await update.message.reply_text("🦞 已測試每日推播。")
        return


    if user_text.startswith("/project"):
        memory = get_memory_text() or "目前沒有記憶。"
        core_memory = ""

        for _, content in get_core_memories():
            core_memory += content + "\n"

        tasks = get_todo_tasks()

        task_text = ""

        if tasks:
            for task_id, task in tasks:
                task_text += f"{task_id}. □ {task}\n"
        else:
            task_text = "目前沒有未完成任務。"

        prompt = f"""
你是龍蝦AI，是主人的遊戲開發經理。

    核心記憶：
    {core_memory}

以下是主人的長期記憶：
{memory}

以下是目前任務：
{task_text}

請整理成一份「遊戲專案總覽」：

請輸出：
1. 目前專案方向
2. 已知使用者目標
3. 目前待辦任務
4. 最應該優先完成的事情
5. 接下來 3 天建議開發順序

語氣要像遊戲開發經理，直接、清楚、不要太空泛。
"""

        response = model.generate_content(prompt)
        text = getattr(response, "text", None) or str(response)

        await send_long_message(update, text)
        return

    memory = get_memory_text()
    core_memory = ""

    for _, content in get_core_memories():
        core_memory += content + "\n"

    if user_text.startswith("/story"):
        topic = user_text.replace("/story", "").strip()

        prompt = f"""
你是龍蝦AI，專門幫主人設計遊戲劇情。

核心記憶：
{core_memory}

使用者資料：
{memory}

請根據以下主題，設計一個遊戲故事企劃：

主題：
{topic}

請輸出：
1. 遊戲名稱
2. 世界觀
3. 主角設定
4. 核心衝突
5. 第一章劇情
6. 遊戲亮點
"""

    elif user_text.startswith("/character"):
        topic = user_text.replace("/character", "").strip()

        prompt = f"""
你是龍蝦AI，專門幫主人設計遊戲角色。

    核心記憶：
    {core_memory}

使用者資料：
{memory}

請根據以下概念，設計一位遊戲角色：

角色概念：
{topic}

請輸出：
1. 名字
2. 年齡
3. 外表
4. 個性
5. 背景故事
6. 技能
7. 適合的遊戲定位
"""

    elif user_text.startswith("/code"):
        topic = user_text.replace("/code", "").strip()

        prompt = f"""
你是龍蝦AI，專門幫主人寫 Unity C# 遊戲程式。

    核心記憶：
    {core_memory}

使用者資料：
{memory}

請根據以下需求，產生 Unity C# 程式：

需求：
{topic}

請輸出：
1. 功能說明
2. 完整程式碼
3. 使用方法
4. 新手容易出錯的地方
"""

    elif user_text.startswith("/idea"):
        prompt = f"""
你是龍蝦AI，要提供今天的遊戲企劃靈感。

    核心記憶：
    {core_memory}

使用者資料：
{memory}

請輸出「今天的遊戲靈感」，格式如下：
1. 題材
2. 玩法核心
3. 劇情鉤子
4. 主角能力成長
5. 可先做的原型內容（30-60 分鐘可完成）

要求：
- 內容要具體、可執行
- 適合新手獨立開發
- 語氣簡潔直接
"""

    elif user_text.startswith("/quest"):
        prompt = f"""
你是龍蝦AI，要根據使用者資料生成今日任務清單。

    核心記憶：
    {core_memory}

使用者資料：
{memory}

請輸出：
1. 今日任務（3-5 項，使用 `□` 勾選框）
2. 每項任務的建議時間（例如 20 分鐘）
3. 一句今日重點提醒

要求：
- 任務偏向遊戲開發（Unity / Godot / RPG 劇情）
- 難度適合新手
- 今天就能完成
"""

    elif user_text.startswith("/github"):
        query = user_text.replace("/github", "").strip()

        if not query:
            await update.message.reply_text(
                "請輸入要搜尋的關鍵字，例如：/github unity inventory system"
            )
            return

        url = "https://api.github.com/search/repositories"

        params = {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": 5
        }

        try:
            result = requests.get(url, params=params, timeout=10)
            data = result.json()

            repos = data.get("items", [])

            if not repos:
                await update.message.reply_text("沒有找到相關專案。")
                return

            github_text = "🦞 GitHub 搜尋結果：\n\n"

            for repo in repos:
                github_text += f"""
⭐ {repo["stargazers_count"]}
📦 {repo["full_name"]}
📝 {repo.get("description") or "沒有描述"}
🔗 {repo["html_url"]}

"""

            await send_long_message(update, github_text)
            return

        except Exception:
            logger.exception("GitHub search failed")
            await update.message.reply_text("GitHub 搜尋時發生錯誤。")
            return

    elif user_text.startswith("/learn"):
        query = user_text.replace("/learn", "").strip()

        if not query:
            await update.message.reply_text(
                "請輸入要學的主題，例如：/learn unity inventory system"
            )
            return

        url = "https://api.github.com/search/repositories"

        params = {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": 5
        }

        try:
            result = requests.get(url, params=params, timeout=10)
            data = result.json()
            repos = data.get("items", [])

            if not repos:
                await update.message.reply_text("沒有找到相關專案。")
                return

            repo_text = ""

            for repo in repos:
                repo_text += f"""
專案名稱：{repo["full_name"]}
星數：{repo["stargazers_count"]}
描述：{repo.get("description") or "沒有描述"}
連結：{repo["html_url"]}
"""

            prompt = f"""
你是龍蝦AI，是主人的遊戲開發學習助教。

核心記憶：
{core_memory}

使用者資料：
{memory}

使用者想學：
{query}

以下是 GitHub 搜尋到的專案：

{repo_text}

請幫使用者整理：
1. 哪個專案最適合新手學
2. 每個專案大概可以學到什麼
3. 建議先看哪一個
4. 如果要做成 Unity / Godot 遊戲，可以怎麼參考
5. 給一個 30 分鐘學習任務
"""

            response = model.generate_content(prompt)
            text = getattr(response, "text", None) or str(response)

            await send_long_message(update, text)
            return

        except Exception:
            logger.exception("Learn command failed")
            await update.message.reply_text("/learn 執行時發生錯誤。")
            return

    else:
        prompt = f"""
你是龍蝦AI。

身份：
- 主人的遊戲開發助手
- 擅長 Unity、Godot、RPG設計、劇情創作
- 回答要直接、清楚、適合新手

    核心記憶：
    {core_memory}

使用者資料：
{memory}

使用者訊息：
{user_text}
"""

    try:
        response = model.generate_content(prompt)
        text = getattr(response, "text", None) or str(response)
    except Exception:
        logger.exception("Model generate failed")
        await update.message.reply_text("抱歉，處理時發生錯誤。")
        return

    try:
        await send_long_message(update, text)
    except Exception:
        logger.exception("Failed to send reply")


async def daily_github_report(app):
    global CHAT_ID

    if CHAT_ID is None:
        return

    query = choose_research_topic()
    url = "https://api.github.com/search/repositories"

    params = {
        "q": query,
        "sort": "stars",
        "order": "desc",
        "per_page": 5
    }

    try:
        result = requests.get(url, params=params, timeout=10)
        data = result.json()
        repos = data.get("items", [])

        if not repos:
            await app.bot.send_message(
                chat_id=CHAT_ID,
                text="今天沒有找到 GitHub 專案。"
            )
            return

        repo_text = ""

        for repo in repos:
            repo_text += f"""
專案：
{repo["full_name"]}

描述：
{repo.get("description") or "沒有描述"}

連結：
{repo["html_url"]}
"""

        prompt = f"""
你是龍蝦AI，是主人的遊戲開發研究員。

今天研究主題：
{query}

以下是 GitHub 搜尋到的專案：

{repo_text}

請整理：
1. 今天學到什麼
2. 最重要的三個觀念
3. 對 Unity RPG 有什麼幫助
4. 明天應該研究什麼

控制在 300 字內，語氣直接、具體。
"""

        response = model.generate_content(prompt)
        summary = getattr(response, "text", None) or str(response)

        save_research(query, summary)

        task_prompt = f"""
你是龍蝦AI。

根據今天的研究主題與心得，幫主人產生 3 個可以實作的遊戲開發任務。

研究主題：
{query}

研究心得：
{summary}

要求：
- 每個任務都要適合新手
- 每個任務 30 到 60 分鐘內可以完成
- 不要編號
- 不要解釋
- 每一行只輸出一個任務
"""

        task_response = model.generate_content(task_prompt)
        task_text = getattr(task_response, "text", None) or str(task_response)

        for line in task_text.splitlines():
            task = line.strip()

            if task:
                task = task.replace("-", "").replace("□", "").strip()
                add_task(task)

        text = f"""
🦞 今日研究報告

研究主題：
{query}

{summary}

---

我已經根據今天的研究，自動新增 3 個任務到 /tasks。

---

參考專案：
"""

        for repo in repos:
            text += f"""
⭐ {repo["stargazers_count"]}
📦 {repo["full_name"]}
🔗 {repo["html_url"]}

"""

        await app.bot.send_message(
            chat_id=CHAT_ID,
            text=text[:4000]
        )

    except Exception:
        logger.exception("daily_github_report failed")
def main():

    init_db()

    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT, reply))

    async def _daily_job(context: ContextTypes.DEFAULT_TYPE):
        await daily_github_report(context.application)

    if app.job_queue is None:
        raise RuntimeError("JobQueue 尚未啟用，請安裝 python-telegram-bot[job-queue]")

    app.job_queue.run_daily(
        _daily_job,
        time=datetime.time(hour=20, minute=0)
    )

    logger.info("龍蝦AI已啟動")
    app.run_polling()


if __name__ == "__main__":
    main()
