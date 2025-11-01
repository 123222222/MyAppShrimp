from flask import Flask, Response, request, jsonify
from flask_cors import CORS
from functools import wraps
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
import threading

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# ==================== CAMERA SETUP ====================
print("Initializing camera...")
camera = None
camera_lock = threading.Lock()

for i in range(30):
    test_cam = cv2.VideoCapture(i, cv2.CAP_V4L2)
    if test_cam.isOpened():
        ret, frame = test_cam.read()
        if ret:
            print(f"✅ Camera found at /dev/video{i}")
            camera = test_cam
            break
        test_cam.release()

if camera is None:
    print("⚠️  Warning: No camera found! Camera streaming will not work.")
else:
    time.sleep(2)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    camera.set(cv2.CAP_PROP_FPS, 30)
    camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
    print("✅ Camera initialized successfully!")

# ==================== AI MODEL SETUP ====================
MODEL_PATH = os.getenv('YOLO_MODEL_PATH', 'models/best-fp16(1).tflite')
print(f"\nLoading TFLite model from {MODEL_PATH}...")

try:
    from tflite_runtime.interpreter import Interpreter
    print("Using tflite_runtime")
except ImportError:
    try:
        import tensorflow as tf
        Interpreter = tf.lite.Interpreter
        print("Using tensorflow.lite")
    except ImportError:
        print("⚠️  Warning: No TFLite runtime found! Detection will not work.")
        Interpreter = None

if Interpreter and os.path.exists(MODEL_PATH):
    interpreter = Interpreter(model_path=MODEL_PATH)
    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    input_shape = input_details[0]['shape']
    INPUT_HEIGHT = input_shape[1]
    INPUT_WIDTH = input_shape[2]
    print(f"✅ TFLite model loaded successfully!")
    print(f"   Input shape: {input_shape}")
else:
    print("⚠️  Warning: Model not loaded!")
    interpreter = None
    INPUT_HEIGHT = 320
    INPUT_WIDTH = 320

# ==================== CLOUDINARY SETUP ====================
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)
print("✅ Cloudinary configured!")

# ==================== MONGODB SETUP ====================
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
MONGODB_DB = os.getenv('MONGODB_DATABASE', 'shrimp_db')
try:
    mongo_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    mongo_client.server_info()  # Test connection
    db = mongo_client[MONGODB_DB]
    collection = db['detections']
    print(f"✅ Connected to MongoDB: {MONGODB_DB}")
except Exception as e:
    print(f"⚠️  MongoDB connection failed: {e}")
    collection = None

# ==================== AUTH SETUP ====================
USERNAME = os.getenv('CAMERA_USERNAME', 'admin')
PASSWORD = os.getenv('CAMERA_PASSWORD', '123456')

def check_auth(username, password):
    return username == USERNAME and password == PASSWORD

def authenticate():
    return Response(
        'Authentication required', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

# ==================== AI FUNCTIONS ====================
CLASS_NAMES = ['shrimp']

def preprocess_image(image_np):
    """Tiền xử lý ảnh cho TFLite model"""
    img = cv2.resize(image_np, (INPUT_WIDTH, INPUT_HEIGHT))
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = img.astype(np.float32) / 255.0
    img = np.expand_dims(img, axis=0)
    return img

def run_inference(image_np):
    """Chạy inference với TFLite model"""
    if interpreter is None:
        return []

    input_data = preprocess_image(image_np)
    interpreter.set_tensor(input_details[0]['index'], input_data)
    interpreter.invoke()

    outputs = []
    for output in output_details:
        outputs.append(interpreter.get_tensor(output['index']))

    return outputs

def parse_yolo_output(outputs, original_shape, conf_threshold=0.25, iou_threshold=0.45):
    """Parse YOLO TFLite output và apply NMS"""
    detections = []
    orig_h, orig_w = original_shape[:2]

    if len(outputs) == 0:
        return detections

    if len(outputs) == 1:
        output = outputs[0]

        if len(output.shape) == 3:
            output = output[0]

            boxes = []
            scores = []
            class_ids = []

            for detection in output:
                if len(detection) >= 6:
                    x, y, w, h, conf = detection[:5]

                    if conf < conf_threshold:
                        continue

                    if len(detection) == 6:
                        class_id = int(detection[5])
                    else:
                        class_scores = detection[5:]
                        class_id = np.argmax(class_scores)
                        conf = conf * class_scores[class_id]

                    if conf < conf_threshold:
                        continue

                    x1 = int((x - w/2) * orig_w)
                    y1 = int((y - h/2) * orig_h)
                    x2 = int((x + w/2) * orig_w)
                    y2 = int((y + h/2) * orig_h)

                    boxes.append([x1, y1, x2, y2])
                    scores.append(float(conf))
                    class_ids.append(class_id)

            if len(boxes) > 0:
                indices = cv2.dnn.NMSBoxes(boxes, scores, conf_threshold, iou_threshold)

                if len(indices) > 0:
                    for i in indices.flatten():
                        x1, y1, x2, y2 = boxes[i]
                        w = x2 - x1
                        h = y2 - y1
                        x = x1 + w/2
                        y = y1 + h/2

                        detections.append({
                            "className": CLASS_NAMES[class_ids[i]] if class_ids[i] < len(CLASS_NAMES) else f"class_{class_ids[i]}",
                            "confidence": scores[i],
                            "bbox": {
                                "x": float(x),
                                "y": float(y),
                                "width": float(w),
                                "height": float(h)
                            }
                        })

    return detections

def draw_detections(image_np, detections):
    """Vẽ bounding boxes lên ảnh"""
    img = image_np.copy()

    for det in detections:
        bbox = det['bbox']
        x = int(bbox['x'])
        y = int(bbox['y'])
        w = int(bbox['width'])
        h = int(bbox['height'])

        x1 = int(x - w/2)
        y1 = int(y - h/2)
        x2 = int(x + w/2)
        y2 = int(y + h/2)

        color = (0, 255, 0)
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)

        label = f"{det['className']} {det['confidence']:.2f}"
        label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)

        cv2.rectangle(img, (x1, y1 - label_size[1] - 10),
                     (x1 + label_size[0], y1), color, -1)

        cv2.putText(img, label, (x1, y1 - 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)

    return img

# ==================== CAMERA STREAMING ====================
def generate_frames():
    """Generate camera frames for MJPEG streaming"""
    if camera is None:
        # Nếu không có camera, trả về ảnh placeholder
        while True:
            placeholder = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(placeholder, "No Camera", (200, 240),
                       cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
            ret, buffer = cv2.imencode('.jpg', placeholder)
            if ret:
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.1)
    else:
        while True:
            with camera_lock:
                camera.grab()
                success, frame = camera.retrieve()

            if not success:
                time.sleep(0.05)
                continue

            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ret:
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.033)

