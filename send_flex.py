import os
import requests
import json

LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
# CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
USER_ID = os.getenv("LINE_USER_ID")

# -----------------------------
# ① OneNote / Web / AI から情報取得（ダミー関数）
# -----------------------------
def get_onenote_topic():
    return "OneNote最新ネタ：AI作曲の新しい手法"

def get_web_trend():
    return "Web最新情報：YouTubeで癒し系動画が急上昇中"

def get_ai_outline(topic):
    return f"AIアウトライン：\n- 導入\n- {topic} の背景\n- 実践方法\n- 応用例\n- まとめ"

# -----------------------------
# ② Flex 生成
# -----------------------------
def send_flex():
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_TOKEN}"
    }

    # 画像URL（GitHub Pages）
    base = "https://pupipaki.github.io/tatsu-deve/images"

    flex = {
        "type": "flex",
        "altText": "ブログネタ",
        "contents": {
            "type": "carousel",
            "contents": [
                {
                    "type": "bubble",
                    "hero": {
                        "type": "image",
                        "url": f"{base}/mr.png",
                        "size": "full",
                        "aspectRatio": "1:1",
                        "aspectMode": "cover"
                    },
                    "body": {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {"type": "text", "text": "🎵 ミスチル", "weight": "bold"},
                            {"type": "text", "text": onenote_topic, "wrap": True},
                            {"type": "text", "text": web_info, "wrap": True},
                            {"type": "text", "text": outline, "wrap": True},
                            {
                                "type": "button",
                                "style": "primary",
                                "color": "#4B9CD3",
                                "action": {
                                    "type": "uri",
                                    "label": "この記事を書く",
                                    "uri": f"https://your-blog-editor.com/new?topic={onenote_topic}"
                                }
                            },
                            {
                                "type": "text",
                                "text": "※返信するとネタが追加されます",
                                "size": "xs",
                                "color": "#888888"
                            }
                        ]
                    }
                    # "body": {
                    #     "type": "box",
                    #     "layout": "vertical",
                    #     "contents": [
                    #         {"type": "text", "text": "🎵 ミスチル", "weight": "bold"}
                    #     ]
                    # }
                },
                {
                    "type": "bubble",
                    "hero": {
                        "type": "image",
                        "url": f"{base}/composition.png",
                        "size": "full",
                        "aspectRatio": "1:1",
                        "aspectMode": "cover"
                    },
                    "body": {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {"type": "text", "text": "🎼 作曲ノウハウ", "weight": "bold"}
                        ]
                    }
                },
                {
                    "type": "bubble",
                    "hero": {
                        "type": "image",
                        "url": f"{base}/video.png",
                        "size": "full",
                        "aspectRatio": "1:1",
                        "aspectMode": "cover"
                    },
                    "body": {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {"type": "text", "text": "🎬 動画ノウハウ", "weight": "bold"}
                        ]
                    }
                },
                {
                    "type": "bubble",
                    "hero": {
                        "type": "image",
                        "url": f"{base}/boardgame.png",
                        "size": "full",
                        "aspectRatio": "1:1",
                        "aspectMode": "cover"
                    },
                    "body": {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            {"type": "text", "text": "🎲 ボドゲ情報", "weight": "bold"}
                        ]
                    }
                }
            ]
        }
    }

    body = {
        "to": USER_ID,
        "messages": [flex]
    }

    res = requests.post(url, headers=headers, data=json.dumps(body))
    print(res.status_code, res.text)


if __name__ == "__main__":
    send_flex()
