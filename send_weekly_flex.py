import os
import json
import requests

CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
USER_ID = os.getenv("LINE_USER_ID")

def build_flex_contents():
    bubble = {
        "type": "bubble",
        "hero": {
            "type": "image",
            "url": "https://scdn.line-apps.com/n/channel_devcenter/img/fx/01_1_cafe.png",
            "size": "full",
            "aspectRatio": "20:13",
            "aspectMode": "cover"
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "テスト通知",
                    "weight": "bold",
                    "size": "xl"
                },
                {
                    "type": "text",
                    "text": "これはFlex Messageの送信テストです。",
                    "wrap": True,
                    "margin": "md"
                }
            ]
        }
    }

    flex = {
        "type": "carousel",
        "contents": [bubble]
    }

    return flex

def send_flex_message():
    flex_contents = build_flex_contents()

    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}"
    }
    payload = {
        "to": USER_ID,
        "messages": [
            {
                "type": "flex",
                "altText": "テスト通知",
                "contents": flex_contents
            }
        ]
    }

    print("DEBUG USER_ID:", USER_ID)
    print("DEBUG TOKEN:", CHANNEL_ACCESS_TOKEN[:10])
    print("DEBUG Payload:", json.dumps(payload, ensure_ascii=False, indent=2))

    resp = requests.post(url, headers=headers, data=json.dumps(payload))
    print("Status:", resp.status_code, resp.text)

if __name__ == "__main__":
    send_flex_message()