@app.route('/blynk_feed')
def blynk_feed():
    """Camera stream endpoint (no auth for app)"""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/video_feed')
@requires_auth
def video_feed():
    """Camera stream endpoint (with auth)"""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/blynk_player')
def blynk_player():
    """HTML player for camera stream"""
    return '''
    <html>
    <head><title>Camera Stream</title></head>
    <body style="margin:0;padding:0;">
    <img src="/blynk_feed" style="width:100%;height:100%;">
    </body>
    </html>
    '''

# ==================== DETECTION API ====================
@app.route('/api/detect-shrimp', methods=['POST'])
def detect_shrimp():
    """
    Endpoint nhận ảnh từ Android app, xử lý với YOLO TFLite,
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

        if len(image_np.shape) == 3 and image_np.shape[2] == 3:
            image_np = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)

        print(f"[INFO] Image size: {image.size}")

        # Run TFLite inference
        print("[INFO] Running TFLite detection...")
        start_time = time.time()
        outputs = run_inference(image_np)
        inference_time = time.time() - start_time
        print(f"[INFO] Inference time: {inference_time:.3f}s")

        # Parse detections
        detections = parse_yolo_output(outputs, image_np.shape)
        print(f"[INFO] Found {len(detections)} detections")

        # Generate annotated image
        annotated_image = draw_detections(image_np, detections)
        annotated_image_rgb = cv2.cvtColor(annotated_image, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(annotated_image_rgb)

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
        if collection is not None:
            doc = {
                "imageUrl": upload_result['url'],
                "cloudinaryUrl": cloudinary_url,
                "detections": detections,
                "timestamp": int(time.time() * 1000),
                "capturedFrom": source,
                "inferenceTime": inference_time
            }
            result = collection.insert_one(doc)
            mongo_id = str(result.inserted_id)
            print(f"[INFO] Saved to MongoDB with ID: {mongo_id}")
        else:
            mongo_id = "no-mongodb"

        return jsonify({
            "success": True,
            "imageUrl": upload_result['url'],
            "cloudinaryUrl": cloudinary_url,
            "detections": detections,
            "mongoId": mongo_id,
            "inferenceTime": inference_time,
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
        if collection is None:
            return jsonify([])

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
        if collection is None:
            return jsonify({
                "success": False,
                "message": "MongoDB not available"
            }), 503

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
        if collection is None:
            return jsonify({
                "success": False,
                "message": "MongoDB not available"
            }), 503

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
        "camera": "available" if camera is not None else "not found",
        "model": MODEL_PATH,
        "model_type": "TFLite",
        "model_loaded": interpreter is not None,
        "mongodb": "connected" if collection is not None else "not connected",
        "cloudinary": "configured"
    })

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🦐 Shrimp Detection Server (TFLite) Starting...")
    print("="*50)
    print(f"Camera: {'✅ Available' if camera else '❌ Not found'}")
    print(f"Model: {'✅ Loaded' if interpreter else '❌ Not loaded'}")
    print(f"MongoDB: {'✅ Connected' if collection else '❌ Not connected'}")
    print(f"Cloudinary: ✅ Configured")
    print("\nEndpoints:")
    print("  - Camera Stream: /blynk_feed")
    print("  - Detection API: /api/detect-shrimp")
    print("  - Gallery API: /api/shrimp-images")
    print("  - Health Check: /health")
    print("="*50 + "\n")

    app.run(host='0.0.0.0', port=8000, debug=False, threaded=True)

