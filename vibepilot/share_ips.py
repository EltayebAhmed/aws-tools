from flask import Flask, request, jsonify, render_template_string
from datetime import datetime
from zoneinfo import ZoneInfo
from collections import OrderedDict

app = Flask(__name__)
registered_entries = []  # store (ip, timestamp) in order

@app.route('/register', methods=['GET'])
def register_ip():
    ip = request.remote_addr
    now = datetime.now(ZoneInfo("Europe/London"))
    timestamp = int(now.timestamp())
    registered_entries.append((ip, timestamp))
    return jsonify({"status": "registered", "ip": ip, "timestamp": timestamp}), 200

@app.route('/replay', methods=['GET'])
def replay_ips():
    # group entries by calendar day in London time
    groups = OrderedDict()
    for ip, ts in registered_entries:
        date = datetime.fromtimestamp(ts, ZoneInfo("Europe/London")).date().isoformat()
        if date not in groups:
            groups[date] = []
        groups[date].append({"ip": ip, "timestamp": ts})

    # render HTML tables per date
    html = ['<html><body>']
    html.append('<h1>IP Addresses Registered</h1>')
    for date, entries in groups.items():
        html.append(f'<h2>{date}</h2>')
        html.append('<table border="1"><tr><th>IP Address</th><th>Timestamp</th></tr>')
        for item in entries:
            dt = datetime.fromtimestamp(item["timestamp"], ZoneInfo("Europe/London"))
            ts_str = dt.strftime("%d/%m/%Y - %H:%M:%S")
            html.append(f'<tr><td>{item["ip"]}</td><td>{ts_str}</td></tr>')
        html.append('</table>')
    html.append('</body></html>')

    return render_template_string(''.join(html)), 200, {'Content-Type': 'text/html'}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3671)
