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
import io
from PIL import Image
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
# --- HÀM NÉN ẢNH (TỐI ƯU TỐC ĐỘ) ---
def compress_image(file_storage):
    """Nén ảnh xuống kích thước tối đa 1024px để gửi đi nhanh hơn"""
    try:
        img = Image.open(file_storage)
        # Chuyển về RGB nếu là ảnh PNG trong suốt
        if img.mode in ('RGBA', 'P'): img = img.convert('RGB')
        
        # Resize nếu ảnh quá to (>1024px)
        max_size = 1024
        if max(img.size) > max_size:
            img.thumbnail((max_size, max_size))
        
        # Lưu vào bộ nhớ đệm
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG', quality=85) # Nén chất lượng 85%
        return img_byte_arr.getvalue()
    except Exception as e:
        print(f"⚠️ Lỗi nén ảnh: {e}, dùng ảnh gốc.")
        file_storage.seek(0)
        return file_storage.read()
# --- PROMPT OCR (GIỮ NGUYÊN) ---
PROMPT_QUESTION = r"""
Bạn là chuyên gia LaTeX và Xử lý dữ liệu. Nhiệm vụ: Chuyển đổi chính xác hình ảnh thành code LaTeX.

QUY TẮC SỐNG CÒN:
1. NỘI DUNG: 
- CHỈ trả về nội dung (Body). BỎ QUA \documentclass.
- CHỈ trả về nội dung cốt lõi (phần nằm giữa \begin{document} và \end{document}).
- TUYỆT ĐỐI KHÔNG bao gồm \documentclass, \usepackage.
- TUYỆT ĐỐI KHÔNG liệt kê tên các gói (như amsmath, tikz, graphicx...).
- Bắt đầu ngay bằng: \textbf{Câu...}

2. LOGIC TẠO BẢNG (TABLE) - PHẢI TUÂN THỦ 4 BƯỚC:
   - BƯỚC 1 (QUAN SÁT): Đếm chính xác số lượng cột dọc trong ảnh.
   - BƯỚC 2 (KHUNG): Khai báo số lượng cột trong \begin{tabular}{|...|} phải KHỚP.
   - BƯỚC 3 (DỮ LIỆU): Điền dữ liệu từng hàng ngang.
   - BƯỚC 4 (THẨM MỸ): Luôn bao quanh bảng bằng: \begin{center} \resizebox{0.75\linewidth}{!}{ ... } \end{center}

3. ĐỊNH DẠNG VĂN BẢN:
   - Câu hỏi: \textbf{Câu 1:} (In đậm).
   - Trắc nghiệm: \begin{enumerate}[label=\textbf{\Alph*.}, leftmargin=1cm]
   - Khi cần tạo dòng kẻ chấm để học sinh điền câu trả lời (giống như trong các đề thi), BẮT BUỘC phải sử dụng cấu trúc: \noindent\makebox[\linewidth]{\dotfill} \\

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

Bạn là một trợ lý chuyên giải bài tập Vật lý và Hóa học, là Giáo viên giỏi của Việt Nam. Nhiệm vụ của bạn là giải chính xác và xuất ra lời giải dưới định dạng LaTeX chuẩn, đẹp và chuyên nghiệp.

TUÂN THỦ NGHIÊM NGẶT CÁC QUY TẮC SAU:


1. NGÔN NGỮ: 100% Tiếng Việt. KHÔNG chèn tiếng Anh.
2. ĐỊNH DẠNG: \textbf{Câu 1:}, Công thức $...$. Kết luận \textbf{Chọn đáp án A.}
3. HÌNH/BẢNG: Copy quy tắc resizebox/pgfplots từ phần OCR.
4. QUY TẮC VỀ BIẾN SỐ VÀ CHỈ SỐ (QUAN TRỌNG NHẤT):
   - Tuyệt đối KHÔNG viết trực tiếp chữ tiếng Việt hoặc văn bản trong môi trường toán học ($...$) mà không có bao bọc.
   - Khi biến số có chỉ số dưới là văn bản (tên người, tên vật), BẮT BUỘC phải dùng lệnh \text{}.
   - Ví dụ SAI: v_{Hoàng}, v_{TB}, m_{nước}
   - Ví dụ ĐÚNG: v_{\text{Hoàng}}, v_{\text{TB}}, m_{\text{nước}}
   - Đơn vị đo lường cũng phải dùng \text{}. Ví dụ: 2,5 \text{ m/s}.

5. QUY TẮC CĂN LỀ VÀ TRÌNH BÀY:
   - Với các phép tính có nhiều dòng hoặc so sánh, BẮT BUỘC sử dụng môi trường \begin{align*} ... \end{align*} để căn thẳng hàng các dấu bằng (=) hoặc dấu so sánh.
   - Không lạm dụng gạch đầu dòng (itemize) cho các đoạn văn phân tích dài. Hãy viết thành đoạn văn (paragraph) và xuống dòng hợp lý.
   - Thêm khoảng cách giữa các phần bằng lệnh \vspace{0.5em} hoặc xuống dòng đơn giản để lời giải thoáng mắt.

6. ĐỊNH DẠNG SỐ:
   - Sử dụng dấu phẩy (,) cho số thập phân theo chuẩn Việt Nam (ví dụ: 2,5 thay vì 2.5).

7. Quy tắc đơn vị Vật lý (Units):

   -Đơn vị đo lường (m, kg, s, m/s, Pa, N/m²,...) KHÔNG được để in nghiêng (không được để trực tiếp trong cặp dấu $...$).

   - BẮT BUỘC bọc đơn vị trong lệnh \text{} khi nằm trong môi trường toán học.

   - Ví dụ SAI: $10 m/s$, $v = 5 m/s^2$.

   - Ví dụ ĐÚNG: $10 \text{ m/s}$, $v = 5 \text{ m/s}^2$, $0,06 \text{ m}^3$.

   -Phải có một khoảng cách nhỏ giữa con số và đơn vị (ví dụ: 10 \text{ kg}).
8 . JSON: {"answer_latex": "Nội dung lời giải..."}
"""

