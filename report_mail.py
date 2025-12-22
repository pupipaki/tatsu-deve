import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import gspread
from oauth2client.service_account import ServiceAccountCredentials

TARGET_CITIES = ["日野市", "多摩市", "昭島市", "立川市"]
KEYWORDS = ["初心者", "ビギナー", "初ライブ", "はじめて", "入門", "初心者歓迎"]

MUSIC365_URL = "https://www.music365.jp/livehouse/tokyo/"  # 東京のライブハウス一覧

def fetch_livehouse_links():
    res = requests.get(MUSIC365_URL)
    soup = BeautifulSoup(res.text, "html.parser")
    links = []

    for a in soup.select("a"):
        href = a.get("href", "")
        if "/livehouse/" in href:
            links.append("https://www.music365.jp" + href)

    return list(set(links))

def fetch_events_from_livehouse(url):
    res = requests.get(url)
    soup = BeautifulSoup(res.text, "html.parser")

    events = []
    for event in soup.select(".event-item"):  # 仮のクラス名（実際のHTMLに合わせて調整）
        title = event.select_one(".event-title").get_text(strip=True)
        date = event.select_one(".event-date").get_text(strip=True)
        detail_url = event.select_one("a").get("href")

        # 初心者向け判定
        if any(k in title for k in KEYWORDS):
            events.append({
                "title": title,
                "date": date,
                "url": detail_url,
                "venue": soup.select_one("h1").get_text(strip=True)
            })

    return events

def generate_report(events):
    if not events:
        return "該当する初心者向けライブは見つかりませんでした。"

    lines = []
    for e in events:
        lines.append(f"""
■ {e['title']}
日付：{e['date']}
会場：{e['venue']}
URL：{e['url']}
""")
    return "\n".join(lines)

def send_mail(report):
    sender = "fujifujitatsutatsu@hotmail.com"
    password = "xdjjsnhuuazhqpht"
    receiver = "fujifujitatsutatsu@hotmail.com"

    msg = MIMEMultipart()
    msg["Subject"] = "【週次レポート】初心者向けバンドライブ情報"
    msg["From"] = sender
    msg["To"] = receiver

    msg.attach(MIMEText(report, "plain"))

    with smtplib.SMTP("smtp.office365.com", 587) as server:
        server.starttls()
        server.login(sender, password)
        server.send_message(msg)

def main():
    livehouses = fetch_livehouse_links()
    all_events = []

    for lh in livehouses:
        events = fetch_events_from_livehouse(lh)
        all_events.extend(events)

    report = generate_report(all_events)
    send_mail(report)

    #Google スプレッドシートに保存
    save_to_google_sheet(all_events)

    print("レポート送信完了")



def save_to_google_sheet(events):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)

    sheet = client.open("ライブログ").sheet1

    for e in events:
        sheet.append_row([
            e["date"],
            e["title"],
            e["venue"],
            e["url"]
        ])



if __name__ == "__main__":
    main()