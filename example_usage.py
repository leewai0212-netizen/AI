#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音评论爬虫使用示例
"""

from douyin_comments_scraper import DouyinCommentsScraper


def example_basic():
    """基本使用示例"""
    # 创建爬虫实例
    scraper = DouyinCommentsScraper()
    
    # 视频URL（示例）
    video_url = "https://www.douyin.com/video/1234567890"
    
    # 爬取100条评论
    comments = scraper.scrape_all_comments(video_url, max_comments=100)
    
    # 打印评论
    for i, comment in enumerate(comments[:5], 1):
        print(f"{i}. {comment['nickname']}: {comment['text']}")
    
    # 保存数据
    scraper.save_to_json(comments, 'comments.json')
    scraper.save_to_csv(comments, 'comments.csv')


def example_with_cookie():
    """使用Cookie的示例（如果需要登录）"""
    scraper = DouyinCommentsScraper()
    
    # 添加Cookie（需要从浏览器中获取）
    # 方法：打开抖音网站 -> F12开发者工具 -> Network标签 -> 找到任意请求 -> 复制Cookie
    cookie = "your_cookie_string_here"
    scraper.session.headers.update({
        'Cookie': cookie
    })
    
    video_url = "https://www.douyin.com/video/1234567890"
    comments = scraper.scrape_all_comments(video_url, max_comments=50)
    
    scraper.save_to_json(comments)


def example_custom_headers():
    """自定义请求头的示例"""
    scraper = DouyinCommentsScraper()
    
    # 添加更多请求头
    scraper.session.headers.update({
        'Accept': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
        # 可以添加更多需要的请求头
    })
    
    video_url = "https://www.douyin.com/video/1234567890"
    comments = scraper.scrape_all_comments(video_url, max_comments=50)
    
    scraper.save_to_json(comments)


if __name__ == '__main__':
    print("请选择示例:")
    print("1. 基本使用")
    print("2. 使用Cookie")
    print("3. 自定义请求头")
    
    choice = input("请输入选择 (1/2/3): ").strip()
    
    if choice == "1":
        example_basic()
    elif choice == "2":
        example_with_cookie()
    elif choice == "3":
        example_custom_headers()
    else:
        print("无效选择")
