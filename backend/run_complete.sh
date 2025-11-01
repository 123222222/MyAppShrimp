#!/bin/bash
# Script chạy backend HOÀN CHỈNH (Camera + AI Detection) trên Raspberry Pi

echo "=========================================="
echo "🦐 Shrimp Detection Backend (Complete)"
echo "=========================================="

# Kiểm tra Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 chưa được cài đặt!"
    exit 1
fi

echo "✅ Python version: $(python3 --version)"

# Kiểm tra .env file
if [ ! -f .env ]; then
    echo "❌ File .env không tồn tại!"
    echo "Vui lòng tạo file .env với các thông tin sau:"
    echo "  CLOUDINARY_CLOUD_NAME=your_cloud_name"
    echo "  CLOUDINARY_API_KEY=your_api_key"
    echo "  CLOUDINARY_API_SECRET=your_api_secret"
    echo "  MONGODB_URI=your_mongodb_uri"
    echo "  MONGODB_DATABASE=shrimp_db"
    echo "  YOLO_MODEL_PATH=models/best-fp16(1).tflite"
    echo "  CAMERA_USERNAME=admin"
    echo "  CAMERA_PASSWORD=123456"
    exit 1
fi

echo "✅ File .env đã tồn tại"

# Kiểm tra model file
MODEL_PATH=$(grep YOLO_MODEL_PATH .env | cut -d '=' -f2 | tr -d ' ')
if [ -z "$MODEL_PATH" ]; then
    MODEL_PATH="models/best-fp16(1).tflite"
fi

if [ ! -f "$MODEL_PATH" ]; then
    echo "⚠️  Cảnh báo: Model file không tồn tại tại: $MODEL_PATH"
    echo "Backend vẫn sẽ chạy nhưng detection sẽ không hoạt động"
else
    echo "✅ Model file found: $MODEL_PATH"
fi

# Kiểm tra camera
echo "🔍 Checking camera..."
if ls /dev/video* 1> /dev/null 2>&1; then
    echo "✅ Camera device(s) found:"
    ls -l /dev/video*
else
    echo "⚠️  Cảnh báo: Không tìm thấy camera"
    echo "Backend vẫn sẽ chạy nhưng stream sẽ không hoạt động"
fi

# Kiểm tra virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Tạo virtual environment..."
    python3 -m venv venv
fi

echo "🔄 Kích hoạt virtual environment..."
source venv/bin/activate

# Cài đặt dependencies
echo "📦 Cài đặt dependencies..."
pip install -r requirements_tflite.txt

# Cài đặt TFLite runtime cho Raspberry Pi
echo "📦 Cài đặt TFLite runtime..."
pip install --extra-index-url https://google-coral.github.io/py-repo/ tflite_runtime 2>/dev/null || echo "⚠️  TFLite runtime install failed, will use tensorflow"

echo ""
echo "=========================================="
echo "🚀 Starting complete server..."
echo "=========================================="
echo ""

# Chạy server
python3 app_complete.py

