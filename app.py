import streamlit as st
import pandas as pd
import json

# ==========================================
# 頁面基本設定
# ==========================================
st.set_page_config(
    page_title="分店自動排班系統原型",
    page_icon="📋",
    layout="wide"
)

st.title("📋 分店自動排班系統 (Streamlit 模擬原型)")
st.caption("支援 Layer 0~4 規則引擎與 Layer 3 手動解鎖診斷卡片")

# ==========================================
# 👈 左側邊欄：門市設定與 Layer 3 開關
# ==========================================
with st.sidebar:
    st.header("⚙️ 門市與演算法參數")
    
    store_id = st.text_input("門市代號", value="STORE_TAIWAN_001")
    
    st.subheader("🔓 Layer 3 手動解鎖開關 (Overrides)")
    st.caption("預設全關。僅在系統判定無解時由管理者手動勾選：")
    
    allow_leave = st.checkbox("[解鎖 A] 放寬劃假限制", value=False)
    allow_overtime = st.checkbox("[解鎖 B] 允許休息日加班", value=False)
    allow_single = st.checkbox("[解鎖 C] 放寬單人當班 (僅一般日)", value=False)
    allow_night_morning = st.checkbox("[解鎖 D] 放寬晚接早 (間隔≥11h)", value=False)
    
    st.divider()
    
    btn_run_solver = st.button("🚀 執行自動排班", type="primary", use_container_width=True)

# ==========================================
# 核心內容區 (Tabs)
# ==========================================
tab1, tab2, tab3 = st.tabs(["📅 自動產生班表檢視", "🚨 Layer 3 無解診斷卡片 (模擬)", "⚙️ 人員與劃假資料"])

# ------------------------------------------
# Tab 1: 班表結果展示
# ------------------------------------------
with tab1:
    st.subheader("🗓️ 本週排班結果 (Gantt View / Table)")
    
    # 模擬排班引擎回傳的成功資料
    mock_schedule_data = {
        "員工姓名": ["張藥師 (正職)", "李正職", "王 PPT (資深)", "陳 PT (新人)", "林 PT (資深)"],
        "角色屬性": ["正職藥師", "正職店長", "資深 PPT", "新人 PT", "資深 PT"],
        "週一 (08/17)": ["早班 (09-17)", "晚班 (14-22)", "OFF", "早班 (09-17)", "晚班 (14-22)"],
        "週二 (08/18)": ["早班 (09-17)", "OFF", "晚班 (14-22)", "早班 (09-17)", "OFF"],
        "週三 (08/19)": ["會議 (09-17)", "早班 (09-17)", "晚班 (14-22)", "OFF", "晚班 (14-22)"],
        "週四 (08/20)": ["早班 (09-17)", "晚班 (14-22)", "OFF", "早班 (09-17)", "OFF"],
        "週五 (08/21)": ["OFF", "早班 (09-17)", "晚班 (14-22)", "OFF", "晚班 (14-22)"],
        "週六 (08/22) [特]": ["早班 (09-17)", "晚班 (14-22)", "晚班 (14-22)", "中班 (12-20)", "OFF"],
        "週日 (08/23) [特]": ["晚班 (14-22)", "早班 (09-17)", "早班 (09-17)", "OFF", "晚班 (14-22)"],
    }
    
    df_schedule = pd.DataFrame(mock_schedule_data)
    
    # 呈現表格
    st.dataframe(
        df_schedule, 
        use_container_width=True,
        hide_index=True
    )
    
    st.divider()
    
    # 指標與加分展示
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="PPT 當班次數 (目標最大化)", value="3 次", delta="+1 (最佳化成效)")
    with col2:
        st.metric(label="藥師搭班合規率", value="100%", delta="無單人/雙藥師衝突")
    with col3:
        st.metric(label="Timeline 15/30m 檢核", value="Pass", delta="隨時 ≥ 2人/≥1當班")

# ------------------------------------------
# Tab 2: Layer 3 無解診斷卡片 (當系統算不出時)
# ------------------------------------------
with tab2:
    st.error("⚠️ 系統首輪運算結果：INFEASIBLE (無解)")
    st.markdown("由於門市人力吃緊或過多資深人員劃假，**Layer 0~2 限制條件無法同時滿足**。請選擇以下解鎖方案：")
    
    # 用卡片 containers 模擬 App 彈出的診斷選單
    with st.container(border=True):
        st.markdown("### 🔓 建議解鎖方案 (可多選)")
        
        c1, c2 = st.columns([1, 4])
        with c1:
            u_a = st.checkbox("勾選解鎖", key="card_a")
        with c2:
            st.markdown("**【選項 A】放寬劃假限制**")
            st.caption("提示：取消 [張藥師] 於 08/17 的劃假即可成功算出班表。")
            
        st.divider()
        
        c3, c4 = st.columns([1, 4])
        with c3:
            u_b = st.checkbox("勾選解鎖", key="card_b")
        with c4:
            st.markdown("**【選項 B】允許休息日加班**")
            st.caption("允許 [李正職] 於週六加班支援晚班 (發放 1.34/1.67 倍加班費)。")

        st.divider()

        c5, c6 = st.columns([1, 4])
        with c5:
            u_c = st.checkbox("勾選解鎖", key="card_c")
        with c6:
            st.markdown("**【選項 C】放寬單人當班**")
            st.caption("允許一般日平峰時段改為 1 人當班 (僅限資深正職/成熟 PPT，特殊日強制屏蔽此放寬)。")

    if st.button("🔄 載入勾選條件並重新求解", type="primary"):
        st.success("已載入解鎖條件，重新計算中...")

# ------------------------------------------
# Tab 3: 人員屬性與劃假資料設定
# ------------------------------------------
with tab3:
    st.subheader("👥 門市人員屬性清單")
    
    mock_emp_data = {
        "員工編號": ["E001", "E002", "E003", "E004", "E005"],
        "姓名": ["張藥師", "李正職", "王 PPT", "陳 PT", "林 PT"],
        "角色 (Role)": ["FULL_TIME", "FULL_TIME", "PPT", "PT", "PT"],
        "具備當班資格": [True, True, True, False, False],
        "成熟人力 (Seniority)": ["SENIOR", "SENIOR", "SENIOR", "JUNIOR", "SENIOR"],
        "每週至少上班天數": [5, 5, 3, 3, 3],
        "偏好班別": ["MORNING", "ANY", "NIGHT", "ANY", "NIGHT"]
    }
    
    st.dataframe(pd.DataFrame(mock_emp_data), use_container_width=True)
    
    st.subheader("📝 劃假需求 JSON")
    st.json({
        "E001": [0, 1], # 週一週二劃假
        "E003": [4]    # 週五劃假
    })
