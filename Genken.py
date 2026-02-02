import streamlit as st
import requests
from bs4 import BeautifulSoup
import random
from collections import Counter

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
    .status-live {
        font-weight: bold; font-size: 14px;
        padding: 5px 12px; border-radius: 15px;
        display: inline-block; margin-bottom: 10px;
        border: 1px solid;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNKCJA POBIERANIA DANYCH (SCRAPER ALTERNATYWNY) ---
@st.cache_data(ttl=180) # Odświeżaj co 3 minuty
def get_live_draws():
    # Zamiast Lotto.pl, używamy serwisu, który nie blokuje serwerów w USA
    url = "https://www.wynikilotto.net.pl/keno/wyniki/"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parsowanie HTML (czytanie strony)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        parsed_draws = []
        
        # Szukamy tabeli z wynikami (struktura strony wynikilotto.net.pl)
        # Zazwyczaj wyniki są w tabeli o klasie 'wyniki' lub podobnej
        rows = soup.find_all('tr')
        
        for row in rows:
            # Szukamy komórek z liczbami (często mają specyficzne klasy lub są wewnątrz divów)
            # Na tej stronie liczby są często w obrazkach alt lub w tekście
            # Prosta heurystyka: szukamy wiersza, który ma dużo liczb
            text = row.get_text(separator=' ')
            # Czyścimy tekst, zostawiamy tylko cyfry
            import re
            numbers = re.findall(r'\b\d+\b', text)
            
            # Wiersz Keno ma datę, numer losowania i 20 liczb.
            # Więc szukamy wierszy, które mają > 20 liczb.
            
            # Filtrujemy liczby (1-70)
            valid_nums = []
            for n in numbers:
                val = int(n)
                if 1 <= val <= 70:
                    valid_nums.append(val)
            
            # Usuwamy duplikaty zachowując kolejność (bo data może mieć te same cyfry co wynik)
            # Ale w Keno liczby są unikalne.
            # Zazwyczaj ostatnie 20 liczb w wierszu to wynik.
            
            if len(valid_nums) >= 20:
                # Zakładamy, że 20 ostatnich liczb to wynik losowania
                draw_result = list(set(valid_nums[-20:])) # set usuwa duplikaty, ale keno ich nie ma
                if len(draw_result) >= 15: # Zabezpieczenie
                    parsed_draws.append(draw_result)

        if not parsed_draws:
            return [], "Nie udało się odczytać tabeli wyników."
            
        return parsed_draws, None

    except Exception as e:
        return [], f"Błąd połączenia: {str(e)}"

def get_hot_weights(draws):
    if not draws:
        return [1] * 70
    flat = [n for d in draws for n in d]
    c = Counter(flat)
    return [c.get(i, 1) for i in range(1, 71)]

# --- ALGORYTM ---
def generate_keno_live(weights, num_picks=10):
    population = list(range(1, 71))
    
    # Jeśli mamy mało danych (np. tylko 30 losowań ze strony), 
    # musimy lekko spłaszczyć wagi, żeby nie faworyzować liczb zbyt mocno
    # na podstawie małej próbki.
    
    for _ in range(5000):
        stronger_weights = [w**1.2 for w in weights] # Mniejszy potęga dla bezpieczeństwa
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
    
    with st.spinner("Pobieranie wyników z bazy alternatywnej..."):
        draws, error_msg = get_live_draws()
    
    if draws:
        # Serwisy zewnętrzne na jednej stronie pokazują zazwyczaj 20-50 ostatnich losowań.
        # To wystarczy do wyłapania "gorących liczb" z ostatnich 2-3 godzin.
        status_html = f"<div class='status-live' style='color:#00ff00; border-color:#00ff00;'>🟢 ONLINE (Mirror): {len(draws)} ostatnich losowań</div>"
        weights = get_hot_weights(draws)
    else:
        status_html = f"<div class='status-live' style='color:#ffa500; border-color:#ffa500;'>🟠 TRYB SYMULACJI ({error_msg})</div>"
        weights = [1] * 70

    st.markdown(status_html, unsafe_allow_html=True)

    # Przyciski
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
        st.subheader(f"Typ na {picks} liczb:")
        
        html = "<div style='display: flex; flex-wrap: wrap; justify-content: center;'>"
        for n in res:
            html += f"<div class='keno-ball'>{n}</div>"
        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        c1.markdown(f"<div class='metric-box'>⚖️ Parzyste: <b>{ev}/{picks}</b></div>", unsafe_allow_html=True)
        src = "WynikiLotto.net" if draws else "Matematyka"
        c2.markdown(f"<div class='metric-box'>🔥 Źródło<br><small>{src}</small></div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
    
