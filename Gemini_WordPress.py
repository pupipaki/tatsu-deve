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
    model = genai.GenerativeModel(model_name="gemini-2.5-flash")
    
    prompt = f"""
    以下のメモ（タイトルと内容）を元に、ブログ記事の下書きを作成してください。
    
    【元のメモタイトル】: {note_title}
    【元のメモ内容】: {note_content}
    
    【出力ルール】:
    1.読者が検索しそうな「メインキーワード」と「関連キーワード」を5つ抽出してください。
    2. 記事の構成（目次案）を最初に示してください。
    3.記事タイトルにはメインキーワードを必ず含めてください。
    4. 本文は、読者に寄り添った丁寧な口調で、詳しく書いてください。
    5. HTML形式（h2, h3, pタグなど）で出力してください。
    6.**重要**: 出力の最後に、以下の形式でメタデータを付与してください。
       [KEYWORDS]: キーワード1, キーワード2, キーワード3...
       [DESCRIPTION]: 記事の要約（120文字以内）
    """
    
    response = model.generate_content(prompt)
    return response.text

# --- 3. WordPress API 関連 ---
def post_to_wordpress(title, content, keywords=None):
    url = f"{WP_SITE_URL}/wp-json/wp/v2/posts"
    auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    
    payload = {
        "title": title,
        "content": content,
        "status": "draft",
        "tags": keywords  # キーワードをタグとして登録
    }
    
    # 実際には、キーワード文字列をタグIDに変換するか、
    # 文字列のまま扱えるプラグインの設定が必要です。
    # 標準APIではタグID（数値）の配列を受け取ります。

# def post_to_wordpress(title, content):
#     url = f"{WP_SITE_URL}/wp-json/wp/v2/posts"
#     auth = HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)
    
#     payload = {
#         "title": title,
#         "content": content,
#         "status": "draft"
#     }
    
    try:
        res = requests.post(url, json=payload, auth=auth)
        # 成功以外（401, 403, 404など）なら例外を発生させる
        res.raise_for_status() 
        return res.json().get("link")
    except requests.exceptions.RequestException as e:
        print(f"WP投稿エラー詳細: {e}")
        if res is not None:
             print(f"サーバーからのレスポンス: {res.text[:200]}") # 冒頭200文字を表示
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

# --- OneNote ページ移動用の関数 ---
def move_page_to_fin_section(access_token, page_id, note_title, note_content):
    """ページを 'fin' セクションに新しく作成し、成功したら元のページを削除する"""
    try:
        # 1. "fin" セクションの ID を取得
        fin_section_id = get_section_id(access_token, "fin")
        
        # 2. "fin" セクションに新しいページを作成する
        create_url = f"https://graph.microsoft.com/v1.0/me/onenote/sections/{fin_section_id}/pages"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/xhtml+xml" # HTML形式で送る
        }
        
        # 元のHTMLコンテンツをそのまま新しいページとして作成
        res = requests.post(create_url, headers=headers, data=note_content.encode('utf-8'))
        
        if res.status_code == 201:
            print(f"ページ '{note_title}' を fin セクションへ作成しました。")
            
            # 3. 作成に成功したら、元の（'write'セクション内の）ページを削除
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

# --- メイン処理 (修正版) ---

def main():
    try:
        access_token = refresh_access_token()
        section_id = get_section_id(access_token, TARGET_SECTION_NAME)
        pages = get_pages_in_section(access_token, section_id)
        
        if not pages:
            print("処理対象のページがありませんでした。")
            return

        for page in pages:
            page_id = page['id']
            original_title = page['title']
            print(f"--- 処理開始: {original_title} ---")
            
            # 本文取得
            note_content = get_page_content(access_token, page_id)
            
            # Geminiで下書き生成
            generated_text = generate_blog_with_gemini(original_title, note_content)
            
            # WordPressに投稿
            wp_link = post_to_wordpress(original_title, generated_text)
            
            # 投稿に成功したら移動処理を行う
            if wp_link:
                # LINE通知
                msg = f"✅ ブログ下書き完了！\n元ネタ: {original_title}\nURL: {wp_link}"
                send_line_notification(msg)
                
                # --- 追加：処理済みページを "fin" セクションへ移動 ---
                move_page_to_fin_section(access_token, page_id, original_title, note_content)
                print(f"ページ '{original_title}' を fin セクションへ移動しました。")
            
    except Exception as e:
        error_msg = f"❌ システムエラー:\n{str(e)}"
        send_line_notification(error_msg)
        print(error_msg)


if __name__ == "__main__":
    main()
