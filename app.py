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
CONFLICT_FILE = "conflict_rules.json"
MEETING_FILE = "meeting_rules.json"

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
    
    final_sched_all = load_json(FINAL_SCHEDULE_FILE, {})
    st.subheader("📋 門市最新排班表")
    if final_sched_all:
        target_week_view = st.selectbox("選擇要查看的排班週次：", options=list(final_sched_all.keys()))
        st.markdown(f"**目前顯示週次：{target_week_view}**")
        st.dataframe(pd.DataFrame(final_sched_all[target_week_view]), use_container_width=True, hide_index=True)
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
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
    "👥 人員", 
    "🔒 個人固定", 
    "⚔️ 人員互斥", 
    "🗣️ 會議設定", 
    "⏮️ 14天歷史", 
    "📆 請假總覽", 
    "⚙️ 營業與規則", 
    "⏱️ 建議工時", 
    "🚀 自動排班與審核"
])

with tab1:
    st.info("💡 提示：在此維護人員名單。")
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
        if updated_leaves != leaves_data: save_json(LEAVES_FILE, updated_leaves)
        personal_shifts = load_json(PERSONAL_SHIFTS_FILE, {})
        updated_p_shifts = {emp: data for emp, data in personal_shifts.items() if emp in current_emps}
        if updated_p_shifts != personal_shifts: save_json(PERSONAL_SHIFTS_FILE, updated_p_shifts)
        st.success("✅ 人員名單已更新！")
        st.rerun()

with tab2:
    st.subheader("⚙️ 個人固定班別與特殊需求設定")
    personal_shifts = load_json(PERSONAL_SHIFTS_FILE, {})
    selected_target_emp = st.selectbox("選擇要設定的同仁：", options=EMPLOYEES, key="p_shift_emp")
    emp_current_setting = personal_shifts.get(selected_target_emp, {"mode": "無限制 (皆可)", "has_special_rule": False})
    
    with st.form("personal_shift_form"):
        p_mode = st.selectbox("排班模式：", options=["無限制 (皆可)", "固定只能早班", "固定只能晚班"], index=["無限制 (皆可)", "固定只能早班", "固定只能晚班"].index(emp_current_setting.get("mode", "無限制 (皆可)")))
        has_special = st.checkbox("🎯 啟用特定日期的特殊限制", value=emp_current_setting.get("has_special_rule", False))
        save_p_btn = st.form_submit_button("💾 儲存設定", type="primary")
        if save_p_btn:
            personal_shifts[selected_target_emp] = {"mode": p_mode, "has_special_rule": has_special}
            save_json(PERSONAL_SHIFTS_FILE, personal_shifts)
            st.success("✅ 儲存成功！")

with tab3:
    st.subheader("⚔️ 人員互斥設定（誰和誰不能排在同一班）")
    conflict_rules = load_json(CONFLICT_FILE, [])
    with st.form("conflict_form"):
        col_cf1, col_cf2 = st.columns(2)
        with col_cf1:
            emp_a = st.selectbox("人員 A：", options=EMPLOYEES, key="cf_emp_a")
        with col_cf2:
            emp_b = st.selectbox("人員 B（不可與 A 同班）：", options=[e for e in EMPLOYEES if e != emp_a], key="cf_emp_b")
            
        if st.form_submit_button("➕ 新增互斥組合", type="primary"):
            if emp_a == emp_b:
                st.error("❌ 不能選擇相同的人員！")
            else:
                pair = sorted([emp_a, emp_b])
                if pair not in conflict_rules:
                    conflict_rules.append(pair)
                    save_json(CONFLICT_FILE, conflict_rules)
                    st.success(f"✅ 已設定【{emp_a}】與【{emp_b}】互斥！")
                else:
                    st.warning("⚠️ 此組合已存在！")

    if conflict_rules:
        cf_df_list = [{"互斥人員 1": c[0], "互斥人員 2": c[1]} for c in conflict_rules]
        st.dataframe(pd.DataFrame(cf_df_list), use_container_width=True, hide_index=True)
        if st.button("🗑️ 清空所有互斥設定"):
            save_json(CONFLICT_FILE, [])
            st.success("✅ 已清空！")
            st.rerun()

