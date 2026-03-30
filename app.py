import streamlit as st
import google.generativeai as genai
import json
from fpdf import FPDF

# ==========================================
# 1. KONFIGURASI AI TERPENGAMAN (SECRETS)
# ==========================================
# Mengambil API key dari Streamlit Secrets (bukan hardcode)
try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-pro')
except KeyError:
    st.error("🔑 API Key belum diatur di Streamlit Secrets!")
    st.stop()

def get_ai_response(prompt):
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error AI: {str(e)}"

# ==========================================
# 2. LOGIKA PDF GENERATOR 
# ==========================================
class PDFResume(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 20)
        self.set_text_color(40, 40, 40)
    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Halaman {self.page_no()}', 0, 0, 'C')
    def chapter_title(self, title):
        self.set_font('Helvetica', 'B', 14)
        self.set_fill_color(240, 240, 240)
        self.cell(0, 10, title.upper(), border=0, new_x="LMARGIN", new_y="NEXT", align='L', fill=True)
        self.ln(2)
    def section_body(self, body):
        self.set_font('Times', '', 12)
        self.set_text_color(50, 50, 50)
        self.multi_cell(0, 7, body)
        self.ln(4)

def generate_pdf(json_data, enhanced_experience):
    try:
        data = json.loads(json_data)
    except:
        data = {}
    
    pdf = PDFResume()
    pdf.add_page()
    
    # Header
    pdf.set_font('Helvetica', 'B', 24)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 15, data.get('nama', 'Nama Tidak Ditemukan'), border=0, new_x="LMARGIN", new_y="NEXT", align='C')
    
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(100, 100, 100)
    contact_info = f"Email: {data.get('email', '-')} | Lokasi: Indonesia"
    pdf.cell(0, 5, contact_info, border=0, new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.ln(10)

    # Pendidikan
    if data.get('pendidikan'):
        pdf.chapter_title("Pendidikan")
        edu_text = ""
        for edu in data['pendidikan']:
            ins = edu.get('institusi', '-')
            jur = edu.get('jurusan', '-')
            thn = edu.get('tahun', '-')
            edu_text += f"{ins} - {jur} ({thn})\n"
        pdf.section_body(edu_text)

    # Pengalaman
    pdf.chapter_title("Pengalaman Kerja")
    if enhanced_experience:
        pdf.section_body(enhanced_experience)
    else:
        pdf.section_body("Data pengalaman tidak tersedia.")

    # Keahlian
    if data.get('keahlian'):
        pdf.chapter_title("Keahlian")
        skills_text = ", ".join(data['keahlian'])
        pdf.section_body(skills_text)

    return bytes(pdf.output())

# ==========================================
# 3. TAMPILAN WEB STREAMLIT
# ==========================================
st.set_page_config(page_title="AI CV Builder", page_icon="📝")
st.title("📝 AI CV Builder - Profesional & ATS-Friendly")
st.markdown("---")

st.header("Langkah 1: Masukkan Data Mentah Anda")
raw_text_input = st.text_area(
    "Tempelkan (paste) teks CV lama Anda di sini", 
    placeholder="Contoh: Nama Budi Santoso. Email budi@email.com. Pernah kerja jadi admin 2022 di PT Maju Mundur...",
    height=200
)

if st.button("✨ Proses CV Saya dengan AI"):
    if not raw_text_input:
        st.warning("⚠️ Masukkan teks CV Anda terlebih dahulu!")
    else:
        with st.spinner("🧠 AI sedang menyusun CV Anda..."):
            prompt_ext = f"""
            Ekstrak info dari teks ini ke JSON. WAJIB JSON valid tanpa markdown (```json).
            Struktur: {{"nama": "", "email": "", "pendidikan": [], "pengalaman": [], "keahlian": []}}.
            Teks: {raw_text_input}
            """
            json_result = get_ai_response(prompt_ext)
            
            try:
                temp_data = json.loads(json_result.replace('```json', '').replace('```', '').strip())
                posisi = temp_data['pengalaman'][0].get('posisi', 'Pekerjaan') if temp_data.get('pengalaman') else "Pekerjaan"
                deskripsi = temp_data['pengalaman'][0].get('deskripsi', '') if temp_data.get('pengalaman') else ""
            except:
                posisi, deskripsi = "Pekerjaan", raw_text_input

            prompt_enh = f"""
            Perbaiki deskripsi kerja ini agar profesional, gunakan action verbs, ATS-friendly.
            Posisi: {posisi}
            Deskripsi: {deskripsi}
            Berikan 3-4 bullet points perbaikan bahasa Indonesia baku. Hanya tulis bullet points.
            """
            enhanced_result = get_ai_response(prompt_enh)

            st.session_state['json_cv'] = json_result
            st.session_state['enhanced_cv'] = enhanced_result
            st.session_state['processed'] = True

if st.session_state.get('processed'):
    st.markdown("---")
    st.header("Langkah 2: Unduh PDF")
    st.success("CV Anda berhasil diproses!")
    
    try:
        clean_json = st.session_state['json_cv'].replace('```json', '').replace('```', '').strip()
        pdf_bytes = generate_pdf(clean_json, st.session_state['enhanced_cv'])
        st.download_button(
            label="📄 Unduh CV PDF Anda",
            data=pdf_bytes,
            file_name="CV_Profesional_AI.pdf",
            mime="application/pdf"
        )
    except Exception as e:
        st.error(f"Gagal membuat PDF: {e}")
