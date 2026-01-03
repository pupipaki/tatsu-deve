import os
import requests
import json

# -----------------------------
# ① Graph API アクセストークン取得
# -----------------------------
def get_access_token():
    url = f"https://login.microsoftonline.com/{os.getenv('TENANT_ID')}/oauth2/v2.0/token"
    data = {
        "client_id": os.getenv("CLIENT_ID"),
        "client_secret": os.getenv("CLIENT_SECRET"),
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials"
    }
    res = requests.post(url, data=data)
    print("Graph API response:", res.status_code, res.text)  # ← ここを追加
    
    data = res.json()
    if "access_token" not in data:
        print("アクセストークン取得失敗:", data)
        raise Exception("アクセストークンが取得できませんでした")
    return data["access_token"]

# -----------------------------
# ② "WordPress"セクションID取得
# -----------------------------
def get_section_id(access_token, section_name="WordPress"):
    url = "https://graph.microsoft.com/v1.0/me/onenote/sections"
    headers = {"Authorization": f"Bearer {access_token}"}
    res = requests.get(url, headers=headers)
    print("セクション取得レスポンス:", res.status_code, res.text)  # ← ログ追加

    data = res.json()
    if "value" not in data:
        raise Exception("OneNoteセクション一覧の取得に失敗しました")

    for section in data["value"]:
        if section["displayName"] == section_name:
            return section["id"]
    return None

# -----------------------------
# ③ "article"ページ群のタイトル抽出
# -----------------------------
def get_article_titles(access_token, section_id):
    url = f"https://graph.microsoft.com/v1.0/me/onenote/sections/{section_id}/pages"
    headers = {"Authorization": f"Bearer {access_token}"}
    res = requests.get(url, headers=headers).json()
    titles = [page["title"] for page in res["value"] if "article" in page["title"].lower()]
    return titles

# -----------------------------
# ④ Flex Message生成
# -----------------------------
def build_flex(titles):
    base = "https://pupipaki.github.io/tatsu-deve/images"
    bubbles = []
    for title in titles[:5]:  # 最大5件
        bubbles.append({
            "type": "bubble",
            "hero": {
                "type": "image",
                "url": f"{base}/note.png",
                "size": "full",
                "aspectRatio": "1:1",
                "aspectMode": "cover"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "📝 ブログネタ", "weight": "bold"},
                    {"type": "text", "text": title, "wrap": True},
                    {
                        "type": "button",
                        "style": "primary",
                        "color": "#4B9CD3",
                        "action": {
                            "type": "uri",
                            "label": "この記事を書く",
                            "uri": f"https://echo-letter.com/wp-admin/post-new.php?post_title={title}"
                        }
                    }
                ]
            }
        })
    return {
        "type": "flex",
        "altText": "ブログネタ一覧",
        "contents": {
            "type": "carousel",
            "contents": bubbles
        }
    }

# -----------------------------
# ⑤ LINE通知
# -----------------------------
def send_line_message(flex):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.getenv('LINE_CHANNEL_ACCESS_TOKEN')}"
    }
    body = {
        "to": os.getenv("LINE_USER_ID"),
        "messages": [flex]
    }
    res = requests.post(url, headers=headers, data=json.dumps(body))
    print(res.status_code, res.text)

# -----------------------------
# 実行
# -----------------------------
if __name__ == "__main__":
    token = get_access_token()
    section_id = get_section_id(token)
    titles = get_article_titles(token, section_id)
    flex = build_flex(titles)
    send_line_message(flex)
