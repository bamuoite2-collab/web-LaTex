import google.generativeai as genai

# THAY API KEY CỦA BẠN VÀO ĐÂY
genai.configure(api_key="AIzaSyA0e1AccjR_zDiey2_vuiZ0zgQ0FBrn6uk")

print("Đang lấy danh sách các model khả dụng...")
try:
    models = genai.list_models()
    found = False
    for m in models:
        # Lọc chỉ hiện các model tạo văn bản (generateContent)
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
            if "gemini-1.5-flash" in m.name:
                found = True
    
    print("\n-----------------------------------")
    if found:
        print("✅ KẾT QUẢ: Có thấy 'gemini-1.5-flash'. Bạn có thể dùng bình thường.")
    else:
        print("❌ KẾT QUẢ: Không tìm thấy 'gemini-1.5-flash'. Hãy thử dùng 'gemini-pro' hoặc 'gemini-1.5-pro'.")

except Exception as e:
    print(f"Lỗi khi kết nối: {e}")