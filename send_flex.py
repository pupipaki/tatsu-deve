import os
import requests
import json

LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
# CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
USER_ID = os.getenv("LINE_USER_ID")

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
        "altText": "今週のAI画像が届きました！",
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
                            {"type": "text", "text": "🎵 MRジャンル", "weight": "bold"}
                        ]
                    }
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
                            {"type": "text", "text": "🎼 作曲ジャンル", "weight": "bold"}
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
                            {"type": "text", "text": "🎬 動画ジャンル", "weight": "bold"}
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
                            {"type": "text", "text": "🎲 ボードゲーム", "weight": "bold"}
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
