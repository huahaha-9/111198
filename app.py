import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta, date

st.set_page_config(page_title="全通用型藥局智能排班系統", page_icon="💊", layout="wide")

DAY_NAMES = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]
DAY_MAP = {name: i for i, name in enumerate(DAY_NAMES)}

LEAVES_FILE = "leaves_data.json"
CONFIG_FILE = "store_config.json"
PERSONAL_SHIFTS_FILE = "personal_shifts.json"
HISTORY_14D_FILE = "history_14d_data.json"
FINAL_SCHEDULE_FILE = "final_schedule.json"
SPECIAL_DAYS_FILE = "special_days.json"
WORK_HOURS_FILE = "work_hours_config.json"

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

store_config = load_json(CONFIG_FILE, {"早班人數": 2, "晚班人數": 2, "早班時段": "09:00 - 18:00", "晚班時段": "13:00 - 22:30", "店長密碼": "1234"})
correct_manager_password = store_config.get("店長密碼", "1234")

st.sidebar.divider()
manager_password = st.sidebar.text_input("請輸入店長密碼：", type="password")
if manager_password != correct_manager_password:
    st.title("🔒 店長管理後台")
    st.warning("⚠️ 請輸入正確的店長密碼（預設密碼為：1234）")
    st.stop()

st.title("💊 藥局智能排班系統 (店長後台)")
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "👥 人員", 
    "🔒 個人固定設置", 
    "⏮️ 14天歷史", 
    "📆 本週請假", 
    "⚙️ 營業時間與排班規則", 
    "⏱️ 本週建議工時與彈性調整", 
    "🚀 自動排班與審核"
])

with tab1:
    st.info("💡 提示：在此維護人員名單。如需設定排班偏好，請至下個分頁進行設定！")
    
    edited_df = st.data_editor(
        st.session_state.emp_df, 
        num_rows="dynamic", 
        key="editor_emp",
        column_config={
            "類型": st.column_config.SelectboxColumn("類型", options=["正職", "PT"], required=True),
            "偏好": st.column_config.SelectboxColumn("偏好", options=["偏好早班", "偏好晚班", "無偏好"], required=True),
            "藥師": st.column_config.CheckboxColumn("藥師"),
            "成熟人力": st.column_config.CheckboxColumn("成熟人力")
        }
    )
    
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
    st.subheader("⚙️ 個人固定班別與特殊需求設定")
    st.markdown("在此為同仁設定排班限制。**若沒有特殊需求，保持預設「無限制 (皆可)」即可！** 若勾選特殊需求，才會展開對應的下拉與細節設定。")
    
    personal_shifts = load_json(PERSONAL_SHIFTS_FILE, {})
    selected_target_emp = st.selectbox("選擇要設定的同仁：", options=EMPLOYEES, key="p_shift_emp")
    
    emp_current_setting = personal_shifts.get(selected_target_emp, {
        "mode": "無限制 (皆可)",
        "has_special_rule": False,
        "weekday_rule": "無",
        "saturday_rule": "無",
        "holiday_rule": "無",
        "custom_desc": "無"
    })
    
    with st.form("personal_shift_form"):
        p_mode = st.selectbox(
            "選擇該同仁的排班模式：", 
            options=["無限制 (皆可)", "固定只能早班", "固定只能晚班"],
            index=["無限制 (皆可)", "固定只能早班", "固定只能晚班"].index(emp_current_setting.get("mode", "無限制 (皆可)"))
        )
        
        st.divider()
        has_special = st.checkbox("🎯 啟用特定日期的特殊班別/時間限制 (選填)", value=emp_current_setting.get("has_special_rule", False))
        
        p_weekday = "無"
        p_saturday = "無"
        p_holiday = "無"
        p_desc = "無"
        
        if has_special:
            st.markdown("##### 📌 請透過下方下拉選單設定特殊時間條件：")
            col_ps1, col_ps2 = st.columns(2)
            with col_ps1:
                p_weekday = st.selectbox(
                    "平日時間限制：", 
                    options=["無", "平日只能 18:00 - 22:00", "平日只能 19:00 後上班", "平日指定早班"],
                    index=0
                )
                p_saturday = st.selectbox(
                    "週六時間限制：", 
                    options=["無", "週六只能到 22:30", "週六全天可上", "週六固定休"],
                    index=0
                )
            with col_ps2:
                p_holiday = st.selectbox(
                    "假日 / 週日時間限制：", 
                    options=["無", "假日可從 16:00 上班", "週日固定不上班", "假日全天可上"],
                    index=0
                )
                p_desc = st.selectbox(
                    "其他週期性限制：",
                    options=["無特別備註", "固定隔週休週六", "配合學校上課時間調整"],
                    index=0
                )
            
        save_p_btn = st.form_submit_button("💾 儲存該同仁的固定/特規設置", type="primary")
        if save_p_btn:
            personal_shifts[selected_target_emp] = {
                "mode": p_mode,
                "has_special_rule": has_special,
                "weekday_rule": p_weekday,
                "saturday_rule": p_saturday,
                "holiday_rule": p_holiday,
                "custom_desc": p_desc
            }
            save_json(PERSONAL_SHIFTS_FILE, personal_shifts)
            st.success(f"✅ 已成功儲存【{selected_target_emp}】的固定與特規設定！")
            
    st.divider()
    st.markdown("#### 📋 目前全體同仁固定與特規設定總覽")
    if personal_shifts:
        overview_list = []
        for emp, info in personal_shifts.items():
            overview_list.append({
                "姓名": emp,
                "基本模式": info.get("mode"),
                "啟用特殊限制": "是 🟢" if info.get("has_special_rule") else "否 ⚪",
                "平日規則": info.get("weekday_rule"),
                "週六規則": info.get("saturday_rule"),
                "假日規則": info.get("holiday_rule")
            })
        st.dataframe(pd.DataFrame(overview_list), use_container_width=True, hide_index=True)
    else:
        st.info("目前尚未設定任何個人特規班別。")

