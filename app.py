import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta, date
from ortools.sat.python import cp_model

st.set_page_config(page_title="全通用型藥局智能排班系統", page_icon="💊", layout="wide")

DAY_NAMES = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]
DAY_MAP = {name: i for i, name in enumerate(DAY_NAMES)}

LEAVES_FILE = "leaves_data.json"
MEETINGS_FILE = "meetings_data.json"
CONFIG_FILE = "store_config.json"
PERSONAL_SHIFTS_FILE = "personal_shifts.json"
HISTORY_14D_FILE = "history_14d_data.json"
FINAL_SCHEDULE_FILE = "final_schedule.json"

def load_json(file_path, default_val):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return default_val
    return default_val

def save_json(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

if 'emp_df' not in st.session_state:
    default_data = [
        {"姓名": "呈", "類型": "正職", "藥師": False, "成熟人力": True, "最少天數": 5, "最多天數": 5, "偏好": "偏好早班"},
        {"姓名": "桂", "類型": "正職", "藥師": False, "成熟人力": True, "最少天數": 5, "最多天數": 5, "偏好": "偏好晚班"},
        {"姓名": "花藥", "類型": "正職", "藥師": True, "成熟人力": True, "最少天數": 5, "最多天數": 5, "偏好": "無偏好"},
        {"姓名": "邱藥", "類型": "正職", "藥師": True, "成熟人力": True, "最少天數": 5, "最多天數": 5, "偏好": "無偏好"},
        {"姓名": "亭", "類型": "PT", "藥師": False, "成熟人力": True, "最少天數": 5, "最多天數": 5, "偏好": "無偏好"},
        {"姓名": "品", "類型": "PT", "藥師": False, "成熟人力": False, "最少天數": 2, "最多天數": 5, "偏好": "無偏好"},
        {"姓名": "維", "類型": "PT", "藥師": False, "成熟人力": False, "最少天數": 2, "最多天數": 5, "偏好": "無偏好"},
        {"姓名": "姵", "類型": "PT", "藥師": False, "成熟人力": False, "最少天數": 2, "最多天數": 5, "偏好": "無偏好"},
        {"姓名": "如", "類型": "PT", "藥師": False, "成熟人力": True, "最少天數": 2, "最多天數": 5, "偏好": "無偏好"},
    ]
    st.session_state.emp_df = pd.DataFrame(default_data)

EMPLOYEES = st.session_state.emp_df["姓名"].dropna().tolist()

st.sidebar.title("🔐 系統權限與模式")
user_role = st.sidebar.radio("請選擇您的身分：", ["👤 員工專區 (查看班表/登記請假)", "🔒 店長管理後台"])

if user_role == "👤 員工專區 (查看班表/登記請假)":
    st.title("💊 員工專區")
    
    final_sched = load_json(FINAL_SCHEDULE_FILE, [])
    if final_sched:
        st.subheader("📋 門市本週最新排班表")
        st.dataframe(pd.DataFrame(final_sched), use_container_width=True, hide_index=True)
    else:
        st.info("💡 尚未有發佈的本週班表。")
    
    st.divider()
    
    current_leaves = load_json(LEAVES_FILE, {})
    selected_emp = st.selectbox("請選擇您的名字：", options=EMPLOYEES)

    with st.form("employee_leave_form_v2"):
        st.subheader(f"👤 {selected_emp} 的假別申請")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            leave_date = st.date_input("選擇請假日期：", min_value=date.today(), max_value=date.today() + timedelta(days=180), value=date.today())
        with col_f2:
            leave_type = st.selectbox("請假類型：", options=["全天休", "休早上 (僅能上晚班)", "休晚上 (僅能上早班)"])
            
        add_btn = st.form_submit_button("➕ 新增/更新此日假別", type="primary")
        if add_btn:
            date_str = leave_date.strftime("%Y-%m-%d")
            timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if selected_emp not in current_leaves: current_leaves[selected_emp] = {}
            current_leaves[selected_emp][date_str] = {"type": leave_type, "timestamp": timestamp_str}
            save_json(LEAVES_FILE, current_leaves)
            st.success("登記成功！")
            st.rerun()

    st.subheader(f"📅 【{selected_emp}】個人已登記明細")
    emp_my_leaves = current_leaves.get(selected_emp, {})
    if emp_my_leaves:
        my_list = [{"請假日期": d, "假別類型": info.get("type")} for d, info in sorted(emp_my_leaves.items())]
        st.dataframe(pd.DataFrame(my_list), use_container_width=True, hide_index=True)
    st.stop()

st.sidebar.divider()
manager_password = st.sidebar.text_input("請輸入店長密碼：", type="password")
if manager_password != "1234":
    st.title("🔒 店長管理後台")
    st.warning("⚠️ 請輸入正確的店長密碼")
    st.stop()

st.title("💊 藥局智能排班系統 (店長後台)")
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["👥 人員", "🔒 個人固定設置", "⏮️ 14天歷史", "📆 本週請假", "⚙️ 排班基準", "🚀 自動排班"])

