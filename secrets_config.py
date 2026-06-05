import os


def get_credentials():
    token = os.getenv("BOT_TOKEN")
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not token:
        raise ValueError("BOT_TOKEN 沒有設定")
    
    if not api_key:
        raise ValueError("GEMINI_API_KEY 沒有設定")
    
    return token, api_key