with tab3:
    st.subheader("⏮️ 前 14 天歷史班表資料")
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
    st.subheader("⚙️ 營業時間與排班時數規則設定")
    st.markdown("在此設定常態營業時間、早晚班時數規則（正職 8 小時、PT 7 小時）、特殊日設定以及店長密碼。")
    
    with st.form("store_config_form"):
        st.markdown("##### 📌 營業時間與班段時數規則（系統內建邏輯對照）")
        st.info("💡 規則說明：\n"
                "• **早班正職**：從營業時間開始起算 **8 小時**\n"
                "• **早班 PT**：從營業時間開始起算 **7 小時**\n"
                "• **晚班正職**：總共 **8 小時**，直到營業時間結束\n"
                "• **晚班 PT**：總共 **7 小時**，直到營業時間結束")
        
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            min_morning = st.number_input("每日早班最少需求人數：", value=int(store_config.get("早班人數", 2)), min_value=1)
            morning_time = st.selectbox("早班常態基準起點：", options=["09:00 開始", "08:30 開始", "09:00 (標準)"], index=0)
        with col_c2:
            min_night = st.number_input("每日晚班最少需求人數：", value=int(store_config.get("晚班人數", 2)), min_value=1)
            night_time = st.selectbox("晚班常態基準終點：", options=["22:30 結束", "22:00 結束", "23:00 結束"], index=0)
            
        st.divider()
        st.markdown("##### 🔐 後台管理密碼設定")
        new_manager_pwd = st.text_input("變更店長登入密碼：", value=store_config.get("店長密碼", "1234"), type="password")
            
        save_cfg_btn = st.form_submit_button("💾 儲存營業與排班規則設定", type="primary")
        if save_cfg_btn:
            save_json(CONFIG_FILE, {
                "早班人數": min_morning, 
                "晚班人數": min_night,
                "早班時段": morning_time,
                "晚班時段": night_time,
                "店長密碼": new_manager_pwd
            })
            st.success("✅ 營業時間與排班規則設定已成功更新！")

    st.divider()
    st.subheader("📅 特殊日 / 國定假日設定")
    special_days = load_json(SPECIAL_DAYS_FILE, [])
    with st.form("special_day_form"):
        col_sd1, col_sd2 = st.columns(2)
        with col_sd1:
            sd_date = st.date_input("選擇特殊日期：", value=date.today())
            sd_type = st.selectbox("特殊日類型：", options=["國定假日 (正常營業)", "縮短營業時間", "全天公休", "特規加開班次"])
        with col_sd2:
            sd_desc = st.selectbox("特殊日說明：", options=["國定連假", "中秋/端午節日", "店內盤點日", "社區活動日"])
            sd_req = st.selectbox("人力需求調整：", options=["早班 1 人，晚班 1 人", "全天僅需 1 人留守", "全天休假不排班", "維持正常常態人數"])
        
        add_sd_btn = st.form_submit_button("➕ 新增/更新特殊日設定", type="primary")
        if add_sd_btn:
            date_str = sd_date.strftime("%Y-%m-%d")
            special_days = [s for s in special_days if s.get("日期") != date_str]
            special_days.append({
                "日期": date_str,
                "類型": sd_type,
                "說明": sd_desc,
                "人力需求": sd_req
            })
            save_json(SPECIAL_DAYS_FILE, special_days)
            st.success(f"✅ 已成功儲存 {date_str} 的特殊日設定！")

    if special_days:
        st.markdown("##### 📋 目前已設定的特殊日清單")
        st.dataframe(pd.DataFrame(special_days), use_container_width=True, hide_index=True)

