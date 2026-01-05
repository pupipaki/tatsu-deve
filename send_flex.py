import os
import requests
import json
from datetime import datetime


# Google Trends 用ライブラリと描画
# 必要なパッケージ: pytrends, matplotlib
# インストール例: pip install pytrends matplotlib
try:
    import matplotlib
    matplotlib.use('Agg')  # ヘッドレス環境で必須
    from pytrends.request import TrendReq
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    font_paths = [f.fname for f in font_manager.fontManager.ttflist if 'Noto' in f.name or 'IPAPGothic' in f.name or 'Meiryo' in f.name]
    if font_paths:
        plt.rcParams['font.family'] = font_manager.FontProperties(fname=font_paths[0]).get_name()

except Exception:
    TrendReq = None
    plt = None

LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
# CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
USER_ID = os.getenv("LINE_USER_ID")

# -----------------------------
# ① OneNote / Web / AI から情報取得（ダミー関数）
# -----------------------------
def get_onenote_topic():
    """
    Google Trends を使って、キーワード "ミスチル" とともに検索された関連キーワード上位10を取得して
    テキストで返します。可能なら棒グラフを作成してカレントディレクトリに 'trends_mr.png' として保存します。

    返り値: str (上位10キーワードの整形テキスト)
    """
    keyword = "ミスチル"
    max_items = 10
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    image_filename = f"trends_mr_{timestamp}.png"

    if TrendReq is None or plt is None:
        return "Google Trends を取得するためのライブラリが見つかりません。pytrends と matplotlib をインストールしてください。"

    try:
        # pytrends 初期化（日本語ロケール、タイムゾーンは JST=540）
        pytrends = TrendReq(hl='ja-JP', tz=540)

        # 関連クエリを取得
        pytrends.build_payload([keyword], cat=0, timeframe='today 12-m', geo='JP', gprop='')
        related = pytrends.related_queries()

        # related は dict 形式: { 'ミスチル': {'top': DataFrame, 'rising': DataFrame} }
        top_df = None
        if related and keyword in related and related[keyword].get('top') is not None:
            top_df = related[keyword]['top']
        else:
            # top がない場合は rising を試す
            if related and keyword in related and related[keyword].get('rising') is not None:
                top_df = related[keyword]['rising']

        if top_df is None or top_df.empty:
            return f"'{keyword}' の関連検索ワードが見つかりませんでした。"

        # 上位 N 件を抽出
        top_df = top_df.head(max_items)
        # DataFrame のカラムは通常 ['query', 'value']
        queries = top_df['query'].tolist()
        values = top_df['value'].tolist()

        # テキスト整形
        lines = [f"Google Trends: '{keyword}' と一緒に検索された上位 {len(queries)} キーワード"]
        for i, (q, v) in enumerate(zip(queries, values), start=1):
            lines.append(f"{i}. {q} — スコア: {v}")
        result_text = "\n".join(lines)

        # グラフ作成（日本語フォントの設定を試みる）
        try:
            # 日本語フォント候補
            jp_fonts = ["IPAexGothic", "Noto Sans CJK JP", "TakaoPGothic", "Yu Gothic", "Meiryo"]
            available = {f.name for f in font_manager.fontManager.ttflist}
            chosen = None
            for f in jp_fonts:
                if f in available:
                    chosen = f
                    break
            if chosen:
                plt.rcParams['font.family'] = chosen
        except Exception:
            pass  # フォント設定に失敗しても続行

        # 横棒グラフ（見やすくするために逆順にする）
        fig, ax = plt.subplots(figsize=(8, max(4, len(queries) * 0.5)))
        y_pos = list(range(len(queries)))[::-1]
        ax.barh(y_pos, values[::-1], color="#4B9CD3")
        ax.set_yticks(y_pos)
        ax.set_yticklabels(queries[::-1])
        ax.set_xlabel("スコア")
        ax.set_title(f"'{keyword}' と一緒に検索されたキーワード（上位 {len(queries)}）")
        plt.tight_layout()
        fig.savefig(image_filename, dpi=150)
        plt.close(fig)

        # 最終メッセージに画像ファイル名を付加（送信側で利用可能）
        result_text += f"\n\nグラフを '{image_filename}' に保存しました。"

        return result_text

    except Exception as e:
        return f"Google Trends の取得中にエラーが発生しました: {e}"



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

    onenote_topic_text = get_onenote_topic()
    print("get_onenote_topic() result:\n", onenote_topic_text)
    
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
                            # 必要なら onenote_topic_text をここに入れて表示できます（長文は wrap=True に）
                            {"type": "text", "text": onenote_topic_text, "wrap": True},
                            # {"type": "text", "text": "ミスチルブログ", "wrap": True},
                            # {"type": "text", "text": "最新情報", "wrap": True},
                            # {"type": "text", "text": "AIのアウトライン", "wrap": True},
                            {
                                "type": "button",
                                "style": "primary",
                                "color": "#4B9CD3",
                                "action": {
                                    "type": "uri",
                                    "label": "この記事を書く",
                                    "uri": f"https://echo-letter.com/wp-admin/post-new.php"
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



    
    # flex = {
    #     "type": "flex",
    #     "altText": "ブログネタ",
    #     "contents": {
    #         "type": "carousel",
    #         "contents": [
    #             {
    #                 "type": "bubble",
    #                 "hero": {
    #                     "type": "image",
    #                     "url": f"{base}/mr.png",
    #                     "size": "full",
    #                     "aspectRatio": "1:1",
    #                     "aspectMode": "cover"
    #                 },
    #                 "body": {
    #                     "type": "box",
    #                     "layout": "vertical",
    #                     "contents": [
    #                         {"type": "text", "text": "🎵 ミスチル", "weight": "bold"},
    #                         #{"type": "text", "text": onenote_topic, "wrap": True},
    #                         {"type": "text", "text": "ミスチルブログ", "wrap": True},
    #                         #{"type": "text", "text": web_info, "wrap": True},
    #                         {"type": "text", "text": "最新情報", "wrap": True},
    #                         #{"type": "text", "text": outline, "wrap": True},
    #                         {"type": "text", "text": "AIのアウトライン", "wrap": True},
    #                         {
    #                             "type": "button",
    #                             "style": "primary",
    #                             "color": "#4B9CD3",
    #                             "action": {
    #                                 "type": "uri",
    #                                 "label": "この記事を書く",
    #                                 "uri": f"https://echo-letter.com/wp-admin/post-new.php"
    #                             }
    #                         },
    #                         {
    #                             "type": "text",
    #                             "text": "※返信するとネタが追加されます",
    #                             "size": "xs",
    #                             "color": "#888888"
    #                         }
    #                     ]
    #                 }
    #                 # "body": {
    #                 #     "type": "box",
    #                 #     "layout": "vertical",
    #                 #     "contents": [
    #                 #         {"type": "text", "text": "🎵 ミスチル", "weight": "bold"}
    #                 #     ]
    #                 # }
    #             },
    #             {
    #                 "type": "bubble",
    #                 "hero": {
    #                     "type": "image",
    #                     "url": f"{base}/composition.png",
    #                     "size": "full",
    #                     "aspectRatio": "1:1",
    #                     "aspectMode": "cover"
    #                 },
    #                 "body": {
    #                     "type": "box",
    #                     "layout": "vertical",
    #                     "contents": [
    #                         {"type": "text", "text": "🎼 作曲ノウハウ", "weight": "bold"}
    #                     ]
    #                 }
    #             },
    #             {
    #                 "type": "bubble",
    #                 "hero": {
    #                     "type": "image",
    #                     "url": f"{base}/video.png",
    #                     "size": "full",
    #                     "aspectRatio": "1:1",
    #                     "aspectMode": "cover"
    #                 },
    #                 "body": {
    #                     "type": "box",
    #                     "layout": "vertical",
    #                     "contents": [
    #                         {"type": "text", "text": "🎬 動画ノウハウ", "weight": "bold"}
    #                     ]
    #                 }
    #             },
    #             {
    #                 "type": "bubble",
    #                 "hero": {
    #                     "type": "image",
    #                     "url": f"{base}/boardgame.png",
    #                     "size": "full",
    #                     "aspectRatio": "1:1",
    #                     "aspectMode": "cover"
    #                 },
    #                 "body": {
    #                     "type": "box",
    #                     "layout": "vertical",
    #                     "contents": [
    #                         {"type": "text", "text": "🎲 ボドゲ情報", "weight": "bold"}
    #                     ]
    #                 }
    #             }
    #         ]
    #     }
    # }

    body = {
        "to": USER_ID,
        "messages": [flex]
    }

    res = requests.post(url, headers=headers, data=json.dumps(body))
    print(res.status_code, res.text)


if __name__ == "__main__":
    print(get_onenote_topic())
    send_flex()
