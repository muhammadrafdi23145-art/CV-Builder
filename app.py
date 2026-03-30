import streamlit as st
import google.generativeai as genai
import json
from fpdf import FPDF
import os

# ==============================================================================
# 1. KONFIGURASI HALAMAN & API SECRETS
# ==============================================================================
st.set_page_config(page_title="AI CV Builder Pro", layout="wide")

try:
    API_KEY = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=API_KEY)
except KeyError:
    st.error("API Key belum diatur di Streamlit Secrets!")
    st.stop()

# ==============================================================================
# 2. LOGIKA PDF GENERATOR (BACKEND)
# ==============================================================================
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

# ==============================================================================
# 3. SIDEBAR & KONFIGURASI AI
# ==============================================================================
with st.sidebar:
    st.header("Konfigurasi Sistem")
    model_name = st.selectbox("Pilih Model AI", ["gemini-pro", "gemini-1.5-flash"])
    
    st.markdown("---")
    st.markdown("**Target Lowongan Kerja:**")
    st.info("Bantu AI menyesuaikan gaya bahasa CV Anda dengan posisi yang sedang Anda lamar.")
    target_job_title = st.text_input("Posisi yang Dilamar", value="Data Entry / Admin")
    target_job_desc = st.text_area(
        "Detail Lowongan (Opsional)", 
        value="Dicari admin yang teliti, mahir entry data, dan bisa membalas komplain pelanggan...", 
        height=150
    )

# Inisialisasi Model
model = genai.GenerativeModel(model_name)

def get_ai_response(prompt):
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error AI: {str(e)}"

# ==============================================================================
# 4. ANTARMUKA UTAMA (MAIN UI)
# ==============================================================================
st.title("AI CV Builder Pro")
st.markdown("*Sistem Pembuat CV Otomatis Berbasis AI untuk Memaksimalkan Skor ATS (Applicant Tracking System)*")
st.markdown("---")

st.markdown("### 1. Masukkan Data Mentah Anda")
raw_text_input = st.text_area(
    "Tempelkan (paste) coretan pengalaman kerja, pendidikan, dan kontak Anda di sini:", 
    placeholder="Contoh: Nama saya Budi Santoso. Email budi@email.com. Pernah kerja jadi admin tahun 2022 di PT Maju Mundur, tugas input data dan balesin email...",
    height=150
)

st.markdown("---")
if st.button("Analisis & Bangun CV ATS-Friendly", type="primary", use_container_width=True):
    if not raw_text_input:
        st.warning("Masukkan teks CV Anda terlebih dahulu di kotak atas!")
    else:
        with st.spinner("AI sedang menyusun ulang rekam jejak Anda menjadi CV profesional..."):
            
            # 1. PROMPT EKSTRAKSI JSON
            prompt_ext = f"""
            Ekstrak info dari teks ini ke JSON. WAJIB JSON valid tanpa markdown (```json).
            Struktur: {{"nama": "", "email": "", "pendidikan": [], "pengalaman": [], "keahlian": []}}.
            Teks: {raw_text_input}
            """
            json_result = get_ai_response(prompt_ext)
            
            # Mengambil posisi dan deskripsi dari hasil JSON
            try:
                temp_data = json.loads(json_result.replace('```json', '').replace('```', '').strip())
                posisi_mentah = temp_data['pengalaman'][0].get('posisi', 'Pekerjaan') if temp_data.get('pengalaman') else "Pekerjaan"
                deskripsi_mentah = temp_data['pengalaman'][0].get('deskripsi', '') if temp_data.get('pengalaman') else ""
            except:
                posisi_mentah, deskripsi_mentah = "Pekerjaan", raw_text_input

            # 2. PROMPT ENHANCEMENT (Disesuaikan dengan Sidebar)
            prompt_enh = f"""
            Kamu adalah pakar penulisan CV tingkat dunia. Perbaiki deskripsi kerja ini agar terlihat sangat profesional, 
            gunakan action verbs yang kuat, tambahkan metrik kuantitatif logis, dan buat ATS-friendly.
            
            Konteks Target Pekerjaan: {target_job_title}
            Kriteria Lowongan: {target_job_desc}
            
            Posisi Saat Ini: {posisi_mentah}
            Deskripsi Mentah User: {deskripsi_mentah}
            
            Berikan 3-4 bullet points perbaikan dalam bahasa Indonesia yang baku dan elegan. Hanya tulis bullet points.
            """
            enhanced_result = get_ai_response(prompt_enh)

            # Simpan ke Session State
            st.session_state['json_cv'] = json_result
            st.session_state['enhanced_cv'] = enhanced_result
            st.session_state['processed'] = True

# ==============================================================================
# 5. HASIL & UNDUH PDF
# ==============================================================================
if st.session_state.get('processed'):
    st.success("Dokumen CV berhasil disusun dan dioptimasi!")
    
    st.markdown("### 2. Pratinjau & Hasil Optimasi AI")
    
    col1, col2 = st.columns(2)
    with col1:
        st.info("**Perbaikan Pengalaman (Siap Tembus ATS)**")
        st.markdown(st.session_state['enhanced_cv'])
        
    with col2:
        with st.expander("Lihat Detail Data Mentah (Ekstraksi JSON)"):
            st.code(st.session_state['json_cv'], language='json')
            
    st.markdown("---")
    st.markdown("### 3. Unduh Dokumen CV")
    
    try:
        # Bersihkan JSON dari kemungkinan markdown backticks
        clean_json = st.session_state['json_cv'].replace('```json', '').replace('```', '').strip()
        pdf_bytes = generate_pdf(clean_json, st.session_state['enhanced_cv'])
        
        st.download_button(
            label="Klik Disini untuk Unduh CV (PDF)",
            data=pdf_bytes,
            file_name="CV_ATS_Friendly.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )
    except Exception as e:
        st.error(f"Gagal membuat PDF: {e}")
