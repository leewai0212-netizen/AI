#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音视频评论爬虫 (Selenium版本)
使用浏览器自动化方式爬取评论，更适合处理需要登录的情况
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import json
import time
import csv
from typing import List, Dict


class DouyinCommentsScraperSelenium:
    """使用Selenium的抖音评论爬虫"""
    
    def __init__(self, headless: bool = False):
        """
        初始化爬虫
        
        Args:
            headless: 是否使用无头模式（不显示浏览器窗口）
        """
        self.headless = headless
        self.driver = None
        self.setup_driver()
    
    def setup_driver(self):
        """设置浏览器驱动"""
        options = webdriver.ChromeOptions()
        
        if self.headless:
            options.add_argument('--headless')
        
        # 添加其他选项以提高稳定性
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # 设置User-Agent
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        try:
            self.driver = webdriver.Chrome(options=options)
            # 执行脚本隐藏webdriver特征
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    })
                '''
            })
        except Exception as e:
            print(f"无法启动Chrome浏览器: {e}")
            print("请确保已安装Chrome浏览器和ChromeDriver")
            print("安装方法: https://chromedriver.chromium.org/")
            raise
    
    def get_comments_from_page(self, video_url: str, max_scroll: int = 10) -> List[Dict]:
        """
        从页面中提取评论
        
        Args:
            video_url: 视频URL
            max_scroll: 最大滚动次数
            
        Returns:
            评论列表
        """
        print(f"正在打开视频页面: {video_url}")
        self.driver.get(video_url)
        
        # 等待页面加载
        time.sleep(3)
        
        comments = []
        scroll_count = 0
        
        try:
            # 尝试找到评论区域
            # 注意：这些选择器可能需要根据实际页面结构调整
            comment_selectors = [
                "//div[contains(@class, 'comment')]",
                "//div[contains(@class, 'CommentItem')]",
                "//div[@data-e2e='comment-item']",
            ]
            
            print("开始滚动页面加载评论...")
            
            while scroll_count < max_scroll:
                # 滚动页面
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                
                # 尝试提取评论
                for selector in comment_selectors:
                    try:
                        comment_elements = self.driver.find_elements(By.XPATH, selector)
                        if comment_elements:
                            print(f"找到 {len(comment_elements)} 个评论元素")
                            break
                    except:
                        continue
                
                scroll_count += 1
                print(f"已滚动 {scroll_count} 次")
            
            # 提取评论数据
            print("开始提取评论数据...")
            # 这里需要根据实际页面结构来解析
            # 由于抖音页面结构复杂且经常变化，这里提供一个基础框架
            
        except Exception as e:
            print(f"提取评论时出错: {e}")
        
        return comments
    
    def get_comments_via_api(self, video_url: str) -> List[Dict]:
        """
        通过浏览器获取API调用来提取评论
        这个方法会监听网络请求，找到评论API的调用
        
        Args:
            video_url: 视频URL
            
        Returns:
            评论列表
        """
        print("注意: 此方法需要手动在浏览器中操作")
        print("1. 浏览器会自动打开视频页面")
        print("2. 请手动滚动页面加载评论")
        print("3. 打开浏览器开发者工具 (F12)")
        print("4. 在Network标签中找到评论相关的API请求")
        print("5. 复制请求的URL和Headers")
        
        self.driver.get(video_url)
        
        # 保持浏览器打开，让用户操作
        input("\n完成操作后，按Enter键继续...")
        
        # 这里可以添加代码来读取浏览器日志或使用其他方法获取API数据
        return []
    
    def save_to_json(self, comments: List[Dict], filename: str = 'douyin_comments_selenium.json'):
        """保存评论到JSON文件"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(comments, f, ensure_ascii=False, indent=2)
        print(f"\n评论已保存到: {filename}")
    
    def save_to_csv(self, comments: List[Dict], filename: str = 'douyin_comments_selenium.csv'):
        """保存评论到CSV文件"""
        if not comments:
            print("没有评论数据可保存")
            return
        
        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=comments[0].keys())
            writer.writeheader()
            writer.writerows(comments)
        print(f"\n评论已保存到: {filename}")
    
    def close(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()
            print("浏览器已关闭")


def main():
    """主函数"""
    print("=" * 50)
    print("抖音视频评论爬虫 (Selenium版本)")
    print("=" * 50)
    print("\n注意: 此版本需要安装Chrome浏览器和ChromeDriver")
    print("安装ChromeDriver: pip install webdriver-manager")
    print("或者手动下载: https://chromedriver.chromium.org/")
    
    try:
        scraper = DouyinCommentsScraperSelenium(headless=False)
        
        video_url = input("\n请输入抖音视频链接: ").strip()
        
        if not video_url:
            print("错误: 未输入视频链接")
            scraper.close()
            return
        
        print("\n选择爬取方式:")
        print("1. 自动从页面提取 (可能不稳定)")
        print("2. 手动获取API数据 (推荐)")
        
        choice = input("请选择 (1/2，默认2): ").strip() or "2"
        
        if choice == "1":
            max_scroll = int(input("最大滚动次数 (默认10): ").strip() or "10")
            comments = scraper.get_comments_from_page(video_url, max_scroll)
        else:
            comments = scraper.get_comments_via_api(video_url)
        
        if comments:
            save_format = input("\n保存格式 (json/csv/both，默认both): ").strip().lower() or "both"
            
            if save_format in ['json', 'both']:
                scraper.save_to_json(comments)
            
            if save_format in ['csv', 'both']:
                scraper.save_to_csv(comments)
        else:
            print("\n未能获取到评论数据")
            print("建议使用 requests 版本的爬虫，或手动分析API接口")
        
        scraper.close()
        
    except KeyboardInterrupt:
        print("\n\n用户中断操作")
    except Exception as e:
        print(f"\n发生错误: {e}")


if __name__ == '__main__':
    main()
