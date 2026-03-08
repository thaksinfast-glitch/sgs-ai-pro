import streamlit as st
import pandas as pd
import pdfplumber
import json
from openai import OpenAI
from io import BytesIO

# ==========================================
# 🔑 เชื่อมต่อ API ของ DeepSeek (ฝังกุญแจไว้ให้แล้วครับ)
# ==========================================
API_KEY = "sk-40631a851f774914a88c1c83cf3897d7"
client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")

# ==========================================
# 🎨 ตั้งค่าหน้าตาแอปพลิเคชัน
# ==========================================
st.set_page_config(page_title="SGS Auditor AI", page_icon="🐳", layout="wide")

st.markdown("""
    <div style='background-color: #f8f9fa; padding: 20px; border-radius: 15px; margin-bottom: 20px;'>
        <h1 style='color: #18181b; margin-bottom: 0px;'>🐳 SGS Auditor AI (Powered by DeepSeek)</h1>
        <p style='color: #71717a; font-size: 16px;'>ระบบตรวจสอบเกรดและเวลาเรียน ขับเคลื่อนด้วยสมองกล DeepSeek-V3 เก่งตรรกะ แม่นยำ และอ่าน PDF ได้</p>
    </div>
""", unsafe_allow_html=True)

# ==========================================
# 📁 ส่วนอัปโหลดไฟล์
# ==========================================
col1, col2, col3 = st.columns(3)
with col1:
    sgs_files = st.file_uploader("📂 1. ไฟล์ SGS", type=['pdf', 'xlsx', 'csv', 'xls'], accept_multiple_files=True)
with col2:
    to_files = st.file_uploader("📂 2. ไฟล์ Toschool", type=['pdf', 'xlsx', 'csv', 'xls'], accept_multiple_files=True)
with col3:
    time_files = st.file_uploader("📂 3. ไฟล์เวลาเรียน", type=['pdf', 'xlsx', 'csv', 'xls'], accept_multiple_files=True)

# ฟังก์ชันดึงข้อความจากไฟล์ต่างๆ เพื่อเตรียมส่งให้ AI
def extract_text_from_files(files, prefix):
    combined_text = f"\n--- เริ่มข้อมูล {prefix} ---\n"
    for f in files:
        ext = f.name.split('.')[-1].lower()
        try:
            if ext == 'pdf':
                with pdfplumber.open(f) as pdf:
                    for page in pdf.pages:
                        text = page.extract_text()
                        if text: combined_text += text + "\n"
            elif ext == 'csv':
                df = pd.read_csv(f)
                combined_text += df.to_csv(index=False) + "\n"
            else:
                df = pd.read_excel(f)
                combined_text += df.to_csv(index=False) + "\n"
        except Exception as e:
            st.warning(f"ดึงข้อมูลไฟล์ {f.name} ไม่สำเร็จ: {e}")
    combined_text += f"--- จบข้อมูล {prefix} ---\n"
    return combined_text

