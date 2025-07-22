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
            margin-bottom: 15px;
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
        }
    </style>
""", unsafe_allow_html=True)

# App title with tight layout
st.markdown("""
    <div class="title-container">
        <h1>🌧️ Metro Manila Route Visualizer</h1>
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
if "route_points" not in st.session_state:
    st.session_state.route_points = None
if "is_loading" not in st.session_state:
    st.session_state.is_loading = False
if "start_search" not in st.session_state:
    st.session_state.start_search = ""
if "end_search" not in st.session_state:
    st.session_state.end_search = ""

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

# Create flood visualization map with draggable markers
def create_flood_map():
    # Create light-themed map
    m = folium.Map(
        location=[14.5995, 120.9842], 
        zoom_start=12, 
        tiles="CartoDB positron",  # Light theme map
        control_scale=True,
        prefer_canvas=True
    )
    
    # High-contrast blue shades for flood levels
    flood_colors = {
        1.0: "#6baed6",  # Light Blue
        2.0: "#2171b5",  # Medium Blue
        3.0: "#08306b"   # Dark Blue
    }
    
    # Add flood zones only if they intersect the route
    if flood_gdf is not None and st.session_state.route_points:
        # Create route LineString
        route_line = LineString([(point[1], point[0]) for point in st.session_state.route_points])
        
        # Find intersecting floods
        intersecting_floods = flood_gdf[flood_gdf.intersects(route_line)]
        
        for _, row in intersecting_floods.iterrows():
            depth = row['Var']
            color = flood_colors.get(depth, "#6baed6")
            
            folium.GeoJson(
                row['geometry'],
                style_function=lambda feature, color=color: {
                    'fillColor': color,
                    'color': '#000000',
                    'weight': 1,
                    'fillOpacity': 0.8
                }
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
    if st.session_state.route_points is not None:
        folium.PolyLine(
            locations=st.session_state.route_points,
            color="#FF5733",
            weight=5,
            opacity=0.9,
            popup="Fastest Route"
        ).add_to(m)
    
    return m

# Find fastest route between points
def find_fastest_route(start, end):
    try:
        # Get road network for Metro Manila
        graph = ox.graph_from_place("Metro Manila, Philippines", network_type="drive")
        
        # Convert points to (y, x) format (latitude, longitude)
        start_point = (start[0], start[1])
        end_point = (end[0], end[1])
        
        # Get nearest nodes
        orig_node = ox.distance.nearest_nodes(graph, X=[start_point[1]], Y=[start_point[0]])[0]
        dest_node = ox.distance.nearest_nodes(graph, X=[end_point[1]], Y=[end_point[0]])[0]
        
        # Find shortest path
        route = nx.shortest_path(graph, orig_node, dest_node, weight="length")
        
        # Get route coordinates
        route_points = []
        for node in route:
            point = graph.nodes[node]
            route_points.append((point['y'], point['x']))
        
        return route_points
    except Exception as e:
        st.error(f"Routing error: {str(e)}")
        return None

# Main app layout
if flood_gdf is None:
    st.error("Flood data not found! Please ensure shapefile is in the app directory.")
    st.stop()

# Create columns with controls on the left
col1, col2 = st.columns([1, 2])  # Left column smaller for controls

with col1:
    # Search functionality
    st.markdown("### Search Locations")
    
    # Start location search
    start_col1, start_col2 = st.columns([3, 1])
    with start_col1:
        start_search = st.text_input("Start Location", 
                                   value=st.session_state.start_search,
                                   key="start_search_input",
                                   placeholder="e.g., Manila City Hall")
    with start_col2:
        start_search_clicked = st.button("🔍", 
                                       key="start_search_btn",
                                       help="Search start location",
                                       use_container_width=True)
    
    # End location search
    end_col1, end_col2 = st.columns([3, 1])
    with end_col1:
        end_search = st.text_input("Destination Location", 
                                 value=st.session_state.end_search,
                                 key="end_search_input",
                                 placeholder="e.g., Makati CBD")
    with end_col2:
        end_search_clicked = st.button("🔍", 
                                     key="end_search_btn",
                                     help="Search destination location",
                                     use_container_width=True)
    
    # Handle search actions
    if start_search_clicked and start_search:
        new_location = geocode_location(start_search)
        if new_location:
            st.session_state.start_point = new_location
            st.session_state.start_search = start_search
            st.session_state.route_points = None
            st.session_state.map_key = str(time.time())
            st.rerun()
        else:
            st.error("Location not found. Try a different query.")
    
    if end_search_clicked and end_search:
        new_location = geocode_location(end_search)
        if new_location:
            st.session_state.end_point = new_location
            st.session_state.end_search = end_search
            st.session_state.route_points = None
            st.session_state.map_key = str(time.time())
            st.rerun()
        else:
            st.error("Location not found. Try a different query.")
    
    # Instructions
    st.markdown("""
    <div class="instruction-box">
        <h3>How to Use</h3>
        <p>1. Search or drag markers to set locations</p>
        <p>2. Click Calculate Route</p>
        <p>3. Route appears in orange</p>
        <p>4. Floods intersecting route are shown</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Big Calculate Route button
    calculate_clicked = st.button("Calculate Route", 
                                 type="primary", 
                                 use_container_width=True,
                                 key="big_button",
                                 help="Find the fastest route between markers"
                                 )
    
    # Simplified legend
    st.markdown("""
    <div class="legend-box">
        <h3>Map Legend</h3>
        <div style="display: flex; align-items: center; margin-bottom: 10px;">
            <div style="width: 20px; height: 20px; background-color: green; margin-right: 10px;"></div>
            <span>Start Point</span>
        </div>
        <div style="display: flex; align-items: center; margin-bottom: 10px;">
            <div style="width: 20px; height: 20px; background-color: red; margin-right: 10px;"></div>
            <span>End Point</span>
        </div>
        <div style="display: flex; align-items: center; margin-bottom: 10px;">
            <div style="width: 20px; height: 3px; background-color: #FF5733; margin-right: 10px;"></div>
            <span>Route</span>
        </div>
        <div style="display: flex; align-items: center; margin-bottom: 10px;">
            <div style="width: 20px; height: 20px; background-color: #6baed6; margin-right: 10px; border: 1px solid #000;"></div>
            <span>Flood Area</span>
        </div>
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
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Actually calculate the route
        route_points = find_fastest_route(
            st.session_state.start_point, 
            st.session_state.end_point
        )
        
        if route_points:
            # Store route for display
            st.session_state.route_points = route_points
            # Reset map key to force clean rerender
            st.session_state.map_key = str(time.time())
        
        st.session_state.is_loading = False
        st.rerun()
    else:
        # Show map loading indicator for initial load
        if not st.session_state.map_initialized:
            with st.spinner("Loading flood map..."):
                flood_map = create_flood_map()
                st.session_state.map_initialized = True
        else:
            flood_map = create_flood_map()
        
        # Display the map in a container
        map_data = st_folium(
            flood_map, 
            height=600,
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
            st.session_state.route_points = None
            st.rerun()

# Updated footer
st.markdown("""
<div class="footer">
    Flood data: Metro Manila 100-Year Flood from Project NOAH | Routing: OpenStreetMap | Geocoding: Nominatim
</div>
""", unsafe_allow_html=True)