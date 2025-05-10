# IoT Dashboard: Teplota & Vlhkosť

Jednoduchá IoT aplikácia na platforme Raspberry Pi + ESP32, ktorá meria teplotu a vlhkosť a poskytuje live dashboard aj historické zobrazenie dát.

---

## 🚀 Funkcie

- **ESP32 Firmware**  
  - Číta DHT11 (teplota, vlhkosť) a PIR senzor  
  - Prepínanie merania cez HTTP GET `/toggle`  
  - Odosielanie dát (`cmd=data`) a statusu (`cmd=status`) POST `/upload`  

- **Flask Server**  
  - **GET** `/status` – live JSON so stavom a poslednými hodnotami  
  - **POST** `/upload` – prijíma a ukladá merania do MySQL a CSV  
  - **GET/POST** `/history` – zobrazenie histórie z databázy  
  - **GET/POST** `/fileview` – zobrazenie histórie zo súboru `data_log.csv`  
  - Autom. inicializácia DB (`measurements_zav`) a CSV (`data_log.csv`)  

- **Webový klient**  
  - Dashboard v `index.html` s numerickými ukazovateľmi, grafom Plotly aj toggle tlačidlom  
  - `history.html` pre graf meraní z MySQL podľa ID  
  - `fileview.html` pre graf meraní zo súboru CSV podľa indexu  

---
