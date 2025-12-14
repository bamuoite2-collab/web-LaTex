import streamlit as st
import google.generativeai as genai
from PIL import Image
import requests

# --- CẤU HÌNH TRANG WEB ---
st.set_page_config(
    page_title="Trợ Lý Soạn Đề Vật Lý",
    page_icon="⚛️",
    layout="wide"
)

# --- CSS TÙY CHỈNH ---
st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 5px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ff4b4b;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# --- LẤY API KEY ---
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("⚠️ Chưa cấu hình API Key.")
    st.stop()

# --- CẤU HÌNH AI ---
# Dùng model mạnh nhất hiện có của bạn
model = genai.GenerativeModel("gemini-2.5-flash", system_instruction="""
Bạn là Trợ lý Giáo viên Vật lý & LaTeX chuyên nghiệp.
Nhiệm vụ:
1. Nhận ảnh đề thi -> Chuyển thành code LaTeX chuẩn (gói lệnh: inputenc, vietnamese babel, amsmath, geometry, tikz).
2. Nếu người dùng yêu cầu "CÓ LỜI GIẢI":
   - Hãy giải chi tiết từng câu hỏi ngay bên dưới.
   - Trình bày lời giải đẹp, dùng môi trường enumerate hoặc itemize.
   - QUAN TRỌNG: Phải tách riêng phần "Đề bài thuần túy" và phần "Lời giải" bằng dòng chữ chính xác là: <<<PHAN_CACH_LOI_GIAI>>>
   - Phần đầu là code LaTeX của đề thi (để in đề).
   - Phần sau là code LaTeX của lời giải (để in đáp án).
3. Nếu KHÔNG yêu cầu lời giải: Chỉ trả về code LaTeX đề thi.
4. Không viết lời dẫn thừa thãi.
""")

# Hàm làm sạch code
def clean_latex_code(text):
    text = text.replace("```latex", "").replace("```", "").strip()
    return text

# Hàm in PDF
def convert_to_pdf(latex_code):
    url = "https://latex.online/compile"
    try:
        response = requests.post(url, data={'text': latex_code, 'command': 'pdflatex'}, timeout=60)
        return response.content if response.status_code == 200 else None
    except:
        return None

# --- GIAO DIỆN CHÍNH ---
st.title("⚛️ Tool Soạn Đề & Giải Đề Tự Động")
st.caption("Hỗ trợ giáo viên Vật lý - Powered by Gemini 2.5")
st.markdown("---")

col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("1. Đầu vào")
    uploaded_file = st.file_uploader("Tải ảnh đề thi lên", type=["jpg", "png", "jpeg"])
    
    # TÙY CHỌN MỚI
    st.markdown("#### Tùy chọn xử lý:")
    include_solution = st.toggle("✅ Kèm Lời Giải Chi Tiết", value=False, help="AI sẽ tự động giải đề thi này cho bạn")
    
    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="Ảnh gốc", use_column_width=True)

with col2:
    st.subheader("2. Kết quả")
    
    if uploaded_file and st.button("🚀 BẮT ĐẦU XỬ LÝ", type="primary", use_container_width=True):
        status = st.status("Đang phân tích đề bài...", expanded=True)
        
        try:
            # TẠO PROMPT DỰA TRÊN LỰA CHỌN
            user_prompt = "Chuyển ảnh này thành LaTeX."
            if include_solution:
                user_prompt += " YÊU CẦU: Có kèm lời giải chi tiết và dùng dấu phân cách <<<PHAN_CACH_LOI_GIAI>>>."
            
            # GỌI GEMINI
            response = model.generate_content([user_prompt, image])
            full_text = clean_latex_code(response.text)
            
            # XỬ LÝ TÁCH ĐỀ VÀ GIẢI
            if "<<<PHAN_CACH_LOI_GIAI>>>" in full_text:
                parts = full_text.split("<<<PHAN_CACH_LOI_GIAI>>>")
                question_code = parts[0].strip()
                solution_code = parts[1].strip()
                has_solution = True
            else:
                question_code = full_text
                solution_code = ""
                has_solution = False
            
            status.update(label="Đã xong! Đang hiển thị...", state="complete", expanded=False)
            
            # HIỂN THỊ DẠNG TAB (Rất tiện cho GV)
            tab1, tab2 = st.tabs(["📄 ĐỀ THI (Học sinh)", "📝 ĐÁP ÁN (Giáo viên)"])
            
            with tab1:
                st.info("Dưới đây là code đề thi (không có giải):")
                st.code(question_code, language='latex')
                # Nút in PDF Đề
                if st.button("🖨️ Xuất PDF Đề Thi"):
                    with st.spinner("Đang in PDF..."):
                        pdf_data = convert_to_pdf(question_code)
                        if pdf_data:
                            st.download_button("📥 TẢI PDF ĐỀ", pdf_data, "De_thi.pdf", "application/pdf")
                        else:
                            st.error("Server in bận. Hãy copy code trên vào Overleaf.")

            with tab2:
                if has_solution:
                    st.success("AI đã giải xong! Dưới đây là code lời giải:")
                    st.code(solution_code, language='latex')
                    st.warning("⚠️ Lưu ý: Hãy kiểm tra lại các con số tính toán của AI trước khi dùng.")
                else:
                    if include_solution:
                        st.warning("AI quên tách lời giải. Hãy kiểm tra lại code ở Tab 1.")
                    else:
                        st.info("Bạn chưa chọn chế độ giải đề. Hãy gạt nút bên trái rồi chạy lại.")
                        
        except Exception as e:
            st.error(f"Lỗi: {e}")