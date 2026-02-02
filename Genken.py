import streamlit as st
import requests
import random
import time
from collections import Counter
from datetime import datetime

# --- KONFIGURACJA KENO ---
st.set_page_config(
    page_title="Keno Smart System LIVE",
    page_icon="⚡",
    layout="centered"
)

# --- STYL ---
st.markdown("""
    <style>
    .stApp { background-color: #0d1f12; color: #e8f5e9; }
    .keno-ball {
        font-size: 20px; font-weight: bold; color: white;
        background: radial-gradient(circle at 30% 30%, #43a047, #1b5e20);
        border: 2px solid #66bb6a;
        border-radius: 50%;
        width: 45px; height: 45px; display: inline-flex;
        justify-content: center; align-items: center;
        margin: 4px; box-shadow: 0 0 10px rgba(76, 175, 80, 0.4);
    }
    .metric-box {
        background-color: #1b3a24; padding: 10px; border-radius: 8px;
        text-align: center; border: 1px solid #2e7d32;
        color: #a5d6a7; margin-bottom: 10px;
    }
    h1 { color: #66bb6a !important; }
    .status-live {
        font-weight: bold; font-size: 14px;
        padding: 5px 10px; border-radius: 15px;
        display: inline-block; margin-bottom: 10px;
    }
    .error-box {
        color: #ff5555; border: 1px solid #ff5555; padding: 10px; border-radius: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNKCJA POBIERANIA DANYCH (Z NAGŁÓWKAMI - "PAKIETAMI") ---
@st.cache_data(ttl=120) # Odświeżaj co 2 minuty
def get_live_draws():
    # To jest oficjalny endpoint, który "podsłuchaliśmy" w przeglądarce
    url = "https://www.lotto.pl/api/lotteries/draw-results/by-gametype?game=Keno&index=1&size=600&sort=drawSystemId&order=DESC"
    
    # TU JEST KLUCZ DO SUKCESU:
    # Udajemy przeglądarkę Chrome na Windowsie. Bez tego serwer nas blokuje.
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.lotto.pl/keno/wyniki-i-wygrane",
        "Origin": "https://www.lotto.pl"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return [], f"Błąd serwera: Kod {response.status_code}"
            
        data = response.json()
        
        parsed_draws = []
        # Parsowanie JSON (struktury danych Lotto)
        for item in data.get('items', []):
            try:
                results = item.get('results', [])
                if results:
                    nums = results[0].get('resultsJson', [])
                    nums = [int(n) for n in nums]
                    parsed_draws.append(nums)
            except:
                continue
        
        if not parsed_draws:
            return [], "Pobrane dane są puste (zmieniona struktura API?)"
            
        return parsed_draws, None
        
    except Exception as e:
        return [], f"Błąd połączenia: {str(e)}"

def get_hot_weights(draws):
    flat = [n for d in draws for n in d]
    c = Counter(flat)
    return [c.get(i, 1) for i in range(1, 71)]

# --- ALGORYTM ---
def generate_keno_live(weights, num_picks=10):
    population = list(range(1, 71))
    for _ in range(5000):
        stronger_weights = [w**1.3 for w in weights]
        candidates = set()
        while len(candidates) < num_picks:
            c = random.choices(population, weights=stronger_weights, k=1)[0]
            candidates.add(c)
        nums = sorted(list(candidates))
        
        # Filtry
        if num_picks >= 5:
            z1 = sum(1 for n in nums if n <= 23)
            z2 = sum(1 for n in nums if 23 < n <= 46)
            z3 = sum(1 for n in nums if n > 46)
            if num_picks == 10 and (z1 == 0 or z2 == 0 or z3 == 0): continue
        
        even = sum(1 for n in nums if n % 2 == 0)
        if num_picks == 10 and (even < 4 or even > 6): continue
        
        consecutive = 0
        max_cons = 0
        for i in range(len(nums)-1):
            if nums[i+1] == nums[i] + 1: consecutive += 1
            else: consecutive = 0
            max_cons = max(max_cons, consecutive)
        if max_cons >= 2: continue
            
        return nums, even
    return nums, 0

# --- INTERFEJS ---
def main():
    st.title("⚡ Keno Smart System")
    
    # Próba pobrania danych
    with st.spinner("Łączenie z serwerem Lotto (udawanie przeglądarki)..."):
        draws, error_msg = get_live_draws()
    
    if error_msg:
        st.markdown(f"<div class='error-box'>⚠️ {error_msg}</div>", unsafe_allow_html=True)
        st.warning("Uruchamiam tryb awaryjny (losowy).")
        weights = [1] * 70
        status_html = "<div class='status-live' style='color:red; border-color:red;'>🔴 OFFLINE</div>"
    else:
        weights = get_hot_weights(draws)
        status_html = f"<div class='status-live' style='color:#00ff00; border-color:#00ff00;'>🟢 ONLINE: {len(draws)} losowań</div>"

    st.markdown(status_html, unsafe_allow_html=True)

    # Przyciski
    c1, c2 = st.columns(2)
    with c1:
        mode_10 = st.button("Gra na 10 liczb", use_container_width=True)
    with c2:
        mode_5 = st.button("Gra na 5 liczb", use_container_width=True)

    if 'live_res' not in st.session_state:
        st.session_state['live_res'] = None
        
    if mode_10:
        res, ev = generate_keno_live(weights, 10)
        st.session_state['live_res'] = (res, ev, 10)
    if mode_5:
        res, ev = generate_keno_live(weights, 5)
        st.session_state['live_res'] = (res, ev, 5)

    if st.session_state['live_res']:
        res, ev, picks = st.session_state['live_res']
        st.divider()
        st.subheader(f"Typ na {picks} liczb:")
        html = "<div style='display: flex; flex-wrap: wrap; justify-content: center;'>"
        for n in res:
            html += f"<div class='keno-ball'>{n}</div>"
        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        m1, m2 = st.columns(2)
        m1.markdown(f"<div class='metric-box'>⚖️ Parzyste: <b>{ev}/{picks}</b></div>", unsafe_allow_html=True)
        m2.markdown(f"<div class='metric-box'>🔥 Źródło<br><small>{'API Lotto' if not error_msg else 'Losowe'}</small></div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
    
