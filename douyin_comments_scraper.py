#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音视频评论爬虫
使用 Playwright 模拟浏览器获取评论数据
"""

import re
import json
import time
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, parse_qs

import pandas as pd
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from playwright.async_api import async_playwright, Page, BrowserContext

console = Console()


class DouyinCommentsScraper:
    """抖音评论爬虫类"""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.comments_data = []
        self.video_info = {}
        
    async def init_browser(self):
        """初始化浏览器"""
        console.print("[cyan]正在启动浏览器...[/cyan]")
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage',
            ]
        )
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='zh-CN',
        )
        
        # 添加反检测脚本
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
        """)
        
        self.page = await self.context.new_page()
        console.print("[green]✓ 浏览器启动成功[/green]")
        
    async def close_browser(self):
        """关闭浏览器"""
        if self.browser:
            await self.browser.close()
            console.print("[green]✓ 浏览器已关闭[/green]")
            
    def extract_video_id(self, url: str) -> Optional[str]:
        """从URL中提取视频ID"""
        # 处理分享链接 (短链接)
        # 格式: https://v.douyin.com/xxxxx/
        if 'v.douyin.com' in url:
            return None  # 需要重定向获取真实链接
            
        # 处理标准链接
        # 格式: https://www.douyin.com/video/7123456789012345678
        match = re.search(r'/video/(\d+)', url)
        if match:
            return match.group(1)
            
        # 处理 note 链接
        # 格式: https://www.douyin.com/note/7123456789012345678
        match = re.search(r'/note/(\d+)', url)
        if match:
            return match.group(1)
            
        return None
    
    async def resolve_short_url(self, short_url: str) -> Optional[str]:
        """解析短链接获取真实URL"""
        console.print(f"[cyan]正在解析短链接: {short_url}[/cyan]")
        try:
            await self.page.goto(short_url, wait_until='domcontentloaded', timeout=15000)
            await asyncio.sleep(2)
            real_url = self.page.url
            console.print(f"[green]✓ 真实链接: {real_url}[/green]")
            return real_url
        except Exception as e:
            console.print(f"[red]✗ 解析短链接失败: {e}[/red]")
            return None
            
    async def get_video_page(self, video_url: str) -> bool:
        """访问视频页面"""
        console.print(f"[cyan]正在访问视频页面...[/cyan]")
        try:
            await self.page.goto(video_url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(3)
            
            # 等待页面加载
            try:
                await self.page.wait_for_selector('[class*="comment"]', timeout=10000)
            except:
                console.print("[yellow]⚠ 未检测到评论区域，页面可能需要登录[/yellow]")
                
            return True
        except Exception as e:
            console.print(f"[red]✗ 访问视频页面失败: {e}[/red]")
            return False
            
    async def extract_video_info(self):
        """提取视频信息"""
        try:
            # 尝试获取视频标题
            title_selectors = [
                '[class*="title"]',
                'h1',
                '[data-e2e="video-desc"]',
            ]
            title = ""
            for selector in title_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        title = await element.inner_text()
                        if title and len(title) > 5:
                            break
                except:
                    continue
                    
            # 尝试获取作者信息
            author_selectors = [
                '[class*="author-name"]',
                '[class*="nickname"]',
                '[data-e2e="user-info"] span',
            ]
            author = ""
            for selector in author_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        author = await element.inner_text()
                        if author:
                            break
                except:
                    continue
                    
            self.video_info = {
                'title': title.strip() if title else '未知',
                'author': author.strip() if author else '未知',
                'url': self.page.url,
            }
            
            console.print(f"[green]视频标题: {self.video_info['title'][:50]}...[/green]")
            console.print(f"[green]视频作者: {self.video_info['author']}[/green]")
            
        except Exception as e:
            console.print(f"[yellow]⚠ 提取视频信息时出错: {e}[/yellow]")
            self.video_info = {'title': '未知', 'author': '未知', 'url': self.page.url}
            
    async def scroll_and_collect_comments(self, max_comments: int = 100, max_scrolls: int = 50):
        """滚动页面并收集评论"""
        console.print(f"[cyan]开始收集评论 (目标: {max_comments} 条)...[/cyan]")
        
        collected_comments = set()  # 用于去重
        scroll_count = 0
        no_new_count = 0
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]收集评论中...", total=max_comments)
            
            while len(self.comments_data) < max_comments and scroll_count < max_scrolls:
                scroll_count += 1
                
                # 收集当前可见的评论
                comments = await self.extract_comments_from_page()
                
                new_comments_count = 0
                for comment in comments:
                    comment_id = f"{comment['nickname']}_{comment['content'][:20]}"
                    if comment_id not in collected_comments:
                        collected_comments.add(comment_id)
                        self.comments_data.append(comment)
                        new_comments_count += 1
                        
                        if len(self.comments_data) >= max_comments:
                            break
                
                progress.update(task, completed=len(self.comments_data))
                
                if new_comments_count == 0:
                    no_new_count += 1
                    if no_new_count >= 5:
                        console.print("[yellow]⚠ 连续5次未获取到新评论，停止滚动[/yellow]")
                        break
                else:
                    no_new_count = 0
                    
                # 滚动页面
                await self.page.evaluate("""
                    window.scrollBy(0, 500);
                """)
                await asyncio.sleep(1)
                
                # 尝试点击"展开更多评论"按钮
                try:
                    more_btn = await self.page.query_selector('[class*="more-comment"], [class*="展开"]')
                    if more_btn:
                        await more_btn.click()
                        await asyncio.sleep(1)
                except:
                    pass
                    
        console.print(f"[green]✓ 共收集到 {len(self.comments_data)} 条评论[/green]")
        
    async def extract_comments_from_page(self) -> list:
        """从当前页面提取评论"""
        comments = []
        
        # 定义多种可能的评论选择器
        comment_selectors = [
            '[class*="comment-item"]',
            '[class*="CommentItem"]',
            '[data-e2e="comment-item"]',
            '[class*="comment-list"] > div',
        ]
        
        for selector in comment_selectors:
            try:
                elements = await self.page.query_selector_all(selector)
                if elements and len(elements) > 0:
                    for element in elements:
                        try:
                            comment = await self.parse_comment_element(element)
                            if comment and comment.get('content'):
                                comments.append(comment)
                        except:
                            continue
                    if comments:
                        break
            except:
                continue
                
        return comments
        
    async def parse_comment_element(self, element) -> dict:
        """解析单个评论元素"""
        try:
            # 获取评论内容
            content = ""
            content_selectors = ['[class*="content"]', '[class*="text"]', 'p', 'span']
            for selector in content_selectors:
                try:
                    content_el = await element.query_selector(selector)
                    if content_el:
                        content = await content_el.inner_text()
                        if content and len(content) > 0:
                            break
                except:
                    continue
                    
            # 获取用户昵称
            nickname = ""
            nickname_selectors = ['[class*="name"]', '[class*="nickname"]', '[class*="user"]', 'a']
            for selector in nickname_selectors:
                try:
                    name_el = await element.query_selector(selector)
                    if name_el:
                        nickname = await name_el.inner_text()
                        if nickname and len(nickname) > 0:
                            break
                except:
                    continue
                    
            # 获取点赞数
            likes = "0"
            like_selectors = ['[class*="like"]', '[class*="digg"]']
            for selector in like_selectors:
                try:
                    like_el = await element.query_selector(selector)
                    if like_el:
                        likes = await like_el.inner_text()
                        break
                except:
                    continue
                    
            # 获取时间
            time_str = ""
            time_selectors = ['[class*="time"]', '[class*="date"]', 'time']
            for selector in time_selectors:
                try:
                    time_el = await element.query_selector(selector)
                    if time_el:
                        time_str = await time_el.inner_text()
                        break
                except:
                    continue
                    
            return {
                'nickname': nickname.strip() if nickname else '匿名用户',
                'content': content.strip() if content else '',
                'likes': likes.strip() if likes else '0',
                'time': time_str.strip() if time_str else '',
                'collected_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
        except Exception as e:
            return {}
            
    def save_to_excel(self, filename: str = None):
        """保存评论到Excel文件"""
        if not self.comments_data:
            console.print("[yellow]⚠ 没有评论数据可保存[/yellow]")
            return None
            
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"douyin_comments_{timestamp}.xlsx"
            
        df = pd.DataFrame(self.comments_data)
        
        # 添加视频信息
        df['video_title'] = self.video_info.get('title', '未知')
        df['video_author'] = self.video_info.get('author', '未知')
        df['video_url'] = self.video_info.get('url', '')
        
        # 重新排列列顺序
        columns = ['nickname', 'content', 'likes', 'time', 'video_title', 'video_author', 'video_url', 'collected_at']
        df = df[[col for col in columns if col in df.columns]]
        
        # 重命名列为中文
        df.columns = ['用户昵称', '评论内容', '点赞数', '发布时间', '视频标题', '视频作者', '视频链接', '采集时间'][:len(df.columns)]
        
        output_path = Path(filename)
        df.to_excel(output_path, index=False, engine='openpyxl')
        console.print(f"[green]✓ 评论已保存到: {output_path.absolute()}[/green]")
        
        return str(output_path.absolute())
        
    def save_to_json(self, filename: str = None):
        """保存评论到JSON文件"""
        if not self.comments_data:
            console.print("[yellow]⚠ 没有评论数据可保存[/yellow]")
            return None
            
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"douyin_comments_{timestamp}.json"
            
        output_data = {
            'video_info': self.video_info,
            'comments_count': len(self.comments_data),
            'collected_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'comments': self.comments_data,
        }
        
        output_path = Path(filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
            
        console.print(f"[green]✓ 评论已保存到: {output_path.absolute()}[/green]")
        return str(output_path.absolute())
        
    def display_comments(self, limit: int = 10):
        """在终端显示评论"""
        if not self.comments_data:
            console.print("[yellow]⚠ 没有评论数据[/yellow]")
            return
            
        table = Table(title=f"抖音视频评论 (显示前 {min(limit, len(self.comments_data))} 条)")
        table.add_column("用户", style="cyan", no_wrap=True)
        table.add_column("评论内容", style="white")
        table.add_column("点赞", style="red", justify="right")
        table.add_column("时间", style="dim")
        
        for comment in self.comments_data[:limit]:
            content = comment.get('content', '')
            if len(content) > 50:
                content = content[:50] + "..."
            table.add_row(
                comment.get('nickname', '匿名')[:10],
                content,
                str(comment.get('likes', '0')),
                comment.get('time', '')[:20],
            )
            
        console.print(table)


async def scrape_douyin_comments(
    video_url: str,
    max_comments: int = 100,
    headless: bool = True,
    output_format: str = 'both',
):
    """
    爬取抖音视频评论的主函数
    
    参数:
        video_url: 抖音视频链接 (支持短链接和完整链接)
        max_comments: 最大评论数量
        headless: 是否无头模式运行浏览器
        output_format: 输出格式 ('excel', 'json', 'both')
    """
    console.print("[bold magenta]═══════════════════════════════════════[/bold magenta]")
    console.print("[bold magenta]      抖音视频评论爬虫 v1.0          [/bold magenta]")
    console.print("[bold magenta]═══════════════════════════════════════[/bold magenta]")
    console.print()
    
    scraper = DouyinCommentsScraper(headless=headless)
    
    try:
        await scraper.init_browser()
        
        # 解析短链接
        if 'v.douyin.com' in video_url:
            real_url = await scraper.resolve_short_url(video_url)
            if real_url:
                video_url = real_url
            else:
                console.print("[red]✗ 无法解析视频链接[/red]")
                return
                
        # 访问视频页面
        success = await scraper.get_video_page(video_url)
        if not success:
            console.print("[red]✗ 无法访问视频页面[/red]")
            return
            
        # 提取视频信息
        await scraper.extract_video_info()
        
        # 收集评论
        await scraper.scroll_and_collect_comments(max_comments=max_comments)
        
        # 显示部分评论
        scraper.display_comments(limit=10)
        
        # 保存结果
        if output_format in ('excel', 'both'):
            scraper.save_to_excel()
        if output_format in ('json', 'both'):
            scraper.save_to_json()
            
    except Exception as e:
        console.print(f"[red]✗ 发生错误: {e}[/red]")
        import traceback
        traceback.print_exc()
    finally:
        await scraper.close_browser()


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='抖音视频评论爬虫',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python douyin_comments_scraper.py https://v.douyin.com/xxxxx/
  python douyin_comments_scraper.py https://www.douyin.com/video/7123456789 -n 200
  python douyin_comments_scraper.py VIDEO_URL -n 500 --no-headless

注意事项:
  1. 首次运行需要安装 playwright 浏览器: playwright install chromium
  2. 如果遇到验证码，可以使用 --no-headless 参数手动处理
  3. 抖音有反爬机制，请适度使用
        """
    )
    
    parser.add_argument('url', help='抖音视频链接')
    parser.add_argument('-n', '--max-comments', type=int, default=100, help='最大评论数量 (默认: 100)')
    parser.add_argument('--no-headless', action='store_true', help='显示浏览器窗口')
    parser.add_argument('-o', '--output', choices=['excel', 'json', 'both'], default='both', help='输出格式')
    
    args = parser.parse_args()
    
    asyncio.run(scrape_douyin_comments(
        video_url=args.url,
        max_comments=args.max_comments,
        headless=not args.no_headless,
        output_format=args.output,
    ))


if __name__ == '__main__':
    main()
