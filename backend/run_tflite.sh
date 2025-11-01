#!/bin/bash
# Script chạy backend TFLite trên Raspberry Pi

echo "=========================================="
echo "🦐 Shrimp Detection Backend (TFLite)"
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
    exit 1
fi

echo "✅ File .env đã tồn tại"

# Kiểm tra model file
MODEL_PATH=$(grep YOLO_MODEL_PATH .env | cut -d '=' -f2)
if [ -z "$MODEL_PATH" ]; then
    MODEL_PATH="models/best-fp16(1).tflite"
fi

if [ ! -f "$MODEL_PATH" ]; then
    echo "⚠️  Cảnh báo: Model file không tồn tại tại: $MODEL_PATH"
    echo "Vui lòng đảm bảo file model đã được đặt đúng vị trí"
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
pip install --extra-index-url https://google-coral.github.io/py-repo/ tflite_runtime

echo ""
echo "=========================================="
echo "🚀 Starting server..."
echo "=========================================="
echo ""

# Chạy server
python3 app_tflite.py

