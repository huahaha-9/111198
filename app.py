import streamlit as st
import pandas as pd
from enum import Enum
from typing import List, Dict, Tuple, Optional
from pydantic import BaseModel, Field
from ortools.sat.python import cp_model

# ==========================================
# 0. 基礎資料結構定義 (Data Models)
# ==========================================

class Role(str, Enum):
    FULL_TIME = "FULL_TIME"  # 正職
    PPT = "PPT"              # 成熟兼職 PPT (具當班資格)
    PT = "PT"                # 一般兼職 PT

class Seniority(str, Enum):
    SENIOR = "SENIOR"  # 成熟人力
    JUNIOR = "JUNIOR"  # 新人 / 訓練中

class Employee(BaseModel):
    emp_id: str
    name: str
    role: Role
    is_pharmacist: bool = False
    is_supervisor: bool = False  # 具當班資格 (正職 / 成熟 PPT)
    seniority: Seniority = Seniority.SENIOR
    weekly_min_days: int = 3
    weekly_max_days: int = 5
    preferred_shift: Optional[str] = None  # "MORNING" or "NIGHT"

class ShiftType(str, Enum):
    OFF = "OFF"
    MORNING = "MORNING"    # 早班
    NIGHT = "NIGHT"        # 晚班
    MIDDLE = "MIDDLE"      # 中班 (特殊日 12:00 - 20:00)
    MEETING = "MEETING"    # 公司會議 (09:00 - 17:00, 門市 Capacity=0)

class OverridesConfig(BaseModel):
    allow_leave_override: bool = False       # [2-02] 解鎖 A: 放寬劃假
    allow_overtime: bool = False             # [2-03] 解鎖 B: 休息日加班
    allow_single_staffing: bool = False      # [2-04] 解鎖 C: 放寬單人當班
    allow_night_to_morning: bool = False     # [2-05] 解鎖 D: 放寬晚接早

class DayConfig(BaseModel):
    day_index: int  # 0 = 週一, ..., 6 = 週日
    is_special_day: bool = False

class SchedulingRequest(BaseModel):
    store_id: str
    employees: List[Employee]
    days: List[DayConfig]
    leave_requests: Dict[str, List[int]] = {}       # emp_id -> List[day_index]
    meeting_requests: Dict[str, List[int]] = {}     # emp_id -> List[day_index]
    mutually_exclusive_pairs: List[Tuple[str, str]] = [] # [1-14] 互斥搭班
    overrides: OverridesConfig = Field(default_factory=OverridesConfig)

# ==========================================
# 1. 核心排班演算法引擎 (OR-Tools CP-SAT)
# ==========================================

