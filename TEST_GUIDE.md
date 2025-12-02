# 测试指南

## 快速测试步骤

### 1. 环境检查

```bash
# 检查Python版本（需要3.7+）
python3 --version

# 检查是否安装了Chrome
google-chrome --version
# 或
chromium-browser --version
```

### 2. 安装依赖

```bash
# 方式1: 使用安装脚本（推荐）
bash install.sh

# 方式2: 手动安装
pip3 install -r requirements.txt
```

### 3. 测试导入

```bash
# 测试模块是否能正常导入
python3 -c "from douyin_comment_scraper import DouyinCommentScraper; print('导入成功！')"
```

### 4. 功能测试

#### 测试1: 基础功能测试

创建测试文件 `test_basic.py`:

```python
from douyin_comment_scraper import DouyinCommentScraper

# 测试初始化
print("测试1: 初始化爬虫...")
scraper = DouyinCommentScraper(headless=False)
print("✓ 初始化成功")

# 测试浏览器
print("\n测试2: 打开浏览器...")
scraper._init_driver()
print("✓ 浏览器启动成功")

# 测试访问抖音
print("\n测试3: 访问抖音主页...")
scraper.driver.get("https://www.douyin.com")
print("✓ 页面加载成功")

# 清理
print("\n清理测试环境...")
scraper.close()
print("✓ 测试完成")
```

运行测试：
```bash
python3 test_basic.py
```

#### 测试2: 模拟数据测试

创建测试文件 `test_data.py`:

```python
from douyin_comment_scraper import DouyinCommentScraper

# 创建模拟数据
scraper = DouyinCommentScraper()
scraper.comments = [
    {
        'index': 1,
        'username': '测试用户1',
        'content': '这是一条测试评论',
        'likes': 100,
        'time': '1天前'
    },
    {
        'index': 2,
        'username': '测试用户2',
        'content': '这是另一条测试评论',
        'likes': 50,
        'time': '2天前'
    }
]

# 测试JSON导出
print("测试JSON导出...")
scraper.save_to_json('test_comments.json')
print("✓ JSON导出成功")

# 测试CSV导出
print("测试CSV导出...")
scraper.save_to_csv('test_comments.csv')
print("✓ CSV导出成功")

print("\n所有数据导出测试通过！")
```

运行测试：
```bash
python3 test_data.py
```

### 5. 实际爬取测试

⚠️ **注意**: 需要真实的抖音视频链接

```bash
# 使用交互式脚本测试
python3 quick_start.py
```

按提示输入：
1. 视频链接: 粘贴一个抖音视频URL
2. 评论数量: 建议先输入 10-20 测试
3. 滚动次数: 建议先输入 3-5 测试
4. 无头模式: 选择 n（显示浏览器）

### 6. 检查输出文件

```bash
# 查看生成的文件
ls -lh *.json *.csv 2>/dev/null

# 查看JSON内容
cat douyin_comments.json | python3 -m json.tool | head -20

# 查看CSV内容
head douyin_comments.csv
```

## 常见测试问题

### 问题1: selenium.common.exceptions.WebDriverException

**原因**: ChromeDriver未安装或版本不匹配

**解决**:
```bash
pip3 install webdriver-manager --upgrade
```

### 问题2: 浏览器闪退

**原因**: 可能是内存不足或权限问题

**解决**:
```bash
# 检查系统资源
free -h
# 使用更小的窗口
# 修改 config.py: WINDOW_SIZE = "1280,720"
```

### 问题3: 未找到评论

**原因**: 
- 视频没有评论
- 需要登录
- 页面加载时间不够

**解决**:
1. 使用有大量评论的热门视频测试
2. 手动登录后再运行
3. 增加等待时间

### 问题4: 数据不完整

**原因**: 滚动次数不够

**解决**: 增加 `scroll_times` 参数

## 测试检查清单

- [ ] Python版本 >= 3.7
- [ ] Chrome浏览器已安装
- [ ] 依赖包安装完成
- [ ] 模块可以正常导入
- [ ] 浏览器可以正常启动
- [ ] 可以访问抖音网站
- [ ] 数据导出功能正常
- [ ] 实际爬取测试成功

## 性能测试

### 测试爬取速度

```python
import time
from douyin_comment_scraper import DouyinCommentScraper

scraper = DouyinCommentScraper(headless=True)

start_time = time.time()

try:
    comments = scraper.scrape_comments(
        video_url="你的视频链接",
        max_comments=100,
        scroll_times=10
    )
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"爬取评论数: {len(comments)}")
    print(f"耗时: {duration:.2f} 秒")
    print(f"平均速度: {len(comments)/duration:.2f} 条/秒")
    
finally:
    scraper.close()
```

### 测试内存占用

```bash
# Linux
ps aux | grep python | grep douyin

# 或使用htop
htop -p $(pgrep -f douyin_comment)
```

## 自动化测试脚本

创建 `run_all_tests.sh`:

```bash
#!/bin/bash

echo "======================================"
echo "运行所有测试"
echo "======================================"

# 测试1: 导入测试
echo -e "\n[测试1] 模块导入测试..."
python3 -c "from douyin_comment_scraper import DouyinCommentScraper; print('✓ 导入成功')" || exit 1

# 测试2: 配置文件测试
echo -e "\n[测试2] 配置文件测试..."
python3 -c "import config; print('✓ 配置加载成功')" || exit 1

# 测试3: 数据导出测试
echo -e "\n[测试3] 数据导出测试..."
python3 test_data.py || exit 1

echo -e "\n======================================"
echo "所有测试通过！✓"
echo "======================================"
```

运行：
```bash
chmod +x run_all_tests.sh
./run_all_tests.sh
```

## 测试环境要求

### 最低配置
- CPU: 2核
- 内存: 2GB
- 磁盘: 100MB可用空间
- 网络: 稳定的互联网连接

### 推荐配置
- CPU: 4核+
- 内存: 4GB+
- 磁盘: 500MB+
- 网络: 高速宽带

## 测试完成后

1. 清理测试文件：
```bash
rm -f test_*.py test_comments.*
```

2. 查看文档继续使用：
```bash
cat 使用指南.md
```

3. 开始正式使用！

---

**测试通过后即可开始正式使用爬虫！** 🎉
