#!/bin/bash
# 标书通用检测工具 - macOS 安装脚本
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="$HOME/.bid-check-tool"
APP_DIR="$HOME/Applications/标书检测工具.app"

echo "🦐 标书通用检测工具 - 安装中..."
echo ""

# 1. 复制项目文件
echo "📦 安装程序文件..."
mkdir -p "$INSTALL_DIR"
cp "$SCRIPT_DIR/analyzer.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/parsers.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/report_generator.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/streamlit_app.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/requirements.txt" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/bid_check.py" "$INSTALL_DIR/"
mkdir -p "$INSTALL_DIR/uploads" "$INSTALL_DIR/output"

# 2. 创建虚拟环境
echo "🐍 创建 Python 虚拟环境..."
python3 -m venv "$INSTALL_DIR/.venv"
source "$INSTALL_DIR/.venv/bin/activate"

# 3. 安装依赖
echo "📥 安装依赖包..."
pip install --upgrade pip -q
pip install -r "$INSTALL_DIR/requirements.txt" -q

echo "✅ 依赖安装完成"

# 4. 保存配置
echo "$INSTALL_DIR" > "$INSTALL_DIR/.install_path"

# 5. 创建 macOS App
echo "🖥️  创建桌面应用..."
mkdir -p "$APP_DIR/Contents/MacOS"
mkdir -p "$APP_DIR/Contents/Resources"

# Info.plist
cat > "$APP_DIR/Contents/Info.plist" << 'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>launcher</string>
    <key>CFBundleName</key>
    <string>标书检测工具</string>
    <key>CFBundleIdentifier</key>
    <string>com.bidcheck.tool</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
</dict>
</plist>
PLIST

# Launcher script
cat > "$APP_DIR/Contents/MacOS/launcher" << 'LAUNCHER'
#!/bin/bash
INSTALL_DIR="$HOME/.bid-check-tool"
PORT=8501

# 检查端口是否被占用，如果占用就换一个
while lsof -i :$PORT > /dev/null 2>&1; do
    PORT=$((PORT + 1))
done

# 激活虚拟环境
source "$INSTALL_DIR/.venv/bin/activate"

# 启动Streamlit（后台运行）
cd "$INSTALL_DIR"
streamlit run streamlit_app.py --server.port=$PORT --server.headless=true --browser.gatherUsageStats=false &
STPID=$!

# 等待服务启动
sleep 2

# 打开浏览器
open "http://localhost:$PORT"

# 保持进程运行
wait $STPID
LAUNCHER

chmod +x "$APP_DIR/Contents/MacOS/launcher"

# 创建退出脚本（用于关闭服务）
cat > "$INSTALL_DIR/stop.sh" << 'STOP'
#!/bin/bash
pkill -f "streamlit run streamlit_app.py" 2>/dev/null
echo "服务已停止"
STOP
chmod +x "$INSTALL_DIR/stop.sh"

echo ""
echo "========================================="
echo "✅ 安装完成！"
echo ""
echo "📍 应用位置: ~/Applications/标书检测工具.app"
echo "📂 安装目录: $INSTALL_DIR"
echo ""
echo "🚀 使用方式:"
echo "   双击「标书检测工具」即可启动"
echo "   首次打开如提示"无法验证开发者"，右键→打开"
echo ""
echo "⏹️  关闭服务: 运行 ~/.bid-check-tool/stop.sh"
echo "========================================="
