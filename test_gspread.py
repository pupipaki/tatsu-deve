import gspread
from oauth2client.service_account import ServiceAccountCredentials

def test_google_sheet():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = ServiceAccountCredentials.from_json_keyfile_name(
        "credentials.json", scope
    )
    client = gspread.authorize(creds)

    # ここはあなたが作ったスプレッドシート名に変更
    sheet = client.open("ライブログ").sheet1

    sheet.append_row(["テスト成功", "Google Sheets 連携OK"])

    print("✅ Google Sheets への書き込み成功")

if __name__ == "__main__":
    test_google_sheet()