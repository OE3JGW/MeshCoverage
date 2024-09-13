## Meshtastic Node Map Viewer

This is a Flask web application that visualizes nearby Meshtastic nodes on an interactive map. The app connects to a Meshtastic device over TCP, retrieves information about connected nodes, and displays their locations along with signal quality indicators.

## Features
- **Interactive Map Visualization**: Displays nodes on a map using Folium, with clustering support for better visualization.
- **Signal Quality Indicators**: Draws lines between your device and connected nodes, color-coded based on Signal-to-Noise Ratio (SNR).
- **Real-Time Data Retrieval**: Fetches the latest node information and updates the map accordingly.

**Use following url format to connect to it: http://localhost:5000/?host=127.0.0.1**
