import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import osmnx as ox
import os
import time
import networkx as nx
from shapely.geometry import LineString, Point
from geopy.geocoders import Nominatim

# Set page configuration with dark theme
st.set_page_config(
    page_title="Metro Manila Route Mapper",
    layout="wide",
    page_icon="🌧️"
)

# Apply dark theme with tight layout
st.markdown("""
    <style>
        :root {
            --dark-bg: #0e1117;
            --dark-card: #1e2130;
            --light-text: #f0f0f0;
            --accent: #4f8bf9;
        }
        
        body {
            background-color: var(--dark-bg);
            color: var(--light-text);
            margin: 0;
            padding: 0;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        .stApp {
            background-color: var(--dark-bg);
            padding: 0 10px !important;
        }
        .stMarkdown, .stMetric, .stButton>button {
            color: var(--light-text) !important;
        }
        .legend-box {
            background-color: var(--dark-card);
            padding: 10px;
            border-radius: 8px;
            margin: 10px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        }
        .instruction-box {
            background-color: var(--dark-card);
            padding: 15px;
            border-radius: 8px;
            margin: 10px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        }
        .big-button {
            font-size: 18px !important;
            padding: 12px !important;
            margin: 15px 0 !important;
            background-color: var(--accent) !important;
            border: none !important;
            transition: all 0.3s ease;
        }
        .big-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
        }
        .footer {
            font-size: 12px;
            color: #aaa;
            margin-top: 10px;
            text-align: center;
        }
        .map-container {
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            height: 600px;
        }
        .st-emotion-cache-1v0mbdj {
            border-radius: 10px;
        }
        .title-container {
            text-align: center;
            margin-top: -20px;
            margin-bottom: 5px;
        }
        .stColumn {
            padding: 5px !important;
        }
        /* Align columns to top */
        .st-emotion-cache-1wrcr25 {
            align-items: flex-start;
        }
        .loading-container {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 600px;
            background-color: var(--dark-card);
            border-radius: 10px;
            text-align: center;
        }
        .search-box {
            margin-bottom: 15px;
        }
        .search-button {
            margin-top: 5px !important;
            align-self: flex-end;
        }
        .button-container {
            display: flex;
            align-items: flex-end;
            height: 100%;
        }
        .route-info {
            background-color: var(--dark-card);
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
        }
    </style>
""", unsafe_allow_html=True)

# App title with tighter layout
st.markdown("""
    <div class="title-container">
        <h1>Metro Manila Route Visualizer</h1>
        <p>Search locations or drag markers to set start and end points</p>
    </div>
""", unsafe_allow_html=True)

# Initialize session states
if "map_initialized" not in st.session_state:
    st.session_state.map_initialized = False
if "start_point" not in st.session_state:
    st.session_state.start_point = [14.5995, 120.9842]  # Manila City Hall
if "end_point" not in st.session_state:
    st.session_state.end_point = [14.5522, 121.0445]    # Makati CBD
if "map_key" not in st.session_state:
    st.session_state.map_key = str(time.time())
if "is_loading" not in st.session_state:
    st.session_state.is_loading = False
if "start_search" not in st.session_state:
    st.session_state.start_search = ""
if "end_search" not in st.session_state:
    st.session_state.end_search = ""
if "route" not in st.session_state:
    st.session_state.route = None
if "road_colors" not in st.session_state:
    st.session_state.road_colors = {}
if "show_flood_overlay" not in st.session_state:
    st.session_state.show_flood_overlay = False

# Initialize geocoder
geolocator = Nominatim(user_agent="metro_manila_route_visualizer")

# Geocode function
def geocode_location(query):
    try:
        location = geolocator.geocode(query + ", Metro Manila, Philippines")
        if location:
            return [location.latitude, location.longitude]
        return None
    except Exception:
        return None

# Load Flood Data
@st.cache_data
def load_flood_data():
    shapefile_path = "MetroManila_Flood_100year.shp"
    if os.path.exists(shapefile_path):
        gdf = gpd.read_file(shapefile_path)
        return gdf.to_crs(epsg=4326)  # Convert to WGS84
    return None

flood_gdf = load_flood_data()

# Get flood level for a point
def get_flood_level(point):
    point_geom = Point(point[1], point[0])  # Point takes (x, y) = (lon, lat)
    for _, row in flood_gdf.iterrows():
        if row['geometry'].contains(point_geom):
            return row['Var']
    return 0  # No flood

