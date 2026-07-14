#!/usr/bin/env python3
import feedparser
import requests
import os
import time
from datetime import datetime
from email.utils import formatdate
from xml.sax.saxutils import escape

# 配置
FEEDS_FILE = 'feeds.txt'
OUTPUT_DIR = 'public'
OUTPUT_FILE = os.path.join(OUTPUT_DIR, 'feed.xml')
MAX_ITEMS_PER_FEED = 20  # 每个源最多保留20条
TOTAL_MAX_ITEMS = 200    # 聚合后总条目最多200条
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

def load_feeds():
    """加载订阅源列表"""
    feeds = []
    if os.path.exists(FEEDS_FILE):
        with open(FEEDS_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    feeds.append(line)
    return feeds

def fetch_feed(url):
    """抓取单个RSS源"""
    items = []
    try:
        headers = {'User-Agent': USER_AGENT}
        resp = requests.get(url, headers=headers, timeout=15, verify=False)
        resp.encoding = resp.apparent_encoding or 'utf-8'
        feed = feedparser.parse(resp.content)
        
        for entry in feed.entries[:MAX_ITEMS_PER_FEED]:
            # 提取字段
            title = entry.get('title', '无标题')
            link = entry.get('link', '')
            if not link:
                continue
            # 时间处理
            pub_date = entry.get('published_parsed') or entry.get('updated_parsed')
            if pub_date:
                pub_ts = time.mktime(pub_date)
            else:
                pub_ts = time.time()
            # 描述/内容
            description = entry.get('summary', '')
            if entry.get('content'):
                description = entry['content'][0].get('value', description)
            # 来源
            source = feed.feed.get('title', url)
            
            items.append({
                'title': title,
                'link': link,
                'pub_ts': pub_ts,
                'pub_date': formatdate(pub_ts, localtime=False),
                'description': description,
                'source': source
            })
        print(f'✅ 成功抓取 {url}: {len(items)} 条')
    except Exception as e:
        print(f'❌ 抓取失败 {url}: {str(e)}')
    return items

def deduplicate(items):
    """去重，按链接去重"""
    seen = set()
    unique_items = []
    for item in items:
        link = item['link'].strip()
        if link not in seen:
            seen.add(link)
            unique_items.append(item)
    # 按时间倒序排序
    unique_items.sort(key=lambda x: x['pub_ts'], reverse=True)
    return unique_items[:TOTAL_MAX_ITEMS]

def generate_rss(items):
    """生成标准RSS 2.0 XML文件"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    rss_header = f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
  <title>我的专属聚合RSS</title>
  <link>https://baich110.github.io/rss-feed/</link>
  <description>自动聚合多个优质科技/数码/技术资讯源，每小时更新</description>
  <language>zh-CN</language>
  <lastBuildDate>{formatdate(localtime=False)}</lastBuildDate>
  <atom:link href="https://baich110.github.io/rss-feed/feed.xml" rel="self" type="application/rss+xml" />
'''
    
    rss_items = ''
    for item in items:
        title = escape(item['title'])
        link = escape(item['link'])
        description = escape(item['description'])
        pub_date = item['pub_date']
        source = escape(item['source'])
        rss_items += f'''  <item>
    <title>[{source}] {title}</title>
    <link>{link}</link>
    <description><![CDATA[{item['description']}]]></description>
    <pubDate>{pub_date}</pubDate>
    <guid isPermaLink="true">{link}</guid>
    <source url="{link}">{source}</source>
  </item>
'''
    
    rss_footer = '''</channel>
</rss>'''
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(rss_header + rss_items + rss_footer)
    print(f'🎉 RSS生成完成，共{len(items)}条内容，保存到{OUTPUT_FILE}')

def main():
    print('=== 开始RSS聚合任务 ===')
    feeds = load_feeds()
    print(f'加载到{len(feeds)}个订阅源')
    all_items = []
    for feed_url in feeds:
        all_items.extend(fetch_feed(feed_url))
    print(f'总共抓取{len(all_items)}条内容')
    unique_items = deduplicate(all_items)
    print(f'去重后剩余{len(unique_items)}条内容')
    generate_rss(unique_items)
    print('=== 任务完成 ===')

if __name__ == '__main__':
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    main()
