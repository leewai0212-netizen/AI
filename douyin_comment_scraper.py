#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音视频评论爬虫
支持爬取指定视频的评论数据
"""

import time
import json
import random
import re
from typing import List, Dict, Optional
from urllib.parse import urlparse, parse_qs
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pandas as pd


class DouyinCommentScraper:
    """抖音评论爬虫类"""
    
    def __init__(self, headless: bool = False):
        """
        初始化爬虫
        
        Args:
            headless: 是否使用无头模式
        """
        self.headless = headless
        self.driver = None
        self.comments = []
        
    def _init_driver(self):
        """初始化Chrome浏览器驱动"""
        chrome_options = Options()
        
        # 添加反检测选项
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # 设置用户代理
        user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        chrome_options.add_argument(f'user-agent={user_agent}')
        
        # 其他选项
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        if self.headless:
            chrome_options.add_argument('--headless=new')
        
        # 初始化驱动
        self.driver = webdriver.Chrome(options=chrome_options)
        
        # 执行CDP命令来隐藏webdriver特征
        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            '''
        })
        
    def _extract_video_id(self, url: str) -> Optional[str]:
        """
        从抖音视频URL中提取视频ID
        
        Args:
            url: 抖音视频链接
            
        Returns:
            视频ID或None
        """
        # 支持多种URL格式
        patterns = [
            r'video/(\d+)',  # https://www.douyin.com/video/1234567890
            r'share/video/(\d+)',  # 分享链接
            r'/(\d{19})',  # 19位数字ID
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def _scroll_to_load_comments(self, scroll_times: int = 5):
        """
        滚动页面加载更多评论
        
        Args:
            scroll_times: 滚动次数
        """
        for i in range(scroll_times):
            # 滚动到页面底部
            self.driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            )
            time.sleep(random.uniform(1.5, 3.0))
            print(f"正在加载评论... ({i+1}/{scroll_times})")
    
    def _parse_comment_element(self, element) -> Optional[Dict]:
        """
        解析单个评论元素
        
        Args:
            element: Selenium元素对象
            
        Returns:
            评论数据字典或None
        """
        try:
            comment_data = {}
            
            # 提取用户名
            try:
                username_elem = element.find_element(By.CSS_SELECTOR, '[class*="name"]')
                comment_data['username'] = username_elem.text
            except NoSuchElementException:
                comment_data['username'] = '未知用户'
            
            # 提取评论内容
            try:
                content_elem = element.find_element(By.CSS_SELECTOR, '[class*="text"], [class*="content"]')
                comment_data['content'] = content_elem.text
            except NoSuchElementException:
                comment_data['content'] = ''
            
            # 提取点赞数
            try:
                like_elem = element.find_element(By.CSS_SELECTOR, '[class*="like"], [class*="digg"]')
                like_text = like_elem.text
                comment_data['likes'] = self._parse_number(like_text)
            except NoSuchElementException:
                comment_data['likes'] = 0
            
            # 提取时间
            try:
                time_elem = element.find_element(By.CSS_SELECTOR, '[class*="time"], [class*="date"]')
                comment_data['time'] = time_elem.text
            except NoSuchElementException:
                comment_data['time'] = ''
            
            return comment_data if comment_data.get('content') else None
            
        except Exception as e:
            print(f"解析评论时出错: {e}")
            return None
    
    def _parse_number(self, text: str) -> int:
        """
        解析数字字符串（支持1.2w等格式）
        
        Args:
            text: 数字文本
            
        Returns:
            整数
        """
        if not text:
            return 0
        
        text = text.strip().lower()
        
        # 处理万
        if 'w' in text or '万' in text:
            num = float(re.findall(r'[\d.]+', text)[0])
            return int(num * 10000)
        
        # 处理千
        if 'k' in text or '千' in text:
            num = float(re.findall(r'[\d.]+', text)[0])
            return int(num * 1000)
        
        # 普通数字
        numbers = re.findall(r'\d+', text)
        return int(numbers[0]) if numbers else 0
    
    def scrape_comments(
        self, 
        video_url: str, 
        max_comments: int = 100,
        scroll_times: int = 10
    ) -> List[Dict]:
        """
        爬取视频评论
        
        Args:
            video_url: 抖音视频链接
            max_comments: 最大评论数量
            scroll_times: 滚动次数
            
        Returns:
            评论列表
        """
        print(f"开始爬取视频评论: {video_url}")
        
        try:
            # 初始化浏览器
            if not self.driver:
                self._init_driver()
            
            # 访问视频页面
            print("正在打开视频页面...")
            self.driver.get(video_url)
            
            # 等待页面加载
            time.sleep(random.uniform(3, 5))
            
            # 等待评论区加载
            print("等待评论区加载...")
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '[class*="comment"]'))
                )
            except TimeoutException:
                print("警告: 未检测到评论区，尝试继续...")
            
            # 滚动加载更多评论
            self._scroll_to_load_comments(scroll_times)
            
            # 查找所有评论元素
            print("开始提取评论数据...")
            comment_selectors = [
                '[class*="comment-item"]',
                '[class*="CommentItem"]',
                '[data-e2e="comment-item"]',
                'div[class*="comment"]',
            ]
            
            comment_elements = []
            for selector in comment_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        comment_elements = elements
                        print(f"使用选择器 '{selector}' 找到 {len(elements)} 个评论元素")
                        break
                except:
                    continue
            
            if not comment_elements:
                print("警告: 未找到评论元素，尝试保存页面源代码...")
                self._save_page_source()
                return []
            
            # 解析评论
            comments = []
            for idx, elem in enumerate(comment_elements[:max_comments]):
                comment_data = self._parse_comment_element(elem)
                if comment_data:
                    comment_data['index'] = idx + 1
                    comments.append(comment_data)
                    print(f"已提取 {len(comments)} 条评论", end='\r')
            
            print(f"\n成功提取 {len(comments)} 条评论")
            self.comments = comments
            return comments
            
        except Exception as e:
            print(f"爬取过程中发生错误: {e}")
            self._save_page_source()
            return []
    
    def _save_page_source(self):
        """保存页面源代码用于调试"""
        try:
            with open('page_source.html', 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            print("页面源代码已保存到 page_source.html")
        except:
            pass
    
    def save_to_json(self, filename: str = 'douyin_comments.json'):
        """
        保存评论到JSON文件
        
        Args:
            filename: 文件名
        """
        if not self.comments:
            print("没有评论数据可保存")
            return
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.comments, f, ensure_ascii=False, indent=2)
        print(f"评论已保存到 {filename}")
    
    def save_to_csv(self, filename: str = 'douyin_comments.csv'):
        """
        保存评论到CSV文件
        
        Args:
            filename: 文件名
        """
        if not self.comments:
            print("没有评论数据可保存")
            return
        
        df = pd.DataFrame(self.comments)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"评论已保存到 {filename}")
    
    def save_to_excel(self, filename: str = 'douyin_comments.xlsx'):
        """
        保存评论到Excel文件
        
        Args:
            filename: 文件名
        """
        if not self.comments:
            print("没有评论数据可保存")
            return
        
        df = pd.DataFrame(self.comments)
        df.to_excel(filename, index=False, engine='openpyxl')
        print(f"评论已保存到 {filename}")
    
    def close(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()
            print("浏览器已关闭")


def main():
    """主函数示例"""
    # 抖音视频URL（请替换为实际的视频链接）
    video_url = "https://www.douyin.com/video/1234567890"
    
    # 创建爬虫实例
    scraper = DouyinCommentScraper(headless=False)
    
    try:
        # 爬取评论
        comments = scraper.scrape_comments(
            video_url=video_url,
            max_comments=100,  # 最多爬取100条评论
            scroll_times=10    # 滚动10次加载更多评论
        )
        
        # 打印前5条评论
        print("\n" + "="*50)
        print("前5条评论预览:")
        print("="*50)
        for comment in comments[:5]:
            print(f"\n用户: {comment.get('username', 'N/A')}")
            print(f"内容: {comment.get('content', 'N/A')}")
            print(f"点赞: {comment.get('likes', 0)}")
            print(f"时间: {comment.get('time', 'N/A')}")
            print("-" * 50)
        
        # 保存数据
        scraper.save_to_json('douyin_comments.json')
        scraper.save_to_csv('douyin_comments.csv')
        
        # 如果需要保存为Excel，取消下面一行的注释
        # scraper.save_to_excel('douyin_comments.xlsx')
        
    except Exception as e:
        print(f"程序执行出错: {e}")
    
    finally:
        # 关闭浏览器
        scraper.close()


if __name__ == "__main__":
    main()