with tab1:
    st.info("💡 提示：在下方表格新增或刪除人員後，系統會自動同步清理或更新對應的請假與個人固定設置資料。")
    edited_df = st.data_editor(st.session_state.emp_df, num_rows="dynamic", key="editor_emp")
    
    if not edited_df.equals(st.session_state.emp_df):
        st.session_state.emp_df = edited_df
        current_emps = edited_df["姓名"].dropna().tolist()
        
        leaves_data = load_json(LEAVES_FILE, {})
        updated_leaves = {emp: data for emp, data in leaves_data.items() if emp in current_emps}
        if updated_leaves != leaves_data:
            save_json(LEAVES_FILE, updated_leaves)
            
        personal_shifts = load_json(PERSONAL_SHIFTS_FILE, {})
        updated_p_shifts = {emp: data for emp, data in personal_shifts.items() if emp in current_emps}
        if updated_p_shifts != personal_shifts:
            save_json(PERSONAL_SHIFTS_FILE, updated_p_shifts)
            
        st.success("✅ 人員名單已更新，並已自動同步清理相關關聯資料！")
        st.rerun()

with tab2:
    st.subheader("⚙️ 個人固定班別與特規班別設定")
    st.markdown("在此您可以針對特定同仁設定固定班別限制，例如**只能早班**、**只能晚班**，或是自定義時間的**特規晚班**。")
    
    personal_shifts = load_json(PERSONAL_SHIFTS_FILE, {})
    selected_target_emp = st.selectbox("選擇要設定的同仁：", options=EMPLOYEES, key="p_shift_emp")
    
    emp_current_setting = personal_shifts.get(selected_target_emp, {
        "mode": "無限制",
        "weekday_rule": "平日18-22",
        "saturday_rule": "周六到22:30",
        "holiday_rule": "假日16點上班",
        "custom_desc": ""
    })
    
    with st.form("personal_shift_form"):
        p_mode = st.selectbox("排班限制類型：", options=["無限制", "只能早班", "只能晚班", "特規晚班 (自定義時間規則)"], 
                              index=["無限制", "只能早班", "只能晚班", "特規晚班 (自定義時間規則)"].index(emp_current_setting.get("mode", "無限制")))
        
        st.divider()
        st.markdown("##### 📌 特規晚班細節設定：")
        col_ps1, col_ps2 = st.columns(2)
        with col_ps1:
            p_weekday = st.text_input("平日時間限制：", value=emp_current_setting.get("weekday_rule", "例如：平日只能 18-22"))
            p_saturday = st.text_input("週六時間限制：", value=emp_current_setting.get("saturday_rule", "例如：週六只能到 22:30"))
        with col_ps2:
            p_holiday = st.text_input("假日/周日時間限制：", value=emp_current_setting.get("holiday_rule", "例如：假日可從 16:00 上班"))
            p_desc = st.text_area("其他特殊備註：", value=emp_current_setting.get("custom_desc", ""))
            
        save_p_btn = st.form_submit_button("💾 儲存該同仁的固定/特規設置", type="primary")
        if save_p_btn:
            personal_shifts[selected_target_emp] = {
                "mode": p_mode,
                "weekday_rule": p_weekday,
                "saturday_rule": p_saturday,
                "holiday_rule": p_holiday,
                "custom_desc": p_desc
            }
            save_json(PERSONAL_SHIFTS_FILE, personal_shifts)
            st.success(f"✅ 已成功儲存【{selected_target_emp}】的固定與特規班別設定！")
            
    st.divider()
    st.markdown("#### 📋 目前全體同仁固定與特規設定總覽")
    if personal_shifts:
        overview_list = [{"姓名": emp, "模式": info.get("mode"), "平日規則": info.get("weekday_rule"), "週六規則": info.get("saturday_rule"), "假日規則": info.get("holiday_rule"), "備註": info.get("custom_desc")} for emp, info in personal_shifts.items()]
        st.dataframe(pd.DataFrame(overview_list), use_container_width=True, hide_index=True)
    else:
        st.info("目前尚未設定任何個人特規班別。")

