import subprocess
from flask import Flask, render_template, request
import folium
from folium.plugins import MarkerCluster
import re
import os

os.environ['PYTHONIOENCODING'] = 'utf-8'
app = Flask(__name__)

# Funktion zum Abrufen der Nodes
def get_nodes(host):
    command = f"meshtastic --host {host} --nodes"
    result = subprocess.run(command, shell=True, capture_output=True, text=True, encoding='utf-8')

    if result.returncode != 0:
        print(f"Error executing command: {result.stderr}")
        return []

    output = result.stdout
    return parse_nodes(output)

# Funktion zum Parsen der Nodes
def parse_nodes(output):
    nodes = []
    lines = output.splitlines()
    
    for line in lines:
        if not line.startswith('│') or '═════' in line or '╘' in line:
            continue

        parts = line.split('│')
        if len(parts) < 17:
            continue

        user = parts[2].strip()
        id = parts[3].strip()
        aka = parts[4].strip()
        hardware = parts[5].strip()
        latitude = parts[6].strip()
        longitude = parts[7].strip()
        altitude = parts[8].strip()
        battery = parts[9].strip()
        channel_util = parts[10].strip()
        tx_air_util = parts[11].strip()
        snr = parts[12].strip()
        hops_away = parts[13].strip()
        channel = parts[14].strip()
        last_heard = parts[15].strip()
        since = parts[16].strip()

        if snr == 'N/A':
            snr_val = None
        else:
            try:
                snr_val = float(snr.replace(' dB', ''))
            except ValueError:
                snr_val = None

        if 'unknown' in hops_away:
            hops_away_val = 'unknown'
        else:
            try:
                hops_away_val = int(hops_away)
            except ValueError:
                hops_away_val = 'unknown'

        try:
            time_parts = since.split()
            if len(time_parts) >= 2:
                if 'sec' in time_parts[1]:
                    since_val = int(time_parts[0])
                elif 'min' in time_parts[1]:
                    since_val = int(time_parts[0]) * 60
                elif 'hour' in time_parts[1]:
                    since_val = int(time_parts[0]) * 3600
                elif 'day' in time_parts[1]:
                    since_val = int(time_parts[0]) * 86400
                else:
                    since_val = 0
            else:
                since_val = 0
        except (IndexError, ValueError):
            since_val = 0

        if latitude == 'N/A' or longitude == 'N/A':
            coordinates = None
        else:
            try:
                lat = float(latitude.replace('°', ''))
                lon = float(longitude.replace('°', ''))
                coordinates = (lat, lon)
            except ValueError:
                coordinates = None

        node_data = {
            'id': id,
            'name': user,
            'snr': snr_val,
            'lastHeard': since_val,
            'hopsAway': hops_away_val,
            'coordinates': coordinates
        }

        if is_direct_connection(node_data):
            nodes.append(node_data)

    return nodes

# Überprüft, ob die Node eine direkte Verbindung hat
def is_direct_connection(node):
    return (
        (node['hopsAway'] == 0 or node['hopsAway'] == 'unknown') and
        node['snr'] is not None and
        node['lastHeard'] < 86400  # 86400 Sekunden = 1 Tag
    )

# Funktion zum Abrufen eigener Informationen (--info)
def get_info(host):
    command = f"meshtastic --host {host} --info"
    result = subprocess.run(command, shell=True, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error executing command: {result.stderr}")
        return {}

    output = result.stdout
    info = {}

    try:
        owner_pattern = re.compile(r'Owner: (.+)')
        owner_match = owner_pattern.search(output)
        if owner_match:
            info['owner'] = owner_match.group(1)

        lat_pattern = re.compile(r'"latitude":\s*([\d\.]+)')
        lon_pattern = re.compile(r'"longitude":\s*([\d\.]+)')

        lat_match = lat_pattern.search(output)
        lon_match = lon_pattern.search(output)

        if lat_match and lon_match:
            info['latitude'] = float(lat_match.group(1))
            info['longitude'] = float(lon_match.group(1))
        else:
            info['latitude'], info['longitude'] = None, None

    except Exception as e:
        print(f"Failed to extract data: {e}")
        return {}

    return info

# Flask-Route für die Kartenanzeige
@app.route('/')
def map_view():
    # Abrufen der Ziel-URL des TCP-Nodes aus den URL-Parametern
    host = request.args.get('host')
    if not host:
        return "Fehler: Bitte geben Sie den 'host'-Parameter in der URL an.", 400

    nodes_data = get_nodes(host)
    info = get_info(host)

    own_latitude = info.get('latitude')
    own_longitude = info.get('longitude')

    if own_latitude is None or own_longitude is None:
        own_latitude, own_longitude = 48.2082, 16.3738  # Standardwert für die Kartenmitte (z.B. Wien)

    # Erstellen der Karte
    folium_map = folium.Map(location=[own_latitude, own_longitude], zoom_start=13)
    marker_cluster = MarkerCluster().add_to(folium_map)

    # Eigene Position auf der Karte markieren
    folium.Marker(
        location=[own_latitude, own_longitude],
        popup=f"Eigene Position: {info.get('owner', 'Unbekannt')}",
        icon=folium.Icon(color="blue")
    ).add_to(folium_map)

    # Sammeln der SNR-Werte und Berechnung der Schwellenwerte
    snr_values = [node['snr'] for node in nodes_data if node['snr'] is not None]
    snr_values.sort()
    N = len(snr_values)
    if N > 1:
        lower_index = int(N * (1/3))
        upper_index = int(N * (2/3))
        lower_threshold = snr_values[lower_index]
        upper_threshold = snr_values[upper_index]
    else:
        lower_threshold = upper_threshold = snr_values[0] if snr_values else 0

    # Die Nodes auf der Karte anzeigen und Linien zeichnen
    for node in nodes_data:
        if node['coordinates']:
            node_lat, node_lon = node['coordinates']
            folium.Marker(
                location=node['coordinates'],
                popup=f"{node['name']} (SNR: {node['snr']})",
                icon=folium.Icon(color="green")
            ).add_to(marker_cluster)

            # Bestimmen der Linienfarbe basierend auf dem SNR
            snr = node['snr']
            if snr is not None:
                if snr <= lower_threshold:
                    line_color = 'red'
                elif snr >= upper_threshold:
                    line_color = 'green'
                else:
                    line_color = 'yellow'
            else:
                line_color = 'gray'  # Falls SNR unbekannt

            # Linie vom Node zur eigenen Position zeichnen
            folium.PolyLine(
                locations=[node['coordinates'], [own_latitude, own_longitude]],
                color=line_color,
                weight=6,  # Dicke der Linie anpassen
                opacity=0.9
            ).add_to(folium_map)

    # Karte speichern und anzeigen
    folium_map.save('templates/map.html')
    return render_template('map.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
