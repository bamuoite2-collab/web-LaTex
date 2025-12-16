import os
import json
import traceback
import time
import threading
# 👇 1. THÊM send_file VÀO DÒNG NÀY
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import google.generativeai as genai
from dotenv import load_dotenv
import json_repair

load_dotenv()

# --- CẤU HÌNH KEY & THREADING ---
keys_env = os.getenv("GEMINI_API_KEYS") or os.getenv("GEMINI_API_KEY")
API_KEYS = [k.strip() for k in keys_env.split(',') if k.strip()] if keys_env else []
current_key_index = 0
key_lock = threading.Lock()

if not API_KEYS:
    print("❌ LỖI: Chưa cấu hình GEMINI_API_KEYS trong file .env")
else:
    print(f"🔥 Server đang chạy với {len(API_KEYS)} API Key.")
    genai.configure(api_key=API_KEYS[0])

def rotate_key():
    global current_key_index
    if not API_KEYS: return
    with key_lock:
        current_key_index = (current_key_index + 1) % len(API_KEYS)
        print(f"🔄 Đổi sang Key #{current_key_index + 1}")
        genai.configure(api_key=API_KEYS[current_key_index])

app = Flask(__name__)
CORS(app)

# --- 👇 2. QUAN TRỌNG: THÊM ROUTE CHO TRANG CHỦ & ẢNH ---
@app.route('/')
def home():
    # Khi vào trang chủ, trả về file giao diện
    return send_file('index.html')

@app.route('/images.png')
def serve_image():
    # Giúp web tải được ảnh nền Doraemon
    return send_file('images.png')
# --------------------------------------------------------

# --- PROMPT OCR (GIỮ NGUYÊN) ---
PROMPT_QUESTION = r"""
Bạn là chuyên gia LaTeX và Xử lý dữ liệu. Nhiệm vụ: Chuyển đổi chính xác hình ảnh thành code LaTeX.

QUY TẮC SỐNG CÒN:
1. NỘI DUNG: CHỈ trả về nội dung (Body). BỎ QUA \documentclass.

2. LOGIC TẠO BẢNG (TABLE) - PHẢI TUÂN THỦ 4 BƯỚC:
   - BƯỚC 1 (QUAN SÁT): Đếm chính xác số lượng cột dọc trong ảnh.
   - BƯỚC 2 (KHUNG): Khai báo số lượng cột trong \begin{tabular}{|...|} phải KHỚP.
   - BƯỚC 3 (DỮ LIỆU): Điền dữ liệu từng hàng ngang.
   - BƯỚC 4 (THẨM MỸ): Luôn bao quanh bảng bằng: \begin{center} \resizebox{0.75\linewidth}{!}{ ... } \end{center}

3. ĐỊNH DẠNG VĂN BẢN:
   - Câu hỏi: \textbf{Câu 1:} (In đậm).
   - Trắc nghiệm: \begin{enumerate}[label=\textbf{\Alph*.}, leftmargin=1cm]

4. HÌNH VẼ & ĐỒ THỊ (PGFPLOTS):
   - BẮT BUỘC dùng môi trường `axis` với cấu hình sau:
     \begin{center}
     \begin{tikzpicture}
     \begin{axis}[
         axis lines = middle,
         axis line style={->, >=stealth, thick},
         xlabel = {$t$ (s)}, ylabel = {$x$ (m)},
         xlabel style={at={(ticklabel* cs:1)}, anchor=west}, 
         ylabel style={at={(ticklabel* cs:1)}, anchor=south},
         grid = both, major grid style = {dashed, gray!30},
         width = 8cm, height = 6cm,
     ]
     \addplot[thick, blue, mark=*] coordinates { ... };
     \end{axis}
     \end{tikzpicture}
     \end{center}

5. OUTPUT: Chỉ trả về JSON {"question_latex": "..."}
"""

PROMPT_SOLVER = r"""
Bạn là Giáo viên giỏi của Việt Nam. Giải chi tiết đề bài.

QUY TẮC BẤT DI BẤT DỊCH:
1. NGÔN NGỮ: 100% Tiếng Việt. KHÔNG chèn tiếng Anh.
2. ĐỊNH DẠNG: \textbf{Câu 1:}, Công thức $...$. Kết luận \textbf{Chọn đáp án A.}
3. HÌNH/BẢNG: Copy quy tắc resizebox/pgfplots từ phần OCR.
4. JSON: {"answer_latex": "Nội dung lời giải..."}
"""

def process_with_retry(files, prompt, retry_count=0):
    if not API_KEYS: return jsonify({"error": "Chưa cấu hình API Key"}), 500
    if retry_count >= len(API_KEYS):
        return jsonify({"error": "429 Quota Exceeded. Hệ thống quá tải, vui lòng đợi 60 giây."}), 429

    try:
        gemini_inputs = [prompt]
        for file in files:
            file.seek(0)
            gemini_inputs.append({
                "mime_type": getattr(file, 'content_type', 'image/jpeg'),
                "data": file.read()
            })

        # 👇 3. SỬA TÊN MODEL VỀ BẢN CHUẨN (2.0)
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash", 
            generation_config={"response_mime_type": "application/json"}
        )

        response = model.generate_content(gemini_inputs)
        
        try: return jsonify(json.loads(response.text))
        except: return jsonify(json_repair.loads(response.text))

    except Exception as e:
        err = str(e)
        if "429" in err or "Quota" in err or "403" in err:
            print("⚠️ Lỗi Quota. Đang đổi key...")
            rotate_key()
            time.sleep(1)
            return process_with_retry(files, prompt, retry_count + 1)
        
        print("❌ Lỗi Server:", traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route('/convert_questions', methods=['POST'])
def convert_questions():
    return process_with_retry(request.files.getlist('file'), PROMPT_QUESTION)

@app.route('/solve_problems', methods=['POST'])
def solve_problems():
    return process_with_retry(request.files.getlist('file'), PROMPT_SOLVER)

if __name__ == '__main__':
    app.run(debug=True, port=5000)