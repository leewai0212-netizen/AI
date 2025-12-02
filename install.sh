#!/bin/bash
# 安装脚本

echo "======================================"
echo "抖音评论爬虫 - 安装脚本"
echo "======================================"
echo ""

# 检查Python版本
echo "检查Python版本..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python版本: $python_version"
echo ""

# 检查Chrome是否安装
echo "检查Chrome浏览器..."
if command -v google-chrome &> /dev/null; then
    chrome_version=$(google-chrome --version)
    echo "✓ Chrome已安装: $chrome_version"
elif command -v chromium-browser &> /dev/null; then
    chrome_version=$(chromium-browser --version)
    echo "✓ Chromium已安装: $chrome_version"
else
    echo "✗ 未检测到Chrome浏览器"
    echo "请手动安装Chrome: https://www.google.com/chrome/"
    echo "或在Linux上运行:"
    echo "  wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb"
    echo "  sudo dpkg -i google-chrome-stable_current_amd64.deb"
    echo "  sudo apt-get install -f"
fi
echo ""

# 创建虚拟环境（可选）
echo "是否创建虚拟环境? (y/n)"
read -r create_venv
if [[ $create_venv == "y" || $create_venv == "Y" ]]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
    echo "✓ 虚拟环境创建成功"
    echo "激活虚拟环境: source venv/bin/activate"
    echo ""
fi

# 安装依赖
echo "安装Python依赖包..."
pip3 install -r requirements.txt

echo ""
echo "======================================"
echo "安装完成！"
echo "======================================"
echo ""
echo "使用方法:"
echo "1. 查看示例: python3 example.py"
echo "2. 查看文档: cat README.md"
echo "3. 开始使用: 编辑example.py中的视频链接后运行"
echo ""