# ==========================================
# 🚀 ระบบประมวลผลด้วย DeepSeek
# ==========================================
st.markdown("<br>", unsafe_allow_html=True)
if st.button("🚀 เริ่มวิเคราะห์ด้วย DeepSeek AI", type="primary", use_container_width=True):
    if not sgs_files or not to_files or not time_files:
        st.error("⚠️ กรุณาอัปโหลดไฟล์ให้ครบทั้ง 3 หมวดก่อนทำการวิเคราะห์ครับ")
    else:
        with st.spinner("🐳 กำลังให้สมองกล DeepSeek อ่านไฟล์และจับผิดข้อมูล (อาจใช้เวลา 1-2 นาที)..."):
            try:
                # 1. แปลงไฟล์ทั้งหมดเป็นข้อความ
                sgs_text = extract_text_from_files(sgs_files, "SGS")
                to_text = extract_text_from_files(to_files, "Toschool")
                time_text = extract_text_from_files(time_files, "เวลาเรียน")

                # 2. เตรียม Prompt สั่งงาน
                prompt = f"""
                บทบาท: คุณคือ AI Auditor ระดับสูง ที่มีความแม่นยำด้านตัวเลข 100%
                ภารกิจ: เปรียบเทียบข้อมูล 3 แหล่ง (SGS, Toschool, เวลาเรียน) เพื่อหาจุดที่ไม่สอดคล้องกันของนักเรียนแต่ละคน

                ข้อมูลที่สกัดมา:
                {sgs_text}
                {to_text}
                {time_text}

                กฎการตรวจสอบ:
                1. เปรียบเทียบคะแนน (ต้องตรงกันทุกจุด): SGS(ก่อนกลาง) vs Toschool(ก่อนกลาง), SGS(หลังกลาง) vs Toschool(หลังกลาง), SGS(กลางภาค) vs Toschool(Mid), SGS(ปลายภาค) vs Toschool(Final), SGS(รวม) vs Toschool(รวม), SGS(เกรด) vs Toschool(เกรด)
                2. เวลาเรียน:
                   - ถ้า SGS(เกรด) = 'มส' -> เวลาเรียนต้อง < 80.00
                   - ถ้า SGS(เกรด) เป็นตัวเลข 0-4 -> เวลาเรียนต้อง >= 80.00
                3. การอ่าน คิดวิเคราะห์ เขียน:
                   - ถ้าเกรด = 0, มส, ร -> คะแนนอ่านฯ ต้องเป็น 1 
                   - ถ้าเกรด = 1 ถึง 4 -> คะแนนอ่านฯ ต้องเป็น 3

                คำสั่งสำคัญ: โปรดตอบกลับเป็นข้อมูลรูปแบบ JSON เท่านั้น โดยใช้โครงสร้างนี้ ห้ามมีข้อความอื่นปนเด็ดขาด:
                {{
                  "discrepancies": [{{"name": "ชื่อ-สกุล", "issue": "ปัญหาที่พบ", "details": "รายละเอียด"}}],
                  "allStudents": [{{"name": "ชื่อ-สกุล", "sgsPreMid": "x", "toPreMid": "y", "sgsPostMid": "x", "toPostMid": "y", "sgsMid": "x", "toMid": "y", "sgsFinal": "x", "toFinal": "y", "sgsTotal": "x", "toTotal": "y", "sgsGrade": "x", "toGrade": "y", "attendance": "x", "sgsReading": "x", "status": "ปกติ/ผิดปกติ", "details": "ข้อสังเกต"}}]
                }}
                """

                # 3. เรียกใช้งาน DeepSeek API
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": "You are a data formatting assistant. You must output valid JSON only. Do not wrap it in ```json blocks."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )

                # 4. แปลงผลลัพธ์ JSON มาแสดงเป็นตาราง
                raw_json = response.choices[0].message.content.strip()
                data = json.loads(raw_json)
                
                df_disc = pd.DataFrame(data.get("discrepancies", []))
                if not df_disc.empty:
                    st.error(f"🚨 พบข้อผิดพลาด {len(df_disc)} รายการ")
                    st.dataframe(df_disc, use_container_width=True)
                else:
                    st.success("✅ ข้อมูลทุกไฟล์สอดคล้องกัน 100% ไม่พบข้อผิดพลาด!")

                st.markdown("### 📋 ตารางเปรียบเทียบข้อมูลนักเรียนทั้งหมด")
                df_all = pd.DataFrame(data.get("allStudents", []))
                st.dataframe(df_all, use_container_width=True)

                # 5. สร้างไฟล์ Excel
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_all.to_excel(writer, sheet_name='นักเรียนทั้งหมด', index=False)
                    if not df_disc.empty:
                        df_disc.to_excel(writer, sheet_name='รายชื่อที่พบข้อผิดพลาด', index=False)
                
                st.download_button(
                    label="📥 ดาวน์โหลดผลลัพธ์ (Excel)",
                    data=output.getvalue(),
                    file_name="DeepSeek_Auditor_Report.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary"
                )

            except Exception as e:
                st.error(f"เกิดข้อผิดพลาดในการวิเคราะห์: {str(e)}")