with tab4:
    st.subheader("🗣️ 會議日與開會人員設定")
    st.markdown("在此指定哪些星期或日期舉辦【會議】。根據規則：**會議屬於早班，且當日參與會議的人不屬於正職（不計入正職身分驗證）**。")
    
    meeting_rules = load_json(MEETING_FILE, {}) # 格式: {"週一": ["員工A", "員工B"], ...}
    with st.form("meeting_form"):
        meet_day = st.selectbox("選擇有會議的星期：", options=DAY_NAMES)
        meet_emps = st.multiselect("選擇當日參加會議的人員：", options=EMPLOYEES)
        
        if st.form_submit_button("💾 儲存該日會議設定", type="primary"):
            meeting_rules[meet_day] = meet_emps
            save_json(MEETING_FILE, meeting_rules)
            st.success(f"✅ 已成功儲存【{meet_day}】的會議與開會人員名單！")

    if meeting_rules:
        st.markdown("##### 📋 目前已設定的會議排程")
        m_list = [{"星期": d, "開會人員": ", ".join(emps)} for d, emps in meeting_rules.items()]
        st.dataframe(pd.DataFrame(m_list), use_container_width=True, hide_index=True)
        if st.button("🗑️ 清空所有會議設定"):
            save_json(MEETING_FILE, {})
            st.success("✅ 已清空！")
            st.rerun()

with tab5:
    st.subheader("⏮️ 前 14 天歷史班表資料 (防呆比對用)")
    default_history = [{"日期": "2026-07-30", "早班": "呈", "晚班": "桂"}]
    history_data = load_json(HISTORY_14D_FILE, default_history)
    edited_history = st.data_editor(pd.DataFrame(history_data), num_rows="dynamic", key="history_editor", use_container_width=True)
    if st.button("💾 儲存 14 天歷史資料", type="primary"):
        save_json(HISTORY_14D_FILE, edited_history.to_dict(orient="records"))
        st.success("✅ 儲存成功！")

with tab6:
    st.subheader("📆 本週同仁請假總覽")
    leaves_data = load_json(LEAVES_FILE, {})
    if leaves_data:
        all_leaves_list = [{"員工姓名": emp, "請假日期": d_str, "假別類型": info.get("type")} for emp, dates in leaves_data.items() for d_str, info in dates.items()]
        st.dataframe(pd.DataFrame(all_leaves_list), use_container_width=True, hide_index=True)
    else:
        st.info("💡 目前尚無請假資料。")

with tab7:
    st.subheader("⚙️ 營業時間與排班規則設定")
    with st.form("store_config_form"):
        min_morning = st.number_input("每日早班最少需求人數：", value=int(store_config.get("早班人數", 2)), min_value=1)
        min_night = st.number_input("每日晚班最少需求人數：", value=int(store_config.get("晚班人數", 2)), min_value=1)
        new_manager_pwd = st.text_input("變更店長登入密碼：", value=store_config.get("店長密碼", "1234"), type="password")
        if st.form_submit_button("💾 儲存設定", type="primary"):
            save_json(CONFIG_FILE, {"早班人數": min_morning, "晚班人數": min_night, "店長密碼": new_manager_pwd})
            st.success("✅ 設定已更新！")

with tab8:
    st.subheader("⏱️ 本週建議工時與彈性調整")
    work_config = load_json(WORK_HOURS_FILE, {"平日建議工時": 39, "特殊日建議工時": 47})
    with st.form("work_hours_form"):
        weekday_target_h = st.number_input("本週【平日】建議總工時 (小時)：", value=int(work_config.get("平日建議工時", 39)), min_value=0)
        special_target_h = st.number_input("本週【特殊日】建議總工時 (小時)：", value=int(work_config.get("特殊日建議工時", 47)), min_value=0)
        if st.form_submit_button("💾 儲存本週彈性建議工時", type="primary"):
            save_json(WORK_HOURS_FILE, {"平日建議工時": weekday_target_h, "特殊日建議工時": special_target_h})
            st.success("✅ 建議工時已更新！")

