# app.py
import os
import hmac
import hashlib
import base64
import json
from datetime import datetime
from urllib.parse import quote_plus

import requests
from flask import Flask, request, abort, jsonify
# from dotenv import load_dotenv

# load_dotenv()

# 環境変数
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8000/callback")
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")
TARGET_SECTION_NAME = os.getenv("TARGET_SECTION_NAME", "article")

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

GRAPH_BASE = "https://graph.microsoft.com/v1.0"

app = Flask(__name__)


def verify_line_signature(request_body: bytes, signature: str) -> bool:
    """LINE署名検証"""
    if not LINE_CHANNEL_SECRET:
        app.logger.error("LINE_CHANNEL_SECRET is not set")
        return False
    hash = hmac.new(LINE_CHANNEL_SECRET.encode("utf-8"), request_body, hashlib.sha256).digest()
    expected = base64.b64encode(hash).decode("utf-8")
    return hmac.compare_digest(expected, signature)


def refresh_access_token():
    """refresh_token から access_token を取得"""
    if not (CLIENT_ID and CLIENT_SECRET and REFRESH_TOKEN):
        raise Exception("CLIENT_ID/CLIENT_SECRET/REFRESH_TOKEN が未設定です")
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

    app.logger.info("Refresh response: %s", token_data)
    if res.status_code != 200 or "access_token" not in token_data:
        raise Exception(f"アクセストークンの更新に失敗しました: {token_data}")
    return token_data["access_token"]


def get_section_id(access_token, section_name=TARGET_SECTION_NAME):
    """セクション名から Graph API 用のセクションIDを取得"""
    url = f"{GRAPH_BASE}/me/onenote/sections"
    headers = {"Authorization": f"Bearer {access_token}"}
    res = requests.get(url, headers=headers)
    if res.status_code != 200:
        raise Exception(f"セクション一覧取得失敗: status={res.status_code} body={res.text}")
    data = res.json()
    for section in data.get("value", []):
        if section.get("displayName") == section_name:
            return section.get("id")
    raise Exception(f"指定セクションが見つかりません: {section_name}")


def create_onenote_page(access_token, section_id, title, content_html):
    """
    指定セクションに新しい OneNote ページを作成する
    content_html は body 部分の HTML（XHTML 準拠が望ましい）
    """
    url = f"{GRAPH_BASE}/me/onenote/sections/{section_id}/pages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/xhtml+xml"
    }

    # OneNote 用の簡易 XHTML ページ
    html = f"""<!DOCTYPE html>
<html>
  <head>
    <title>{title}</title>
    <meta name="created" content="{datetime.utcnow().isoformat()}Z" />
  </head>
  <body>
    <h1>{title}</h1>
    <div>{content_html}</div>
  </body>
</html>"""

    res = requests.post(url, headers=headers, data=html.encode("utf-8"))
    if res.status_code not in (201, 200):
        raise Exception(f"OneNoteページ作成失敗: status={res.status_code} body={res.text}")
    return res.json()


@app.route("/line/webhook", methods=["POST"])
def line_webhook():
    # 署名検証
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data()
    if not verify_line_signature(body, signature):
        app.logger.warning("Invalid LINE signature")
        abort(403)

    payload = request.get_json(silent=True)
    if not payload:
        app.logger.warning("Empty payload")
        return jsonify({"status": "no payload"}), 400

    # イベント処理（メッセージイベントのみ対応）
    events = payload.get("events", [])
    for ev in events:
        if ev.get("type") != "message":
            continue
        message = ev.get("message", {})
        if message.get("type") != "text":
            continue

        user_text = message.get("text", "").strip()
        user_id = ev.get("source", {}).get("userId", "unknown")
        reply_token = ev.get("replyToken")

        # ここで OneNote に追記（新規ページ作成）
        try:
            access_token = refresh_access_token()
            section_id = get_section_id(access_token, TARGET_SECTION_NAME)

            # ページタイトルと本文を整形
            title = f"{user_text[:60]} - from LINE"
            # 本文は簡易にエスケープして <pre> で囲むか、必要に応じて HTML 化
            safe_content = f"<p>From LINE user: {user_id}</p><pre>{quote_plus(user_text)}</pre>"

            page = create_onenote_page(access_token, section_id, title, safe_content)
            app.logger.info("Created OneNote page: %s", page.get("id"))

            # LINE に返信（簡易）
            reply_message = {
                "type": "text",
                "text": "メッセージを OneNote に保存しました。"
            }
            reply_url = "https://api.line.me/v2/bot/message/reply"
            headers = {
                "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
                "Content-Type": "application/json"
            }
            payload = {"replyToken": reply_token, "messages": [reply_message]}
            r = requests.post(reply_url, headers=headers, json=payload)
            app.logger.info("LINE reply status: %s %s", r.status_code, r.text)

        except Exception as e:
            app.logger.exception("Failed to save to OneNote: %s", e)
            # エラー時はユーザーに通知
            try:
                reply_message = {
                    "type": "text",
                    "text": "OneNote への保存に失敗しました。管理者に確認してください。"
                }
                reply_url = "https://api.line.me/v2/bot/message/reply"
                headers = {
                    "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
                    "Content-Type": "application/json"
                }
                payload = {"replyToken": reply_token, "messages": [reply_message]}
                requests.post(reply_url, headers=headers, json=payload)
            except Exception:
                app.logger.exception("Failed to send error reply to LINE")

    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    # 開発時はポート指定で起動
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