# Find the shortest route
def find_route(start, end):
    try:
        # Get road network for Metro Manila
        graph = ox.graph_from_place("Metro Manila, Philippines", network_type="drive")
        
        # Convert points to (y, x) format (latitude, longitude)
        start_point = (start[0], start[1])
        end_point = (end[0], end[1])
        
        # Get nearest nodes
        orig_node = ox.distance.nearest_nodes(graph, X=[start_point[1]], Y=[start_point[0]])[0]
        dest_node = ox.distance.nearest_nodes(graph, X=[end_point[1]], Y=[end_point[0]])[0]
        
        # Find shortest path by distance
        route_path = nx.shortest_path(graph, orig_node, dest_node, weight="length")
        
        # Process route
        route_pts = []
        segment_colors = {}
        
        for i in range(len(route_path)-1):
            u = route_path[i]
            v = route_path[i+1]
            
            # Get edge geometry
            edge_data = graph.get_edge_data(u, v)[0]
            if 'geometry' in edge_data:
                line = edge_data['geometry']
                coords = list(line.coords)
            else:
                # Straight line between nodes
                u_node = graph.nodes[u]
                v_node = graph.nodes[v]
                coords = [(u_node['x'], u_node['y']), (v_node['x'], v_node['y'])]
            
            # Add coordinates to route
            for coord in coords:
                route_pts.append((coord[1], coord[0]))  # (lat, lon)
            
            # Determine flood level for this road segment
            flood_level = 0
            for coord in coords:
                level = get_flood_level((coord[1], coord[0]))
                if level > flood_level:
                    flood_level = level
            
            # Assign color based on flood level
            if flood_level == 0:
                color = "green"
            elif flood_level == 1:
                color = "#FFCC00"  # Yellow orange
            elif flood_level == 2:
                color = "#FF9900"  # Orange
            elif flood_level >= 3:
                color = "#FF0000"  # Red
            else:
                color = "gray"
            
            # Store color for this segment
            segment_colors[(u, v)] = color
        
        return route_pts, segment_colors
    except Exception as e:
        st.error(f"Routing error: {str(e)}")
        return None, {}

# Create flood visualization map with draggable markers
def create_flood_map():
    # Determine map bounds based on start/end points
    points = [st.session_state.start_point, st.session_state.end_point]
    if st.session_state.route:
        points += st.session_state.route
    
    # Calculate center and zoom
    lats = [p[0] for p in points]
    lons = [p[1] for p in points]
    center_lat = (min(lats) + max(lats)) / 2
    center_lon = (min(lons) + max(lons)) / 2
    
    # Create map
    m = folium.Map(
        location=[center_lat, center_lon], 
        zoom_start=12, 
        tiles="CartoDB positron",  # Light theme map
        control_scale=True,
        prefer_canvas=True
    )
    
    # Fit map to include all points
    m.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]])
    
    # Add flood overlay if toggled
    if st.session_state.show_flood_overlay and flood_gdf is not None:
        # High-contrast blue shades based on flood level
        flood_style = {
            0: {'fillColor': '#1e90ff', 'color': '#1e90ff', 'fillOpacity': 0.2},
            1: {'fillColor': '#0066cc', 'color': '#0066cc', 'fillOpacity': 0.4},
            2: {'fillColor': '#004c99', 'color': '#004c99', 'fillOpacity': 0.6},
            3: {'fillColor': '#003366', 'color': '#003366', 'fillOpacity': 0.8},
            4: {'fillColor': '#001a33', 'color': '#001a33', 'fillOpacity': 0.9}
        }
        
        folium.GeoJson(
            flood_gdf,
            style_function=lambda feature: {
                'fillColor': flood_style.get(feature['properties']['Var']), 
                'color': flood_style.get(feature['properties']['Var']),
                'weight': 1,
                'fillOpacity': flood_style.get(feature['properties']['Var'])['fillOpacity']
            },
            name='Flood Areas'
        ).add_to(m)
    
    # Add draggable markers
    start_marker = folium.Marker(
        location=st.session_state.start_point,
        popup="Start Point (Drag me)",
        icon=folium.Icon(color="green", icon="play", prefix="fa"),
        draggable=True
    )
    start_marker.add_to(m)
    
    end_marker = folium.Marker(
        location=st.session_state.end_point,
        popup="End Point (Drag me)",
        icon=folium.Icon(color="red", icon="flag", prefix="fa"),
        draggable=True
    )
    end_marker.add_to(m)
    
    # Add route if it exists
    if st.session_state.road_colors and st.session_state.route:
        # Get the graph to reconstruct the route segments
        graph = ox.graph_from_place("Metro Manila, Philippines", network_type="drive")
        
        # Draw the route
        for (u, v), color in st.session_state.road_colors.items():
            edge_data = graph.get_edge_data(u, v)[0]
            if 'geometry' in edge_data:
                line = edge_data['geometry']
                coords = [(coord[1], coord[0]) for coord in line.coords]  # (lat, lon)
            else:
                u_node = graph.nodes[u]
                v_node = graph.nodes[v]
                coords = [(u_node['y'], u_node['x']), (v_node['y'], v_node['x'])]
            
            folium.PolyLine(
                locations=coords,
                color=color,
                weight=5,
                opacity=0.9,
                popup="Route"
            ).add_to(m)
    
    return m

# Main app layout
if flood_gdf is None:
    st.error("Flood data not found! Please ensure shapefile is in the app directory.")
    st.stop()

# Create columns with controls on the left
col1, col2 = st.columns([1, 2])  # Left column smaller for controls

