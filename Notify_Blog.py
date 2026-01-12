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
TARGET_SECTION_NAME = os.getenv("TARGET_SECTION_NAME", "article")
WORDPRESS_NEW_POST_URL_BASE = os.getenv("WORDPRESS_NEW_POST_URL_BASE", "https://example.com/wp-admin/post-new.php")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(model_name="gemini-2.0-flash")

# --- トークン更新・セクション取得関数は変更なしのため省略 ---

def get_outline_from_gemini(title):
    """Gemini APIを使用してアウトラインを生成"""
    try:
        prompt = f"""
「{title}」というタイトルを検索する人が、今もっとも知りたい「最新の解決策」に焦点を当てたアウトラインを作成してください。
構成ルール：
- 読者が直面している「最新の課題」を具体化する（100文字程度）。
- 解決までのステップをH2見出しで3段階（Step 1~3）で構成する。
- 各見出しに、盛り込むべきキーワードや最新情報のメモを添える。
- 最後に「よくある質問」の項目を追加する。
- ※余計な説明は不要です。
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
    
    # 改行をHTMLの改行タグに変換
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

def build_flex_carousel(access_token, pages):
    bubbles = []
    for page in pages:
        page_id = page.get("id")
        title = page.get("title", "(no title)")
        onenote_url = page.get("links", {}).get("oneNoteWebUrl", {}).get("href", "#")
        
        # 1. Geminiでアウトライン生成
        outline = get_outline_from_gemini(title)

        # 2. OneNoteに書き込み
        update_onenote_page_with_outline(access_token, page_id, outline)

        # 3. LINE表示用に「最新の課題」部分だけを抽出（プレビュー用）
        # 冒頭から最初の見出しまで、あるいは最初の100文字程度
        preview_text = outline.split('\n')[0] if outline else "アウトラインを作成しました。"
        if len(preview_text) > 60:
            preview_text = preview_text[:60] + "..."

        wp_url = f"{WORDPRESS_NEW_POST_URL_BASE}?post_title={quote_plus(title)}"

        bubble = {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "記事ネタ提案", "size": "xs", "color": "#1DB446", "weight": "bold"},
                    {"type": "text", "text": normalize_title(title), "weight": "bold", "size": "xl", "wrap": True, "margin": "md"},
                    {"type": "separator", "margin": "lg"},
                    {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "lg",
                        "spacing": "sm",
                        "contents": [
                            {"type": "text", "text": "【最新の課題と解決策】", "size": "xs", "color": "#888888", "weight": "bold"},
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
                    {
                        "type": "button",
                        "style": "primary",
                        "color": "#1DB446",
                        "action": {"type": "uri", "label": "WordPressで執筆", "uri": wp_url}
                    },
                    {
                        "type": "button",
                        "style": "secondary",
                        "action": {"type": "uri", "label": "構成案を確認(OneNote)", "uri": onenote_url}
                    }
                ]
            }
        }
        bubbles.append(bubble)

    return {"type": "carousel", "contents": bubbles}

# --- send_line_flex, main 関数は変更なし ---
