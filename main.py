from flask import Flask, render_template, jsonify, request
import threading
import serial
import json
import time
import re
import math
import MySQLdb
import csv
from datetime import datetime
from zoneinfo import ZoneInfo


app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'

db = MySQLdb.connect(
    host="localhost",
    user="root",
    passwd="rpios",
    db="poit_d1",
    autocommit=True
)
cursor = db.cursor()

CSV_PATH = 'data_log.csv'


latest = {"temp": None, "hum": None, "measuring": False}
bufferedFull = []
buffered = []
period_start = None

bratislava_tz = ZoneInfo('Europe/Bratislava')

# #port = '/dev/ttyACM0'
# port = '/dev/ttyUSB0'
# ser = None

def init_db():
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS measurements_zav (
            id INT AUTO_INCREMENT PRIMARY KEY,
            period_start DATETIME NOT NULL,
            period_end DATETIME NOT NULL,
            data JSON NOT NULL
        ) ENGINE=InnoDB;
    """)

def init_csv():
    try:
        with open(CSV_PATH, 'x', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'period_start', 'period_end', 'data'])
    except FileExistsError:
        pass

def fix_booleans(text: str) -> str:
    text = re.sub(r'\bfals?\b', 'false', text)
    text = re.sub(r'\btru?\b', 'true', text)
    return text


# def serial_reader():
#     global latest, port, ser, buffered, period_start
#     try:
#         ser = serial.Serial(port, 115200, timeout=1)
#         print("Serial port opened successfully.")
#     except Exception as e:
#         print(f"Failed to open serial port: {e}")
#         return
    
#     while True:
#         chunk = ser.readline()
#         while b'\n' not in chunk:
#             chunk += ser.readline()
#         line = chunk.decode('utf-8', errors='ignore').strip()
#         print(f"Line: {line}")

#         line = fix_booleans(line)
#         print(f"Line: {line}")

#         try:
#             data = json.loads(line)
#         except json.JSONDecodeError as je:
#             print("JSON error:", je)
#             continue
#         print(f"Data: {data}")

#         cmd = data.get("cmd")
#         if cmd == "data":
#             latest["temp"] = data.get("temp")
#             latest["hum"] = data.get("hum")
#             latest["measuring"] = True
#             print(f"latest: {latest}")
#             buffered.append({'temp':data.get("temp"),'hum':data.get("hum"),'ts':data.get("ts")})
#         elif cmd == "status":
#             meas = data.get('measuring')

#             if meas and not latest['measuring']:
#                 # period_start = time.strftime('%Y-%m-%d %H:%M:%S')
#                 period_start = datetime.fromisoformat(data.get('ts'))
#                 buffered = []
#             if not meas and latest['measuring']:
#                 # period_end = time.strftime('%Y-%m-%d %H:%M:%S')
#                 period_end = datetime.fromisoformat(data.get('ts'))
#                 arr = buffered

#                 cursor.execute(
#                     "INSERT INTO measurements_zav (period_start, period_end, data) VALUES (%s, %s, %s)",
#                     (period_start, period_end, json.dumps(arr))
#                 )
#                 row_id = cursor.lastrowid
#                 with open(CSV_PATH,'a',newline='') as f:
#                     csv.writer(f).writerow([row_id, period_start, period_end, json.dumps(arr)])
        
#             latest["measuring"] = meas
#             latest["temp"] = None
#             latest["hum"] = None

#         time.sleep(0.01)


@app.route('/status')
def status():
    global latest
    print(f"Returning status: {latest}")
    return jsonify(latest)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/session_data')
def session_data():
    return jsonify(bufferedFull)


@app.route('/upload', methods=['POST'])
def upload():
    global latest, buffered, bufferedFull, period_start
    pkt = request.get_json(force=True)
    print(f"PKT: {pkt}")
    pkt = json.loads(fix_booleans(json.dumps(pkt)))

    cmd = pkt.get('cmd')
    ts = pkt.get('ts')
    ts = datetime.fromisoformat(ts).replace(tzinfo=ZoneInfo('UTC'))
    ts = ts.astimezone(bratislava_tz)

    if 'temp' in pkt:
        bufferedFull.append({'temp':pkt['temp'], 'hum':pkt['hum'], 'ts':ts.isoformat()})
    else:
        bufferedFull.append({'temp':None, 'hum':None, 'ts':ts.isoformat()})

    if cmd=='data':
        if not period_start:
            period_start = ts
        buffered.append({'temp':pkt['temp'], 'hum':pkt['hum'], 'ts':ts.isoformat()})
        latest.update({'temp':pkt['temp'], 'hum':pkt['hum'], 'measuring': True})
    elif cmd=='status':
        meas = pkt.get('measuring')
        if meas and not latest['measuring']:
            # period_start = datetime.fromisoformat(ts)
            # period_start = datetime.fromisoformat(ts).replace(tzinfo=ZoneInfo('UTC'))
            period_start = ts

            buffered = []
            latest.update({'temp':None, 'hum':None, 'measuring': True})
        if not meas and latest['measuring']:
            period_end = ts

            arr = buffered
            cursor.execute(
                "INSERT INTO measurements_zav (period_start, period_end, data) VALUES (%s,%s,%s)",
                (period_start, period_end, json.dumps(arr))
            )
            row_id = cursor.lastrowid
            with open(CSV_PATH,'a',newline='') as f:
                csv.writer(f).writerow([row_id, period_start, period_end, json.dumps(arr)])
            latest.update({'temp':None, 'hum':None, 'measuring': False})
            period_start = None

    return jsonify(status='ok')


@app.route('/history', methods=['GET', 'POST'])
def history():
    if request.method == 'POST':
        rec_id = request.form.get('id')
        cursor.execute("SELECT period_start, period_end, data FROM measurements_zav WHERE id = %s", (rec_id,))
        row = cursor.fetchone()
        if row:
            start, end, data = row
            return render_template('history.html', record={'id': rec_id, 'start': start, 'end': end, 'data': data})
        else:
            return render_template('history.html', error='Record not found')
    return render_template('history.html')


@app.route('/fileview', methods=['GET', 'POST'])
def fileview():
    if request.method == 'POST':
        try:
            idx = int(request.form.get('idx'))
        except (TypeError, ValueError):
            return render_template('fileview.html', error="Invalid index")
        with open(CSV_PATH, newline='') as f:
            reader = list(csv.reader(f))
        if 0 <= idx < len(reader):
            row = reader[idx]
            record = {
                'id':          row[0],
                'start':       row[1],
                'end':         row[2],
                'data':        row[3],
                'idx':          idx
            }
            return render_template('fileview.html', record=record)
        else:
            return render_template('fileview.html', error="Index out of range")
    return render_template('fileview.html')


if __name__ == '__main__':
    init_db()
    init_csv()
    app.run(host='0.0.0.0', port=80, debug=True, use_reloader=False)
