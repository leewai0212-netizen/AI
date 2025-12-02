#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速启动脚本 - 交互式使用
"""

from douyin_comment_scraper import DouyinCommentScraper


def main():
    print("=" * 60)
    print("抖音视频评论爬虫 - 快速启动")
    print("=" * 60)
    print()
    
    # 获取用户输入
    video_url = input("请输入抖音视频链接: ").strip()
    
    if not video_url:
        print("错误: 未输入视频链接！")
        return
    
    # 获取爬取数量
    try:
        max_comments = int(input("请输入要爬取的评论数量 (默认100): ").strip() or "100")
    except ValueError:
        max_comments = 100
        print(f"使用默认值: {max_comments}")
    
    # 获取滚动次数
    try:
        scroll_times = int(input("请输入滚动次数 (默认10): ").strip() or "10")
    except ValueError:
        scroll_times = 10
        print(f"使用默认值: {scroll_times}")
    
    # 是否无头模式
    headless_input = input("是否使用无头模式(不显示浏览器)? (y/n, 默认n): ").strip().lower()
    headless = headless_input == 'y'
    
    print()
    print("=" * 60)
    print("开始爬取...")
    print("=" * 60)
    print()
    
    # 创建爬虫实例
    scraper = DouyinCommentScraper(headless=headless)
    
    try:
        # 爬取评论
        comments = scraper.scrape_comments(
            video_url=video_url,
            max_comments=max_comments,
            scroll_times=scroll_times
        )
        
        if comments:
            print()
            print("=" * 60)
            print(f"爬取完成! 共获取 {len(comments)} 条评论")
            print("=" * 60)
            print()
            
            # 显示前3条评论
            print("前3条评论预览:")
            print("-" * 60)
            for comment in comments[:3]:
                print(f"用户: {comment.get('username', 'N/A')}")
                print(f"内容: {comment.get('content', 'N/A')}")
                print(f"点赞: {comment.get('likes', 0)}")
                print(f"时间: {comment.get('time', 'N/A')}")
                print("-" * 60)
            
            # 数据统计
            total_likes = sum(c.get('likes', 0) for c in comments)
            avg_likes = total_likes / len(comments) if comments else 0
            
            print()
            print("数据统计:")
            print(f"  总评论数: {len(comments)}")
            print(f"  总点赞数: {total_likes}")
            print(f"  平均点赞数: {avg_likes:.2f}")
            
            # 保存文件
            print()
            save_format = input("选择保存格式 (1=JSON, 2=CSV, 3=两者都保存, 默认3): ").strip() or "3"
            
            if save_format in ['1', '3']:
                scraper.save_to_json('douyin_comments.json')
            
            if save_format in ['2', '3']:
                scraper.save_to_csv('douyin_comments.csv')
            
            print()
            print("=" * 60)
            print("所有操作完成!")
            print("=" * 60)
        else:
            print()
            print("未能获取到评论数据，可能的原因:")
            print("1. 视频没有评论")
            print("2. 需要登录账号")
            print("3. 页面结构发生变化")
            print("4. 遇到了验证码")
            print()
            print("建议: 使用非无头模式(n)查看实际页面情况")
    
    except KeyboardInterrupt:
        print("\n\n用户中断操作")
    
    except Exception as e:
        print(f"\n错误: {e}")
        print("\n建议查看 page_source.html 文件分析问题")
    
    finally:
        scraper.close()
        print("\n程序已退出")


if __name__ == "__main__":
    main()
