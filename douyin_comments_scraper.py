#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抖音视频评论爬虫
支持爬取指定视频的评论数据
"""

import requests
import json
import time
import random
from typing import List, Dict, Optional
from urllib.parse import urlparse, parse_qs
import re


class DouyinCommentsScraper:
    """抖音评论爬虫类"""
    
    def __init__(self):
        """初始化爬虫"""
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.douyin.com/',
            'Origin': 'https://www.douyin.com',
        }
        self.session.headers.update(self.headers)
        
    def extract_video_id(self, url: str) -> Optional[str]:
        """
        从抖音视频URL中提取视频ID
        
        Args:
            url: 抖音视频链接
            
        Returns:
            视频ID或None
        """
        # 处理短链接和完整链接
        patterns = [
            r'/video/(\d+)',  # 标准格式
            r'video_id=(\d+)',  # 参数格式
            r'aweme_id=(\d+)',  # aweme_id格式
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def get_comments(self, video_id: str, max_count: int = 100, cursor: int = 0) -> Dict:
        """
        获取视频评论
        
        Args:
            video_id: 视频ID
            max_count: 最大获取数量
            cursor: 游标，用于分页
            
        Returns:
            评论数据字典
        """
        # 抖音评论API端点（注意：实际API可能会变化）
        api_url = 'https://www.douyin.com/aweme/v1/web/comment/list/'
        
        params = {
            'aweme_id': video_id,
            'cursor': cursor,
            'count': min(max_count, 20),  # 每次最多20条
            'item_type': 0,
            'insert_ids': '',
        }
        
        try:
            response = self.session.get(api_url, params=params, timeout=10)
            response.raise_for_status()
            
            # 尝试解析JSON
            try:
                data = response.json()
                return data
            except json.JSONDecodeError:
                # 如果返回的不是JSON，可能是HTML页面
                print(f"警告: API返回了非JSON数据，可能需要登录或验证")
                return {'status_code': response.status_code, 'text': response.text[:200]}
                
        except requests.exceptions.RequestException as e:
            print(f"请求错误: {e}")
            return {'error': str(e)}
    
    def parse_comments(self, data: Dict) -> List[Dict]:
        """
        解析评论数据
        
        Args:
            data: API返回的数据
            
        Returns:
            评论列表
        """
        comments = []
        
        if not isinstance(data, dict):
            return comments
        
        # 检查是否有评论数据
        if 'comments' in data:
            for comment in data['comments']:
                comment_info = {
                    'comment_id': comment.get('cid', ''),
                    'user_id': comment.get('user', {}).get('uid', ''),
                    'nickname': comment.get('user', {}).get('nickname', ''),
                    'text': comment.get('text', ''),
                    'like_count': comment.get('digg_count', 0),
                    'reply_count': comment.get('reply_count', 0),
                    'create_time': comment.get('create_time', 0),
                    'ip_label': comment.get('ip_label', ''),
                }
                comments.append(comment_info)
        
        return comments
    
    def scrape_all_comments(self, video_url: str, max_comments: int = 100) -> List[Dict]:
        """
        爬取视频的所有评论
        
        Args:
            video_url: 视频URL
            max_comments: 最大评论数量
            
        Returns:
            评论列表
        """
        # 提取视频ID
        video_id = self.extract_video_id(video_url)
        if not video_id:
            print(f"无法从URL中提取视频ID: {video_url}")
            return []
        
        print(f"视频ID: {video_id}")
        print(f"开始爬取评论，目标数量: {max_comments}")
        
        all_comments = []
        cursor = 0
        page = 1
        
        while len(all_comments) < max_comments:
            print(f"\n正在获取第 {page} 页评论...")
            
            # 获取评论数据
            data = self.get_comments(video_id, max_count=max_comments - len(all_comments), cursor=cursor)
            
            # 解析评论
            comments = self.parse_comments(data)
            
            if not comments:
                print("没有更多评论了")
                break
            
            all_comments.extend(comments)
            print(f"已获取 {len(comments)} 条评论，总计: {len(all_comments)} 条")
            
            # 检查是否有下一页
            if 'has_more' in data and data['has_more'] == 1:
                cursor = data.get('cursor', cursor + len(comments))
            else:
                print("已获取所有评论")
                break
            
            # 随机延迟，避免请求过快
            time.sleep(random.uniform(1, 3))
            page += 1
        
        return all_comments[:max_comments]
    
    def save_to_json(self, comments: List[Dict], filename: str = 'douyin_comments.json'):
        """
        保存评论到JSON文件
        
        Args:
            comments: 评论列表
            filename: 文件名
        """
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(comments, f, ensure_ascii=False, indent=2)
        print(f"\n评论已保存到: {filename}")
    
    def save_to_csv(self, comments: List[Dict], filename: str = 'douyin_comments.csv'):
        """
        保存评论到CSV文件
        
        Args:
            comments: 评论列表
            filename: 文件名
        """
        import csv
        
        if not comments:
            print("没有评论数据可保存")
            return
        
        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=comments[0].keys())
            writer.writeheader()
            writer.writerows(comments)
        print(f"\n评论已保存到: {filename}")


def main():
    """主函数"""
    print("=" * 50)
    print("抖音视频评论爬虫")
    print("=" * 50)
    
    # 创建爬虫实例
    scraper = DouyinCommentsScraper()
    
    # 获取视频URL
    video_url = input("\n请输入抖音视频链接: ").strip()
    
    if not video_url:
        print("错误: 未输入视频链接")
        return
    
    # 获取最大评论数
    try:
        max_comments = int(input("请输入要爬取的最大评论数 (默认100): ").strip() or "100")
    except ValueError:
        max_comments = 100
    
    # 爬取评论
    comments = scraper.scrape_all_comments(video_url, max_comments)
    
    if not comments:
        print("\n未能获取到评论数据")
        print("可能的原因:")
        print("1. 视频URL不正确")
        print("2. 需要登录或验证")
        print("3. API接口已变更")
        print("4. 网络连接问题")
        return
    
    # 显示统计信息
    print("\n" + "=" * 50)
    print(f"爬取完成！共获取 {len(comments)} 条评论")
    print("=" * 50)
    
    # 显示前几条评论示例
    if comments:
        print("\n前3条评论示例:")
        for i, comment in enumerate(comments[:3], 1):
            print(f"\n{i}. 用户: {comment['nickname']}")
            print(f"   评论: {comment['text']}")
            print(f"   点赞: {comment['like_count']}")
    
    # 保存数据
    save_format = input("\n保存格式 (json/csv/both，默认both): ").strip().lower() or "both"
    
    if save_format in ['json', 'both']:
        scraper.save_to_json(comments)
    
    if save_format in ['csv', 'both']:
        scraper.save_to_csv(comments)


if __name__ == '__main__':
    main()
