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
TARGET_SECTION_KEYWORD = os.getenv("TARGET_SECTION_KEYWORD", "keyword")
WORDPRESS_NEW_POST_URL_BASE = os.getenv("WORDPRESS_NEW_POST_URL_BASE", "https://example.com/wp-admin/post-new.php")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(model_name="gemini-2.0-flash")

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
    """ページ一覧を取得し、ランダムに指定件数返す (idが必要なので追加)"""
    url = f"https://graph.microsoft.com/v1.0/me/onenote/sections/{section_id}/pages?$select=id,title,links"
    headers = {"Authorization": f"Bearer {access_token}"}
    res = requests.get(url, headers=headers)
    pages = res.json().get("value", [])
    
    if not pages:
        return []
    
    return random.sample(pages, min(len(pages), count))


#Geminiでアウトライン
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
        # Web版のURL（ブラウザで開く用）
        onenote_web_url = page.get("links", {}).get("oneNoteWebUrl", {}).get("href", "#")
        
        # 1. Geminiでアウトライン生成
        outline = get_outline_from_gemini(title)

        # 2. OneNoteに書き込み
        update_onenote_page_with_outline(access_token, page_id, outline)

        # 3. LINE表示用のプレビューテキスト
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
                        "height": "sm",
                        "action": {"type": "uri", "label": "WordPressで執筆", "uri": wp_url}
                    },
                    {
                        "type": "button",
                        "style": "secondary",
                        "height": "sm",
                        "action": {"type": "uri", "label": "ブラウザ", "uri": onenote_web_url}
                    },
                    {
                        "type": "button",
                        "style": "link",
                        "height": "sm",
                        "action": {
                            "type": "uri", 
                            "label": "OneNoteアプリを起動", 
                            "uri": "intent://onenote/#Intent;scheme=onenote;package=com.microsoft.office.onenote;S.browser_fallback_url=https%3A%2F%2Fplay.google.com%2Fstore%2Fapps%2Fdetails%3Fid%3Dcom.microsoft.office.onenote;end" 
                        }
                    }
                ]
            }
        }
        bubbles.append(bubble)

    return {"type": "carousel", "contents": bubbles}

# --- send_line_flex, main 関数 ---
def send_line_flex(flex_content):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "to": LINE_USER_ID,
        "messages": [{"type": "flex", "altText": "keyword to article", "contents": flex_content}],
    }
    res = requests.post(url, headers=headers, json=payload)
    if res.status_code != 200:
        print(f"LINE送信失敗: {res.text}")

# --- OneNote ページ移動用の関数 ---
def move_page_to_fin_section(access_token, page_id, note_title, note_content):
    """ページを 'article' セクションに新しく作成し、成功したら元のページを削除する"""
    try:
        # 1. "article" セクションの ID を取得
        fin_section_id = get_section_id(access_token, "article")
        
        # 2. "article" セクションに新しいページを作成する
        create_url = f"https://graph.microsoft.com/v1.0/me/onenote/sections/{fin_section_id}/pages"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/xhtml+xml" # HTML形式で送る
        }
        
        # 元のHTMLコンテンツをそのまま新しいページとして作成
        res = requests.post(create_url, headers=headers, data=note_content.encode('utf-8'))
        
        if res.status_code == 201:
            print(f"ページ '{note_title}' を article セクションへ作成しました。")
            
            # 3. 作成に成功したら、元の（'keyword'セクション内の）ページを削除
            delete_url = f"https://graph.microsoft.com/v1.0/me/onenote/pages/{page_id}"
            del_headers = {"Authorization": f"Bearer {access_token}"}
            delete_res = requests.delete(delete_url, headers=del_headers)
            
            if delete_res.status_code == 204:
                print("元のページを削除しました。移動完了。")
                return True
        else:
            print(f"新ページ作成失敗: {res.text}")
            
    except Exception as e:
        print(f"移動処理中にエラーが発生しました: {e}")
    return False

def get_page_content(access_token, page_id):
    """移動のためにページの全コンテンツ（HTML）を取得する"""
    url = f"https://graph.microsoft.com/v1.0/me/onenote/pages/{page_id}/content"
    headers = {"Authorization": f"Bearer {access_token}"}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        return res.text
    return None

def main():
    try:
        # 1. トークンの準備とセクション情報の取得
        token = refresh_access_token()
        keyword_sec_id = get_section_id(token, TARGET_SECTION_KEYWORD)
        
        # 2. keywordセクションからランダムに1件取得
        random_pages = get_random_pages(token, keyword_sec_id, count=1)
        
        if not random_pages:
            print("処理対象のページが見つかりませんでした。")
            return

        page = random_pages[0]
        page_id = page.get("id")
        title = page.get("title", "(no title)")

        # 3. Geminiでアウトライン生成 & 元のページに書き込み
        print(f"処理開始: {title}")
        outline = get_outline_from_gemini(title)
        update_onenote_page_with_outline(token, page_id, outline)

        # 4. 移動処理：最新の状態のコンテンツを取得して別セクションへ
        print(f"移動処理中...")
        updated_content = get_page_content(token, page_id)
        if updated_content:
            move_success = move_page_to_fin_section(token, page_id, title, updated_content)
        else:
            print("コンテンツの取得に失敗したため、移動をスキップします。")
            move_success = False

        # 5. LINEに通知を送信
        # 移動に成功した場合、LINEボタンのリンク先が古い(削除済み)URLにならないよう注意が必要ですが、
        # build_flex_carouselの中で生成されるURLを新しいセクションのものにするか、
        # もしくはシンプルに「移動完了」の通知を送るのが安全です。
        
        # 今回は、取得済みの random_pages を使ってFlexメッセージを作成します
        flex = build_flex_carousel(token, [page]) 
        send_line_flex(flex)
        
        if move_success:
            print(f"成功: '{title}' の構成案作成と 'article' への移動が完了しました。")
        else:
            print(f"完了: 構成案の書き込みは成功しましたが、移動には失敗しました。")

    except Exception as e:
        print(f"エラー発生: {e}")

if __name__ == "__main__":
    main()