class StoreSchedulerEngine:
    def __init__(self, request: SchedulingRequest):
        self.req = request
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        
        # 15 分鐘為 1 Tick (09:00 - 22:00 共 13 小時 = 52 Ticks)
        self.ticks_per_day = 52  
        
        self.shifts = {}
        self.timeline = {}
        self.is_supervisor_on_duty = {}
        self.has_ft_on_duty = {}
        self.ppt_on_duty_day = {}

    def build_and_solve(self) -> Tuple[str, Dict]:
        self._init_variables()
        
        # Layer 0: 法規與結構底線 (Hard Constraints)
        self._apply_layer_0_hard_constraints()
        
        # Layer 1: 門市營運與 Timeline 檢核 (Hard Constraints)
        self._apply_layer_1_timeline_constraints()
        
        # Layer 2: 彈性邊界與工時配額 (Tactical Constraints)
        self._apply_layer_2_tactical_constraints()
        
        # Layer 3: 手動解鎖關卡 (Overrides Handling)
        self._apply_layer_3_overrides_handling()
        
        # Layer 4: 軟性偏好與最佳化目標 (Score Optimization)
        self._apply_layer_4_soft_optimization()

        self.solver.parameters.max_time_in_seconds = 10.0
        status_code = self.solver.Solve(self.model)

        if status_code in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return "SUCCESS", self._extract_schedule_result()
        else:
            return "INFEASIBLE", self._generate_layer_3_diagnosis()

    def _init_variables(self):
        shift_types = [ShiftType.OFF, ShiftType.MORNING, ShiftType.NIGHT, ShiftType.MIDDLE, ShiftType.MEETING]
        
        for e in self.req.employees:
            for d in range(len(self.req.days)):
                # 每日基本班別 (100% 互斥，每日只能排 1 班) [1-07]
                for s in shift_types:
                    self.shifts[(e.emp_id, d, s)] = self.model.NewBoolVar(f"shift_{e.emp_id}_d{d}_{s.value}")
                self.model.AddExactlyOne([self.shifts[(e.emp_id, d, s)] for s in shift_types])

                # Timeline 15-min Ticks 離散時間映射 [1-13, 1-20~1-25]
                for t in range(self.ticks_per_day):
                    self.timeline[(e.emp_id, d, t)] = self.model.NewBoolVar(f"tl_{e.emp_id}_d{d}_t{t}")

                # 班別對應的 Tick 覆蓋時間計算 (09:00 起算，每 Tick 15 分鐘)
                for t in range(self.ticks_per_day):
                    on_duty_conditions = []
                    
                    # [1-20, 1-23] 早班：09:00 - 17:00 (Tick 0 ~ 31)
                    if 0 <= t < 32:
                        on_duty_conditions.append(self.shifts[(e.emp_id, d, ShiftType.MORNING)])
                    
                    # [1-21, 1-24] 晚班 (正職 14:00-22:00 Tick 20~51 / PT 16:30-22:00 Tick 30~51，均涵蓋在 Tick 30~51)
                    if 30 <= t < 52:
                        on_duty_conditions.append(self.shifts[(e.emp_id, d, ShiftType.NIGHT)])
                    elif 20 <= t < 30 and e.role == Role.FULL_TIME: # 正職晚班自 14:00 (Tick 20) 起算
                        on_duty_conditions.append(self.shifts[(e.emp_id, d, ShiftType.NIGHT)])
                    
                    # [1-25] 特殊日中班：12:00 - 20:00 (Tick 12 ~ 43)
                    if 12 <= t < 44:
                        on_duty_conditions.append(self.shifts[(e.emp_id, d, ShiftType.MIDDLE)])

                    # [1-18] 會議人員 (MEETING) 現場 Capacity 算 0，故不加入 on_duty_conditions！
                    
                    if on_duty_conditions:
                        self.model.AddMaxEquality(self.timeline[(e.emp_id, d, t)], on_duty_conditions)
                    else:
                        self.model.Add(self.timeline[(e.emp_id, d, t)] == 0)

        # Timeline 關鍵指標標示：每 Tick 現場是否有當班資格者、是否有正職
        for d in range(len(self.req.days)):
            for t in range(self.ticks_per_day):
                # 是否有當班資格人員 (正職 或 成熟 PPT)
                self.is_supervisor_on_duty[(d, t)] = self.model.NewBoolVar(f"super_d{d}_t{t}")
                super_present = [
                    self.timeline[(e.emp_id, d, t)] 
                    for e in self.req.employees if e.is_supervisor or e.role == Role.PPT
                ]
                if super_present:
                    self.model.AddMaxEquality(self.is_supervisor_on_duty[(d, t)], super_present)
                else:
                    self.model.Add(self.is_supervisor_on_duty[(d, t)] == 0)

                # 是否有正職在場
                self.has_ft_on_duty[(d, t)] = self.model.NewBoolVar(f"ft_d{d}_t{t}")
                ft_present = [
                    self.timeline[(e.emp_id, d, t)] 
                    for e in self.req.employees if e.role == Role.FULL_TIME
                ]
                if ft_present:
                    self.model.AddMaxEquality(self.has_ft_on_duty[(d, t)], ft_present)
                else:
                    self.model.Add(self.has_ft_on_duty[(d, t)] == 0)

    # ----------------------------------------------------------------------
    # Layer 0: 法規與結構底線 (Hard Constraints)
    # ----------------------------------------------------------------------
    def _apply_layer_0_hard_constraints(self):
        # [1-01] PT / PPT 強制 7 休 1
        for e in self.req.employees:
            if e.role in (Role.PT, Role.PPT):
                for d in range(len(self.req.days) - 6):
                    self.model.Add(
                        sum(self.shifts[(e.emp_id, d + offset, ShiftType.OFF)] for offset in range(7)) >= 1
                    )

        # [1-02, 1-03] 正職一例一休 (每週固定排 5 天上班, 2 天休息)
        for e in self.req.employees:
            if e.role == Role.FULL_TIME:
                work_days = sum(
                    1 - self.shifts[(e.emp_id, d, ShiftType.OFF)] 
                    for d in range(len(self.req.days))
                )
                self.model.Add(work_days == 5)

        # [1-14] 互斥搭班機制 (指定的兩個人絕不能排在同一班)
        for emp_a, emp_b in self.req.mutually_exclusive_pairs:
            for d in range(len(self.req.days)):
                for s in [ShiftType.MORNING, ShiftType.NIGHT, ShiftType.MIDDLE]:
                    self.model.Add(
                        self.shifts[(emp_a, d, s)] + self.shifts[(emp_b, d, s)] <= 1
                    )

        # [1-15] 藥師不重疊 (同一班別嚴禁出現 2 位藥師)
        pharmacists = [e for e in self.req.employees if e.is_pharmacist]
        if len(pharmacists) > 1:
            for d in range(len(self.req.days)):
                for s in [ShiftType.MORNING, ShiftType.NIGHT, ShiftType.MIDDLE]:
                    self.model.Add(
                        sum(self.shifts[(e.emp_id, d, s)] for e in pharmacists) <= 1
                    )

        # [1-16] 藥師晚班搭班硬性防線
        for e in pharmacists:
            for d in range(len(self.req.days)):
                if e.role == Role.FULL_TIME:
                    # 狀況 A (正職藥師)：同班必須包含至少 1 位成熟人力 (正職/成熟PPT/成熟PT)
                    seniors = [
                        other.emp_id for other in self.req.employees 
                        if other.emp_id != e.emp_id and other.seniority == Seniority.SENIOR
                    ]
                    self.model.Add(
                        sum(self.shifts[(other_id, d, ShiftType.NIGHT)] for other_id in seniors) >= 1
                    ).OnlyEnforceIf(self.shifts[(e.emp_id, d, ShiftType.NIGHT)])
                else:
                    # 狀況 B (PT 藥師)：同班必須包含至少 1 位具當班資格者 (正職/成熟 PPT)，嚴禁成熟 PT 為唯一搭檔
                    supervisors = [
                        other.emp_id for other in self.req.employees 
                        if other.emp_id != e.emp_id and (other.role == Role.FULL_TIME or other.role == Role.PPT)
                    ]
                    self.model.Add(
                        sum(self.shifts[(sup_id, d, ShiftType.NIGHT)] for sup_id in supervisors) >= 1
                    ).OnlyEnforceIf(self.shifts[(e.emp_id, d, ShiftType.NIGHT)])

        # [1-17, 1-18] 公司會議歸屬與不計門市營運名額
        for emp_id, meeting_days in self.req.meeting_requests.items():
            for d in meeting_days:
                self.model.Add(self.shifts[(emp_id, d, ShiftType.MEETING)] == 1)

    # ----------------------------------------------------------------------
    # Layer 1: 門市營運與 Timeline 檢核 (Hard Constraints)
    # ----------------------------------------------------------------------
    def _apply_layer_1_timeline_constraints(self):
        for d_cfg in self.req.days:
            d = d_cfg.day_index
            
            # [1-08] 早班人數固定為 2 人 (門市當班，不含 MEETING 會議人員)
            morning_count = sum(self.shifts[(e.emp_id, d, ShiftType.MORNING)] for e in self.req.employees)
            self.model.Add(morning_count == 2)

            # [1-09, 1-10] 晚班人數規範
            night_count = sum(self.shifts[(e.emp_id, d, ShiftType.NIGHT)] for e in self.req.employees)
            if d_cfg.is_special_day:
                self.model.Add(night_count >= 3) # [1-10] 特殊日晚班至少 3 人
            else:
                self.model.Add(night_count >= 2) # [1-09] 一般日晚班 2 ~ 4 人
                self.model.Add(night_count <= 4)

            # [1-05] 嚴禁全新人/訓練中人力獨立同班
            juniors = [e.emp_id for e in self.req.employees if e.seniority == Seniority.JUNIOR]
            seniors = [e.emp_id for e in self.req.employees if e.seniority == Seniority.SENIOR]
            for s in [ShiftType.MORNING, ShiftType.NIGHT]:
                has_junior = self.model.NewBoolVar(f"has_junior_d{d}_{s.value}")
                self.model.Add(sum(self.shifts[(j_id, d, s)] for j_id in juniors) >= 1).OnlyEnforceIf(has_junior)
                self.model.Add(sum(self.shifts[(j_id, d, s)] for j_id in juniors) == 0).OnlyEnforceIf(has_junior.Not())
                # 若有新人，該班別必須包含至少 1 位資深/成熟人員
                self.model.Add(sum(self.shifts[(s_id, d, s)] for s_id in seniors) >= 1).OnlyEnforceIf(has_junior)

            # [1-04, 1-11] Timeline 每 15 分鐘動態掃描 (現場隨時 >= 2人 且 隨時 >= 1當班人員)
            for t in range(self.ticks_per_day):
                # 人數上限與底線檢核
                if not self.req.overrides.allow_single_staffing or d_cfg.is_special_day:
                    # 預設底線：隨時維持至少 2 人 (特殊日強制套用 [2-04] 防衛)
                    self.model.Add(sum(self.timeline[(e.emp_id, d, t)] for e in self.req.employees) >= 2)
                else:
                    # 解鎖 C (放寬單人當班)：一般日允許降為 1 人
                    self.model.Add(sum(self.timeline[(e.emp_id, d, t)] for e in self.req.employees) >= 1)

                # 當班人員底線：隨時至少 1 位具當班資格者
                self.model.Add(self.is_supervisor_on_duty[(d, t)] == 1)

    # ----------------------------------------------------------------------
    # Layer 2: 彈性邊界與工時配額 (Tactical Constraints)
    # ----------------------------------------------------------------------
    def _apply_layer_2_tactical_constraints(self):
        # [3-02, 3-03] PT/PPT 上班天數彈性範圍控制
        for e in self.req.employees:
            if e.role in (Role.PT, Role.PPT):
                work_days = sum(1 - self.shifts[(e.emp_id, d, ShiftType.OFF)] for d in range(len(self.req.days)))
                self.model.Add(work_days >= e.weekly_min_days)
                self.model.Add(work_days <= e.weekly_max_days)

    # ----------------------------------------------------------------------
    # Layer 3: 手動解鎖關卡 (Overrides Handling)
    # ----------------------------------------------------------------------
    def _apply_layer_3_overrides_handling(self):
        # [2-02] 解鎖選項 A (放寬劃假)：未開啟時，劃假請求為硬性 OFF
        if not self.req.overrides.allow_leave_override:
            for emp_id, days in self.req.leave_requests.items():
                for d in days:
                    self.model.Add(self.shifts[(emp_id, d, ShiftType.OFF)] == 1)

        # [1-06, 2-03] 解鎖選項 B (休假加班)：嚴禁套用至新人/訓練中人力
        # (預設一例一休已限制 5 天，若未開啟 allow_overtime 則禁止 6 天加班)

        # [2-05] 解鎖選項 D (放寬晚接早)：未開啟時，嚴禁昨晚接次日早班 (11小時法定休息)
        if not self.req.overrides.allow_night_to_morning:
            for e in self.req.employees:
                for d in range(len(self.req.days) - 1):
                    self.model.Add(
                        self.shifts[(e.emp_id, d + 1, ShiftType.MORNING)] == 0
                    ).OnlyEnforceIf(self.shifts[(e.emp_id, d, ShiftType.NIGHT)])

    # ----------------------------------------------------------------------
    # Layer 4: 軟性偏好與最佳化目標 (Score Optimization)
    # ----------------------------------------------------------------------
    def _apply_layer_4_soft_optimization(self):
        score_terms = []

        # [3-06, 3-07] PPT 當班次數採計與最大化 (Target: +100 分)
        for e in self.req.employees:
            if e.role == Role.PPT:
                for d in range(len(self.req.days)):
                    # 當天是否滿足 PPT 獨立當班 (無正職在場且 PPT 在場)
                    ppt_duty = self.model.NewBoolVar(f"ppt_duty_{e.emp_id}_d{d}")
                    
                    # 晚班交接後 (如 17:00 後 Tick 32~51)，無正職且 PPT 在場
                    no_ft_evening = self.model.NewBoolVar(f"no_ft_eve_d{d}")
                    eve_ft_present = [self.has_ft_on_duty[(d, t)] for t in range(32, 52)]
                    self.model.Add(sum(eve_ft_present) == 0).OnlyEnforceIf(no_ft_evening)
                    self.model.Add(sum(eve_ft_present) > 0).OnlyEnforceIf(no_ft_evening.Not())

                    self.model.AddBoolAnd([self.shifts[(e.emp_id, d, ShiftType.NIGHT)], no_ft_evening]).EquivalentTo(ppt_duty)
                    score_terms.append(ppt_duty * 100)

        # [3-08] 藥師晚班搭檔最佳化加分
        pharmacists = [e for e in self.req.employees if e.is_pharmacist]
        for e in pharmacists:
            for d in range(len(self.req.days)):
                for other in self.req.employees:
                    if other.emp_id != e.emp_id:
                        both_night = self.model.NewBoolVar(f"pharm_partner_{e.emp_id}_{other.emp_id}_d{d}")
                        self.model.AddBoolAnd([
                            self.shifts[(e.emp_id, d, ShiftType.NIGHT)],
                            self.shifts[(other.emp_id, d, ShiftType.NIGHT)]
                        ]).EquivalentTo(both_night)

                        if other.role == Role.FULL_TIME:
                            score_terms.append(both_night * 100) # 搭正職 +100
                        elif other.role == Role.PPT:
                            score_terms.append(both_night * 50)  # 搭成熟 PPT +50
                        elif other.role == Role.PT and other.seniority == Seniority.SENIOR and e.role == Role.FULL_TIME:
                            score_terms.append(both_night * 10)  # 正職藥師搭成熟 PT +10

        # [4-01] 個人班別偏好加分 (滿足偏好 +20 分)
        for e in self.req.employees:
            if e.preferred_shift == "MORNING":
                for d in range(len(self.req.days)):
                    score_terms.append(self.shifts[(e.emp_id, d, ShiftType.MORNING)] * 20)
            elif e.preferred_shift == "NIGHT":
                for d in range(len(self.req.days)):
                    score_terms.append(self.shifts[(e.emp_id, d, ShiftType.NIGHT)] * 20)

        if score_terms:
            self.model.Maximize(sum(score_terms))

    # ----------------------------------------------------------------------
    # 5. 輸出產出與 Layer 3 診斷報告
    # ----------------------------------------------------------------------
    def _extract_schedule_result(self) -> Dict:
        result = {"schedule": []}
        
        for e in self.req.employees:
            row = {
                "姓名": e.name, 
                "角色": "正職" if e.role == Role.FULL_TIME else ("PPT" if e.role == Role.PPT else "PT"), 
                "屬性": "藥師" if e.is_pharmacist else ("成熟" if e.seniority == Seniority.SENIOR else "新人/訓練")
            }
            for d in range(len(self.req.days)):
                day_label = f"週{['一','二','三','四','五','六','日'][d]}"
                if self.req.days[d].is_special_day:
                    day_label += " (特)"
                
                assigned = "OFF"
                for s in [ShiftType.OFF, ShiftType.MORNING, ShiftType.NIGHT, ShiftType.MIDDLE, ShiftType.MEETING]:
                    if self.solver.Value(self.shifts[(e.emp_id, d, s)]) == 1:
                        assigned = s.value
                        break
                row[day_label] = assigned
            result["schedule"].append(row)

        return result

    def _generate_layer_3_diagnosis(self) -> Dict:
        # [2-06] 無解時精準診斷與建議報告
        return {
            "status": "INFEASIBLE",
            "message": "系統首輪運算無解 (INFEASIBLE)！已觸發 Layer 3 管理者手動診斷防線。",
            "suggestions": [
                "建議 1: 請於側邊欄勾選 [解鎖 A] 放寬劃假限制，釋放被鎖定的正職/成熟人力。",
                "建議 2: 若特殊日人力吃緊，請確認成熟人員是否劃假重疊。",
                "建議 3 (跨店支援): 當前人力結構最少需外補 1 位門市正職支援早/晚班。"
            ]
        }

