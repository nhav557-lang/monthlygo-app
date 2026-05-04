import streamlit as st
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
import requests
import folium
from streamlit_folium import st_folium
import polyline
from datetime import datetime
from geopy.distance import geodesic
from streamlit_searchbox import st_searchbox
import matplotlib.pyplot as plt
import random
import time


LOGO_PATH = "logo.jpg"

st.set_page_config(page_title="MonthlyGo - Đặt Xe & Gói Cước", page_icon="⏱️", layout="wide")

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

QUICK_LOCATIONS = {
    " UEH Cơ sở A (Nguyễn Đình Chiểu)": (10.7828, 106.6946),
    " UEH Cơ sở B (Nguyễn Tri Phương)": (10.7731, 106.6697),
    " UEH Cơ sở C (Mạc Đĩnh Chi)": (10.7816, 106.6908),
    " UEH Cơ sở E (Trần Quang Khải)": (10.7801, 106.6876),
    " UEH Cơ sở N (Nguyễn Văn Linh)": (10.7130, 106.6784),
    " Sân bay Tân Sơn Nhất": (10.8185, 106.6660),
    " Dinh Độc Lập": (10.7770, 106.6953),
    " Thảo Cầm Viên": (10.7875, 106.7053),
    "Công viên Đầm Sen": (10.7675, 106.6384),
    " Đại Học Bách Khoa HCM": (10.7734, 106.6606),
    " Đại học Khoa học Tự nhiên HCM": (10.7631, 106.6823),
    " Đại học Công nghệ Thông tin UIT": (10.8700, 106.8031),
    " Hồ Gươm (Hà Nội)": (21.0285, 105.8523)
}


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
        # Cơ bản
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

        #  Hỏa tốc
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

        # Thời tiết và kẹt xe
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

        #TH Đặc biệt
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
            return 10, f"Mưa rất to/Bão ⛈️ ({temp}°C)"
        elif code in [51, 53, 55, 61, 63, 80, 81]: 
            return 8, f"Có Mưa ☔ ({temp}°C)" 
       
        else: 
            if temp >= 32:
                return 4, f"Trời Nắng Nóng 🥵 ({temp}°C)" 
            else:
                return 1, f"Trời Đẹp ☀️ ({temp}°C)"
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

if not st.session_state.logged_in:
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        st.image(LOGO_PATH, use_container_width=True)
    
    st.markdown("<h1 style='text-align: center;'>Chào mừng đến với MonthlyGo</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Giải pháp di chuyển thông minh bằng Gói cước AI</p>", unsafe_allow_html=True)
    st.write("---")

    tab1, tab2 = st.tabs(["👤 Đăng nhập Khách Mới (Thực tế)", "🎭 Đăng nhập Tài khoản Demo (Test)"])
    
    with tab1:
        st.info("Trải nghiệm luồng Khách hàng. Các thông số sẽ bị ẩn, chỉ hiển thị UI thân thiện.")
        user_input = st.text_input("Tên của bạn:", key="new_user_input", placeholder="VD: Thanh Nhã...")
        if st.button(" Bắt Đầu Ngay (Khách thật)", type="primary"):
            if user_input.strip() == "": st.error("Vui lòng nhập tên!")
            else:
                st.session_state.logged_in = True
                st.session_state.is_demo = False 
                st.session_state.user_name = user_input
                st.session_state.freq = 0
                st.session_state.point = 0
                st.session_state.urgency_base = 1
                st.session_state.loyalty_points_wallet = 0
                st.session_state.demo_traffic = "Thông thoáng 🟢"
                st.session_state.demo_weather = "Thực tế (API)" 
                st.rerun()
                
    with tab2:
        st.info("Dành cho Developer: Bật khóa công cụ ép giá, ép thời tiết, ép gói cước bên Sidebar.")
        mock_choice = st.selectbox("Chọn Hồ sơ Giả lập:", list(MOCK_ACCOUNTS.keys()))
        if st.button(" Chạy Demo App"):
            st.session_state.logged_in = True
            st.session_state.is_demo = True 
            st.session_state.user_name = mock_choice.split(" (")[0]
            acc = MOCK_ACCOUNTS[mock_choice]
            st.session_state.freq = acc["freq"]
            st.session_state.point = acc["point"]
            st.session_state.urgency_base = acc["urg"]
            st.session_state.loyalty_points_wallet = acc["wallet"]
            st.session_state.demo_traffic = "Thông thoáng 🟢"
            st.session_state.demo_weather = "Thực tế (API)"
            st.rerun()
    st.stop() 


