import os
import requests
import json
import google.generativeai as genai
from requests.auth import HTTPBasicAuth
from urllib.parse import quote_plus

# --- 環境変数 ---
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8000/callback")
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.getenv("LINE_USER_ID")

# OneNote設定
TARGET_SECTION_NAME = os.getenv("TARGET_SECTION_NAME", "write") # 変更点：writeセクション

# Gemini設定
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# WordPress設定
WP_USERNAME = os.getenv("WP_USERNAME")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")
WP_SITE_URL = os.getenv("WP_SITE_URL") # 例: https://yourblog.com

# --- 1. OneNote API 関連 ---

def refresh_access_token():
    url = "https://login.microsoftonline.com/consumers/oauth2/v2.0/token"
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN,
        "grant_type": "refresh_token",
    }
    res = requests.post(url, data=data)
    token_data = res.json()
    if res.status_code != 200:
        raise Exception(f"MSトークン更新失敗: {token_data}")
    return token_data["access_token"]

def get_section_id(access_token, section_name):
    url = "https://graph.microsoft.com/v1.0/me/onenote/sections"
    headers = {"Authorization": f"Bearer {access_token}"}
    res = requests.get(url, headers=headers)
    data = res.json()
    for section in data.get("value", []):
        if section.get("displayName") == section_name:
            return section.get("id")
    raise Exception(f"セクション {section_name} が見つかりません")

def get_pages_in_section(access_token, section_id):
    """セクション内のページ一覧（IDとタイトル）を取得"""
    url = f"https://graph.microsoft.com/v1.0/me/onenote/sections/{section_id}/pages?$select=id,title"
    headers = {"Authorization": f"Bearer {access_token}"}
    res = requests.get(url, headers=headers)
    return res.json().get("value", [])

def get_page_content(access_token, page_id):
    """特定ページの本文（HTML）を取得"""
    url = f"https://graph.microsoft.com/v1.0/me/onenote/pages/{page_id}/content"
    headers = {"Authorization": f"Bearer {access_token}"}
    res = requests.get(url, headers=headers)
    return res.text # HTML形式で返る

# --- 2. Gemini API 関連 ---

def generate_blog_with_gemini(note_title, note_content):
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
    
    prompt = f"""
    以下のメモ（タイトルと内容）を元に、ブログ記事の下書きを作成してください。
    
    【元のメモタイトル】: {note_title}
    【元のメモ内容】: {note_content}
    
    【出力ルール】:
    1. 読者が読みたくなる魅力的な記事タイトルを考えてください。
    2. 記事の構成（目次案）を最初に示してください。
    3. 本文は、読者に寄り添った丁寧な口調で、詳しく書いてください。
    4. HTML形式（h2, h3, pタグなど）で出力してください。
    """
    
    response = model.generate_content(prompt)
    return response.text

# --- 3. WordPress API 関連 ---

def post_to_wordpress(title, content):
    url = f"{WP_SITE_URL}/wp-json/wp/v2/posts"
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    
    payload = {
        "title": title,
        "content": content,
        "status": "draft"  # 下書きとして保存
    }
    
    res = requests.post(url, json=payload, auth=auth)
    if res.status_code == 201:
        return res.json().get("link") # 作成された記事のリンク
    else:
        print(f"WP投稿失敗: {res.text}")
        return None

# --- 4. LINE 通知 関連 ---

def send_line_notification(message):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "to": LINE_USER_ID,
        "messages": [{"type": "text", "text": message}]
    }
    requests.post(url, headers=headers, json=payload)

# --- メイン処理 ---

def main():
    try:
        # 1. OneNoteからネタを取得
        access_token = refresh_access_token()
        section_id = get_section_id(access_token, TARGET_SECTION_NAME)
        pages = get_pages_in_section(access_token, section_id)
        
        if not pages:
            print("処理対象のページがありませんでした。")
            return

        for page in pages:
            page_id = page['id']
            original_title = page['title']
            print(f"処理開始: {original_title}")
            
            # 本文取得
            note_content = get_page_content(access_token, page_id)
            
            # 2. Geminiで下書き生成
            print("Geminiが執筆中...")
            generated_text = generate_blog_with_gemini(original_title, note_content)
            
            # 3. WordPressに投稿
            print("WordPressに下書き保存中...")
            wp_link = post_to_wordpress(original_title, generated_text)
            
            # 4. LINE通知
            if wp_link:
                msg = f"✅ ブログの下書き作成完了！\n元ネタ: {original_title}\nURL: {wp_link}"
                send_line_notification(msg)
                print(f"完了通知送信済: {original_title}")
            
    except Exception as e:
        error_msg = f"❌ システムエラーが発生しました:\n{str(e)}"
        send_line_notification(error_msg)
        print(error_msg)

if __name__ == "__main__":
    main()
