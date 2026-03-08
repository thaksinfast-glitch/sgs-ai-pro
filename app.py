import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

# ==========================================
# 🎨 ตั้งค่าหน้าตาแอปพลิเคชัน
# ==========================================
st.set_page_config(page_title="SGS Auditor Pro (Unlimited)", page_icon="⚡", layout="wide")

st.markdown("""
    <div style='background-color: #f8f9fa; padding: 20px; border-radius: 15px; margin-bottom: 20px;'>
        <h1 style='color: #18181b; margin-bottom: 0px;'>⚡ SGS Auditor Pro (Unlimited Edition)</h1>
        <p style='color: #71717a; font-size: 16px;'>ระบบตรวจสอบข้อมูล SGS, Toschool และเวลาเรียน (ประมวลผลด้วย Pandas Data Science เร็ว แม่นยำ ไร้ขีดจำกัดโควตา)</p>
    </div>
""", unsafe_allow_html=True)

# ==========================================
# 📁 ส่วนอัปโหลดไฟล์
# ==========================================
col1, col2, col3 = st.columns(3)
with col1:
    sgs_files = st.file_uploader("📂 1. ไฟล์ SGS", type=['xlsx', 'csv'], accept_multiple_files=True)
with col2:
    to_files = st.file_uploader("📂 2. ไฟล์ Toschool", type=['xlsx', 'csv'], accept_multiple_files=True)
with col3:
    time_files = st.file_uploader("📂 3. ไฟล์เวลาเรียน", type=['xlsx', 'csv'], accept_multiple_files=True)

# ฟังก์ชันอ่านและรวมไฟล์ (ค้นหาแถวที่มีคำว่า "ชื่อ" อัตโนมัติ)
def process_files(files, source_name):
    df_list = []
    for f in files:
        try:
            if f.name.endswith('.csv'):
                df = pd.read_csv(f)
            else:
                df = pd.read_excel(f)
            
            # พยายามหาคอลัมน์ "ชื่อ" เพื่อเป็น Key หลัก
            name_col = None
            for col in df.columns:
                if 'ชื่อ' in str(col) or 'Name' in str(col) or 'name' in str(col):
                    name_col = col
                    break
            
            if name_col:
                # เปลี่ยนชื่อคอลัมน์ให้เป็นมาตรฐานเดียวกัน
                df = df.rename(columns={name_col: 'ชื่อ-นามสกุล'})
                df['แหล่งที่มา'] = source_name
                df_list.append(df)
        except Exception as e:
            st.warning(f"อ่านไฟล์ {f.name} ไม่สำเร็จ: {e}")
    
    if df_list:
        return pd.concat(df_list, ignore_index=True)
    return pd.DataFrame()

