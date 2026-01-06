import os
import requests
import json
import google.generativeai as genai
from datetime import datetime

# 環境変数の設定
LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
USER_ID = os.getenv("LINE_USER_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ONENOTE_ACCESS_TOKEN = os.getenv("ONENOTE_ACCESS_TOKEN") # 認証準備済みとのことなのでトークンを想定

# Geminiの初期設定
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

# -----------------------------
# ① Gemini API でアウトライン作成
# -----------------------------
def get_gemini_outline(keyword):
    prompt = f"{keyword}というキーワードとともに検索されそうなキーワードとともにブログネタのアウトラインを考えてください"
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Gemini API Error: {e}"

# -----------------------------
# ② OneNote に新ページを追加
# -----------------------------
def add_to_onenote(title, content):
    # 「article」セクションにページを作成するエンドポイント
    # ※セクションIDの特定が必要な場合がありますが、ここではセクション名を指定する形式の概念で記述します
    url = "https://graph.microsoft.com/v1.0/me/onenote/pages?sectionName=article"
    
    headers = {
        "Authorization": f"Bearer {ONENOTE_ACCESS_TOKEN}",
        "Content-Type": "application/xhtml+xml"
    }
    
    # OneNoteはHTML形式での入力を受け付けます
    html_content = f"""
    <!DOCTYPE html>
    <html>
      <head>
        <title>{title} - {datetime.now().strftime('%Y-%m-%d')}</title>
      </head>
      <body>
        <p>{content.replace('\n', '<br>')}</p>
      </body>
    </html>
    """
    
    try:
        res = requests.post(url, headers=headers, data=html_content.encode('utf-8'))
        return res.status_code == 201
    except Exception as e:
        print(f"OneNote Error: {e}")
        return False

# -----------------------------
# ③ Flex 生成と送信
# -----------------------------
def send_flex():
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_TOKEN}"
    }

    base_url = "https://pupipaki.github.io/tatsu-deve/images"
    
    # カテゴリ設定
    categories = [
        {"label": "🎵 ミスチル", "keyword": "ミスチル", "img": "mr.png"},
        {"label": "🎼 作曲ノウハウ", "keyword": "作曲", "img": "composition.png"},
        {"label": "🎬 動画ノウハウ", "keyword": "動画作成", "img": "video.png"},
        {"label": "🎲 ボドゲ情報", "keyword": "ボードゲーム", "img": "boardgame.png"}
    ]

    bubbles = []

    for cat in categories:
        # 1. Geminiでアウトライン取得
        outline = get_gemini_outline(cat['keyword'])
        
        # 2. OneNoteへ保存
        add_to_onenote(f"ブログネタ:{cat['keyword']}", outline)

        # 3. Flex Messageのバブル作成
        bubble = {
            "type": "bubble",
            "hero": {
                "type": "image",
                "url": f"{base_url}/{cat['img']}",
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
                        "text": outline[:100] + "...", # 長すぎるのでプレビュー表示
                        "wrap": True,
                        "size": "sm",
                        "margin": "md",
                        "color": "#666666"
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "color": "#4B9CD3",
                        "margin": "md",
                        "action": {
                            "type": "uri",
                            "label": "記事を書く",
                            "uri": "https://echo-letter.com/wp-admin/post-new.php"
                        }
                    },
                    {
                        "type": "text",
                        "text": "※OneNoteのarticleセクションに追加済み",
                        "size": "xs",
                        "color": "#888888",
                        "margin": "sm"
                    }
                ]
            }
        }
        bubbles.append(bubble)

    flex_payload = {
        "type": "flex",
        "altText": "AIが考えたブログネタアウトライン",
        "contents": {
            "type": "carousel",
            "contents": bubbles
        }
    }

    body = {
        "to": USER_ID,
        "messages": [flex_payload]
    }

    res = requests.post(url, headers=headers, data=json.dumps(body))
    print(res.status_code, res.text)

if __name__ == "__main__":
    send_flex()
