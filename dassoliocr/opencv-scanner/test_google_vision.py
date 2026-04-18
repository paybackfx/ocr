import requests
import base64
import json
import sys # هادي هي اللي غاتخلينا نقراو الـ Arguments

# 1. الساروت ديالك [cite: 2026-02-27]
API_KEY = "AIzaSyCpeixcJjwo9bAVpKqoP72nBrVLx-xdRP0"

def run_vision_test(image_path):
    try:
        # تحويل التصويرة لـ Base64
        with open(image_path, "rb") as f:
            image_content = base64.b64encode(f.read()).decode("utf-8")
        
        url = f"https://vision.googleapis.com/v1/images:annotate?key={API_KEY}"
        payload = {
            "requests": [{
                "image": {"content": image_content},
                "features": [{"type": "TEXT_DETECTION"}]
            }]
        }

        print(f"🚀 صيفطنا '{image_path}' لـ Google Vision...")
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            responses = data.get('responses', [])
            if responses and 'fullTextAnnotation' in responses[0]:
                text = responses[0]['fullTextAnnotation']['text']
                print("\n✅ ها شنو لقى Google فـ الورقة:")
                print("-" * 40)
                print(text)
                print("-" * 40)
            else:
                print("⚠️ Google ما لقى حتى تيكست فـ هاد التصويرة.")
        else:
            print(f"❌ خطأ فـ الـ API: {response.status_code}")
            print(response.text)

    except FileNotFoundError:
        print(f"❌ مالقيتش الملف فـ هاد الـ Path: {image_path}")
    except Exception as e:
        print(f"❌ طرا شي مشكل: {str(e)}")

if __name__ == "__main__":
    # التحقق واش المستعمل عطا الـ Path فـ الـ Terminal
    if len(sys.argv) < 2:
        print("💡 طريقة الاستعمال: python3 vision_arg.py path/to/image.jpg")
    else:
        # كنهزو الـ Argument الأول اللي من بعد سمية السكريبت
        img_path = sys.argv[1]
        run_vision_test(img_path)