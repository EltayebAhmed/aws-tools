from flask import Flask, request, jsonify, render_template_string
from datetime import datetime
from zoneinfo import ZoneInfo
from collections import OrderedDict
import boto3  # add this line

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

@app.route('/spot_requests', methods=['GET'])
def _spot_requests():
    return jsonify(spot_requests()), 200, {'Content-Type': 'application/json'}

def spot_requests():
    ec2 = boto3.client('ec2')
    resp = ec2.describe_spot_instance_requests(
        Filters=[{"Name": "state", "Values": ["active"]}]
    )
    total_result = []
    for req in resp.get("SpotInstanceRequests", []):
        result = {}
        req_id = req["SpotInstanceRequestId"]
        tags = req.get("Tags", [])
        tag_str = ",".join(f"{t['Key']}={t['Value']}" for t in tags)
        print(tag_str)
        result[req_id] = tag_str
        result["KeyName"] = req.get("LaunchSpecification", {}).get("KeyName", "")
        total_result.append(result)
    return total_result

@app.route('/list_instances', methods=['GET'])
def _list_instances():
    return jsonify(list_instances()), 200, {'Content-Type': 'application/json'}

def list_instances():
    ec2 = boto3.client('ec2')
    resp = ec2.describe_instances()
    result = {}
    for reservation in resp.get("Reservations", []):
        for inst in reservation.get("Instances", []):
            inst_id = inst["InstanceId"]
            # skip if instance is not running
            if inst.get("State", {}).get("Name") != "running":
                continue
            # build comma-separated tag string
            tag_str = ",".join(f"{t['Key']}={t['Value']}" for t in inst.get("Tags", []))
            result[inst_id] = {
                "Tags": tag_str,
                "KeyName": inst.get("KeyName", ""),
                "PublicIpAddress": inst.get("PublicIpAddress", "")
            }
    return result

@app.route('/dashboard', methods=['GET'])
def dashboard():
    instances = list_instances()
    spot_reqs = spot_requests()
    html = ['<html><head><style>',
            '.table-container { display:inline-block; vertical-align:top; margin-right:20px; }',
            'table { border-collapse: collapse; }',
            'th, td { border:1px solid black; padding:5px; }',
            '</style></head><body>']
    html.append('<h1>Instances and Spot Requests</h1>')
    # Instances table
    html.append('<div class="table-container">')
    html.append('<h2>Instances</h2>')
    html.append('<table><tr><th>InstanceId</th><th>Tags</th><th>KeyName</th><th>PublicIpAddress</th></tr>')
    for inst_id, details in instances.items():
        html.append(f'<tr><td>{inst_id}</td><td>{details["Tags"]}</td><td>{details["KeyName"]}</td><td>{details["PublicIpAddress"]}</td></tr>')
    html.append('</table></div>')
    # Spot Requests table
    html.append('<div class="table-container">')
    html.append('<h2>Spot Requests</h2>')
    html.append('<table><tr><th>RequestId</th><th>Tags</th><th>KeyName</th></tr>')
    for item in spot_reqs:
        req_id = next((k for k in item.keys() if k != "KeyName"), "")
        tag_str = item.get(req_id, "")
        keyname = item.get("KeyName", "")
        html.append(f'<tr><td>{req_id}</td><td>{tag_str}</td><td>{keyname}</td></tr>')
    html.append('</table></div>')
    html.append('</body></html>')
    return render_template_string(''.join(html)), 200, {'Content-Type': 'text/html'}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3671)