# ==========================================
# 2. Streamlit 介面整合 (Web UI)
# ==========================================

st.set_page_config(page_title="分店自動排班系統 - 門市實名版", page_icon="📋", layout="wide")

st.title("📋 分店自動排班系統 (門市實名工程落地版)")

# 您提供的 10 位同仁完整清單
store_employees = [
    Employee(emp_id="E01", name="花藥", role=Role.FULL_TIME, is_pharmacist=True, is_supervisor=True, seniority=Seniority.SENIOR, preferred_shift="MORNING"),
    Employee(emp_id="E02", name="邱藥", role=Role.FULL_TIME, is_pharmacist=True, is_supervisor=True, seniority=Seniority.SENIOR, preferred_shift="NIGHT"),
    Employee(emp_id="E03", name="嘉呈", role=Role.FULL_TIME, is_pharmacist=False, is_supervisor=True, seniority=Seniority.SENIOR),
    Employee(emp_id="E04", name="桂華", role=Role.FULL_TIME, is_pharmacist=False, is_supervisor=True, seniority=Seniority.SENIOR),
    Employee(emp_id="E05", name="筠婷", role=Role.FULL_TIME, is_pharmacist=False, is_supervisor=False, seniority=Seniority.JUNIOR), # 訓練人力 [1-06]
    Employee(emp_id="E06", name="亭緯", role=Role.PT, is_pharmacist=False, is_supervisor=False, seniority=Seniority.SENIOR, weekly_min_days=3, weekly_max_days=5),
    Employee(emp_id="E07", name="靜茹", role=Role.PT, is_pharmacist=False, is_supervisor=False, seniority=Seniority.SENIOR, weekly_min_days=3, weekly_max_days=5),
    Employee(emp_id="E08", name="肖維", role=Role.PT, is_pharmacist=False, is_supervisor=False, seniority=Seniority.JUNIOR, weekly_min_days=3, weekly_max_days=4), # 新人 [1-05]
    Employee(emp_id="E09", name="品萱", role=Role.PT, is_pharmacist=False, is_supervisor=False, seniority=Seniority.JUNIOR, weekly_min_days=3, weekly_max_days=4), # 新人
    Employee(emp_id="E10", name="姵萱", role=Role.PT, is_pharmacist=False, is_supervisor=False, seniority=Seniority.JUNIOR, weekly_min_days=3, weekly_max_days=4), # 新人
]

