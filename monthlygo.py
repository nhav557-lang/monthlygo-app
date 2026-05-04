import streamlit as st
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
import requests
import folium
from streamlit_folium import st_folium
import polyline
from datetime import datetime, timedelta  # Thêm timedelta để chỉnh múi giờ
from geopy.distance import geodesic
from streamlit_searchbox import st_searchbox
import matplotlib.pyplot as plt
import random
import time

# ==========================================
# KHỞI TẠO ĐƯỜNG DẪN LOGO LOCAL & CẤU HÌNH TRANG
# ==========================================
LOGO_PATH = "logo.jpg"

st.set_page_config(page_title="MonthlyGo - Đặt Xe & Gói Cước", page_icon="⏱️", layout="wide")

# ==========================================
# CSS NHUỘM MÀU THƯƠNG HIỆU & FIX LỖI DARK MODE
# ==========================================
st.markdown(f"""
<style>
    [data-testid="stSidebar"] {{ background-color: #F8F5FF; }}
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] span, 
    [data-testid="stSidebar"] div {{
        color: #4A148C !important;
    }}
    div.stButton > button[kind="primary"] {{
        background-color: #4A148C !important;
        color: white !important;
        border: 2px solid #4A148C !important;
        border-radius: 8px !important;
        font-weight: bold !important;
    }}
    div.stButton > button[kind="primary"]:hover {{
        background-color: #D48E15 !important; 
        border: 2px solid #D48E15 !important;
        color: white !important;
    }}
    h1, h2, h3 {{ color: #4A148C !important; }}
    div[data-testid="stMetricValue"] {{
        color: #D48E15 !important;
        font-weight: bold;
    }}
    .wallet-box {{
        border: 2px solid #D48E15; 
        padding: 15px; 
        border-radius: 12px; 
        background-color: #FFFAEC;
        text-align: center;
        box-shadow: 0px 4px 6px rgba(0,0,0,0.1);
    }}
</style>
""", unsafe_allow_html=True)

# ==========================================
# DANH SÁCH ĐỊA ĐIỂM NỔI BẬT
# ==========================================
QUICK_LOCATIONS = {
    " UEH Cơ sở A (Nguyễn Đình Chiểu)": (10.7828, 106.6946),
    " UEH Cơ sở B (Nguyễn Tri Phương)": (10.7731, 106.6697),
    " UEH Cơ sở C (Mạc Đĩnh Chi)": (10.7816, 106.6908),
    " UEH Cơ sở E (Trần Quang Khải)": (10.7801, 106.6876),
    " UEH Cơ sở N (Nguyễn Văn Linh)": (10.7130, 106.6784),
    " Sân bay Tân Sơn Nhất": (10.8185, 106.6660),
    "Dinh Độc Lập": (10.7770, 106.6953),
    " Thảo Cầm Viên": (10.7875, 106.7053),
    " Công viên Đầm Sen": (10.7675, 106.6384),
    " Đại Học Bách Khoa HCM": (10.7734, 106.6606),
    " Đại học Khoa học Tự nhiên HCM": (10.7631, 106.6823),
    " Đại học Công nghệ Thông tin UIT": (10.8700, 106.8031),
    " Hồ Gươm (Hà Nội)": (21.0285, 105.8523)
}

# ==========================================
# KHỞI TẠO SESSION STATE
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_name' not in st.session_state:
    st.session_state.user_name = ""
    st.session_state.is_demo = False 
    st.session_state.package = None
    st.session_state.is_trial = False 
    st.session_state.used_trials = [] 
    st.session_state.freq = 0
    st.session_state.point = 0
    st.session_state.urgency_base = 1
    st.session_state.loyalty_points_wallet = 0 
    st.session_state.demo_traffic = "Thông thoáng 🟢" 
    st.session_state.demo_weather = "Thực tế (API)"

