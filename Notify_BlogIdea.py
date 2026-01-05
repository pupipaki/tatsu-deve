import os
import requests
import json

# 必要な環境変数（ローカル or GitHub Actions Secrets）
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8000/callback")
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.getenv("LINE_USER_ID")

# OneNoteでタイトルを取りたいセクション名
TARGET_SECTION_NAME = os.getenv("TARGET_SECTION_NAME", "article")


def refresh_access_token():
    if not REFRESH_TOKEN or not CLIENT_ID or not CLIENT_SECRET:
        raise Exception("環境変数が未設定です: CLIENT_ID/CLIENT_SECRET/REFRESH_TOKEN を確認してください")

    url = "https://login.microsoftonline.com/consumers/oauth2/v2.0/token"
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "refresh_token",
    }
    res = requests.post(url, data=data)
    try:
        token_data = res.json()
    except ValueError:
        raise Exception(f"トークン取得でJSON解析失敗: status={res.status_code} body={res.text}")

    print("Refresh response:", res.status_code, token_data)
    if res.status_code != 200 or "access_token" not in token_data:
        raise Exception(f"アクセストークンの更新に失敗しました: {token_data}")

    return token_data["access_token"]


def get_section_id(access_token, section_name=TARGET_SECTION_NAME):
    url = "https://graph.microsoft.com/v1.0/me/onenote/sections"
    headers = {"Authorization": f"Bearer {access_token}"}
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        raise Exception(f"セクション一覧取得失敗: status={res.status_code} body={res.text}")
    data = res.json()
    for section in data.get("value", []):
        if section.get("displayName") == section_name:
            return section.get("id")
    raise Exception(f"指定セクションが見つかりません: {section_name}")

def get_page_titles(access_token, section_id):
    url = f"https://graph.microsoft.com/v1.0/me/onenote/sections/{section_id}/pages"
    headers = {"Authorization": f"Bearer {access_token}"}
    titles = []
    while url:
        res = requests.get(url, headers=headers)
        if res.status_code != 200:
            raise Exception(f"ページ一覧取得失敗: status={res.status_code} body={res.text}")
        data = res.json()
        for page in data.get("value", []):
            titles.append(page.get("title", "(no title)"))
        url = data.get("@odata.nextLink")  # 次ページがあればループ
    return titles


def build_flex_message(titles):
    """
    ページタイトルだけを縦に並べたシンプルなFlex Bubbleを生成
    """
    if not titles:
        titles = ["（今週のネタはありません）"]

    contents = []
    for title in titles:
        contents.append({
            "type": "text",
            "text": title,
            "weight": "bold",
            "size": "sm",
            "wrap": True,
            "margin": "md",
        })

    bubble = {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": contents,
        }
    }
    return bubble


def send_line_flex(flex_content):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "to": LINE_USER_ID,
        "messages": [
            {
                "type": "flex",
                "altText": "ブログネタ一覧",
                "contents": flex_content,
            }
        ],
    }
    res = requests.post(url, headers=headers, json=payload)
    print("LINE通知レスポンス:", res.status_code, res.text)
    if res.status_code != 200:
        # 403/401 は認証、429 はレート制限、500系はサーバーエラー
        raise Exception(f"LINE通知に失敗しました: status={res.status_code} body={res.text}")


def main():
    # 1. アクセストークン更新
    access_token = refresh_access_token()

    # 2. セクションID取得
    section_id = get_section_id(access_token, TARGET_SECTION_NAME)
    print("ターゲットセクションID:", section_id)

    # 3. ページタイトル一覧取得
    titles = get_page_titles(access_token, section_id)
    print("取得タイトル数:", len(titles))

    # 4. Flex生成
    flex = build_flex_message(titles)

    # 5. LINE通知
    send_line_flex(flex)


if __name__ == "__main__":
    main()
