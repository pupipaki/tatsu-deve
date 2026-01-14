import os
import requests
import json
import random
import re
from urllib.parse import quote_plus
import google.generativeai as genai

# --- 環境変数等はそのまま ---
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.getenv("LINE_USER_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TARGET_SECTION = "movネタ"
WORDPRESS_NEW_POST_URL_BASE = os.getenv("WORDPRESS_NEW_POST_URL_BASE", "https://example.com/wp-admin/post-new.php")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(model_name="gemini-2.5-flash") # 最新の名前に適宜調整してください

# --- トークン更新・セクション取得関数 ---
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

def get_random_pages(access_token, section_id, count=1):
    url = f"https://graph.microsoft.com/v1.0/me/onenote/sections/{section_id}/pages?$select=id,title,links"
    headers = {"Authorization": f"Bearer {access_token}"}
    res = requests.get(url, headers=headers)
    pages = res.json().get("value", [])
    if not pages:
        return []
    return random.sample(pages, min(len(pages), count))

def get_page_content(access_token, page_id):
    """ページの全コンテンツ（HTML）を取得する"""
    url = f"https://graph.microsoft.com/v1.0/me/onenote/pages/{page_id}/content"
    headers = {"Authorization": f"Bearer {access_token}"}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        return res.text
    return None

def extract_text_from_html(html_content):
    """HTMLからテキストのみを抽出（簡易版）"""
    if not html_content:
        return ""
    # タグの除去
    text = re.sub(r'<[^>]+>', ' ', html_content)
    # 連続する空白や改行を整理
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# --- Geminiでアウトライン ---
def get_outline_from_gemini(title, content):
    """Gemini APIを使用してタイトルと内容からアウトラインを生成"""
    try:
        prompt = f"""
以下のOneNoteにメモされた「タイトル」と「内容」を元に、ショート動画（YouTube Shorts/TikTok）の構成案を作成してください。

# ページタイトル
{title}

# ページの内容（ネタ詳細）
{content}

# 指示
- 各シーンのアウトラインを出力してください。
- それぞれのシーンについて画像生成AI（Midjourney）で使える英語のプロンプトを出力してください。
- 動画全体は20秒程度、各シーンは5秒程度。
- シーン数は4～5つ。

# 出力フォーマット
-シーン1の名称
-シーン1の説明
-シーン1のプロンプト

以下、シーン2以降繰り返し。
"""
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Geminiエラー: {e}")
        return "アウトラインの生成に失敗しました。"

def update_onenote_page_with_outline(access_token, page_id, outline_text):
    """OneNoteのページ末尾にアウトラインをHTML形式で追記"""
    url = f"https://graph.microsoft.com/v1.0/me/onenote/pages/{page_id}/content"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    formatted_content = outline_text.replace("\n", "<br />")
    changes = [
        {
            'target': 'body',
            'action': 'append',
            'position': 'after',
            'content': f'<div style="margin-top:20px; border-top:1px solid #ccc; padding-top:10px;">'
                       f'<h2 style="color:#2b579a">AI生成アウトライン</h2>'
                       f'<p>{formatted_content}</p></div>'
        }
    ]
    res = requests.patch(url, headers=headers, data=json.dumps(changes))
    return res.status_code == 204

def normalize_title(title, max_len=40):
    t = title.strip()
    return (t[:max_len-1] + "…") if len(t) > max_len else t

def build_flex_carousel(access_token, pages, outline_text):
    """LINE Flex Messageの構築"""
    bubbles = []
    for page in pages:
        title = page.get("title", "(no title)")
        onenote_web_url = page.get("links", {}).get("oneNoteWebUrl", {}).get("href", "#")
        
        preview_text = outline_text.split('\n')[0] if outline_text else "アウトラインを作成しました。"
        if len(preview_text) > 60:
            preview_text = preview_text[:60] + "..."

        wp_url = f"{WORDPRESS_NEW_POST_URL_BASE}?post_title={quote_plus(title)}"

        bubble = {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "AIショートネタ", "size": "xs", "color": "#1DB446", "weight": "bold"},
                    {"type": "text", "text": normalize_title(title), "weight": "bold", "size": "xl", "wrap": True, "margin": "md"},
                    {"type": "separator", "margin": "lg"},
                    {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "lg",
                        "spacing": "sm",
                        "contents": [
                            {"type": "text", "text": "【ショート】", "size": "xs", "color": "#888888", "weight": "bold"},
                            {"type": "text", "text": preview_text, "size": "sm", "color": "#333333", "wrap": True, "maxLines": 3}
                        ]
                    },
                    {"type": "text", "text": "※詳細はOneNoteに追記済み", "size": "xxs", "color": "#aaaaaa", "margin": "md"}
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "contents": [
                    {"type": "button", "style": "primary", "color": "#1DB446", "height": "sm", "action": {"type": "uri", "label": "WordPressで執筆", "uri": wp_url}},
                    {"type": "button", "style": "secondary", "height": "sm", "action": {"type": "uri", "label": "ブラウザでOneNote", "uri": onenote_web_url}}
                ]
            }
        }
        bubbles.append(bubble)
    return {"type": "carousel", "contents": bubbles}

def send_line_flex(flex_content):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {"to": LINE_USER_ID, "messages": [{"type": "flex", "altText": "動画アウトライン生成完了", "contents": flex_content}]}
    res = requests.post(url, headers=headers, json=payload)
    if res.status_code != 200:
        print(f"LINE送信失敗: {res.text}")

def move_page_to_fin_section(access_token, page_id, note_title, note_content):
    try:
        fin_section_id = get_section_id(access_token, "ショート案")
        create_url = f"https://graph.microsoft.com/v1.0/me/onenote/sections/{fin_section_id}/pages"
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/xhtml+xml"}
        
        res = requests.post(create_url, headers=headers, data=note_content.encode('utf-8'))
        if res.status_code == 201:
            delete_url = f"https://graph.microsoft.com/v1.0/me/onenote/pages/{page_id}"
            requests.delete(delete_url, headers={"Authorization": f"Bearer {access_token}"})
            return True
    except Exception as e:
        print(f"移動エラー: {e}")
    return False

# --- メイン処理 ---
def main():
    try:
        token = refresh_access_token()
        keyword_sec_id = get_section_id(token, TARGET_SECTION)
        random_pages = get_random_pages(token, keyword_sec_id, count=1)
        
        if not random_pages:
            print("処理対象のページが見つかりませんでした。")
            return

        page = random_pages[0]
        page_id = page.get("id")
        title = page.get("title", "(no title)")
        print(f"処理開始: {title}")

        # 1. ページ内容を取得
        html_content = get_page_content(token, page_id)
        # Geminiに渡すためにテキスト化
        plain_text_content = extract_text_from_html(html_content)

        # 2. Geminiでアウトライン生成 (タイトルと内容を渡す)
        outline = get_outline_from_gemini(title, plain_text_content)

        # 3. 元のページに書き込み
        update_onenote_page_with_outline(token, page_id, outline)

        # 4. 移動処理 (最新の内容を取得し直して移動)
        updated_content = get_page_content(token, page_id)
        move_success = move_page_to_fin_section(token, page_id, title, updated_content)

        # 5. LINEに通知
        flex = build_flex_carousel(token, [page], outline) 
        send_line_flex(flex)
        
        print(f"成功: '{title}' の構成案作成が完了しました。(移動: {move_success})")

    except Exception as e:
        print(f"エラー発生: {e}")

if __name__ == "__main__":
    main()
