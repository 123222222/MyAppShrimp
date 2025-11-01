from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from ultralytics import YOLO
import cloudinary
import cloudinary.uploader
from pymongo import MongoClient
import base64
from io import BytesIO
from PIL import Image
import numpy as np
import time
import os
from dotenv import load_dotenv
import cv2
from bson import ObjectId

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Load YOLO model
MODEL_PATH = os.getenv('YOLO_MODEL_PATH', 'models/shrimp_best.pt')
print(f"Loading YOLO model from {MODEL_PATH}...")
model = YOLO(MODEL_PATH)
print("YOLO model loaded successfully!")

# Cloudinary config
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)
print("Cloudinary configured!")

# MongoDB config
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
MONGODB_DB = os.getenv('MONGODB_DATABASE', 'shrimp_db')
mongo_client = MongoClient(MONGODB_URI)
db = mongo_client[MONGODB_DB]
collection = db['detections']
print(f"Connected to MongoDB: {MONGODB_DB}")

# Camera stream endpoint (existing)
@app.route('/blynk_feed')
def blynk_feed():
    """MJPEG camera stream endpoint"""
    # Your existing camera stream implementation
    return Response("Camera stream", mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/detect-shrimp', methods=['POST'])
def detect_shrimp():
    """
    Endpoint nhận ảnh từ Android app, xử lý với YOLO,
    lưu lên Cloudinary và MongoDB, trả về kết quả
    """
    try:
        data = request.json
        image_base64 = data.get('image')
        source = data.get('source', 'unknown')

        if not image_base64:
            return jsonify({
                "success": False,
                "message": "No image data provided"
            }), 400

        print(f"[INFO] Receiving image from {source}")

        # Decode base64 image
        image_data = base64.b64decode(image_base64)
        image = Image.open(BytesIO(image_data))
        image_np = np.array(image)

        print(f"[INFO] Image size: {image.size}")

        # Run YOLO detection
        print("[INFO] Running YOLO detection...")
        results = model(image_np)

        # Parse detections
        detections = []
        for r in results:
            boxes = r.boxes
            for box in boxes:
                # Get box coordinates
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                w = x2 - x1
                h = y2 - y1
                x = x1 + w/2
                y = y1 + h/2

                detections.append({
                    "className": r.names[int(box.cls)],
                    "confidence": float(box.conf),
                    "bbox": {
                        "x": float(x),
                        "y": float(y),
                        "width": float(w),
                        "height": float(h)
                    }
                })

        print(f"[INFO] Found {len(detections)} detections")

        # Generate annotated image
        annotated_image = results[0].plot()
        img_pil = Image.fromarray(annotated_image)
        buffer = BytesIO()
        img_pil.save(buffer, format='JPEG', quality=90)
        buffer.seek(0)

        # Upload to Cloudinary
        print("[INFO] Uploading to Cloudinary...")
        upload_result = cloudinary.uploader.upload(
            buffer,
            folder="shrimp-detections",
            resource_type="image"
        )
        cloudinary_url = upload_result['secure_url']
        print(f"[INFO] Uploaded to: {cloudinary_url}")

        # Save to MongoDB
        doc = {
            "imageUrl": upload_result['url'],
            "cloudinaryUrl": cloudinary_url,
            "detections": detections,
            "timestamp": int(time.time() * 1000),
            "capturedFrom": source
        }
        result = collection.insert_one(doc)
        print(f"[INFO] Saved to MongoDB with ID: {result.inserted_id}")

        return jsonify({
            "success": True,
            "imageUrl": upload_result['url'],
            "cloudinaryUrl": cloudinary_url,
            "detections": detections,
            "mongoId": str(result.inserted_id),
            "message": "Detection completed successfully"
        })

    except Exception as e:
        print(f"[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        }), 500

@app.route('/api/shrimp-images', methods=['GET'])
def get_images():
    """Lấy danh sách tất cả ảnh đã lưu"""
    try:
        images = list(collection.find().sort('timestamp', -1).limit(100))
        for img in images:
            img['id'] = str(img['_id'])
            del img['_id']

        print(f"[INFO] Returning {len(images)} images")
        return jsonify(images)
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

@app.route('/api/shrimp-images/<image_id>', methods=['GET'])
def get_image_detail(image_id):
    """Lấy chi tiết 1 ảnh"""
    try:
        image = collection.find_one({'_id': ObjectId(image_id)})
        if image:
            image['id'] = str(image['_id'])
            del image['_id']
            return jsonify(image)
        else:
            return jsonify({
                "success": False,
                "message": "Image not found"
            }), 404
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

@app.route('/api/shrimp-images/<image_id>', methods=['DELETE'])
def delete_image(image_id):
    """Xóa ảnh"""
    try:
        result = collection.delete_one({'_id': ObjectId(image_id)})
        if result.deleted_count > 0:
            print(f"[INFO] Deleted image {image_id}")
            return jsonify({
                "success": True,
                "message": "Image deleted successfully"
            })
        else:
            return jsonify({
                "success": False,
                "message": "Image not found"
            }), 404
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "model": MODEL_PATH,
        "mongodb": "connected",
        "cloudinary": "configured"
    })

if __name__ == '__main__':
    print("=" * 50)
    print("🦐 Shrimp Detection Server Starting...")
    print("=" * 50)
    app.run(host='0.0.0.0', port=8000, debug=True)

