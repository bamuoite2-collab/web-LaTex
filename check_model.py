import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEYS")
if not API_KEY:
    print("❌ Vui lòng đặt biến môi trường GEMINI_API_KEY trước khi chạy script này.")
    raise SystemExit(1)

genai.configure(api_key=API_KEY.split(',')[0])

print("Đang lấy danh sách các model khả dụng...")
try:
    models = genai.list_models()
    found = False
    for m in models:
        if hasattr(m, 'supported_generation_methods') and 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
            if "gemini-2.5-flash" in m.name:
                found = True

    print("\n-----------------------------------")
    if found:
        print("✅ KẾT QUẢ: Có thấy 'gemini-2.5-flash'. Bạn có thể dùng bình thường.")
    else:
        print("❌ KẾT QUẢ: Không tìm thấy 'gemini-2.5-flash'. Hãy thử dùng 'gemini-pro' hoặc 'gemini-1.5-pro'.")

except Exception as e:
    print(f"Lỗi khi kết nối: {e}")