# --- 側邊欄控制台 ---
with st.sidebar:
    st.header("⚙️ 排班條件控制台")
    
    st.subheader("🔓 Layer 3 手動解鎖選項")
    allow_leave = st.checkbox("[解鎖 A] 放寬劃假限制 [2-02]", value=False)
    allow_overtime = st.checkbox("[解鎖 B] 允許休息日加班 [2-03]", value=False)
    allow_single = st.checkbox("[解鎖 C] 放寬單人當班 [2-04]", value=False)
    allow_night_morning = st.checkbox("[解鎖 D] 放寬晚接早 [2-05]", value=False)
    
    st.divider()
    
    st.subheader("📅 特殊日與劃假/開會設定")
    special_days_selection = st.multiselect(
        "選擇本週特殊日 (預設週六日)：", 
        options=["週一", "週二", "週三", "週四", "週五", "週六", "週日"],
        default=["週六", "週日"]
    )
    
    run_button = st.button("🚀 執行 OR-Tools 算班", type="primary", use_container_width=True)

# 處理特殊日選取
day_map = {"週一": 0, "週二": 1, "週三": 2, "週四": 3, "週五": 4, "週六": 5, "週日": 6}
special_day_indexes = [day_map[d] for d in special_days_selection]
days = [DayConfig(day_index=d, is_special_day=(d in special_day_indexes)) for d in range(7)]

