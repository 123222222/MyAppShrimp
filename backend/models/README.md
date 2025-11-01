# Models Directory

Đặt file YOLO model (.pt) vào đây.

## Nếu đã có model train sẵn:

1. Copy file `shrimp_best.pt` vào folder này
2. Update `.env`:
   ```
   YOLO_MODEL_PATH=models/shrimp_best.pt
   ```

## Nếu chưa có model:

Backend sẽ tự động download model mặc định YOLOv8n khi chạy lần đầu.

Để train model riêng cho tôm:
```python
from ultralytics import YOLO

# Load base model
model = YOLO('yolov8n.pt')

# Train on your shrimp dataset
model.train(
    data='shrimp_dataset.yaml',
    epochs=100,
    imgsz=640
)
```

## Download pre-trained models:

- YOLOv8n: https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt
- YOLOv8s: https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8s.pt
- YOLOv8m: https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8m.pt

