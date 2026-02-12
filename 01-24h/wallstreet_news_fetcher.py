import json
import time
from datetime import datetime

import requests


class WallStreetNewsFetcher:
    def __init__(self):
        self.seen_ids = set()
        self.api_base = "https://api-prod.wallstreetcn.com/apiv1/content/lives/pc"

        # 配置：控制获取哪些频道
        self.enabled_channels = ["all"]

        # 频道显示名称映射
        self.channel_map = {
            "global-channel": "宏观",
            "blockchain-channel": "区块链",
            "a-stock-channel": "A股",
            "us-stock-channel": "美股",
            "forex-channel": "外汇",
            "commodity-channel": "商品",
            "all": "全部",
        }

    def fetch_news(self, limit=40):
        """获取华尔街见闻实时快讯"""
        url = f"{self.api_base}?limit={limit}"

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Referer": "https://wallstreetcn.com/",
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            data = response.json()
            if "data" in data:
                all_news = []
                for channel_key, channel_data in data["data"].items():
                    if isinstance(channel_data, dict) and "items" in channel_data:
                        all_news.extend(channel_data["items"])
                return self.parse_news(all_news)
            return []
        except Exception as e:
            print(f"获取华尔街见闻快讯失败: {e}")
            return []

    def parse_news(self, raw_news_list):
        """解析并过滤新闻数据"""
        news_list = []
        processed_ids = set()

        for item in raw_news_list:
            try:
                news_id = str(item.get("id", ""))

                if news_id in processed_ids:
                    continue
                processed_ids.add(news_id)

                channels = item.get("channels", [])

                # 检查是否为目标频道
                matched_channel = None
                for ch in channels:
                    if "all" in self.enabled_channels or ch in self.enabled_channels:
                        matched_channel = ch
                        break

                if not matched_channel:
                    continue

                content_text = item.get("content_text", "")
                if not content_text:
                    content = item.get("content", "")
                    import re

                    content_text = re.sub(r"<[^>]+>", "", content)

                news = {
                    "id": news_id,
                    "title": content_text,
                    "time": item.get("display_time", ""),
                    "content": content_text,
                    "channel": matched_channel,
                    "uri": item.get("uri", ""),
                }
                news_list.append(news)
            except Exception as e:
                continue
        return news_list

    def format_time(self, time_str):
        """格式化时间显示"""
        if not time_str:
            return ""
        try:
            if isinstance(time_str, (int, float)):
                dt = datetime.fromtimestamp(int(time_str))
                return dt.strftime("%m-%d %H:%M")
            elif "T" in time_str:
                dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                return dt.strftime("%m-%d %H:%M")
            elif time_str.isdigit() and len(time_str) == 10:
                dt = datetime.fromtimestamp(int(time_str))
                return dt.strftime("%m-%d %H:%M")
            else:
                return time_str
        except:
            return time_str

    def print_news(self, news):
        """精简打印新闻信息"""
        formatted_time = self.format_time(news.get("time", ""))
        channel = self.channel_map.get(news.get("channel", ""), "其他")
        content = news.get("content", "")

        print(f"{formatted_time} [{channel}] {content}")

    def fetch_and_print_news(self, limit=10):
        """获取并打印新闻"""
        news_list = self.fetch_news(limit=40)

        if not news_list:
            return

        # 按时间从小到大排序
        news_list.sort(key=lambda x: x.get("time", ""))

        new_count = 0
        for news in news_list:
            if news["id"] not in self.seen_ids:
                self.seen_ids.add(news["id"])
                self.print_news(news)
                new_count += 1

                if new_count >= limit:
                    break

        if new_count > 0:
            print(f"\n--- 新增 {new_count} 条 ---\n")

    def watch_news(self, interval=60):
        """持续监控新闻"""
        enabled_channels_str = "、".join(
            [self.channel_map[ch] for ch in self.enabled_channels]
        )
        print(f"华尔街见闻实时快讯监控器")
        print(f"监控频道: {enabled_channels_str}")
        print(f"每 {interval} 秒检查一次更新...")
        print("按 Ctrl+C 停止\n")

        # 首次获取
        print("首次获取最新快讯...\n")
        self.fetch_and_print_news(limit=10)

        try:
            while True:
                time.sleep(interval)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 检查更新...")
                self.fetch_and_print_news(limit=5)
        except KeyboardInterrupt:
            print("\n已停止监控")


def main():
    fetcher = WallStreetNewsFetcher()
    fetcher.watch_news()


if __name__ == "__main__":
    main()