MOCK_ACCOUNTS = {
    "Sinh Viên (Ít đi, Ngân sách thấp)": {"freq": 2, "point": 1, "urg": 1, "wallet": 15},
    "Dân Văn Phòng (Đi đều, Hay gấp)": {"freq": 6, "point": 5, "urg": 5, "wallet": 40},
    "Khách VIP Doanh Nhân (Giàu, Rất gấp)": {"freq": 10, "point": 10, "urg": 8, "wallet": 120}
}

def get_html_badge(pkg_name):
    if not pkg_name: return ""
    if "Eco" in pkg_name: return "<div style='background:#4CAF50; color:white; padding:4px 12px; border-radius:15px; font-weight:bold; font-size:12px; float:right; box-shadow: 0px 2px 5px rgba(0,0,0,0.2);'>🌱 GÓI SINH VIÊN (ECO)</div>"
    if "Đi Làm" in pkg_name: return "<div style='background:#2196F3; color:white; padding:4px 12px; border-radius:15px; font-weight:bold; font-size:12px; float:right; box-shadow: 0px 2px 5px rgba(0,0,0,0.2);'>💼 MEMBER ĐI LÀM</div>"
    if "Premium" in pkg_name: return "<div style='background:#9C27B0; color:white; padding:4px 12px; border-radius:15px; font-weight:bold; font-size:12px; float:right; box-shadow: 0px 2px 5px rgba(0,0,0,0.2);'>💎 VIP PREMIUM</div>"
    if "Doanh Nhân" in pkg_name: return "<div style='background:#D48E15; color:white; padding:4px 12px; border-radius:15px; font-weight:bold; font-size:12px; float:right; box-shadow: 0px 2px 5px rgba(0,0,0,0.2);'>👑 VVIP DOANH NHÂN</div>"
    return ""