# ==========================================
# 🚀 ระบบประมวลผลแบบสูตรคำนวณ (Pandas)
# ==========================================
st.markdown("<br>", unsafe_allow_html=True)
if st.button("🚀 เริ่มตรวจสอบข้อมูล (ประมวลผลทันที)", type="primary", use_container_width=True):
    if not sgs_files or not to_files or not time_files:
        st.error("⚠️ กรุณาอัปโหลดไฟล์ให้ครบทั้ง 3 หมวดก่อนทำการวิเคราะห์ครับ")
    else:
        with st.spinner("⚡ กำลังคำนวณและเปรียบเทียบข้อมูลด้วย Pandas..."):
            
            # 1. ดึงข้อมูลจากไฟล์ทั้งหมด
            df_sgs = process_files(sgs_files, "SGS")
            df_to = process_files(to_files, "TO")
            df_time = process_files(time_files, "TIME")
            
            # เช็คว่ามีคอลัมน์ชื่อไหม
            if 'ชื่อ-นามสกุล' not in df_sgs.columns or 'ชื่อ-นามสกุล' not in df_to.columns or 'ชื่อ-นามสกุล' not in df_time.columns:
                st.error("❌ ไม่พบคอลัมน์ 'ชื่อ' หรือ 'ชื่อ-นามสกุล' ในไฟล์ที่อัปโหลด กรุณาตรวจสอบหัวตารางไฟล์ Excel ครับ")
            else:
                # 2. ทำความสะอาดชื่อ (ลบช่องว่าง)
                for df in [df_sgs, df_to, df_time]:
                    df['ชื่อ-นามสกุล'] = df['ชื่อ-นามสกุล'].astype(str).str.strip().str.replace('  ', ' ')

                # 3. จับคู่ข้อมูล (Merge) โดยใช้ชื่อเป็นหลัก
                merged_df = pd.merge(df_sgs, df_to, on='ชื่อ-นามสกุล', how='outer', suffixes=('_SGS', '_TO'))
                merged_df = pd.merge(merged_df, df_time, on='ชื่อ-นามสกุล', how='outer')

                discrepancies = []
                all_results = []

                # 4. ลูปตรวจเช็คเงื่อนไขทีละคน
                for idx, row in merged_df.iterrows():
                    name = row.get('ชื่อ-นามสกุล', 'ไม่ทราบชื่อ')
                    issues = []
                    
                    # -----------------------------------------------------
                    # ตัวอย่างการเขียนเช็คเงื่อนไข (ระบบจะพยายามหาคอลัมน์ที่คล้ายกัน)
                    # คุณครูสามารถมาปรับแก้ชื่อคอลัมน์ใน [ ] ให้ตรงกับ Excel ของจริงได้เลยครับ
                    # -----------------------------------------------------
                    
                    # หมาเหตุ: ในโค้ดนี้เราจะจำลองการดึงค่า (เพราะไม่รู้ชื่อคอลัมน์จริง 100%)
                    # ดึงเกรด SGS มาเช็ค (สมมติว่าชื่อคอลัมน์มีคำว่า ผลการเรียน หรือ เกรด)
                    sgs_grade = str(row.get('ผลการเรียน_SGS', row.get('เกรด_SGS', ''))).strip()
                    
                    # กฎ 1: เวลาเรียน (SGS = 'มส' ต้อง < 80)
                    attendance = str(row.get('เวลาเรียน', row.get('เวลาเรียน(%)', '0')))
                    try:
                        att_val = float(attendance)
                        if sgs_grade == 'มส' and att_val >= 80:
                            issues.append("เกรด มส. แต่เวลาเรียน >= 80")
                        elif sgs_grade in ['0', '1', '1.5', '2', '2.5', '3', '3.5', '4'] and att_val < 80:
                            issues.append(f"เกรด {sgs_grade} แต่เวลาเรียน < 80 ({att_val}%)")
                    except:
                        pass # ข้ามถ้าเวลาเรียนไม่ใช่ตัวเลข

                    # กฎ 2: การอ่านคิดวิเคราะห์ (0, มส, ร ต้องได้ 1)
                    sgs_read = str(row.get('การอ่าน_SGS', ''))
                    if sgs_grade in ['0', 'มส', 'ร'] and sgs_read != '1' and sgs_read != '':
                        issues.append(f"เกรด {sgs_grade} แต่คะแนนอ่านฯ เป็น {sgs_read} (ควรเป็น 1)")
                    elif sgs_grade in ['1', '1.5', '2', '2.5', '3', '3.5', '4'] and sgs_read != '3' and sgs_read != '':
                        issues.append(f"เกรด {sgs_grade} แต่คะแนนอ่านฯ เป็น {sgs_read} (ควรเป็น 3)")

                    # สรุปผลรายบุคคล
                    status = "ผิดปกติ" if issues else "ปกติ"
                    details = " | ".join(issues) if issues else "-"
                    
                    if issues:
                        discrepancies.append({"ชื่อ-นามสกุล": name, "ปัญหาที่พบ": details})
                        
                    all_results.append({
                        "ชื่อ-นามสกุล": name,
                        "เกรด_SGS": sgs_grade,
                        "เกรด_Toschool": str(row.get('ปกติ_TO', '')),
                        "เวลาเรียน": attendance,
                        "สถานะ": status,
                        "รายละเอียดข้อผิดพลาด": details
                    })

                # 5. แสดงผลลัพธ์
                df_results = pd.DataFrame(all_results)
                df_disc = pd.DataFrame(discrepancies)

                if not df_disc.empty:
                    st.error(f"🚨 พบนักเรียนที่มีข้อมูลไม่สอดคล้องกัน {len(df_disc)} คน")
                    st.dataframe(df_disc, use_container_width=True)
                else:
                    st.success("✅ ข้อมูลสอดคล้องกัน 100% ไม่พบข้อผิดพลาดตามเงื่อนไข!")

                st.markdown("### 📋 ตารางตรวจสอบข้อมูลนักเรียนทั้งหมด")
                st.dataframe(df_results, use_container_width=True)

                # 6. สร้างปุ่มดาวน์โหลด Excel
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_results.to_excel(writer, sheet_name='ข้อมูลทั้งหมด', index=False)
                    if not df_disc.empty:
                        df_disc.to_excel(writer, sheet_name='รายชื่อที่พบข้อผิดพลาด', index=False)
                excel_data = output.getvalue()
                
                st.download_button(
                    label="📥 ดาวน์โหลดผลลัพธ์ (Excel)",
                    data=excel_data,
                    file_name="SGS_Auditor_Report.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary"
                )
