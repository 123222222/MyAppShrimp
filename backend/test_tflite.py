"""
Script test TFLite model trước khi chạy backend đầy đủ
"""
import os
import numpy as np
import cv2
from PIL import Image

# Test import
print("Testing imports...")
try:
    from tflite_runtime.interpreter import Interpreter
    print("✅ Using tflite_runtime")
except ImportError:
    try:
        import tensorflow as tf
        Interpreter = tf.lite.Interpreter
        print("✅ Using tensorflow.lite")
    except ImportError:
        print("❌ Không tìm thấy TFLite! Cần cài đặt tflite_runtime hoặc tensorflow")
        exit(1)

# Load model
MODEL_PATH = os.getenv('YOLO_MODEL_PATH', 'models/best-fp16(1).tflite')
print(f"\nLoading model: {MODEL_PATH}")

if not os.path.exists(MODEL_PATH):
    print(f"❌ Model file không tồn tại: {MODEL_PATH}")
    exit(1)

try:
    interpreter = Interpreter(model_path=MODEL_PATH)
    interpreter.allocate_tensors()
    print("✅ Model loaded successfully!")
except Exception as e:
    print(f"❌ Lỗi khi load model: {e}")
    exit(1)

# Get input/output details
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

print("\n" + "="*50)
print("MODEL INFORMATION")
print("="*50)

print(f"\nInput Details:")
for i, inp in enumerate(input_details):
    print(f"  Input {i}:")
    print(f"    - Shape: {inp['shape']}")
    print(f"    - Type: {inp['dtype']}")
    print(f"    - Index: {inp['index']}")

print(f"\nOutput Details:")
for i, out in enumerate(output_details):
    print(f"  Output {i}:")
    print(f"    - Shape: {out['shape']}")
    print(f"    - Type: {out['dtype']}")
    print(f"    - Index: {out['index']}")

# Test với ảnh dummy
print("\n" + "="*50)
print("TESTING INFERENCE")
print("="*50)

input_shape = input_details[0]['shape']
INPUT_HEIGHT = input_shape[1]
INPUT_WIDTH = input_shape[2]
INPUT_CHANNELS = input_shape[3]

print(f"\nCreating dummy image: {INPUT_HEIGHT}x{INPUT_WIDTH}x{INPUT_CHANNELS}")

# Tạo ảnh dummy
dummy_image = np.random.rand(INPUT_HEIGHT, INPUT_WIDTH, INPUT_CHANNELS).astype(np.float32)
dummy_input = np.expand_dims(dummy_image, axis=0)

print(f"Input shape: {dummy_input.shape}")
print(f"Input dtype: {dummy_input.dtype}")

# Run inference
try:
    print("\nRunning inference...")
    interpreter.set_tensor(input_details[0]['index'], dummy_input)
    interpreter.invoke()

    print("✅ Inference successful!")

    print("\nOutput shapes:")
    for i, out in enumerate(output_details):
        output = interpreter.get_tensor(out['index'])
        print(f"  Output {i}: {output.shape}, min={output.min():.4f}, max={output.max():.4f}")

except Exception as e:
    print(f"❌ Lỗi khi chạy inference: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n" + "="*50)
print("TEST COMPLETED SUCCESSFULLY!")
print("="*50)

print("\n📝 Ghi chú:")
print("  - Model đã load và chạy thành công")
print("  - Input shape:", input_details[0]['shape'])
print("  - Output có", len(output_details), "tensors")
print("\n  Bây giờ bạn có thể chạy backend bằng: python3 app_tflite.py")

