"""
Script test nhanh để kiểm tra backend hoạt động
"""
import requests
import base64
from PIL import Image
from io import BytesIO

def test_backend(image_path, backend_url="http://localhost:8000"):
    """Test detection API với một ảnh"""

    print("=" * 50)
    print("🧪 Testing Backend API")
    print("=" * 50)

    # 1. Health check
    print("\n[1/3] Testing health endpoint...")
    try:
        response = requests.get(f"{backend_url}/health")
        print(f"✅ Health check: {response.json()}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return

    # 2. Load and encode image
    print(f"\n[2/3] Loading image: {image_path}")
    try:
        with open(image_path, 'rb') as f:
            image_data = f.read()
        base64_image = base64.b64encode(image_data).decode('utf-8')
        print(f"✅ Image loaded and encoded ({len(base64_image)} chars)")
    except Exception as e:
        print(f"❌ Failed to load image: {e}")
        return

    # 3. Test detection
    print("\n[3/3] Testing detection API...")
    try:
        response = requests.post(
            f"{backend_url}/api/detect-shrimp",
            json={
                "image": base64_image,
                "source": "test-script"
            },
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            print("✅ Detection successful!")
            print(f"\n📊 Results:")
            print(f"   - Found {len(result['detections'])} shrimps")
            print(f"   - Cloudinary URL: {result['cloudinaryUrl']}")
            print(f"   - MongoDB ID: {result['mongoId']}")
            print(f"\n🦐 Detections:")
            for i, det in enumerate(result['detections'], 1):
                print(f"   {i}. {det['className']} - {det['confidence']:.2%} confidence")
        else:
            print(f"❌ Detection failed: {response.status_code}")
            print(response.json())

    except Exception as e:
        print(f"❌ Detection request failed: {e}")

    print("\n" + "=" * 50)

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python test_backend.py <image_path>")
        print("Example: python test_backend.py test_shrimp.jpg")
        sys.exit(1)

    image_path = sys.argv[1]
    backend_url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:8000"

    test_backend(image_path, backend_url)