# ==========================================
# 1. BỘ NÃO AI: 80 LUẬT KINH DOANH TỐI ƯU
# ==========================================
@st.cache_resource
def build_ai_brain():
    distance = ctrl.Antecedent(np.arange(0, 31, 1), 'distance')
    frequency = ctrl.Antecedent(np.arange(0, 11, 1), 'frequency') 
    peak_ratio = ctrl.Antecedent(np.arange(0, 101, 1), 'peak_ratio') 
    budget_flex = ctrl.Antecedent(np.arange(0, 11, 1), 'budget_flex') 
    weather = ctrl.Antecedent(np.arange(0, 11, 1), 'weather') 
    urgency_level = ctrl.Antecedent(np.arange(0, 11, 1), 'urgency_level') 
    point = ctrl.Antecedent(np.arange(0, 11, 1), 'point') 

    price = ctrl.Consequent(np.arange(200, 1001, 1), 'price')
    reward_pts = ctrl.Consequent(np.arange(1, 6, 1), 'reward_pts') 

    distance['short'] = fuzz.trimf(distance.universe, [0, 0, 10])
    distance['medium'] = fuzz.trimf(distance.universe, [5, 15, 25])
    distance['long'] = fuzz.trimf(distance.universe, [15, 30, 30])
    frequency['low'] = fuzz.trimf(frequency.universe, [0, 0, 3])
    frequency['regular'] = fuzz.trimf(frequency.universe, [2, 5, 8])
    frequency['high'] = fuzz.trimf(frequency.universe, [6, 10, 10])
    peak_ratio['clear'] = fuzz.trimf(peak_ratio.universe, [0, 0, 30])
    peak_ratio['moderate'] = fuzz.trimf(peak_ratio.universe, [20, 50, 80])
    peak_ratio['heavy'] = fuzz.trimf(peak_ratio.universe, [60, 100, 100])
    budget_flex['low'] = fuzz.trimf(budget_flex.universe, [0, 0, 4])
    budget_flex['medium'] = fuzz.trimf(budget_flex.universe, [3, 5, 7])
    budget_flex['high'] = fuzz.trimf(budget_flex.universe, [6, 10, 10])
    weather['good'] = fuzz.trimf(weather.universe, [0, 0, 3])
    weather['hot'] = fuzz.trimf(weather.universe, [2, 4, 6])
    weather['bad'] = fuzz.trimf(weather.universe, [5, 7, 9])
    weather['extreme'] = fuzz.trimf(weather.universe, [8, 10, 10])
    urgency_level['chill'] = fuzz.trimf(urgency_level.universe, [0, 0, 3])
    urgency_level['normal'] = fuzz.trimf(urgency_level.universe, [2, 5, 8])
    urgency_level['urgent'] = fuzz.trimf(urgency_level.universe, [7, 10, 10])
    point['newbie'] = fuzz.trimf(point.universe, [0, 0, 3])
    point['silver_gold'] = fuzz.trimf(point.universe, [2, 5, 8])
    point['vip'] = fuzz.trimf(point.universe, [7, 10, 10])

    price['eco200'] = fuzz.trimf(price.universe, [200, 200, 400])
    price['com400'] = fuzz.trimf(price.universe, [200, 400, 600])
    price['pre600'] = fuzz.trimf(price.universe, [400, 600, 800])
    price['vip800'] = fuzz.trimf(price.universe, [600, 800, 1000])
    
    reward_pts['x1'] = fuzz.trimf(reward_pts.universe, [1, 1, 2])
    reward_pts['x2'] = fuzz.trimf(reward_pts.universe, [1, 2, 3])
    reward_pts['x3'] = fuzz.trimf(reward_pts.universe, [2, 3, 4])
    reward_pts['x5'] = fuzz.trimf(reward_pts.universe, [4, 5, 5])

    rules = [
        # NHÓM 1: CƠ BẢN
        ctrl.Rule(budget_flex['low'] & distance['short'], (price['eco200'], reward_pts['x2'])),
        ctrl.Rule(budget_flex['low'] & distance['medium'], (price['eco200'], reward_pts['x3'])),
        ctrl.Rule(budget_flex['low'] & distance['long'], (price['com400'], reward_pts['x5'])),
        ctrl.Rule(budget_flex['medium'] & distance['short'], (price['eco200'], reward_pts['x1'])),
        ctrl.Rule(budget_flex['medium'] & distance['medium'], (price['com400'], reward_pts['x2'])),
        ctrl.Rule(budget_flex['medium'] & distance['long'], (price['pre600'], reward_pts['x3'])),
        ctrl.Rule(budget_flex['high'] & distance['short'], (price['com400'], reward_pts['x1'])),
        ctrl.Rule(budget_flex['high'] & distance['medium'], (price['pre600'], reward_pts['x2'])),
        ctrl.Rule(budget_flex['high'] & distance['long'], (price['vip800'], reward_pts['x3'])),
        ctrl.Rule(point['newbie'] & frequency['low'], (price['eco200'], reward_pts['x1'])),
        ctrl.Rule(point['newbie'] & frequency['regular'], (price['eco200'], reward_pts['x3'])),
        ctrl.Rule(point['newbie'] & frequency['high'], (price['com400'], reward_pts['x5'])),
        ctrl.Rule(point['silver_gold'] & frequency['low'], (price['eco200'], reward_pts['x2'])),
        ctrl.Rule(point['silver_gold'] & frequency['regular'], (price['com400'], reward_pts['x2'])),
        ctrl.Rule(point['silver_gold'] & frequency['high'], (price['com400'], reward_pts['x3'])),
        ctrl.Rule(point['vip'] & frequency['low'], (price['pre600'], reward_pts['x1'])),
        ctrl.Rule(point['vip'] & frequency['regular'], (price['pre600'], reward_pts['x2'])),
        ctrl.Rule(point['vip'] & frequency['high'], (price['vip800'], reward_pts['x3'])),
        ctrl.Rule(frequency['high'] & budget_flex['low'], (price['eco200'], reward_pts['x5'])),
        ctrl.Rule(frequency['high'] & budget_flex['high'], (price['vip800'], reward_pts['x3'])),
        # NHÓM 2: HỎA TỐC
        ctrl.Rule(urgency_level['urgent'] & budget_flex['low'] & distance['short'], (price['eco200'], reward_pts['x5'])),
        ctrl.Rule(urgency_level['urgent'] & budget_flex['low'] & distance['medium'], (price['com400'], reward_pts['x5'])),
        ctrl.Rule(urgency_level['urgent'] & budget_flex['low'] & distance['long'], (price['com400'], reward_pts['x5'])),
        ctrl.Rule(urgency_level['urgent'] & budget_flex['medium'] & distance['short'], (price['com400'], reward_pts['x3'])),
        ctrl.Rule(urgency_level['urgent'] & budget_flex['medium'] & distance['medium'], (price['pre600'], reward_pts['x3'])),
        ctrl.Rule(urgency_level['urgent'] & budget_flex['medium'] & distance['long'], (price['pre600'], reward_pts['x5'])),
        ctrl.Rule(urgency_level['urgent'] & budget_flex['high'], (price['vip800'], reward_pts['x3'])),
        ctrl.Rule(urgency_level['urgent'] & point['vip'], (price['vip800'], reward_pts['x2'])),
        ctrl.Rule(urgency_level['urgent'] & point['newbie'], (price['com400'], reward_pts['x5'])),
        ctrl.Rule(urgency_level['urgent'] & point['silver_gold'], (price['pre600'], reward_pts['x3'])),
        ctrl.Rule(urgency_level['chill'] & budget_flex['low'], (price['eco200'], reward_pts['x1'])),
        ctrl.Rule(urgency_level['chill'] & budget_flex['medium'], (price['eco200'], reward_pts['x2'])),
        ctrl.Rule(urgency_level['chill'] & budget_flex['high'], (price['com400'], reward_pts['x1'])),
        ctrl.Rule(urgency_level['chill'] & point['vip'], (price['pre600'], reward_pts['x1'])),
        ctrl.Rule(urgency_level['normal'] & distance['short'], (price['eco200'], reward_pts['x1'])),
        ctrl.Rule(urgency_level['normal'] & distance['medium'], (price['com400'], reward_pts['x2'])),
        ctrl.Rule(urgency_level['normal'] & distance['long'], (price['pre600'], reward_pts['x3'])),
        ctrl.Rule(urgency_level['urgent'] & weather['good'], (price['com400'], reward_pts['x3'])),
        ctrl.Rule(urgency_level['urgent'] & peak_ratio['clear'], (price['com400'], reward_pts['x2'])),
        ctrl.Rule(urgency_level['chill'] & peak_ratio['heavy'], (price['eco200'], reward_pts['x3'])),
        # NHÓM 3: THỜI TIẾT & KẸT XE
        ctrl.Rule(weather['extreme'] & budget_flex['low'], (price['com400'], reward_pts['x5'])),
        ctrl.Rule(weather['extreme'] & budget_flex['medium'], (price['pre600'], reward_pts['x5'])),
        ctrl.Rule(weather['extreme'] & budget_flex['high'], (price['vip800'], reward_pts['x3'])),
        ctrl.Rule(weather['extreme'] & point['vip'], (price['vip800'], reward_pts['x5'])),
        ctrl.Rule(weather['bad'] & budget_flex['low'], (price['eco200'], reward_pts['x3'])),
        ctrl.Rule(weather['bad'] & budget_flex['medium'], (price['com400'], reward_pts['x3'])),
        ctrl.Rule(weather['bad'] & budget_flex['high'], (price['pre600'], reward_pts['x2'])),
        ctrl.Rule(weather['hot'] & distance['long'] & budget_flex['low'], (price['com400'], reward_pts['x5'])),
        ctrl.Rule(weather['hot'] & distance['long'] & budget_flex['medium'], (price['pre600'], reward_pts['x3'])),
        ctrl.Rule(weather['hot'] & distance['short'], (price['eco200'], reward_pts['x2'])),
        ctrl.Rule(peak_ratio['heavy'] & budget_flex['low'], (price['eco200'], reward_pts['x5'])),
        ctrl.Rule(peak_ratio['heavy'] & budget_flex['medium'], (price['com400'], reward_pts['x3'])),
        ctrl.Rule(peak_ratio['heavy'] & budget_flex['high'], (price['vip800'], reward_pts['x2'])),
        ctrl.Rule(peak_ratio['heavy'] & point['vip'], (price['vip800'], reward_pts['x5'])),
        ctrl.Rule(peak_ratio['moderate'] & distance['medium'], (price['com400'], reward_pts['x2'])),
        ctrl.Rule(peak_ratio['moderate'] & distance['long'], (price['pre600'], reward_pts['x3'])),
        ctrl.Rule(peak_ratio['clear'] & budget_flex['medium'], (price['eco200'], reward_pts['x1'])),
        ctrl.Rule(peak_ratio['clear'] & budget_flex['high'], (price['com400'], reward_pts['x1'])),
        ctrl.Rule(weather['bad'] & peak_ratio['heavy'] & budget_flex['low'], (price['com400'], reward_pts['x5'])),
        ctrl.Rule(weather['extreme'] & peak_ratio['heavy'], (price['vip800'], reward_pts['x5'])),
        # NHÓM 4: CHUẨN HÓA
        ctrl.Rule(distance['short'] & frequency['low'] & weather['good'], (price['eco200'], reward_pts['x1'])),
        ctrl.Rule(distance['long'] & frequency['high'] & weather['bad'], (price['pre600'], reward_pts['x5'])),
        ctrl.Rule(urgency_level['chill'] & point['newbie'] & distance['short'], (price['eco200'], reward_pts['x1'])),
        ctrl.Rule(urgency_level['urgent'] & point['vip'] & distance['long'], (price['vip800'], reward_pts['x5'])),
        ctrl.Rule(budget_flex['low'] & point['vip'], (price['com400'], reward_pts['x2'])),
        ctrl.Rule(budget_flex['high'] & point['newbie'], (price['pre600'], reward_pts['x3'])),
        ctrl.Rule(weather['hot'] & peak_ratio['clear'] & urgency_level['chill'], (price['eco200'], reward_pts['x1'])),
        ctrl.Rule(weather['good'] & peak_ratio['heavy'] & urgency_level['urgent'], (price['com400'], reward_pts['x3'])),
        ctrl.Rule(distance['medium'] & frequency['regular'] & point['silver_gold'], (price['com400'], reward_pts['x2'])),
        ctrl.Rule(distance['short'] & weather['bad'] & urgency_level['urgent'], (price['com400'], reward_pts['x5'])),
        ctrl.Rule(distance['long'] & peak_ratio['heavy'] & budget_flex['low'], (price['com400'], reward_pts['x5'])),
        ctrl.Rule(frequency['high'] & weather['extreme'] & point['silver_gold'], (price['pre600'], reward_pts['x5'])),
        ctrl.Rule(point['vip'] & weather['good'] & peak_ratio['clear'], (price['pre600'], reward_pts['x1'])),
        ctrl.Rule(point['newbie'] & weather['extreme'] & urgency_level['urgent'], (price['pre600'], reward_pts['x5'])),
        ctrl.Rule(budget_flex['medium'] & distance['short'] & peak_ratio['heavy'], (price['eco200'], reward_pts['x3'])),
        ctrl.Rule(budget_flex['high'] & distance['medium'] & weather['hot'], (price['pre600'], reward_pts['x2'])),
        ctrl.Rule(frequency['low'] & distance['long'] & peak_ratio['moderate'], (price['pre600'], reward_pts['x2'])),
        ctrl.Rule(urgency_level['normal'] & point['silver_gold'] & weather['bad'], (price['com400'], reward_pts['x3'])),
        ctrl.Rule(peak_ratio['clear'] & distance['short'] & budget_flex['high'], (price['com400'], reward_pts['x1'])),
        ctrl.Rule(weather['hot'] & budget_flex['low'] & point['newbie'], (price['eco200'], reward_pts['x2']))
    ]
    return ctrl.ControlSystem(rules)