def process_with_retry(files, prompt, retry_count=0):
    if not API_KEYS: return jsonify({"error": "Chưa cấu hình API Key"}), 500
    if retry_count >= len(API_KEYS):
        return jsonify({"error": "429 Quota Exceeded. Hệ thống quá tải, vui lòng đợi 60 giây."}), 429

    try:
        gemini_inputs = [prompt]
        for file in files:
            try:
                # Kiểm tra loại file (PDF hay ảnh) - ưu tiên kiểm tra filename
                filename = file.filename or ''
                is_pdf = filename.lower().endswith('.pdf')
                
                file.seek(0)  # Reset file pointer
                if is_pdf:
                    # Đọc dữ liệu nhị phân trực tiếp cho PDF
                    pdf_data = file.read()
                    if not pdf_data:
                        raise ValueError(f"Không thể đọc file PDF: {filename}")
                    gemini_inputs.append({"mime_type": "application/pdf", "data": pdf_data})
                else:
                    # Xử lý ảnh như cũ
                    processed_data = compress_image(file)
                    gemini_inputs.append({"mime_type": "image/jpeg", "data": processed_data})
            except Exception as file_err:
                print(f"⚠️ Lỗi xử lý file {file.filename}: {file_err}")
                raise ValueError(f"Lỗi xử lý file {file.filename}: {str(file_err)}")
        

        # 👇 3. SỬA TÊN MODEL VỀ BẢN CHUẨN (2.5)
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash", 
            generation_config={"response_mime_type": "application/json"}
        )

        response = model.generate_content(gemini_inputs)
        
        try: return jsonify(json.loads(response.text))
        except: return jsonify(json_repair.loads(response.text))

    except Exception as e:
        err = str(e)
        print("❌ Lỗi trong process_with_retry:", traceback.format_exc())
        if "429" in err or "Quota" in err or "403" in err:
            print("⚠️ Lỗi Quota. Đang đổi key...")
            rotate_key()
            time.sleep(1)
            # Reset file pointers trước khi retry
            for file in files:
                try:
                    file.seek(0)
                except:
                    pass
            return process_with_retry(files, prompt, retry_count + 1)
        
        return jsonify({"error": str(e)}), 500

@app.route('/convert_questions', methods=['POST'])
def convert_questions():
    return process_with_retry(request.files.getlist('file'), PROMPT_QUESTION)

@app.route('/solve_problems', methods=['POST'])
def solve_problems():
    return process_with_retry(request.files.getlist('file'), PROMPT_SOLVER)

if __name__ == '__main__':
    # Khi chạy local: PORT mặc định 5000
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)