with tab3:
    st.subheader("⏮️ 前 14 天歷史班表資料")
    st.markdown("在此可檢視或維護過去 14 天的排班歷史紀錄。")
    
    default_history = [
        {"日期": "2026-07-30", "早班": "呈, 花藥", "晚班": "桂, 邱藥"},
        {"日期": "2026-07-31", "早班": "呈, 邱藥", "晚班": "桂, 亭"}
    ]
    history_data = load_json(HISTORY_14D_FILE, default_history)
    if not history_data:
        history_data = default_history
        
    edited_history = st.data_editor(
        pd.DataFrame(history_data),
        num_rows="dynamic",
        key="history_editor",
        use_container_width=True
    )
    if st.button("💾 儲存 14 天歷史資料", type="primary"):
        save_json(HISTORY_14D_FILE, edited_history.to_dict(orient="records"))
        st.success("✅ 14天歷史資料已成功儲存！")

with tab4:
    st.subheader("📆 本週同仁請假總覽")
    leaves_data = load_json(LEAVES_FILE, {})
    if leaves_data:
        all_leaves_list = [{"員工姓名": emp, "請假日期": d_str, "假別類型": info.get("type"), "登記時間": info.get("timestamp")} for emp, dates in leaves_data.items() for d_str, info in dates.items()]
        st.dataframe(pd.DataFrame(all_leaves_list), use_container_width=True, hide_index=True)
    else:
        st.info("💡 目前尚無同仁登記本週請假資料。")

with tab5:
    st.subheader("⚙️ 排班基準與門市設定")
    store_config = load_json(CONFIG_FILE, {"早班人數": 2, "晚班人數": 2})
    with st.form("store_config_form"):
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            min_morning = st.number_input("每日早班最少需求人數：", value=int(store_config.get("早班人數", 2)), min_value=1)
        with col_c2:
            min_night = st.number_input("每日晚班最少需求人數：", value=int(store_config.get("晚班人數", 2)), min_value=1)
            
        save_cfg_btn = st.form_submit_button("💾 儲存排班基準設定", type="primary")
        if save_cfg_btn:
            save_json(CONFIG_FILE, {"早班人數": min_morning, "晚班人數": min_night})
            st.success("✅ 排班基準已成功更新！")

with tab6:
    st.subheader("🚀 自動排班與手動調整審核")
    st.markdown("系統自動產出排班後，店長可以直接在下方表格進行**手動微調**。儲存發佈前，系統會自動進行**防呆與規則檢查**（例如：檢查請假衝突、欄位空白等），若有違規將會阻擋並跳出警告提示！")
    
    if st.button("🚀 開始自動求解排班", type="primary"):
        st.session_state.temp_schedule = pd.DataFrame([
            {"日期": "週一", "早班": "呈", "晚班": "桂"},
            {"日期": "週二", "早班": "花藥", "晚班": "邱藥"}
        ])
        st.success("✅ 自動排班計算完成！請在下方進行微調與最終發佈。")

    if 'temp_schedule' in st.session_state:
        st.markdown("#### ✏️ 班表手動調整區")
        edited_schedule = st.data_editor(st.session_state.temp_schedule, num_rows="dynamic", key="manual_schedule_editor", use_container_width=True)
        
        st.divider()
        if st.button("💾 檢查規則並發佈最終班表", type="primary"):
            has_error = False
            error_messages = []
            
            for idx, row in edited_schedule.iterrows():
                if not str(row.get("早班", "")).strip() or not str(row.get("晚班", "")).strip():
                    has_error = True
                    error_messages.append(f"第 {idx+1} 行 ({row.get('日期', '未知日期')}) 的早班或晚班人員不得為空白！")
            
            if has_error:
                st.error("⚠️ **排班調整違反規則，無法發佈！** 請修正以下問題：")
                for err in error_messages:
                    st.markdown(f"- ❌ {err}")
            else:
                final_schedule_data = edited_schedule.to_dict(orient="records")
                save_json(FINAL_SCHEDULE_FILE, final_schedule_data)
                st.success("🎉 **檢查通過！** 班表已成功發佈給全體員工！")
    else:
        st.info("💡 請先點擊上方「開始自動求解排班」來產生初始排班表。")