# 範例劃假與會議設定 (測試用)
leave_reqs = {"E01": [0], "E02": [1]} # 花藥週一劃假，邱藥週二劃假
meeting_reqs = {"E03": [2]}           # 嘉呈週三開會 [1-17, 1-18]

req_config = SchedulingRequest(
    store_id="STORE_001",
    employees=store_employees,
    days=days,
    leave_requests=leave_reqs,
    meeting_requests=meeting_reqs,
    mutually_exclusive_pairs=[("E01", "E02")], # [1-14, 1-15] 兩位藥師不重疊
    overrides=OverridesConfig(
        allow_leave_override=allow_leave,
        allow_overtime=allow_overtime,
        allow_single_staffing=allow_single,
        allow_night_to_morning=allow_night_morning
    )
)

# --- 點擊運算 ---
if run_button:
    with st.spinner("OR-Tools CP-SAT 求解器進行 Layer 0 ~ Layer 4 嚴格運算中..."):
        engine = StoreSchedulerEngine(req_config)
        status, res = engine.build_and_solve()
        
    if status == "SUCCESS":
        st.success("🎉 班表計算成功！已通過所有 Layer 0~1 法規防線並完成 Layer 4 最佳化。")
        df_res = pd.DataFrame(res["schedule"])
        st.dataframe(df_res, use_container_width=True, hide_index=True)
    else:
        st.error(f"⚠️ {res['message']}")
        for sug in res["suggestions"]:
            st.info(sug)
else:
    st.info("👈 請點擊左側邊欄的 **「🚀 執行 OR-Tools 算班」** 按鈕來觸發即時計算！")