with col1:
    # Search functionality
    st.markdown("### Search Locations")
    
    # Use forms to enable Enter key submission
    with st.form(key='start_form'):
        start_search = st.text_input("Start Location", 
                                   value=st.session_state.start_search,
                                   key="start_search_input",
                                   placeholder="e.g., Manila City Hall")
        start_search_submitted = st.form_submit_button("🔍 Search Start")
    
    with st.form(key='end_form'):
        end_search = st.text_input("Destination Location", 
                                 value=st.session_state.end_search,
                                 key="end_search_input",
                                 placeholder="e.g., Makati CBD")
        end_search_submitted = st.form_submit_button("🔍 Search Destination")
    
    # Handle search actions
    if start_search_submitted and start_search:
        new_location = geocode_location(start_search)
        if new_location:
            st.session_state.start_point = new_location
            st.session_state.start_search = start_search
            st.session_state.route = None
            st.session_state.road_colors = {}
            st.session_state.map_key = str(time.time())
            st.rerun()
        else:
            st.error("Location not found. Try a different query.")
    
    if end_search_submitted and end_search:
        new_location = geocode_location(end_search)
        if new_location:
            st.session_state.end_point = new_location
            st.session_state.end_search = end_search
            st.session_state.route = None
            st.session_state.road_colors = {}
            st.session_state.map_key = str(time.time())
            st.rerun()
        else:
            st.error("Location not found. Try a different query.")
    
    # Big Calculate Route button - MOVED BELOW SEARCHES
    calculate_clicked = st.button("Calculate Route", 
                                 type="primary", 
                                 use_container_width=True,
                                 key="big_button",
                                 help="Find the shortest route"
                                 )
    
    # Flood overlay toggle with warning
    st.session_state.show_flood_overlay = st.checkbox(
        "Show Flood Areas Overlay (Very Slow)",
        value=st.session_state.show_flood_overlay,
        key="flood_toggle"
    )
    
    # Instructions
    st.markdown("""
    <div class="instruction-box">
        <h3>How to Use</h3>
        <p>1. Search or drag markers to set locations</p>
        <p>2. Click Calculate Route</p>
        <p>3. Roads are colorized by flood level:</p>
        <p style="margin-left: 20px;">• <span style="color: green">Green</span>: No flood</p>
        <p style="margin-left: 20px;">• <span style="color: #FFCC00">Yellow Orange</span>: Level 1 flood</p>
        <p style="margin-left: 20px;">• <span style="color: #FF9900">Orange</span>: Level 2 flood</p>
        <p style="margin-left: 20px;">• <span style="color: red">Red</span>: Level 3+ flood</p>
        <p>4. Flood overlay shows risk areas in blue shades</p>
        <p>5. <strong>Warning:</strong> Flood overlay may slow down map rendering</p>
    </div>
    """, unsafe_allow_html=True)

    # Handle route calculation
    if calculate_clicked:
        st.session_state.is_loading = True
        st.rerun()

with col2:
    # Show loading indicator instead of map during calculation
    if st.session_state.is_loading:
        st.markdown("""
        <div class="loading-container">
            <div>
                <h3>Calculating Route</h3>
                <div style="font-size: 3em;">⏳</div>
                <p>Processing road network data...</p>
                <p>Analyzing flood levels...</p>
                <p>Finding optimal route...</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Calculate the route
        route_points, road_colors = find_route(
            st.session_state.start_point, 
            st.session_state.end_point
        )
        
        if route_points:
            # Store route and colors
            st.session_state.route = route_points
            st.session_state.road_colors = road_colors
            
            # Reset map key to force clean rerender
            st.session_state.map_key = str(time.time())
        
        st.session_state.is_loading = False
        st.rerun()
    else:
        # Show map loading indicator for initial load
        if not st.session_state.map_initialized:
            with st.spinner("Loading map..."):
                flood_map = create_flood_map()
                st.session_state.map_initialized = True
        else:
            flood_map = create_flood_map()
        
        # Display the map in a container
        map_data = st_folium(
            flood_map, 
            height=800,
            width=800,
            key=st.session_state.map_key,
            returned_objects=["last_object_clicked_tooltip", "last_clicked"]
        )
        
        # Handle marker drag events
        if map_data.get("last_object_clicked_tooltip"):
            tooltip = map_data["last_object_clicked_tooltip"]
            clicked_location = map_data["last_clicked"]
            
            if "Start Point" in tooltip:
                st.session_state.start_point = [clicked_location["lat"], clicked_location["lng"]]
                st.session_state.start_search = ""  # Clear search since user moved marker
            elif "End Point" in tooltip:
                st.session_state.end_point = [clicked_location["lat"], clicked_location["lng"]]
                st.session_state.end_search = ""  # Clear search since user moved marker
            
            # Reset map key to force clean rerender
            st.session_state.map_key = str(time.time())
            st.session_state.route = None
            st.session_state.road_colors = {}
            st.rerun()

# Updated footer
st.markdown("""
<div class="footer">
    Flood data: Metro Manila 100-Year Flood from Project NOAH | Routing: OpenStreetMap | Geocoding: Nominatim
</div>
""", unsafe_allow_html=True)