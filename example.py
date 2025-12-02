#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用示例
"""

from douyin_comment_scraper import DouyinCommentScraper
import config


def example_basic():
    """基础使用示例"""
    print("=" * 60)
    print("示例1: 基础使用")
    print("=" * 60)
    
    # 替换为实际的抖音视频链接
    video_url = "https://www.douyin.com/video/7234567890123456789"
    
    # 创建爬虫实例
    scraper = DouyinCommentScraper(headless=False)
    
    try:
        # 爬取评论
        comments = scraper.scrape_comments(
            video_url=video_url,
            max_comments=50,
            scroll_times=5
        )
        
        # 显示结果
        print(f"\n共爬取到 {len(comments)} 条评论")
        
        # 保存为JSON和CSV
        scraper.save_to_json()
        scraper.save_to_csv()
        
    finally:
        scraper.close()


def example_with_config():
    """使用配置文件的示例"""
    print("=" * 60)
    print("示例2: 使用配置文件")
    print("=" * 60)
    
    # 从config读取配置
    video_url = "https://www.douyin.com/video/7234567890123456789"
    
    scraper = DouyinCommentScraper(headless=config.HEADLESS)
    
    try:
        comments = scraper.scrape_comments(
            video_url=video_url,
            max_comments=config.MAX_COMMENTS,
            scroll_times=config.SCROLL_TIMES
        )
        
        print(f"\n共爬取到 {len(comments)} 条评论")
        
        # 根据配置保存文件
        if config.OUTPUT_JSON:
            scraper.save_to_json(config.JSON_FILENAME)
        
        if config.OUTPUT_CSV:
            scraper.save_to_csv(config.CSV_FILENAME)
        
        if config.OUTPUT_EXCEL:
            scraper.save_to_excel(config.EXCEL_FILENAME)
        
    finally:
        scraper.close()


def example_batch_scrape():
    """批量爬取多个视频的示例"""
    print("=" * 60)
    print("示例3: 批量爬取多个视频")
    print("=" * 60)
    
    # 多个视频链接
    video_urls = [
        "https://www.douyin.com/video/7234567890123456789",
        "https://www.douyin.com/video/7234567890123456790",
        "https://www.douyin.com/video/7234567890123456791",
    ]
    
    scraper = DouyinCommentScraper(headless=False)
    
    try:
        for idx, url in enumerate(video_urls, 1):
            print(f"\n正在爬取第 {idx}/{len(video_urls)} 个视频...")
            
            comments = scraper.scrape_comments(
                video_url=url,
                max_comments=30,
                scroll_times=3
            )
            
            # 为每个视频保存单独的文件
            scraper.save_to_json(f'comments_video_{idx}.json')
            scraper.save_to_csv(f'comments_video_{idx}.csv')
            
    finally:
        scraper.close()


def example_custom_analysis():
    """爬取后进行自定义分析的示例"""
    print("=" * 60)
    print("示例4: 爬取后进行数据分析")
    print("=" * 60)
    
    video_url = "https://www.douyin.com/video/7234567890123456789"
    
    scraper = DouyinCommentScraper(headless=False)
    
    try:
        comments = scraper.scrape_comments(
            video_url=video_url,
            max_comments=100,
            scroll_times=10
        )
        
        if comments:
            # 分析评论数据
            total_likes = sum(c.get('likes', 0) for c in comments)
            avg_likes = total_likes / len(comments) if comments else 0
            
            # 找出点赞最多的评论
            top_comment = max(comments, key=lambda x: x.get('likes', 0))
            
            print(f"\n数据统计:")
            print(f"总评论数: {len(comments)}")
            print(f"总点赞数: {total_likes}")
            print(f"平均点赞数: {avg_likes:.2f}")
            print(f"\n最热评论:")
            print(f"  用户: {top_comment.get('username')}")
            print(f"  内容: {top_comment.get('content')}")
            print(f"  点赞: {top_comment.get('likes')}")
            
            # 保存文件
            scraper.save_to_json()
            scraper.save_to_csv()
        
    finally:
        scraper.close()


if __name__ == "__main__":
    # 运行示例（取消注释想要运行的示例）
    
    # example_basic()
    # example_with_config()
    # example_batch_scrape()
    example_custom_analysis()
    
    print("\n" + "=" * 60)
    print("示例运行完成！")
    print("=" * 60)
