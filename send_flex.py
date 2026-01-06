import os
import requests
import json
from datetime import datetime
from urllib.parse import quote_plus
import google.generativeai as genai
import html

# --- 環境変数（OneNote / LINE / Gemini） ---
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")
LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
USER_ID = os.getenv("LINE_USER_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TARGET_SECTION_NAME = os.getenv("TARGET_SECTION_NAME", "article")

# Geminiの設定
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(model_name="gemini-2.5-flash")

# -----------------------------
# ① OneNote 認証・操作関連
# -----------------------------
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



def create_onenote_page(access_token, section_id, title, content):
    """OneNoteの指定セクションに新しいページを作成する"""
    url = f"https://graph.microsoft.com/v1.0/me/onenote/sections/{section_id}/pages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "text/html"
    }

    # Geminiのアウトラインを安全なHTMLに変換
    safe_content = html.escape(content).replace('\n', '<br>')

    # OneNoteが受け入れやすい最小構造
    html_body = f"""<!DOCTYPE html>
<html>
<head><title>{title}</title></head>
<body>
<p>{safe_content}</p>
</body>
</html>"""

    print("=== OneNote HTML ===")
    print(html_body)
    print("====================")

    res = requests.post(url, headers=headers, data=html_body.encode('utf-8'))
    if res.status_code == 201:
        return res.json().get("links", {}).get("oneNoteWebUrl", {}).get("href", "#")
    else:
        print(f"OneNote作成失敗: {res.text}")
        return "#"

# -----------------------------
# ② Gemini API でアウトライン作成
# -----------------------------
def get_ai_outline(keyword):
    prompt = f"{keyword}というキーワードとともに検索されそうなキーワードとともにブログネタのアウトラインを考えてください"
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI生成エラー: {e}"

# -----------------------------
# ③ LINE Flex Message 送信
# -----------------------------
def send_combined_process():
    try:
        # トークン取得とセクションIDの特定
        access_token = refresh_access_token()
        section_id = get_section_id(access_token, TARGET_SECTION_NAME)

        # 各カテゴリの設定
        categories = [
            {"label": "🎵 ミスチル", "keyword": "ミスチル", "img": "mr.png"},
            {"label": "🎼 作曲ノウハウ", "keyword": "作曲", "img": "composition.png"},
            {"label": "🎬 動画作成ノウハウ", "keyword": "動画作成", "img": "video.png"},
            {"label": "🎲 ボドゲ情報", "keyword": "ボードゲーム", "img": "boardgame.png"}
        ]

        base_img_url = "https://pupipaki.github.io/tatsu-deve/images"
        bubbles = []

        for cat in categories:
            # 1. Geminiでアウトライン生成
            outline = get_ai_outline(cat['keyword'])
            
            # 2. OneNoteに新ページ追加
            page_title = f"{cat['keyword']}のブログネタ_{datetime.now().strftime('%Y%m%d')}"
            onenote_url = create_onenote_page(access_token, section_id, page_title, outline)

            # 3. カルーセルのバブルを作成
            if outline.startswith("AI生成エラー") or not outline.strip():
                text_preview = "AI生成に失敗しました"
            else:
                text_preview = outline.strip()[:100] + "..."
            bubble = {
                "type": "bubble",
                "hero": {
                    "type": "image",
                    "url": f"{base_img_url}/{cat['img']}",
                    "size": "full",
                    "aspectRatio": "1:1",
                    "aspectMode": "cover"
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {"type": "text", "text": cat['label'], "weight": "bold", "size": "xl"},
                        {
                            "type": "text",
                            "text": outline[:100] + "...", # プレビュー用に冒頭のみ
                            "wrap": True,
                            "size": "sm",
                            "margin": "md",
                            "color": "#666666"
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
                            "color": "#4B9CD3",
                            "action": {
                                "type": "uri", 
                                "label": "WPで記事を書く", 
                                "uri": f"https://echo-letter.com/wp-admin/post-new.php?post_title={quote_plus(page_title)}"
                            }
                        },
                        {
                            "type": "button",
                            "style": "secondary",
                            "action": {
                                "type": "uri",
                                "label": "OneNoteで詳細を見る",
                                "uri": onenote_url
                            }
                        }
                    ]
                }
            }
            bubbles.append(bubble)

        # LINE送信
        push_url = "https://api.line.me/v2/bot/message/push"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LINE_TOKEN}"
        }
        payload = {
            "to": USER_ID,
            "messages": [{
                "type": "flex",
                "altText": "AI生成ブログネタ",
                "contents": {
                    "type": "carousel",
                    "contents": bubbles
                }
            }]
        }
        res = requests.post(push_url, headers=headers, json=payload)
        print(f"LINE送信結果: {res.status_code}")

    except Exception as e:
        print(f"エラー発生: {e}")

if __name__ == "__main__":
    send_combined_process()