col_h1, col_h2 = st.columns([1, 15])
with col_h1:
    st.image(LOGO_PATH, width=60)
with col_h2:
    st.title("MonthlyGo - Tiết kiệm thời gian, Tối ưu chi phí")


with st.sidebar:
    st.image(LOGO_PATH, use_container_width=True)
    st.markdown("<h2 style='text-align:center;'>Bảng Điều Khiển</h2>", unsafe_allow_html=True)
    
    with st.expander("🛰️ ĐIỀU KHIỂN VỆ TINH (Presenter)", expanded=True):
        st.caption("Chỉnh thông số trước, Khách chọn đường xong mới thấy:")
        st.session_state.demo_traffic = st.selectbox(" Tình trạng giao thông:", ["Thông thoáng 🟢", "Ùn ứ 🟡", "Kẹt Cứng 🔴"])
        
    if st.session_state.is_demo:
        with st.expander("🛠️ ADMIN PANEL (Ép Profile/Gói/Thời Tiết)", expanded=True):
            st.session_state.demo_weather = st.selectbox("⛅ Ép Thời tiết Demo:", [
                "Thực tế (API)", 
                "Trời đẹp ☀️", 
                "Trời Nắng Nóng 🥵", 
                "Có Mưa ☔", 
                "Mưa Bão Cực Đoan ⛈️"
            ])
            st.markdown("---")
            st.caption("Ép Profile Khách hàng:")
            st.session_state.freq = st.slider("Tần suất đi:", 0, 10, st.session_state.freq)
            st.session_state.point = st.slider("Điểm Loyalty:", 0, 10, st.session_state.point)
            st.markdown("---")
            force_pkg = st.selectbox("Bơm trực tiếp Gói:", ["-- Chọn gói --"] + ALL_PACKAGES)
            if st.button(" Bơm Gói (Dev Test)"):
                if force_pkg != "-- Chọn gói --":
                    st.session_state.package = force_pkg
                    st.session_state.is_trial = False
                    st.toast(f"Đã bơm {force_pkg} thành công!")
                    st.rerun()
    
    if st.button("🔴 Đăng xuất MonthlyGo"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

st.markdown("<hr style='border: 2px solid #E6E6FA;'/>", unsafe_allow_html=True)

col_name, col_badge = st.columns([3, 1])
with col_name:
    st.markdown(f"### 👤 Xin chào, **{st.session_state.user_name}**")
with col_badge:
    html_badge = get_html_badge(st.session_state.package)
    st.markdown(html_badge, unsafe_allow_html=True)

col_pkg, col_wallet = st.columns(2)
with col_pkg:
    if st.session_state.package:
        if st.session_state.is_trial:
            st.success(f"🎟️ Đang dùng thử: **{st.session_state.package}** (Chỉ áp dụng 1 cuốc xe)")
        else:
            st.success(f" Gói của bạn: **{st.session_state.package}** (Đặc quyền Không giới hạn)")
            
        if st.button("❌ Hủy Gói / Đổi Gói Khác"):
            st.session_state.package = None
            st.session_state.is_trial = False 
            st.toast("Đã hủy gói cước. Bạn có thể chọn mua gói khác!", icon="🗑️")
            st.rerun()
    else:
        st.info("💡 Trạng thái: Bạn hiện **CHƯA ĐĂNG KÝ** gói cước nào.")

with col_wallet:
    st.markdown(f"<div class='wallet-box'>"
                f"<h4 style='margin:0; color:#4A148C;'>🌟 Ví Điểm Thưởng: <span style='color:#D48E15; font-size:28px;'>{st.session_state.loyalty_points_wallet}</span></h4>"
                f"</div>", unsafe_allow_html=True)
    
    with st.expander("Cửa hàng Quy đổi Điểm thưởng"):
        st.write("Tích lũy điểm sau mỗi chuyến đi để đổi phần quà:")
        st.write("- **50 Điểm:** 🎫 Mã giảm giá 20% (Tối đa 50k)")
        st.write("- **100 Điểm:** 🚕 01 Cuốc xe dưới 5km giá 0đ")
        st.write("- **200 Điểm:** 💎 Trải nghiệm Premium 1 ngày")
        if st.session_state.loyalty_points_wallet >= 50:
            if st.button("👉 Đổi Mã Giảm Giá (Trừ 50đ)"):
                st.session_state.loyalty_points_wallet -= 50
                st.toast("Đổi mã thành công! Mã ưu đãi đã được lưu vào ví.", icon="🎟️")
                st.rerun()

st.markdown("<hr style='border: 2px solid #E6E6FA;'/>", unsafe_allow_html=True)

st.subheader("📍 Đặt xe cùng MonthlyGo")
c_map1, c_map2 = st.columns([1, 1.5])

with c_map1:
    col_t, col_w = st.columns(2)
    col_t.metric("🕒 Giờ hệ thống", datetime.now().strftime('%H:%M'))
    
    start_choice = st.selectbox("📍 Chọn nhanh Điểm Đón:", ["🗺️ Tự nhập địa chỉ (Tìm kiếm)"] + list(QUICK_LOCATIONS.keys()), key="start_quick")
    if start_choice == "🗺️ Tự nhập địa chỉ (Tìm kiếm)":
        start_loc = st_searchbox(search_address, key="start", placeholder="Nhập địa chỉ điểm đón...")
    else:
        start_loc = QUICK_LOCATIONS[start_choice]

    w_val, w_text = 1, "Đang chờ GPS..."
    if start_loc:
        if st.session_state.demo_weather == "Thực tế (API)":
            w_val, w_text = get_real_weather(start_loc[0], start_loc[1])
        elif st.session_state.demo_weather == "Trời đẹp ☀️":
            w_val, w_text = 1, "Trời đẹp ☀️ (Giả lập Demo)"
        elif st.session_state.demo_weather == "Trời Nắng Nóng 🥵":
            w_val, w_text = 4, "Trời Nắng Nóng 🥵 (Giả lập Demo)"
        elif st.session_state.demo_weather == "Có Mưa ☔":
            w_val, w_text = 8, "Có Mưa ☔ (Giả lập Demo)"
        else:
            w_val, w_text = 10, "Mưa Bão Cực Đoan ⛈️ (Giả lập Demo)"
            
    col_w.metric("🌦️ Thời tiết", w_text)

    st.markdown("<br>", unsafe_allow_html=True)
    
    end_choice = st.selectbox("🏁 Chọn nhanh Điểm Đến:", [" Tự nhập địa chỉ (Tìm kiếm)"] + list(QUICK_LOCATIONS.keys()), key="end_quick")
    if end_choice == " Tự nhập địa chỉ (Tìm kiếm)":
        end_loc = st_searchbox(search_address, key="end", placeholder="Nhập địa chỉ điểm đến...")
    else:
        end_loc = QUICK_LOCATIONS[end_choice]
    
    if st.button("🔄 Làm mới / Xóa Lộ trình"):
        if "start" in st.session_state: del st.session_state["start"]
        if "end" in st.session_state: del st.session_state["end"]
        if "start_quick" in st.session_state: del st.session_state["start_quick"]
        if "end_quick" in st.session_state: del st.session_state["end_quick"]
        st.rerun()
    
    veh_dict = {
        " Xe Máy Thường": {"rate": 6000, "budget": 2},
        " Xe Máy VIP": {"rate": 8000, "budget": 4},
        " Ô tô 4 Chỗ Thường": {"rate": 12000, "budget": 5},
        " Ô tô 4 Chỗ VIP": {"rate": 16000, "budget": 8},
        " Ô tô 7 Chỗ": {"rate": 15000, "budget": 7},
        "Ô tô 7 Chỗ VIP": {"rate": 20000, "budget": 10}
    }
    user_veh = st.selectbox("Chọn phương tiện:", list(veh_dict.keys()))
    base_rate = veh_dict[user_veh]["rate"]
    budget_val = veh_dict[user_veh]["budget"]
    
    is_urgent = st.checkbox(" Đặt Hỏa Tốc (Cần đi ngay)")
    final_urgency = 10 if is_urgent else st.session_state.urgency_base
    
    km_final, time_min, path_coords = 0.0, 0.0, []

    if start_loc and end_loc:
        with st.spinner("Đang định tuyến hệ thống vệ tinh..."):
            km_final, time_min, path_coords = get_route(start_loc, end_loc)

with c_map2:
    m = folium.Map(location=[10.7626, 106.6601], zoom_start=13)
    if start_loc: folium.Marker(start_loc, icon=folium.Icon(color='green')).add_to(m)
    if end_loc: folium.Marker(end_loc, icon=folium.Icon(color='red')).add_to(m)
    if path_coords:
        folium.PolyLine(path_coords, color="purple", weight=5).add_to(m) 
        m.fit_bounds([start_loc, end_loc])
    st_folium(m, width="100%", height=450)

if km_final > 0:
    st.markdown("<hr style='border: 1px dashed #ccc;'/>", unsafe_allow_html=True)
    
    can_book = True
    if "Xe Máy" in user_veh and w_val >= 10:
        st.error("⛈️ **HỆ THỐNG AN TOÀN:** Thời tiết đang Mưa Bão cực đoan. Để đảm bảo an toàn, dịch vụ Xe Máy tạm ngưng. Vui lòng chuyển sang đặt Ô-tô ở bảng bên trên!")
        can_book = False
    elif "Xe Máy" in user_veh and w_val == 8:
        st.warning("☔ Trời đang có mưa. Dịch vụ Xe Máy vẫn hoạt động bình thường, nhưng khuyên dùng Ô-tô để có trải nghiệm tốt nhất nha!")
        
    st.error(f"🚦 **Cảnh báo từ vệ tinh:** Tình trạng giao thông trên tuyến đường hiện tại đang: **{st.session_state.demo_traffic}**")
    
    if can_book:
        peak_val = 10 if "Thông" in st.session_state.demo_traffic else 50 if "Ùn" in st.session_state.demo_traffic else 90
        st.subheader(f" Hóa đơn Cuốc xe - {user_veh.split('(')[0]} ({km_final:.2f} km)")
        
        base_price = km_final * base_rate
        surge_multiplier = 1.0 + (peak_val / 200) + (w_val / 30) 
        
        subscription.input['distance'] = min(km_final, 30)
        subscription.input['frequency'] = st.session_state.freq
        subscription.input['peak_ratio'] = peak_val
        subscription.input['budget_flex'] = budget_val
        subscription.input['weather'] = w_val
        subscription.input['urgency_level'] = final_urgency
        subscription.input['point'] = st.session_state.point
        subscription.compute()
        
        out_price = subscription.output['price']
        out_pts = subscription.output['reward_pts']
        pkg_name, pkg_desc = get_package_info(out_price)
        
        urgent_surcharge_normal = 1.4 if is_urgent else 1.0
        urgent_surcharge_eco = 1.2 if is_urgent else 1.0 
        
        surge_price = base_price * surge_multiplier * urgent_surcharge_normal
        final_pay = surge_price
        
        if st.session_state.package:
            if st.session_state.package == "Gói Doanh Nhân":
                final_pay = 0
                st.info("🚀 **ÁP DỤNG ĐẶC QUYỀN DOANH NHÂN:** Chuyến đi này hoàn toàn MIỄN PHÍ!")
                
            elif st.session_state.package == "Gói Đi Làm":
                if "Ô tô" in user_veh and w_val >= 7:
                    final_pay = (km_final * veh_dict["🏍️ Xe Máy Thường"]["rate"]) * urgent_surcharge_eco
                    st.info("**ÁP DỤNG ĐẶC QUYỀN ĐI LÀM:** Mưa to, nâng cấp cuốc Ô-tô nhưng CHỈ TÍNH TIỀN THEO GIÁ XE MÁY!")
                else:
                    final_pay = base_price * urgent_surcharge_eco
                    if is_urgent:
                        st.info(" **ÁP DỤNG ĐẶC QUYỀN ĐI LÀM:** Khóa giá gốc và ĐƯỢC GIẢM 50% Phụ phí Hỏa Tốc.")
                    else:
                        st.info(" **ÁP DỤNG ĐẶC QUYỀN ĐI LÀM:** Khóa giá gốc, miễn 100% phụ phí kẹt xe/mưa bão.")
                        
            elif st.session_state.package == "Gói Premium":
                final_pay = base_price
                if is_urgent:
                    st.info(" **ÁP DỤNG ĐẶC QUYỀN PREMIUM:** Khóa giá gốc. Đã MIỄN PHÍ 100% cước Hỏa Tốc!")
                else:
                    st.info("**ÁP DỤNG ĐẶC QUYỀN PREMIUM:** Khóa giá và điều phối tài xế VIP ưu tiên đón.")
                    
            elif st.session_state.package == "Gói Eco":
                if "Xe Máy" not in user_veh:
                    final_pay = base_price * urgent_surcharge_eco
                    st.warning("⚠️ **QUY ĐỊNH GÓI ECO:** Đặc quyền Miễn phí dưới 5km CHỈ ÁP DỤNG cho Xe Máy. Chuyến Ô-tô này của bạn sẽ bị tính giá gốc.")
                else:
                    if km_final < 5:
                        final_pay = 0
                        st.info("🌱 **ÁP DỤNG ĐẶC QUYỀN ECO:** Cuốc Xe Máy dưới 5km được MIỄN PHÍ!")
                    else:
                        final_pay = base_price * urgent_surcharge_eco
                        if is_urgent:
                            st.info(" **ÁP DỤNG ĐẶC QUYỀN ECO:** Khóa giá chuyến đi. ĐƯỢC GIẢM 50% Phụ phí Hỏa Tốc.")
                        else:
                            st.info(" **ÁP DỤNG ĐẶC QUYỀN ECO:** Khóa giá chuyến đi gốc.")

        col_rs1, col_rs2 = st.columns(2)
        with col_rs1:
            st.metric("💳 CƯỚC PHÍ CẦN THANH TOÁN:", f"{int(final_pay):,} VNĐ")
            if not st.session_state.package and surge_price > base_price:
                st.caption("⚠️ *Giá cuốc lẻ đang bị cộng thêm phụ phí do tình trạng kẹt xe/thời tiết hoặc gọi Hỏa Tốc.*")
        
        with col_rs2:
            st.write(" ")
            btn_text = " XÁC NHẬN ĐẶT CHUYẾN NGAY"
            if st.button(btn_text, use_container_width=True, type="primary"):
                noti = st.empty()
                
                if final_pay == 0:
                    earned_pts = 0
                    pt_msg = " Chuyến đi 0đ KHÔNG áp dụng tích lũy điểm thưởng để chống trục lợi."
                else:
                    earned_pts = int(out_pts)
                    pt_msg = f"Dự kiến nhận +{earned_pts} điểm thưởng."

                if st.session_state.package and st.session_state.is_trial:
                    st.session_state.package = None 
                    st.session_state.is_trial = False 
                    noti.success(' Đang tìm tài xế...')
                    st.warning(" Chuyến đi trải nghiệm KHÔNG áp dụng tích điểm. Gói dùng thử đã hết hạn.")
                else:
                    st.session_state.loyalty_points_wallet += earned_pts 
                    noti.success(f'🎉 Đang tìm tài xế... {pt_msg}')

                with st.spinner("Vui lòng đợi tài xế xác nhận..."):
                    time.sleep(2.5)
                    
                st.balloons()
                noti.info(" Chuyến đi đã hoàn thành! Cảm ơn bạn đã lựa chọn MonthlyGo.")
                time.sleep(2)
                
                if "start" in st.session_state: del st.session_state["start"]
                if "end" in st.session_state: del st.session_state["end"]
                if "start_quick" in st.session_state: del st.session_state["start_quick"]
                if "end_quick" in st.session_state: del st.session_state["end_quick"]
                st.rerun()

        st.markdown("<hr style='border: 1px dashed #ccc;'/>", unsafe_allow_html=True)
        st.subheader(" Siêu thị Đặc Quyền MonthlyGo")
        
        if not st.session_state.package:
            st.success(f"🤖 **AI SMART SUGGESTION:** Dựa trên thói quen và lộ trình hiện tại, hệ thống MonthlyGo khuyến nghị bạn nên chọn **{pkg_name}**.\n\n{pkg_desc}\n\n🔥 *Đặc biệt: Khi ĐĂNG KÝ gói này, bạn sẽ được nhân **x{out_pts:.0f} Điểm Thưởng** sau mỗi chuyến đi!*")
        else:
            st.info("Cảm ơn bạn đã đồng hành cùng MonthlyGo. Bạn đang được bảo vệ bởi hệ thống giá nội bộ!")

        st.write("**Khám phá các Gói cước (Chỉ được Dùng Thử 1 lần duy nhất cho mỗi gói):**")
        cols = st.columns(4)
        for idx, p_name in enumerate(ALL_PACKAGES):
            with cols[idx]:
                st.markdown(f"**{p_name}**")
                
                if st.button(f"🛒 Đăng ký Gói", key=f"buy_{p_name}", use_container_width=True):
                    st.session_state.package = p_name
                    st.session_state.is_trial = False 
                    st.toast(f'Cảm ơn bạn đã mua {p_name}! Áp dụng đặc quyền tức thì.')
                    st.rerun()
                
                if p_name not in st.session_state.used_trials:
                    if st.button(f" Dùng thử", key=f"trial_{p_name}", use_container_width=True):
                        st.session_state.package = p_name
                        st.session_state.is_trial = True 
                        st.session_state.used_trials.append(p_name) 
                        st.toast(f'Đã kích hoạt 1 lượt dùng thử {p_name}!')
                        st.rerun()
                else:
                    st.button("🔒 Đã dùng thử", key=f"lock_{p_name}", disabled=True, use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("👨‍🏫 BIỂU ĐỒ GIẢI MỜ CENTROID (Admin Data)", expanded=False):
            fig, ax = plt.subplots(figsize=(8, 3))
            x_price = np.arange(200, 1001, 1)
            ax.plot(x_price, fuzz.trimf(x_price, [200, 200, 400]), 'b', label='Eco')
            ax.plot(x_price, fuzz.trimf(x_price, [200, 400, 600]), 'g', label='Đi Làm')
            ax.plot(x_price, fuzz.trimf(x_price, [400, 600, 800]), 'r', label='Premium')
            ax.plot(x_price, fuzz.trimf(x_price, [600, 800, 1000]), 'c', label='VIP')
            
            ax.axvline(x=out_price, color='k', linestyle='--', linewidth=2, label=f'Centroid: {out_price:.0f}')
            ax.set_title("Biểu đồ Suy diễn Hệ mờ MonthlyGo")
            ax.legend()
            st.pyplot(fig)
