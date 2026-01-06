import os
import requests
import json
import random
from urllib.parse import quote_plus
import google.generativeai as genai

# --- 環境変数 ---
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8000/callback")
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.getenv("LINE_USER_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TARGET_SECTION_NAME = os.getenv("TARGET_SECTION_NAME", "article")
WORDPRESS_NEW_POST_URL_BASE = os.getenv("WORDPRESS_NEW_POST_URL_BASE", "https://example.com/wp-admin/post-new.php")

# Geminiの設定 (最新の2.0 Flashを推奨)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(model_name="gemini-2.0-flash")

def refresh_access_token():
    if not REFRESH_TOKEN or not CLIENT_ID or not CLIENT_SECRET:
        raise Exception("環境変数が未設定です")
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
        raise Exception(f"トークン更新失敗: {token_data}")
    return token_data["access_token"]

def get_section_id(access_token, section_name):
    url = "https://graph.microsoft.com/v1.0/me/onenote/sections"
    headers = {"Authorization": f"Bearer {access_token}"}
    res = requests.get(url, headers=headers)
    data = res.json()
    for section in data.get("value", []):
        if section.get("displayName") == section_name:
            return section.get("id")
    raise Exception(f"セクションが見つかりません: {section_name}")

def get_random_pages(access_token, section_id, count=5):
    """ページ一覧を取得し、ランダムに指定件数返す (idが必要なので追加)"""
    url = f"https://graph.microsoft.com/v1.0/me/onenote/sections/{section_id}/pages?$select=id,title,links"
    headers = {"Authorization": f"Bearer {access_token}"}
    res = requests.get(url, headers=headers)
    pages = res.json().get("value", [])
    
    if not pages:
        return []
    
    return random.sample(pages, min(len(pages), count))

def get_keywords_from_gemini(title):
    """Gemini APIを使用してキーワードを3つ抽出"""
    try:
        prompt = f"「{title}」というブログ記事のタイトルに対して、検索されそうなキーワードを3つ、カンマ区切りで出力してください。余計な説明は不要です。"
        response = model.generate_content(prompt)
        return response.text.replace(" ", "").replace("\n", "").split(",")
    except Exception as e:
        print(f"Geminiエラー: {e}")
        return ["キーワード取得失敗"]

def update_onenote_page_with_keywords(access_token, page_id, keywords):
    """OneNoteのページ末尾にキーワードを書き込む"""
    url = f"https://graph.microsoft.com/v1.0/me/onenote/pages/{page_id}/content"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    keyword_text = " / ".join(keywords)
    # ページの最後にHTML要素として追記するPATCHコマンド
    changes = [
        {
            'target': 'body',
            'action': 'append',
            'position': 'after',
            'content': f'<p style="color:gray">AI生成キーワード: {keyword_text}</p>'
        }
    ]
    
    res = requests.patch(url, headers=headers, data=json.dumps(changes))
    if res.status_code != 204:
        print(f"OneNote更新失敗 (PageID: {page_id}): {res.status_code} {res.text}")
    else:
        print(f"OneNoteにキーワードを書き込みました: {keyword_text}")

def normalize_title(title, max_len=40):
    t = title.strip()
    return (t[:max_len-1] + "…") if len(t) > max_len else t

def build_flex_carousel(access_token, pages):
    bubbles = []
    for page in pages:
        page_id = page.get("id")
        title = page.get("title", "(no title)")
        onenote_url = page.get("links", {}).get("oneNoteWebUrl", {}).get("href", "#")
        safe_title = normalize_title(title)
        
        # 1. Geminiでキーワード取得
        keywords = get_keywords_from_gemini(title)
        keyword_text = " / ".join(keywords[:3])

        # 2. OneNoteのページにキーワードを書き込む (追加機能)
        update_onenote_page_with_keywords(access_token, page_id, keywords[:3])

        wp_url = f"{WORDPRESS_NEW_POST_URL_BASE}?post_title={quote_plus(title)}"

        bubble = {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": safe_title, "weight": "bold", "size": "md", "wrap": True},
                    {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "lg",
                        "spacing": "sm",
                        "contents": [
                            {"type": "text", "text": "おすすめキーワード:", "size": "xs", "color": "#888888"},
                            {"type": "text", "text": keyword_text, "size": "sm", "color": "#111111", "wrap": True}
                        ]
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "contents": [
                    {
                        "type": "button",
                        "style": "primary",
                        "height": "sm",
                        "action": {"type": "uri", "label": "WPで記事を書く", "uri": wp_url}
                    },
                    {
                        "type": "button",
                        "style": "secondary",
                        "height": "sm",
                        "action": {"type": "uri", "label": "OneNoteで開く", "uri": onenote_url}
                    }
                ]
            }
        }
        bubbles.append(bubble)

    return {"type": "carousel", "contents": bubbles}

def send_line_flex(flex_content):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "to": LINE_USER_ID,
        "messages": [{"type": "flex", "altText": "本日のブログネタ", "contents": flex_content}],
    }
    res = requests.post(url, headers=headers, json=payload)
    if res.status_code != 200:
        print(f"LINE送信失敗: {res.text}")

def main():
    try:
        token = refresh_access_token()
        sec_id = get_section_id(token, TARGET_SECTION_NAME)
        random_pages = get_random_pages(token, sec_id, count=5)
        
        if not random_pages:
            print("ページが見つかりませんでした。")
            return

        # access_tokenを引数に追加
        flex = build_flex_carousel(token, random_pages)
        send_line_flex(flex)
        print("処理が正常に完了しました。")
    except Exception as e:
        print(f"エラー発生: {e}")

if __name__ == "__main__":
    main()
