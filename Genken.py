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
    .status-badge {
        font-weight: bold; font-size: 14px;
        padding: 5px 12px; border-radius: 15px;
        display: inline-block; margin-bottom: 10px;
        border: 1px solid;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNKCJA POBIERANIA DANYCH (ZAAWANSOWANA) ---
@st.cache_data(ttl=180)
def get_live_draws():
    # Definiujemy nagłówki udające przeglądarkę
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.lotto.pl/keno/wyniki-i-wygrane",
        "Origin": "https://www.lotto.pl",
        "Connection": "keep-alive"
    }

    session = requests.Session()
    session.headers.update(headers)

    parsed_draws = []
    error_log = ""

    try:
        # KROK 1: Wejdź na stronę główną po ciasteczka (Cookies)
        # To kluczowe - bez tego API często odrzuca
        session.get("https://www.lotto.pl/keno/wyniki-i-wygrane", timeout=5)
        
        # KROK 2: Próba pobrania danych (Endpoint publiczny)
        # Pobieramy 600 ostatnich losowań
        api_url = "https://www.lotto.pl/api/lotteries/draw-results/by-gametype?game=Keno&index=1&size=600&sort=drawSystemId&order=DESC"
        
        response = session.get(api_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            for item in data.get('items', []):
                results = item.get('results', [])
                if results:
                    nums = results[0].get('resultsJson', [])
                    if nums:
                        parsed_draws.append([int(n) for n in nums])
            
            if parsed_draws:
                return parsed_draws, None # SUKCES
        else:
            error_log += f"API Error: {response.status_code}. "

    except Exception as e:
        error_log += f"Connection Error: {str(e)}. "

    # KROK 3: Jeśli tu jesteśmy, to nie udało się pobrać danych.
    # Zwracamy pustą listę i błąd.
    return [], error_log if error_log else "Brak danych z API"

def get_hot_weights(draws):
    if not draws:
        # Jeśli brak danych, zwróć równe wagi (bezpiecznik)
        return [1] * 70
    flat = [n for d in draws for n in d]
    c = Counter(flat)
    return [c.get(i, 1) for i in range(1, 71)]

# --- ALGORYTM ---
def generate_keno_live(weights, num_picks=10):
    population = list(range(1, 71))
    
    # Jeśli wagi są "płaskie" (tryb awaryjny), symulujemy "Hot Numbers"
    # żeby generator nie był całkowicie głupi
    if len(set(weights)) == 1:
        # Symulacja: środek tabeli wpada częściej (rozkład Gaussa)
        temp_weights = []
        for i in population:
            if 20 <= i <= 50: temp_weights.append(1.2)
            else: temp_weights.append(1.0)
        weights = temp_weights

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
        if num_picks == 5 and (even < 2 or even > 3): continue
            
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
    
    with st.spinner("Łączenie z bazą Totalizatora..."):
        draws, error_msg = get_live_draws()
    
    if draws:
        status_html = f"<div class='status-badge' style='color:#00ff00; border-color:#00ff00;'>🟢 ONLINE (Lotto.pl): {len(draws)} losowań</div>"
        weights = get_hot_weights(draws)
    else:
        # TRYB AWARYJNY
        status_html = f"<div class='status-badge' style='color:#ffa500; border-color:#ffa500;'>🟠 TRYB SYMULACJI (Błąd połączenia)</div>"
        st.markdown(status_html, unsafe_allow_html=True)
        if error_msg:
            with st.expander("Szczegóły błędu (dla administratora)"):
                st.write(error_msg)
                st.caption("Streamlit Cloud może być blokowany przez geolokalizację Lotto.pl.")
        
        weights = [1] * 70 # Równe wagi, algorytm użyje symulacji
        
    if draws:
        st.markdown(status_html, unsafe_allow_html=True)

    # Wybór gry
    col1, col2 = st.columns(2)
    with col1:
        mode_10 = st.button("Gra na 10 liczb", use_container_width=True)
    with col2:
        mode_5 = st.button("Gra na 5 liczb", use_container_width=True)

    if 'keno_res' not in st.session_state:
        st.session_state['keno_res'] = None
        
    if mode_10:
        res, ev = generate_keno_live(weights, 10)
        st.session_state['keno_res'] = (res, ev, 10)
    if mode_5:
        res, ev = generate_keno_live(weights, 5)
        st.session_state['keno_res'] = (res, ev, 5)

    if st.session_state['keno_res']:
        res, ev, picks = st.session_state['keno_res']
        
        st.divider()
        st.subheader(f"Wygenerowany typ ({picks} liczb):")
        
        # Kule
        html = "<div style='display: flex; flex-wrap: wrap; justify-content: center;'>"
        for n in res:
            html += f"<div class='keno-ball'>{n}</div>"
        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        c1.markdown(f"<div class='metric-box'>⚖️ Parzyste: <b>{ev}/{picks}</b></div>", unsafe_allow_html=True)
        src = "API Lotto" if draws else "Symulacja Statystyczna"
        c2.markdown(f"<div class='metric-box'>🔥 Źródło<br><small>{src}</small></div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
        
