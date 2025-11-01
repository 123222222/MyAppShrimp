from flask import Flask, request, jsonify
from flask_cors import CORS
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

# Load TFLite model
MODEL_PATH = os.getenv('YOLO_MODEL_PATH', 'models/best-fp16(1).tflite')
print(f"Loading TFLite model from {MODEL_PATH}...")

try:
    # Thử import tflite_runtime trước (cho Raspberry Pi)
    from tflite_runtime.interpreter import Interpreter
    print("Using tflite_runtime")
except ImportError:
    # Nếu không có, dùng tensorflow
    import tensorflow as tf
    Interpreter = tf.lite.Interpreter
    print("Using tensorflow.lite")

# Khởi tạo interpreter
interpreter = Interpreter(model_path=MODEL_PATH)
interpreter.allocate_tensors()

# Lấy thông tin input/output
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

print(f"TFLite model loaded successfully!")
print(f"Input shape: {input_details[0]['shape']}")
print(f"Output details: {len(output_details)} outputs")
for i, output in enumerate(output_details):
    print(f"  Output {i}: shape={output['shape']}, dtype={output['dtype']}")

# Lấy kích thước input
input_shape = input_details[0]['shape']
INPUT_HEIGHT = input_shape[1]
INPUT_WIDTH = input_shape[2]

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

# Class names - cập nhật theo model của bạn
CLASS_NAMES = ['shrimp']  # Thêm các class khác nếu có

def preprocess_image(image_np):
    """Tiền xử lý ảnh cho TFLite model"""
    # Resize về kích thước input của model
    img = cv2.resize(image_np, (INPUT_WIDTH, INPUT_HEIGHT))

    # Convert BGR to RGB
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # Normalize về [0, 1] cho FP16 model
    img = img.astype(np.float32) / 255.0

    # Thêm batch dimension
    img = np.expand_dims(img, axis=0)

    return img

def run_inference(image_np):
    """Chạy inference với TFLite model"""
    # Preprocess
    input_data = preprocess_image(image_np)

    # Set input tensor
    interpreter.set_tensor(input_details[0]['index'], input_data)

    # Run inference
    interpreter.invoke()

    # Get output tensors
    outputs = []
    for output in output_details:
        outputs.append(interpreter.get_tensor(output['index']))

    return outputs

def parse_yolo_output(outputs, original_shape, conf_threshold=0.25, iou_threshold=0.45):
    """
    Parse YOLO TFLite output và apply NMS

    Output format phụ thuộc vào cách export model:
    - Format 1: [1, N, 6] - (x, y, w, h, conf, class)
    - Format 2: [1, 25200, 85] - (x, y, w, h, conf, class1, class2, ...)
    - Format 3: Multiple outputs - boxes, scores, classes
    """

    detections = []
    orig_h, orig_w = original_shape[:2]

    # Kiểm tra format output
    if len(outputs) == 1:
        output = outputs[0]

        # Format [1, N, 6] hoặc [1, N, 85]
        if len(output.shape) == 3:
            output = output[0]  # Remove batch dimension

            boxes = []
            scores = []
            class_ids = []

            for detection in output:
                # Format: [x, y, w, h, conf, class] hoặc [x, y, w, h, conf, class_scores...]
                if len(detection) >= 6:
                    x, y, w, h, conf = detection[:5]

                    if conf < conf_threshold:
                        continue

                    # Lấy class
                    if len(detection) == 6:
                        class_id = int(detection[5])
                    else:
                        # Multi-class: lấy class có score cao nhất
                        class_scores = detection[5:]
                        class_id = np.argmax(class_scores)
                        conf = conf * class_scores[class_id]  # Nhân với class confidence

                    if conf < conf_threshold:
                        continue

                    # Convert từ normalized coords về pixel coords
                    x1 = int((x - w/2) * orig_w)
                    y1 = int((y - h/2) * orig_h)
                    x2 = int((x + w/2) * orig_w)
                    y2 = int((y + h/2) * orig_h)

                    boxes.append([x1, y1, x2, y2])
                    scores.append(float(conf))
                    class_ids.append(class_id)

            # Apply NMS
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

    elif len(outputs) >= 3:
        # Format với boxes, scores, classes riêng biệt (như TF Object Detection API)
        boxes = outputs[0][0]  # [N, 4]
        scores = outputs[1][0]  # [N]
        classes = outputs[2][0]  # [N]

        for i in range(len(scores)):
            if scores[i] >= conf_threshold:
                y1, x1, y2, x2 = boxes[i]
                x1 = int(x1 * orig_w)
                y1 = int(y1 * orig_h)
                x2 = int(x2 * orig_w)
                y2 = int(y2 * orig_h)

                w = x2 - x1
                h = y2 - y1
                x = x1 + w/2
                y = y1 + h/2

                class_id = int(classes[i])

                detections.append({
                    "className": CLASS_NAMES[class_id] if class_id < len(CLASS_NAMES) else f"class_{class_id}",
                    "confidence": float(scores[i]),
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

        # Vẽ bounding box
        color = (0, 255, 0)  # Green
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)

        # Vẽ label
        label = f"{det['className']} {det['confidence']:.2f}"
        label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)

        # Background cho text
        cv2.rectangle(img, (x1, y1 - label_size[1] - 10),
                     (x1 + label_size[0], y1), color, -1)

        # Text
        cv2.putText(img, label, (x1, y1 - 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)

    return img

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

        # Convert RGB to BGR for OpenCV
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
        doc = {
            "imageUrl": upload_result['url'],
            "cloudinaryUrl": cloudinary_url,
            "detections": detections,
            "timestamp": int(time.time() * 1000),
            "capturedFrom": source,
            "inferenceTime": inference_time
        }
        result = collection.insert_one(doc)
        print(f"[INFO] Saved to MongoDB with ID: {result.inserted_id}")

        return jsonify({
            "success": True,
            "imageUrl": upload_result['url'],
            "cloudinaryUrl": cloudinary_url,
            "detections": detections,
            "mongoId": str(result.inserted_id),
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
        "model_type": "TFLite",
        "input_shape": input_details[0]['shape'].tolist(),
        "mongodb": "connected",
        "cloudinary": "configured"
    })

if __name__ == '__main__':
    print("=" * 50)
    print("🦐 Shrimp Detection Server (TFLite) Starting...")
    print("=" * 50)
    app.run(host='0.0.0.0', port=8000, debug=True)