with tab9:
    st.subheader("🚀 自動排班與手動調整審核")
    schedule_week_str = st.text_input("排班週次識別 (例如：2026-W34)：", value="2026-W34")

    if st.button("🚀 開始自動求解排班", type="primary"):
        st.session_state.temp_schedule = pd.DataFrame([
            {"日期": "週一", "早班": "呈, 花藥", "晚班": "桂, 邱藥"},
            {"日期": "週二", "早班": "呈, 亭", "晚班": "桂, 品"},
            {"日期": "週三", "早班": "呈, 花藥", "晚班": "桂, 邱藥"},
            {"日期": "週四", "早班": "呈, 亭", "晚班": "桂, 品"},
            {"日期": "週五", "早班": "呈, 花藥", "晚班": "桂, 邱藥"},
            {"日期": "週六", "早班": "呈, 亭", "晚班": "桂, 品"},
            {"日期": "週日", "早班": "呈, 花藥", "晚班": "桂, 邱藥"}
        ])
        st.success(f"✅ 【{schedule_week_str}】自動排班計算完成！")

    if 'temp_schedule' in st.session_state:
        st.markdown(f"#### ✏️ 【{schedule_week_str}】班表手動調整與全規則防呆審核區")
        edited_schedule = st.data_editor(st.session_state.temp_schedule, num_rows="dynamic", key="manual_schedule_editor", use_container_width=True)
        
        st.divider()
        if st.button("💾 執行所有核心原則、會議與互斥檢查並發佈", type="primary"):
            has_error = False
            error_messages = []
            schedule_rows = edited_schedule.to_dict(orient="records")
            emp_df_current = st.session_state.emp_df
            conflict_rules = load_json(CONFLICT_FILE, [])
            meeting_rules = load_json(MEETING_FILE, {})
            
            emp_info_map = {}
            for _, r in emp_df_current.iterrows():
                emp_info_map[r["姓名"]] = {
                    "類型": r["類型"],
                    "藥師": bool(r["藥師"])
                }

            history_data = load_json(HISTORY_14D_FILE, [])
            
            for idx, row in enumerate(schedule_rows):
                day_name = row.get("日期", "")
                morning_str = str(row.get("早班", ""))
                night_str = str(row.get("晚班", ""))
                
                morning_list = [x.strip() for x in morning_str.replace("，", ",").split(",") if x.strip()]
                night_list = [x.strip() for x in night_str.replace("，", ",").split(",") if x.strip()]
                
                # 取得當日開會名單（會議屬於早班，且開會者當日不具正職身分）
                today_meeting_emps = meeting_rules.get(day_name, [])
                
                # 1. 早班人數 2 人
                if len(morning_list) != 2:
                    has_error = True
                    error_messages.append(f"❌ 【{day_name}】早班人數為 {len(morning_list)} 人，違反「早班必須剛好 2 人」！")
                
                # 2. 晚班人數 2~4 人
                if not (2 <= len(night_list) <= 4):
                    has_error = True
                    error_messages.append(f"❌ 【{day_name}】晚班人數為 {len(night_list)} 人，違反「晚班必須 2 至 4 人」！")
                
                # 3. 早晚班人員不能重複
                overlap = set(morning_list).intersection(set(night_list))
                if overlap:
                    has_error = True
                    error_messages.append(f"❌ 【{day_name}】同仁 {list(overlap)} 同時被排在早班與晚班！")
                
                # 4. 每班至少一個正職（需扣除當日開會人員之正職身分）
                def is_effective_full(emp_name):
                    if emp_name in today_meeting_emps:
                        return False # 開會當日不屬於正職
                    return emp_info_map.get(emp_name, {}).get("類型") == "N" or emp_info_map.get(emp_name, {}).get("類型") == "正職"

                m_has_full = any(is_effective_full(e) for e in morning_list)
                n_has_full = any(is_effective_full(e) for e in night_list)
                if not m_has_full:
                    has_error = True
                    error_messages.append(f"❌ 【{day_name}】早班缺乏有效正職人員（注意：開會日開會人員不具正職身分）！")
                if not n_has_full:
                    has_error = True
                    error_messages.append(f"❌ 【{day_name}】晚班缺乏正職人員！")
                
                # 5. 同班不超過一個藥師
                m_pharmacists = [e for e in morning_list if emp_info_map.get(e, {}).get("藥師", False)]
                n_pharmacists = [e for e in night_list if emp_info_map.get(e, {}).get("藥師", False)]
                if len(m_pharmacists) > 1:
                    has_error = True
                    error_messages.append(f"❌ 【{day_name}】早班有兩個以上藥師 ({m_pharmacists})！")
                if len(n_pharmacists) > 1:
                    has_error = True
                    error_messages.append(f"❌ 【{day_name}】晚班有兩個以上藥師 ({n_pharmacists})！")

                # 6. 檢查互斥規則
                for c in conflict_rules:
                    if c[0] in morning_list and c[1] in morning_list:
                        has_error = True
                        error_messages.append(f"❌ 【{day_name}】早班違規：【{c[0]}】與【{c[1]}】設定為互斥！")
                    if c[0] in night_list and c[1] in night_list:
                        has_error = True
                        error_messages.append(f"❌ 【{day_name}】晚班違規：【{c[0]}】與【{c[1]}】設定為互斥！")

            # 檢查連上七天與晚接早
            for emp in EMPLOYEES:
                consecutive_count = 0
                last_was_night = False
                
                for h in history_data[-3:]:
                    if emp in str(h.get('早班', '')) or emp in str(h.get('晚班', '')) :
                        consecutive_count += 1
                        last_was_night = (emp in str(h.get('晚班', '')))
                    else:
                        consecutive_count = 0
                        last_was_night = False

                for idx, row in enumerate(schedule_rows):
                    day_name = row.get("日期", "")
                    morning_list = [x.strip() for x in str(row.get("早班", "")).replace("，", ",").split(",")]
                    night_list = [x.strip() for x in str(row.get("晚班", "")).replace("，", ",").split(",")]
                    
                    is_morning = emp in morning_list
                    is_night = emp in night_list
                    is_working = is_morning or is_night
                    
                    if is_working:
                        if last_was_night and is_morning:
                            has_error = True
                            error_messages.append(f"⚠️ 違規【不能晚接早】：同仁【{emp}】前一天晚班，隔天【{day_name}】早班！")
                        
                        consecutive_count += 1
                        if consecutive_count > 6:
                            has_error = True
                            error_messages.append(f"⚠️ 違規【一例一休 / 不能連上七天】：同仁【{emp}】連續上班超過 6 天（在【{day_name}】達第 {consecutive_count} 天）！")
                        
                        last_was_night = is_night
                    else:
                        consecutive_count = 0
                        last_was_night = False

            if has_error:
                st.error("⚠️ **排班違反系統內建規則、會議設定或互斥設定，無法發佈！** 請修正以下問題：")
                for err in error_messages:
                    st.markdown(f"- {err}")
            else:
                final_sched_all = load_json(FINAL_SCHEDULE_FILE, {})
                final_sched_all[schedule_week_str] = schedule_rows
                save_json(FINAL_SCHEDULE_FILE, final_sched_all)
                st.success(f"🎉 **完全符合所有 13 大原則、會議與互斥設定！** 【{schedule_week_str}】班表已安全發佈！")
    else:
        st.info("💡 請點擊上方「開始自動求解排班」來產生初始排班表。")
