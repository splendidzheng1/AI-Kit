import json
import time
from datetime import datetime

import requests


class FinanceNews24hFetcher:
    def __init__(self):
        self.seen_ids = set()
        self.api_base = "http://zhibo.sina.com.cn/api/zhibo/feed"
        self.max_time = None

    def fetch_24h_news(self, page=1, page_size=20):
        url = f"{self.api_base}?page={page}&page_size={page_size}&zhibo_id=152"
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            data = response.json()
            if (
                "result" in data
                and "data" in data["result"]
                and "feed" in data["result"]["data"]
                and "list" in data["result"]["data"]["feed"]
            ):
                news_list = data["result"]["data"]["feed"]["list"]
                return self.parse_news(news_list)
            return []
        except Exception as e:
            print(f"获取24h新闻失败: {e}")
            return []

    def parse_news(self, raw_news_list):
        news_list = []
        for item in raw_news_list:
            try:
                multimedia = item.get("multimedia", {})
                if isinstance(multimedia, str):
                    multimedia = {}

                images = multimedia.get("img_url", [])

                news = {
                    "id": str(item.get("id", "")),
                    "title": item.get("rich_text", ""),
                    "time": item.get("create_time", ""),
                    "rich_text": item.get("rich_text", ""),
                    "images": images,
                    "source": "新浪7x24财经",
                }
                news_list.append(news)
            except Exception as e:
                continue
        return news_list

    def format_time(self, time_str):
        if not time_str:
            return ""
        try:
            return time_str
        except:
            return time_str

    def print_news(self, news):
        if not news:
            return

        formatted_time = self.format_time(news.get("time", ""))

        print(f"{formatted_time}")

        rich_text = news.get("rich_text", "")
        if rich_text:
            print(f"\n{rich_text}")

        images = news.get("images", [])
        if images:
            print(f"\n【相关图片】")
            for img in images[:2]:
                if isinstance(img, str):
                    print(f"  {img}")
                elif isinstance(img, dict):
                    print(f"  {img.get('url', '')}")

        print(f"{'=' * 100}")

    def fetch_and_print_news(self, limit=10):
        page = 1
        new_count = 0
        max_pages = 5

        while new_count < limit and page <= max_pages:
            news_list = self.fetch_24h_news(page=page, page_size=20)

            if not news_list:
                break

            news_list.sort(key=lambda x: x.get("time", ""))

            for news in news_list:
                news_time = news.get("time", "")

                if self.max_time is not None and news_time <= self.max_time:
                    continue

                if news["id"] not in self.seen_ids:
                    self.seen_ids.add(news["id"])
                    self.print_news(news)
                    new_count += 1

                    if self.max_time is None or news_time > self.max_time:
                        self.max_time = news_time

                    if new_count >= limit:
                        break

            if new_count >= limit or len(news_list) < 20:
                break

            page += 1
            time.sleep(0.5)

    def watch_news(self, interval=60):
        print(f"开始监控24小时财经新闻，每 {interval} 秒检查一次更新...")
        print("按 Ctrl+C 停止\n")

        self.fetch_and_print_news(10)
        try:
            while True:
                time.sleep(interval)
                self.fetch_and_print_news(5)
        except KeyboardInterrupt:
            print("\n已停止监控")


fetcher = FinanceNews24hFetcher()
fetcher.watch_news(interval=180)