sub_ctrl = build_ai_brain()
subscription = ctrl.ControlSystemSimulation(sub_ctrl)

# ==========================================
# 2. XỬ LÝ API
# ==========================================
def search_address(search_term: str):
    if not search_term or len(search_term) < 3: return []
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={search_term}&format=json&countrycodes=vn&limit=5"
        res = requests.get(url, headers={'User-Agent': 'ueh_ai_project'}, timeout=5).json()
        return [(p['display_name'], (float(p['lat']), float(p['lon']))) for p in res]
    except: return []

def get_route(start, end):
    fallback_dist = geodesic(start, end).km * 1.3
    try:
        url = f"http://router.project-osrm.org/route/v1/driving/{start[1]},{start[0]};{end[1]},{end[0]}?overview=full&geometries=polyline"
        res = requests.get(url).json()
        if res.get("code") == "Ok":
            dist_km = res["routes"][0]["distance"]/1000.0
            duration_min = res["routes"][0]["duration"] / 60.0
            path = polyline.decode(res["routes"][0]["geometry"])
            return dist_km, duration_min, path
    except: pass
    return fallback_dist, fallback_dist * 2.5, [start, end]

def get_real_weather(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        res = requests.get(url, timeout=5).json()
        temp = res['current_weather']['temperature']
        code = res['current_weather']['weathercode']
        if code in [65, 67, 82, 95, 96, 99]: 
            return 10, f"Mưa rất to/Bão ({temp}°C)"
        elif temp >= 32:
            return 4, f"Trời Nắng Nóng  ({temp}°C)"
        elif code in [51, 53, 55, 61, 63, 80, 81]: 
            return 8, f"Có Mưa  ({temp}°C)"
        else: 
            return 1, f"Trời Đẹp  ({temp}°C)"
    except: return 1, "Chưa xác định (25°C)"

def get_package_info(price_val):
    if price_val <= 300: 
        return "Gói Eco", "🎓 **Gói Sinh Viên Eco - Trợ giá tối đa:**\n- 💸 **Miễn phí 100%** các cuốc XE MÁY ngắn dưới 5km.\n- 🛡️ Khóa giá cố định, không bị x2 x3 cước vào giờ kẹt xe.\n- ⚡ **Hỗ trợ 50% Phụ phí Hỏa Tốc** dành riêng cho sinh viên."
    elif price_val <= 500: 
        return "Gói Đi Làm", "💼 **Gói Đi Làm - Chấp mọi thời tiết:**\n- ☔ Mưa to? **Nâng cấp Ô-tô tính tiền theo giá Xe Máy**!\n- 🚦 Miễn trừ toàn bộ phụ phí kẹt xe.\n- ⚡ **Hỗ trợ 50% Phụ phí Hỏa Tốc** cho người đi làm."
    elif price_val <= 700: 
        return "Gói Premium", "👨‍👩‍👧 **Gói Premium Gia Đình - Tiện nghi & Ưu tiên:**\n- 🚙 Điều phối độc quyền các dòng xe rộng rãi (Ô-tô 4/7 chỗ VIP).\n- ⚡ **Miễn phí 100% Cước Hỏa Tốc**, tài xế ưu tiên đón mọi lúc."
    else: 
        return "Gói Doanh Nhân", "👑 **Gói VVIP Doanh Nhân - Quyền Lực Tối Thượng:**\n- 💳 **0đ cho mọi chuyến đi!** Chỉ cần lên xe, hệ thống lo phần còn lại.\n- 🤵 Tài xế Elite phục vụ riêng biệt 24/7."

ALL_PACKAGES = ["Gói Eco", "Gói Đi Làm", "Gói Premium", "Gói Doanh Nhân"]

# ==========================================
# 3. MÀN HÌNH ĐĂNG NHẬP
# ==========================================
if not st.session_state.logged_in:
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        st.image(LOGO_PATH, use_container_width=True)
    st.markdown("<h1 style='text-align: center;'>Chào mừng đến với MonthlyGo</h1>", unsafe_allow_html=True)
    st.write("---")
    tab1, tab2 = st.tabs(["👤 Đăng nhập Khách Mới", "🎭 Đăng nhập Tài khoản Demo"])
    with tab1:
        user_input = st.text_input("Tên của bạn:", key="new_user_input", placeholder="VD: Thanh Nhã...")
        if st.button("🚀 Bắt Đầu Ngay (Khách thật)", type="primary"):
            if user_input.strip() == "": st.error("Vui lòng nhập tên!")
            else:
                st.session_state.logged_in = True
                st.session_state.user_name = user_input
                st.session_state.demo_weather = "Thực tế (API)" 
                st.rerun()
    with tab2:
        mock_choice = st.selectbox("Chọn Hồ sơ Giả lập:", list(MOCK_ACCOUNTS.keys()))
        if st.button(" Chạy Demo App"):
            st.session_state.logged_in = True
            st.session_state.is_demo = True 
            st.session_state.user_name = mock_choice.split(" (")[0]
            acc = MOCK_ACCOUNTS[mock_choice]
            st.session_state.freq, st.session_state.point, st.session_state.urgency_base, st.session_state.loyalty_points_wallet = acc["freq"], acc["point"], acc["urg"], acc["wallet"]
            st.session_state.demo_weather = "Thực tế (API)"
            st.rerun()
    st.stop() 

# ==========================================
# 4. GIAO DIỆN CHÍNH
# ==========================================
col_h1, col_h2 = st.columns([1, 15])
with col_h1: st.image(LOGO_PATH, width=60)
with col_h2: st.title("MonthlyGo - Tiết kiệm thời gian, Tối ưu chi phí")

# SIDEBAR
with st.sidebar:
    st.image(LOGO_PATH, use_container_width=True)
    with st.expander("🛰️ ĐIỀU KHIỂN VỆ TINH", expanded=True):
        st.session_state.demo_traffic = st.selectbox("🚦 Ép Kẹt xe:", ["Thông thoáng 🟢", "Ùn ứ 🟡", "Kẹt Cứng 🔴"])
    if st.session_state.is_demo:
        with st.expander("🛠️ ADMIN PANEL", expanded=True):
            st.session_state.demo_weather = st.selectbox("⛅ Ép Thời tiết Demo:", ["Thực tế (API)", "Trời đẹp ", "Trời Nắng Nóng ", "Có Mưa ", "Mưa Bão Cực Đoan "])
            st.session_state.freq = st.slider("Tần suất đi:", 0, 10, st.session_state.freq)
            st.session_state.point = st.slider("Điểm Loyalty:", 0, 10, st.session_state.point)
            force_pkg = st.selectbox("Bơm trực tiếp Gói:", ["-- Chọn gói --"] + ALL_PACKAGES)
            if st.button("💉 Bơm Gói"):
                if force_pkg != "-- Chọn gói --":
                    st.session_state.package = force_pkg
                    st.toast(f"Đã bơm {force_pkg}!")
                    st.rerun()
    if st.button("🔴 Đăng xuất"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

# KHÁCH HÀNG & VÍ
st.markdown("<hr style='border: 2px solid #E6E6FA;'/>", unsafe_allow_html=True)
col_n, col_b = st.columns([3, 1])
col_n.markdown(f"### 👤 Xin chào, **{st.session_state.user_name}**")
col_b.markdown(get_html_badge(st.session_state.package), unsafe_allow_html=True)

col_p, col_w = st.columns(2)
with col_p:
    if st.session_state.package:
        st.success(f"Gói của bạn: **{st.session_state.package}**")
        if st.button("❌ Hủy Gói"):
            st.session_state.package = None
            st.rerun()
    else: st.info("💡 Bạn chưa đăng ký gói cước nào.")
with col_w:
    st.markdown(f"<div class='wallet-box'><h4>🌟 Ví Điểm: <span style='font-size:28px;'>{st.session_state.loyalty_points_wallet}</span></h4></div>", unsafe_allow_html=True)

# ĐẶT CHUYẾN
st.subheader("📍 Đặt xe cùng MonthlyGo")
c1, c2 = st.columns([1, 1.5])
with c1:
    # --- FIX GIỜ VIỆT NAM TẠI ĐÂY ---
    vn_time = datetime.now() + timedelta(hours=7)
    st.metric("🕒 Giờ Việt Nam", vn_time.strftime('%H:%M'))
    
    s_c = st.selectbox("📍 Điểm Đón:", [" Tự nhập"] + list(QUICK_LOCATIONS.keys()), key="sq")
    s_l = QUICK_LOCATIONS[s_c] if s_c != " Tự nhập" else st_searchbox(search_address, key="s")
    
    w_v, w_tx = 1, "Chờ GPS..."
    if s_l:
        if st.session_state.demo_weather == "Thực tế (API)": w_v, w_tx = get_real_weather(s_l[0], s_l[1])
        elif st.session_state.demo_weather == "Trời đẹp ": w_v, w_tx = 1, "Trời đẹp "
        elif st.session_state.demo_weather == "Trời Nắng Nóng ": w_v, w_tx = 4, "Trời Nắng Nóng "
        elif st.session_state.demo_weather == "Có Mưa ": w_v, w_tx = 8, "Có Mưa ☔"
        else: w_v, w_tx = 10, "Mưa Bão "
    st.metric("🌦️ Thời tiết", w_tx)

    e_c = st.selectbox("🏁 Điểm Đến:", [" Tự nhập"] + list(QUICK_LOCATIONS.keys()), key="eq")
    e_l = QUICK_LOCATIONS[e_c] if e_c != " Tự nhập" else st_searchbox(search_address, key="e")
    
    veh_dict = {"🏍️ Xe Máy Thường": {"rate": 6000, "budget": 2}, "🚗 Ô tô 4 Chỗ": {"rate": 12000, "budget": 5}}
    u_v = st.selectbox("Phương tiện:", list(veh_dict.keys()))
    is_u = st.checkbox("⚡ Đặt Hỏa Tốc")
    km, path = 0.0, []
    if s_l and e_l: km, _, path = get_route(s_l, e_l)

with c2:
    m = folium.Map(location=[10.7626, 106.6601], zoom_start=13)
    if s_l: folium.Marker(s_l, icon=folium.Icon(color='green')).add_to(m)
    if e_l: folium.Marker(e_l, icon=folium.Icon(color='red')).add_to(m)
    if path: folium.PolyLine(path, color="purple", weight=5).add_to(m); m.fit_bounds([s_l, e_l])
    st_folium(m, width="100%", height=400)

if km > 0:
    st.markdown("---")
    can_b = True
    if "Xe Máy" in u_v and w_v >= 10: st.error("⛈️ Bão cực đoan, ngưng xe máy!"); can_b = False
    if can_b:
        p_v = 10 if "Thông" in st.session_state.demo_traffic else 90
        subscription.input['distance'], subscription.input['frequency'], subscription.input['peak_ratio'], subscription.input['budget_flex'], subscription.input['weather'], subscription.input['urgency_level'], subscription.input['point'] = min(km, 30), st.session_state.freq, p_v, veh_dict[u_v]["budget"], w_v, (10 if is_u else 1), st.session_state.point
        subscription.compute()
        o_p, o_pts = subscription.output['price'], subscription.output['reward_pts']
        pkg_n, pkg_d = get_package_info(o_p)
        f_p = km * veh_dict[u_v]["rate"] * (1.4 if is_u else 1.0)
        
        if st.session_state.package:
            if st.session_state.package == "Gói Doanh Nhân": f_p = 0
            elif st.session_state.package == "Gói Đi Làm" and "Ô tô" in u_v and w_v >= 7: f_p = km * 6000
            elif st.session_state.package == "Gói Eco" and "Xe Máy" in u_v and km < 5: f_p = 0

        st.metric("💳 THANH TOÁN:", f"{int(f_p):,} VNĐ")
        if st.button("🚕 ĐẶT XE", type="primary"):
            st.session_state.loyalty_points_wallet += (int(o_pts) if f_p > 0 else 0)
            st.balloons(); st.success("Xong!"); time.sleep(1); st.rerun()

        st.subheader(" Gợi ý gói cước")
        if not st.session_state.package: st.success(f"🤖 Gợi ý: **{pkg_n}**\n\n{pkg_d}")
