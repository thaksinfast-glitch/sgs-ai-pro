import streamlit as st
import google.generativeai as genai
import tempfile
import os
import json
import pandas as pd
from io import BytesIO

# ==========================================
# 🔑 เชื่อมต่อ API Key จากตู้เซฟ Streamlit Secrets
# ==========================================
API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=API_KEY)

# ==========================================
# 🎨 ตั้งค่าหน้าตาแอปพลิเคชัน
# ==========================================
st.set_page_config(page_title="SGS Auditor AI", page_icon="🤖", layout="wide")

st.markdown("""
    <div style='background-color: #f8f9fa; padding: 20px; border-radius: 15px; margin-bottom: 20px;'>
        <h1 style='color: #18181b; margin-bottom: 0px;'>🤖 SGS Auditor AI</h1>
        <p style='color: #71717a; font-size: 16px;'>ระบบตรวจสอบความสอดคล้องข้อมูล SGS, Toschool และเวลาเรียน ด้วย Gemini 2.0 Flash ⚡</p>
    </div>
""", unsafe_allow_html=True)

# ==========================================
# 📁 ส่วนอัปโหลดไฟล์ (รองรับหลายไฟล์)
# ==========================================
col1, col2, col3 = st.columns(3)
with col1:
    sgs_files = st.file_uploader("📂 1. ไฟล์ SGS", type=['pdf', 'xlsx', 'csv'], accept_multiple_files=True)
with col2:
    to_files = st.file_uploader("📂 2. ไฟล์ Toschool", type=['pdf', 'xlsx', 'csv'], accept_multiple_files=True)
with col3:
    time_files = st.file_uploader("📂 3. ไฟล์เวลาเรียน", type=['pdf', 'xlsx', 'csv'], accept_multiple_files=True)

def upload_to_gemini(files, prefix):
    uploaded_g_files = []
    for f in files:
        ext = f.name.split('.')[-1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
            tmp.write(f.getvalue())
            tmp_path = tmp.name
        g_file = genai.upload_file(path=tmp_path, display_name=f"{prefix}_{f.name}")
        uploaded_g_files.append(g_file)
        os.remove(tmp_path)
    return uploaded_g_files

# ==========================================
# 🚀 ระบบประมวลผล
# ==========================================
st.markdown("<br>", unsafe_allow_html=True)
col_btn, _ = st.columns([1, 2])
with col_btn:
    start_btn = st.button("🚀 เริ่มวิเคราะห์เชิงลึกด้วย Gemini 2.0 Flash", type="primary", use_container_width=True)

if start_btn:
    if not sgs_files or not to_files or not time_files:
        st.error("⚠️ กรุณาอัปโหลดไฟล์ให้ครบทั้ง 3 ช่องก่อนทำการวิเคราะห์ครับ")
    else:
        with st.spinner("⚡ กำลังให้สมองกล Flash อ่านไฟล์และเปรียบเทียบข้อมูลอย่างรวดเร็ว..."):
            try:
                g_sgs = upload_to_gemini(sgs_files, "SGS")
                g_to = upload_to_gemini(to_files, "TO")
                g_time = upload_to_gemini(time_files, "TIME")
                
                all_files = g_sgs + g_to + g_time

                prompt = """
                บทบาท: คุณคือ AI Auditor ระดับสูง ที่มีความแม่นยำด้านตัวเลข 100%
                ภารกิจ: เปรียบเทียบไฟล์ 3 ไฟล์ (SGS, Toschool, เวลาเรียน) เพื่อหาจุดที่ไม่สอดคล้องกัน

                กฎการตรวจสอบ:
                1. เปรียบเทียบคะแนน (ต้องตรงกันทุกจุด): SGS(ก่อนกลางภาค) vs Toschool(ก่อนกลาง), SGS(หลังกลาง) vs Toschool(หลังกลาง), SGS(กลางภาค) vs Toschool(Mid), SGS(ปลายภาค) vs Toschool(Final), SGS(รวม) vs Toschool(รวม), SGS(ผลการเรียน) vs Toschool(ปกติ)
                2. เวลาเรียน: ใช้ข้อมูลจาก "ไฟล์เวลาเรียน" เท่านั้น (ห้ามเอาเวลาเรียนใน SGS มาปน)
                   - ถ้า SGS(ผลการเรียน) = 'มส' -> เวลาเรียนต้อง < 80.00
                   - ถ้า SGS(ผลการเรียน) = 0-4 -> เวลาเรียนต้อง >= 80.00
                3. การอ่าน คิดวิเคราะห์ เขียน:
                   - ถ้าเกรด = {0, มส, ร} -> คะแนนอ่านฯ ต้องเป็น 1 
                   - ถ้าเกรด = {1-4} -> คะแนนอ่านฯ ต้องเป็น 3

                คำสั่งสำคัญ: โปรดตอบกลับเป็นข้อมูลรูปแบบ JSON เท่านั้น โดยใช้โครงสร้างนี้เป๊ะๆ ห้ามมีข้อความอื่นปน:
                {
                  "discrepancies": [{"name": "ชื่อ", "issue": "ปัญหาที่พบ", "details": "รายละเอียด"}],
                  "allStudents": [{"name": "ชื่อ", "sgsPreMid": "x", "toPreMid": "y", "sgsPostMid": "x", "toPostMid": "y", "sgsMid": "x", "toMid": "y", "sgsFinal": "x", "toFinal": "y", "sgsTotal": "x", "toTotal": "y", "sgsGrade": "x", "toGrade": "y", "attendance": "x", "sgsReading": "x", "toReading": "y", "status": "ปกติ/ผิดปกติ", "details": "ข้อสังเกต"}]
                }
                """

                # เปลี่ยนมาใช้รุ่น Flash ที่นี่ครับ
                model = genai.GenerativeModel("gemini-2.0-flash")
                response = model.generate_content(
                    all_files + [prompt],
                    generation_config=genai.GenerationConfig(
                        response_mime_type="application/json",
                        max_output_tokens=8192
                    )
                )

                data = json.loads(response.text)
                
                if data.get("discrepancies"):
                    st.error(f"🚨 พบข้อผิดพลาด {len(data['discrepancies'])} รายการ")
                    df_disc = pd.DataFrame(data["discrepancies"])
                    st.dataframe(df_disc, use_container_width=True)
                else:
                    st.success("✅ ข้อมูลทุกไฟล์สอดคล้องกัน 100% ไม่พบข้อผิดพลาด!")
                    df_disc = pd.DataFrame() 

                st.markdown("### 📋 ตารางเปรียบเทียบข้อมูลนักเรียนทั้งหมด")
                df_all = pd.DataFrame(data.get("allStudents", []))
                st.dataframe(df_all, use_container_width=True)

                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_all.to_excel(writer, sheet_name='นักเรียนทั้งหมด', index=False)
                    if not df_disc.empty:
                        df_disc.to_excel(writer, sheet_name='รายชื่อที่พบข้อผิดพลาด', index=False)
                excel_data = output.getvalue()
                
                st.download_button(
                    label="📥 ดาวน์โหลดผลลัพธ์ (Excel)",
                    data=excel_data,
                    file_name="AI_Teacher_Audit_Flash.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary"
                )

            except Exception as e:
                st.error(f"เกิดข้อผิดพลาดในการวิเคราะห์: {str(e)}")