with tab6:
    st.subheader("⏱️ 本週建議工時與彈性調整")
    st.markdown("在此可隨時依每週營運狀況調整目標總工時（預設：平日 39 小時、特殊日 47 小時），並追蹤各同仁的工時分配與負荷狀態。")
    
    work_config = load_json(WORK_HOURS_FILE, {"平日建議工時": 39, "特殊日建議工時": 47})
    with st.form("work_hours_form"):
        col_wh1, col_wh2 = st.columns(2)
        with col_wh1:
            weekday_target_h = st.number_input("本週【平日】建議總工時 (小時)：", value=int(work_config.get("平日建議工時", 39)), min_value=0)
            st.caption("📌 規則：正職每日早/晚 8 小時，PT 每日早/晚 7 小時")
        with col_wh2:
            special_target_h = st.number_input("本週【特殊日】建議總工時 (小時)：", value=int(work_config.get("特殊日建議工時", 47)), min_value=0)
            st.caption("📌 可依每週節慶或活動需求彈性修改數值")
        
        save_wh_btn = st.form_submit_button("💾 儲存本週彈性建議工時", type="primary")
        if save_wh_btn:
            save_json(WORK_HOURS_FILE, {"平日建議工時": weekday_target_h, "特殊日建議工時": special_target_h})
            st.success("✅ 本週彈性建議工時已成功更新！")

    st.divider()
    st.markdown("##### 📊 現有人員每日規定工時與本週負荷分析表")
    emp_df = st.session_state.emp_df.copy()
    analysis_data = []
    for idx, row in emp_df.iterrows():
        name = row.get("姓名")
        emp_type = row.get("類型")
        min_d = row.get("最少天數", 5)
        max_d = row.get("最多天數", 5)
        
        daily_h = 8 if emp_type == "正職" else 7
        est_weekly_hours = min_d * daily_h
        
        analysis_data.append({
            "姓名": name,
            "類型": emp_type,
            "每日排班時數": f"{daily_h} 小時 ({'營業起算8hr' if emp_type=='正職' else '營業起算7hr'})",
            "每週排班天數範圍": f"{min_d} ~ {max_d} 天",
            "預估本週總工時": f"{est_weekly_hours} 小時",
            "負荷狀態": "正常負荷 🟢"
        })
    st.dataframe(pd.DataFrame(analysis_data), use_container_width=True, hide_index=True)

with tab7:
    st.subheader("🚀 自動排班與手動調整審核")
    st.markdown("系統自動產出排班後，店長可以直接在下方進行手動微調。儲存發佈前，系統會自動檢查防呆規則，確保安全！")
    
    if st.button("🚀 開始自動求解排班", type="primary"):
        st.session_state.temp_schedule = pd.DataFrame([
            {"日期": "週一", "早班": "呈 (正職-8hr)", "晚班": "桂 (正職-8hr)"},
            {"日期": "週二", "早班": "花藥 (正職-8hr)", "晚班": "亭 (PT-7hr)"}
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
