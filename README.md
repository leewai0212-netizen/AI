# 抖音视频评论爬虫

一个用于爬取抖音视频评论的Python工具。

## 功能特点

- ✅ 支持从抖音视频链接提取视频ID
- ✅ 自动分页获取评论数据
- ✅ 支持导出为JSON和CSV格式
- ✅ 包含请求延迟，避免被封禁
- ✅ 详细的错误处理和提示信息

## 安装依赖

```bash
pip install -r requirements.txt
```

## 文件说明

- `douyin_comments_scraper.py` - 主爬虫脚本（使用requests库）
- `douyin_comments_scraper_selenium.py` - Selenium版本（需要浏览器驱动）
- `example_usage.py` - 使用示例代码
- `requirements.txt` - 依赖包列表

## 使用方法

### 方法一：使用requests版本（推荐）

```bash
python douyin_comments_scraper.py
```

运行后会提示输入：
1. 抖音视频链接
2. 要爬取的最大评论数
3. 保存格式（json/csv/both）

### 方法二：使用Selenium版本

如果需要处理需要登录的情况或遇到反爬虫限制：

```bash
# 首先安装Selenium相关依赖
pip install selenium webdriver-manager

# 运行Selenium版本
python douyin_comments_scraper_selenium.py
```

**注意**: Selenium版本需要安装Chrome浏览器和ChromeDriver

### 代码示例

```python
from douyin_comments_scraper import DouyinCommentsScraper

# 创建爬虫实例
scraper = DouyinCommentsScraper()

# 爬取评论
video_url = "https://www.douyin.com/video/1234567890"
comments = scraper.scrape_all_comments(video_url, max_comments=100)

# 保存数据
scraper.save_to_json(comments, 'comments.json')
scraper.save_to_csv(comments, 'comments.csv')
```

## 输出数据格式

每条评论包含以下字段：

- `comment_id`: 评论ID
- `user_id`: 用户ID
- `nickname`: 用户昵称
- `text`: 评论内容
- `like_count`: 点赞数
- `reply_count`: 回复数
- `create_time`: 创建时间戳
- `ip_label`: IP归属地

## 注意事项

⚠️ **重要提示**：

1. **API限制**: 抖音的API接口可能会变化，如果无法获取数据，可能需要：
   - 使用浏览器开发者工具查看最新的API端点
   - 添加Cookie和Token认证
   - 使用Selenium等工具模拟浏览器

2. **反爬虫机制**: 抖音有较强的反爬虫机制，建议：
   - 控制请求频率，避免过快
   - 使用代理IP（如需要）
   - 模拟真实浏览器行为

3. **法律合规**: 
   - 请遵守抖音的服务条款
   - 仅用于学习和研究目的
   - 不要用于商业用途或侵犯他人隐私

4. **登录认证**: 某些视频可能需要登录才能查看评论，此时需要：
   - 获取登录后的Cookie
   - 在请求头中添加Cookie
   - 或使用Selenium自动登录

## 高级用法

### 添加Cookie认证

如果需要登录后才能访问，可以在代码中添加Cookie：

```python
scraper = DouyinCommentsScraper()
scraper.session.headers.update({
    'Cookie': 'your_cookie_here'
})
```

### 使用代理

```python
proxies = {
    'http': 'http://proxy.example.com:8080',
    'https': 'https://proxy.example.com:8080'
}
scraper.session.proxies.update(proxies)
```

## 如何获取真实的API端点

如果默认的API端点无法工作，可以手动获取：

1. 打开Chrome浏览器，访问抖音视频页面
2. 按F12打开开发者工具
3. 切换到Network（网络）标签
4. 滚动页面加载评论
5. 在Network标签中找到评论相关的请求（通常包含"comment"关键字）
6. 查看请求的：
   - URL（完整地址）
   - Request Headers（请求头，特别是Cookie）
   - Request Method（GET/POST）
7. 将这些信息更新到代码中的`get_comments`方法

## 故障排除

### 问题：无法获取评论数据

**解决方案**：
1. 检查视频URL是否正确
2. 尝试在浏览器中打开视频链接，确认可以访问
3. 查看浏览器开发者工具的Network标签，找到评论API的实际端点
4. 检查是否需要登录或Cookie
5. 尝试使用Selenium版本

### 问题：返回HTML而不是JSON

**解决方案**：
- 抖音可能检测到了爬虫行为
- 尝试添加更完整的请求头
- 添加Cookie（从浏览器中复制）
- 使用Selenium等工具模拟真实浏览器

### 问题：Selenium版本无法启动

**解决方案**：
1. 确保已安装Chrome浏览器
2. 安装ChromeDriver：
   ```bash
   pip install webdriver-manager
   ```
   或手动下载：https://chromedriver.chromium.org/
3. 确保ChromeDriver版本与Chrome浏览器版本匹配

## 许可证

MIT License

## 免责声明

本工具仅供学习和研究使用。使用本工具时请遵守相关法律法规和平台服务条款，作者不对任何使用本工具造成的后果负责。
