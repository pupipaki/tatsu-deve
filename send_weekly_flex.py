import os
import json
import requests

CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
USER_ID = os.getenv("LINE_USER_ID")  # 後で自分のuserIdを入れる

def build_flex_contents():
    # ここは後で OneNote / スクレイピング / AI から動的に入れる
    mr_news = "新曲◯◯が発表されました"
    mr_outline = "・曲の背景\n・コード進行\n・SNSの反応"
    music_news = "海外で◯◯テクが話題"
    music_outline = "・テクの概要\n・DAW別の応用\n・実践例"
    video_news = "DaVinci Resolve 18.6 がリリース"
    video_outline = "・新機能\n・カラグレ\n・ショート動画応用"
    board_news = "BGGで新作ボドゲ◯◯が急上昇"
    board_outline = "・プレイ感\n・心理戦ポイント\n・初心者へのおすすめ度"

    # 仮の画像URL（後でAI生成画像のURLに差し替え）
    mr_image = "https://example.com/mr_children.jpg"
    music_image = "https://example.com/composition.jpg"
    video_image = "https://example.com/video_edit.jpg"
    board_image = "https://example.com/boardgame.jpg"

    flex = {
        "type": "carousel",
        "contents": [
            {
                "type": "bubble",
                "size": "mega",
                "hero": {
                    "type": "image",
                    "url": mr_image,
                    "size": "full",
                    "aspectRatio": "20:13",
                    "aspectMode": "cover"
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {"type": "text", "text": "🎵 ミスチル", "weight": "bold", "size": "lg"},
                        {"type": "text", "text": f"最新：{mr_news}", "wrap": True, "margin": "md"},
                        {"type": "text", "text": mr_outline, "wrap": True, "margin": "md"}
                    ]
                },
                "footer": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "button",
                            "style": "primary",
                            "action": {
                                "type": "message",
                                "label": "この記事を書く",
                                "text": "ミスチル記事を書く"
                            }
                        }
                    ]
                }
            },
            {
                "type": "bubble",
                "size": "mega",
                "hero": {
                    "type": "image",
                    "url": music_image,
                    "size": "full",
                    "aspectRatio": "20:13",
                    "aspectMode": "cover"
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {"type": "text", "text": "🎼 作曲ノウハウ", "weight": "bold", "size": "lg"},
                        {"type": "text", "text": f"最新：{music_news}", "wrap": True, "margin": "md"},
                        {"type": "text", "text": music_outline, "wrap": True, "margin": "md"}
                    ]
                },
                "footer": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "button",
                            "style": "primary",
                            "action": {
                                "type": "message",
                                "label": "この記事を書く",
                                "text": "作曲記事を書く"
                            }
                        }
                    ]
                }
            },
            {
                "type": "bubble",
                "size": "mega",
                "hero": {
                    "type": "image",
                    "url": video_image,
                    "size": "full",
                    "aspectRatio": "20:13",
                    "aspectMode": "cover"
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {"type": "text", "text": "🎬 動画制作", "weight": "bold", "size": "lg"},
                        {"type": "text", "text": f"最新：{video_news}", "wrap": True, "margin": "md"},
                        {"type": "text", "text": video_outline, "wrap": True, "margin": "md"}
                    ]
                },
                "footer": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "button",
                            "style": "primary",
                            "action": {
                                "type": "message",
                                "label": "この記事を書く",
                                "text": "動画記事を書く"
                            }
                        }
                    ]
                }
            },
            {
                "type": "bubble",
                "size": "mega",
                "hero": {
                    "type": "image",
                    "url": board_image,
                    "size": "full",
                    "aspectRatio": "20:13",
                    "aspectMode": "cover"
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {"type": "text", "text": "🎲 ボードゲーム", "weight": "bold", "size": "lg"},
                        {"type": "text", "text": f"最新：{board_news}", "wrap": True, "margin": "md"},
                        {"type": "text", "text": board_outline, "wrap": True, "margin": "md"}
                    ]
                },
                "footer": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "button",
                            "style": "primary",
                            "action": {
                                "type": "message",
                                "label": "この記事を書く",
                                "text": "ボドゲ記事を書く"
                            }
                        }
                    ]
                }
            }
        ]
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
                "altText": "今週のブログネタ案",
                "contents": flex_contents
            }
        ]
    }

    resp = requests.post(url, headers=headers, data=json.dumps(payload))
    print("Status:", resp.status_code, resp.text)

if __name__ == "__main__":
    send_flex_message()
