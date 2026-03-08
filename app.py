import streamlit as st
import pandas as pd
import numpy as np
import re
import pdfplumber
from io import BytesIO

# ==========================================
# 🎨 ตั้งค่าหน้าตาแอปพลิเคชัน
# ==========================================
st.set_page_config(page_title="SGS Auditor Pro", page_icon="⚡", layout="wide")

st.markdown("""
    <div style='background-color: #f8f9fa; padding: 20px; border-radius: 15px; margin-bottom: 20px;'>
        <h1 style='color: #18181b; margin-bottom: 0px;'>⚡ SGS Auditor Pro (Unlimited Edition)</h1>
        <p style='color: #71717a; font-size: 16px;'>ระบบตรวจสอบเกรด SGS, Toschool และเวลาเรียน (รองรับ PDF, Excel, CSV ไร้ขีดจำกัด)</p>
    </div>
""", unsafe_allow_html=True)

# ==========================================
# 📁 ส่วนอัปโหลดไฟล์ (รองรับ PDF หลายไฟล์แล้ว)
# ==========================================
col1, col2, col3 = st.columns(3)
with col1:
    sgs_files = st.file_uploader("📂 1. ไฟล์ SGS", type=['xlsx', 'csv', 'xls', 'pdf'], accept_multiple_files=True)
with col2:
    to_files = st.file_uploader("📂 2. ไฟล์ Toschool", type=['xlsx', 'csv', 'xls', 'pdf'], accept_multiple_files=True)
with col3:
    time_files = st.file_uploader("📂 3. ไฟล์เวลาเรียน", type=['xlsx', 'csv', 'xls', 'pdf'], accept_multiple_files=True)

# ฟังก์ชันดึงข้อมูลและหาคอลัมน์ชื่อ (รองรับการอ่าน PDF)
def load_and_combine(files, source):
    df_list = []
    for f in files:
        try:
            # 📄 กรณีไฟล์ PDF
            if f.name.lower().endswith('.pdf'):
                all_tables = []
                with pdfplumber.open(f) as pdf:
                    for page in pdf.pages:
                        table = page.extract_table()
                        if table:
                            # ล้างข้อมูลช่องว่างและตัวขึ้นบรรทัดใหม่
                            cleaned_table = [[str(cell).replace('\n', ' ').strip() if cell is not None else "" for cell in row] for row in table]
                            all_tables.extend(cleaned_table)
                
                if all_tables:
                    # เอาแถวแรกสุดมาเป็นหัวตาราง
                    header = all_tables[0]
                    df = pd.DataFrame(all_tables[1:], columns=header)
                    # ลบแถวที่เป็นหัวตารางซ้ำๆ (กรณี PDF มีหลายหน้า)
                    df = df[df[df.columns[0]] != header[0]]
                else:
                    st.warning(f"⚠️ ไม่พบรูปแบบตารางที่อ่านได้ในไฟล์ PDF: {f.name}")
                    continue

            # 📊 กรณีไฟล์ CSV
            elif f.name.lower().endswith('.csv'):
                df = pd.read_csv(f)
            
            # 📊 กรณีไฟล์ Excel
            else:
                df = pd.read_excel(f)
            
            # ค้นหาคอลัมน์ที่น่าจะเป็น "ชื่อ"
            name_col = None
            for col in df.columns:
                if type(col) == str and ('ชื่อ' in col or 'Name' in col or 'name' in col):
                    name_col = col
                    break
            
            if name_col:
                df = df.rename(columns={name_col: 'ชื่อ-นามสกุล'})
                df['ชื่อ-นามสกุล'] = df['ชื่อ-นามสกุล'].astype(str).str.strip().str.replace('  ', ' ')
                df['แหล่งที่มา'] = source
                df_list.append(df)
            else:
                st.warning(f"⚠️ ไม่พบคอลัมน์ 'ชื่อ' ในไฟล์: {f.name}")
                
        except Exception as e:
            st.error(f"อ่านไฟล์ {f.name} ไม่สำเร็จ: {e}")
    
    if df_list:
        return pd.concat(df_list, ignore_index=True)
    return pd.DataFrame()

