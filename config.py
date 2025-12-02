#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件
"""

# 浏览器配置
HEADLESS = False  # 是否使用无头模式（True: 不显示浏览器窗口）
WINDOW_SIZE = "1920,1080"  # 浏览器窗口大小

# 爬虫配置
MAX_COMMENTS = 100  # 最大爬取评论数
SCROLL_TIMES = 10  # 滚动次数（每次滚动会加载更多评论）
SCROLL_PAUSE_TIME = (1.5, 3.0)  # 滚动后的等待时间范围（秒）

# 输出配置
OUTPUT_JSON = True  # 是否输出JSON文件
OUTPUT_CSV = True  # 是否输出CSV文件
OUTPUT_EXCEL = False  # 是否输出Excel文件

# 文件名配置
JSON_FILENAME = 'douyin_comments.json'
CSV_FILENAME = 'douyin_comments.csv'
EXCEL_FILENAME = 'douyin_comments.xlsx'

# 用户代理
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