# ฟังก์ชันทำความสะอาดตัวเลข (ลบทศนิยม .0)
def safe_str(val):
    if pd.isna(val) or val == 'None' or val == '': return ""
    if isinstance(val, float) and val.is_integer(): return str(int(val))
    return str(val).strip()

# ==========================================
# 🚀 ระบบประมวลผล (Pandas Data Science)
# ==========================================
st.markdown("<br>", unsafe_allow_html=True)
if st.button("🚀 เริ่มตรวจสอบข้อมูลทั้งหมด (ประมวลผลทันที)", type="primary", use_container_width=True):
    if not sgs_files or not to_files or not time_files:
        st.error("⚠️ กรุณาอัปโหลดไฟล์ให้ครบทั้ง 3 หมวดก่อนทำการวิเคราะห์ครับ")
    else:
        with st.spinner("⚡ กำลังคำนวณและเปรียบเทียบข้อมูล..."):
            df_sgs = load_and_combine(sgs_files, "SGS")
            df_to = load_and_combine(to_files, "TO")
            df_time = load_and_combine(time_files, "TIME")

            if df_sgs.empty or df_to.empty or df_time.empty:
                st.error("❌ ระบบดึงข้อมูลไม่สำเร็จ กรุณาตรวจสอบว่าไฟล์ที่อัปโหลดมีตารางและคอลัมน์ชื่อครับ")
            else:
                # รวมตารางด้วยชื่อ
                df_merged = pd.merge(df_sgs, df_to, on='ชื่อ-นามสกุล', how='outer', suffixes=('_SGS', '_TO'))
                df_merged = pd.merge(df_merged, df_time, on='ชื่อ-นามสกุล', how='outer')

                results = []
                discrepancies = []

                for idx, row in df_merged.iterrows():
                    name = row.get('ชื่อ-นามสกุล', 'ไม่ทราบชื่อ')
                    if name == 'nan' or name == '': continue
                    issues = []

                    # ฟังก์ชันช่วยหาค่าจากคอลัมน์ (เผื่อชื่อหัวตารางมาไม่ตรงกัน)
                    def get_val(keywords):
                        for col in row.index:
                            for kw in keywords:
                                if kw in str(col):
                                    return safe_str(row[col])
                        return ""

                    # 1. เปรียบเทียบคะแนน
                    sgs_pre = get_val(['ก่อนกลางภาค_SGS', 'ก่อนกลางภาค'])
                    to_pre = get_val(['ก่อนกลางภาค(รวม)_TO', 'ก่อนกลางภาค'])
                    if sgs_pre and to_pre and sgs_pre != to_pre: issues.append(f"ก่อนกลางภาค (SGS={sgs_pre}, TO={to_pre})")

                    sgs_mid = get_val(['กลางภาค_SGS', 'กลางภาค'])
                    to_mid = get_val(['Mid_TO', 'Mid', 'mid'])
                    if sgs_mid and to_mid and sgs_mid != to_mid: issues.append(f"กลางภาค (SGS={sgs_mid}, TO={to_mid})")

                    sgs_post = get_val(['หลังกลางภาค_SGS', 'หลังกลางภาค'])
                    to_post = get_val(['หลังกลางภาค(รวม)_TO', 'หลังกลางภาค'])
                    if sgs_post and to_post and sgs_post != to_post: issues.append(f"หลังกลางภาค (SGS={sgs_post}, TO={to_post})")

                    sgs_final = get_val(['ปลายภาค_SGS', 'ปลายภาค'])
                    to_final = get_val(['Final_TO', 'Final', 'final'])
                    if sgs_final and to_final and sgs_final != to_final: issues.append(f"ปลายภาค (SGS={sgs_final}, TO={to_final})")

                    sgs_total = get_val(['รวม_SGS', 'รวม'])
                    to_total = get_val(['รวมทั้งสิ้น_TO', 'รวมทั้งสิ้น'])
                    if sgs_total and to_total and sgs_total != to_total: issues.append(f"คะแนนรวม (SGS={sgs_total}, TO={to_total})")

                    sgs_grade = get_val(['ผลการเรียน_SGS', 'เกรด_SGS', 'ผลการเรียน'])
                    to_grade = get_val(['ปกติ_TO', 'เกรด_TO', 'ปกติ'])
                    if sgs_grade and to_grade and sgs_grade != to_grade: issues.append(f"เกรด (SGS={sgs_grade}, TO={to_grade})")

                    # 2. ตรวจสอบเวลาเรียน
                    time_str = get_val(['เวลาเรียน', 'Attendance', 'ร้อยละ', '%'])
                    if sgs_grade and time_str:
                        try:
                            numbers = re.findall(r'\d+\.?\d*', time_str)
                            if numbers:
                                time_val = float(numbers[-1]) 
                                if sgs_grade == 'มส' and time_val >= 80:
                                    issues.append(f"เกรด มส. แต่เวลาเรียน {time_val}% (ควร < 80)")
                                elif sgs_grade in ['0','1','1.5','2','2.5','3','3.5','4'] and time_val < 80:
                                    issues.append(f"เกรด {sgs_grade} แต่เวลาเรียน {time_val}% (ควร >= 80)")
                        except:
                            pass

                    # 3. การอ่าน คิดวิเคราะห์ เขียน
                    sgs_read = get_val(['อ่าน_SGS', 'การอ่าน', 'คิดวิเคราะห์'])
                    if sgs_grade in ['0', 'มส', 'ร'] and sgs_read and sgs_read != '1': 
                        issues.append(f"เกรด {sgs_grade} แต่คะแนนอ่านฯ เป็น {sgs_read} (ควรเป็น 1)")
                    elif sgs_grade in ['1','1.5','2','2.5','3','3.5','4'] and sgs_read and sgs_read != '3':
                        issues.append(f"เกรด {sgs_grade} แต่คะแนนอ่านฯ เป็น {sgs_read} (ควรเป็น 3)")

                    # สรุปผล
                    status = "ผิดปกติ ❌" if issues else "ปกติ ✅"
                    details = " | ".join(issues) if issues else "-"

                    if issues:
                        discrepancies.append({"ชื่อ-นามสกุล": name, "ปัญหาที่พบ": details})

                    results.append({
                        "ชื่อ-นามสกุล": name,
                        "SGS(ก่อนกลาง)": sgs_pre, "TO(ก่อนกลาง)": to_pre,
                        "SGS(กลางภาค)": sgs_mid, "TO(Mid)": to_mid,
                        "SGS(หลังกลาง)": sgs_post, "TO(หลังกลาง)": to_post,
                        "SGS(ปลายภาค)": sgs_final, "TO(Final)": to_final,
                        "SGS(รวม)": sgs_total, "TO(รวมทั้งสิ้น)": to_total,
                        "SGS(เกรด)": sgs_grade, "TO(เกรด)": to_grade,
                        "เวลาเรียน": time_str,
                        "SGS(อ่านฯ)": sgs_read,
                        "สถานะ": status,
                        "รายละเอียดข้อผิดพลาด": details
                    })

                df_results = pd.DataFrame(results)
                df_disc = pd.DataFrame(discrepancies)

                if not df_disc.empty:
                    st.error(f"🚨 พบนักเรียนที่มีข้อมูลไม่สอดคล้องกัน {len(df_disc)} คน")
                    st.dataframe(df_disc, use_container_width=True)
                else:
                    st.success("✅ ข้อมูลสอดคล้องกัน 100% ไม่พบข้อผิดพลาดตามเงื่อนไข!")

                st.markdown("### 📋 ตารางตรวจสอบข้อมูลนักเรียนทั้งหมด")
                st.dataframe(df_results, use_container_width=True)

                # สร้าง Excel
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_results.to_excel(writer, sheet_name='ข้อมูลทั้งหมด', index=False)
                    if not df_disc.empty:
                        df_disc.to_excel(writer, sheet_name='รายชื่อที่พบข้อผิดพลาด', index=False)
                
                st.download_button(
                    label="📥 ดาวน์โหลดผลลัพธ์ (Excel)",
                    data=output.getvalue(),
                    file_name="SGS_Auditor_Unlimited.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary"
                )
