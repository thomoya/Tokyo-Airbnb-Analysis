import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import numpy as np

# --- SAFETY CHECK FOR STATSMODELS ---
try:
    import statsmodels
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False

# 1. Page Configuration
st.set_page_config(page_title="Tokyo Airbnb Explorer", layout="wide")
st.title("Tokyo Airbnb Market Explorer")

# --- SESSION STATE ---
if 'selected_id' not in st.session_state:
    st.session_state.selected_id = None

# 2. Helper for Distance Calculation
def calculate_distance(lat1, lon1, lat2, lon2):
    return np.sqrt((lat1 - lat2)**2 + (lon1 - lon2)**2) * 111

# 3. Data Loading & Cleaning
@st.cache_data
def load_data():
    try:
        df = pd.read_csv('data/listings.csv', low_memory=False)
        df = df.dropna(subset=['latitude', 'longitude', 'price'])
        if df['price'].dtype == 'O':
            df['price'] = df['price'].replace({'\$': '', ',': ''}, regex=True).astype(float)
        
        # FEATURE ENGINEERING: Proximity to NEAREST Station
        try:
            with open('data/stations.geojson', encoding='utf-8') as f:
                station_json = json.load(f)
            station_coords = [(feat['geometry']['coordinates'][1], feat['geometry']['coordinates'][0]) for feat in station_json['features']]
            def get_min_station_dist(lat, lon):
                return min([calculate_distance(lat, lon, s[0], s[1]) for s in station_coords])
            df['dist_to_nearest_station'] = df.apply(lambda row: get_min_station_dist(row['latitude'], row['longitude']), axis=1)
        except:
            df['dist_to_nearest_station'] = 0.5 
        
        # FEATURE ENGINEERING: Value Index
        df['value_index'] = (df['number_of_reviews'] / ((df['price'] + 1) * (df['dist_to_nearest_station'] + 0.5))) * 1000
        df['reviews_per_month'] = df['reviews_per_month'].fillna(0)
        
        price_cap = df['price'].quantile(0.95)
        df = df[df['price'] <= price_cap]
        df['number_of_reviews'] = df['number_of_reviews'].fillna(0)
        return df
    except FileNotFoundError:
        st.error("listings.csv not found.")
        return pd.DataFrame()

@st.cache_data
def load_reviews():
    try:
        df = pd.read_csv('data/reviews.csv.gz', usecols=['listing_id', 'date', 'comments'])
        df['date'] = pd.to_datetime(df['date'])
        return df
    except:
        try: 
            df = pd.read_csv('data/reviews.csv', usecols=['listing_id', 'date', 'comments'])
            df['date'] = pd.to_datetime(df['date'])
            return df
        except: return pd.DataFrame()

def get_station_list():
    try:
        with open('data/stations.geojson', encoding='utf-8') as f:
            data = json.load(f)
        return {f['properties'].get('name', 'Unknown'): (f['geometry']['coordinates'][1], f['geometry']['coordinates'][0]) for f in data['features']}
    except: return {"Shinjuku": (35.6896, 139.7005)}

data = load_data()
reviews_data = load_reviews()
stations_dict = get_station_list()

if data.empty:
    st.stop()

# GLOBAL COLOR MAP
ROOM_COLOR_MAP = {
    "Entire home/apt": "#636EFA",
    "Private room": "#EF553B",
    "Shared room": "#00CC96",
    "Hotel room": "#AB63FA"
}

# 4. Sidebar Filters (Apply to all tabs)
st.sidebar.header("Global Filters")
if st.sidebar.button("Clear Selection"):
    st.session_state.selected_id = None
    st.rerun()

st.sidebar.markdown("---")
color_by_value = st.sidebar.toggle("Highlight Hidden Gems on Map", value=True)
room_types_list = data['room_type'].unique()
selected_room_type = st.sidebar.multiselect("Select Room Type(s):", room_types_list, default=room_types_list)
price_range = st.sidebar.slider("Select Price Range (Yen):", int(data['price'].min()), int(data['price'].max()), (int(data['price'].min()), int(data['price'].max())))
top_neighbourhoods = data['neighbourhood'].value_counts().nlargest(15).index.tolist()
selected_neighbourhoods = st.sidebar.multiselect("Select Ward(s):", top_neighbourhoods, default=top_neighbourhoods[:5])

st.sidebar.markdown("---")
show_transit = st.sidebar.checkbox("Show Major Transit Lines", value=True)
show_stations = st.sidebar.checkbox("Show Major Train Stations", value=True)
show_borders = st.sidebar.checkbox("Show Bolder Ward Borders", value=True)
show_landmarks = st.sidebar.checkbox("Show Major Landmarks", value=True)

filtered_data = data[
    (data['room_type'].isin(selected_room_type)) &
    (data['price'].between(price_range[0], price_range[1])) &
    (data['neighbourhood'].isin(selected_neighbourhoods))
].reset_index(drop=True)

# Smart Default
if not filtered_data.empty:
    if st.session_state.selected_id is None or st.session_state.selected_id not in filtered_data['id'].values:
        st.session_state.selected_id = filtered_data.nlargest(1, 'value_index')['id'].values[0]

# --- TAB DEFINITION ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Project Introduction", 
    "Market Overview", 
    "Geospatial Map", 
    "Value Rankings", 
    "Connectivity Analysis"
])

# TAB 1: INTRODUCTION & METHODOLOGY
with tab1:
    st.header("Research Motivation")
    st.markdown("""
    Tokyo travelers often face a difficult trade-off between nightly cost and proximity to major transit hubs. 
    This project identifies 'Hidden Gems'—listings that offer high popularity and transit connectivity at a lower price point.
    """)
    st.subheader("The Optimization Formula")
    st.markdown("We calculated a custom **Value Index** for every listing using the following methodology:")
    st.latex(r'''\text{Value Index} = \left( \frac{\text{Success (Total Reviews)}}{(\text{Price} + 1) \times (\text{Distance to Station} + 0.5)} \right) \times 1000''')

# TAB 2: MARKET OVERVIEW (Density & Room Types)
with tab2:
    st.header("Tokyo Market Composition")
    
    # Ward Density Chart
    st.subheader("Listing Density by Ward")
    ward_counts = filtered_data['neighbourhood'].value_counts().reset_index()
    ward_counts.columns = ['Ward', 'Listing Count']
    fig_density = px.bar(ward_counts, x='Listing Count', y='Ward', orientation='h',
                         color='Listing Count', color_continuous_scale='Viridis',
                         labels={'Listing Count': 'Number of Listings', 'Ward': 'Ward'},
                         template="plotly_white", height=500)
    fig_density.update_layout(yaxis={'categoryorder':'total ascending'}, coloraxis_showscale=False)
    st.plotly_chart(fig_density, use_container_width=True)

    st.markdown("---")
    
    # Room Type Analysis
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.subheader("Inventory Distribution")
        fig_pie = px.pie(filtered_data, names='room_type', hole=0.4,
                         color='room_type', color_discrete_map=ROOM_COLOR_MAP,
                         labels={'room_type': 'Room Type'}, height=400)
        st.plotly_chart(fig_pie, use_container_width=True)
    with col_c2:
        st.subheader("Average Booking Rate")
        room_success = filtered_data.groupby('room_type')['reviews_per_month'].mean().sort_values(ascending=False).reset_index()
        fig_success = px.bar(room_success, x='room_type', y='reviews_per_month',
                             color='room_type', color_discrete_map=ROOM_COLOR_MAP,
                             labels={'room_type': 'Room Type', 'reviews_per_month': 'Avg. Reviews Per Month'},
                             height=400, template="plotly_white")
        fig_success.update_layout(showlegend=False)
        st.plotly_chart(fig_success, use_container_width=True)

# TAB 3: GEOSPATIAL MAP & INSPECTOR
with tab3:
    st.header("Geospatial Value Analysis")
    color_col = "value_index" if color_by_value else "price"
    color_label = "Value Index" if color_by_value else "Price (Yen)"
    color_scale = px.colors.sequential.Bluered if color_by_value else px.colors.sequential.Viridis

    fig_map = px.scatter_mapbox(
        filtered_data, lat="latitude", lon="longitude", color=color_col,
        size="number_of_reviews", size_max=15, color_continuous_scale=color_scale,
        hover_name="name",
        hover_data={"neighbourhood": True, "price": True, "value_index": ":.2f", "dist_to_nearest_station": ":.2f", "id": True, "latitude": False, "longitude": False},
        labels={"neighbourhood": "Ward", "price": "Price (Yen)", "value_index": "Value Index", "dist_to_nearest_station": "Distance to Station (km)", "id": "Listing ID"},
        zoom=11, mapbox_style="carto-positron", height=600
    )
    fig_map.update_layout(coloraxis_colorbar=dict(title=color_label))

    # Trace Logic (Black Stations, Yellow Landmarks, Cyan Highlight)
    if st.session_state.selected_id:
        sel_row = filtered_data[filtered_data['id'] == st.session_state.selected_id]
        if not sel_row.empty:
            fig_map.add_trace(go.Scattermapbox(lat=sel_row['latitude'], lon=sel_row['longitude'], mode='markers',
                                               marker=go.scattermapbox.Marker(size=30, color='Cyan', opacity=0.3), name='Selection Glow', hoverinfo='none'))
            fig_map.add_trace(go.Scattermapbox(lat=sel_row['latitude'], lon=sel_row['longitude'], mode='markers',
                                               marker=go.scattermapbox.Marker(size=18, color='Cyan', opacity=0.9), name='Selected Pick', hoverinfo='none'))
    if show_stations:
        s_names, s_coords = list(stations_dict.keys()), list(stations_dict.values())
        fig_map.add_trace(go.Scattermapbox(lat=[c[0] for c in s_coords], lon=[c[1] for c in s_coords], mode='markers', name='Stations',
                                           marker=go.scattermapbox.Marker(size=8, color='Black', opacity=0.8), text=s_names, hoverinfo='text'))
    if show_landmarks:
        l_data = {"name": ["Tokyo Skytree", "Tokyo Tower", "Senso-ji Temple", "Shibuya Crossing", "Imperial Palace"],
                  "lat": [35.7101, 35.6586, 35.7148, 35.6595, 35.6852], "lon": [139.8107, 139.7454, 139.7967, 139.7005, 139.7528]}
        fig_map.add_trace(go.Scattermapbox(lat=l_data["lat"], lon=l_data["lon"], mode='markers', name='Landmarks',
                                           marker=go.scattermapbox.Marker(size=14, color='Yellow', opacity=1.0), text=l_data["name"], hoverinfo='text'))

    # GeoJSON Layers
    layers = []
    if show_borders:
        try:
            with open('data/neighbourhoods.geojson', encoding='utf-8') as f:
                ward_json = json.load(f)
            f_feats = [f for f in ward_json['features'] if f['properties']['neighbourhood'] in selected_neighbourhoods]
            layers.append({"sourcetype": "geojson", "source": {"type": "FeatureCollection", "features": f_feats}, "type": "fill", "color": "rgba(100, 149, 237, 0.20)", "below": "traces"})
            layers.append({"sourcetype": "geojson", "source": {"type": "FeatureCollection", "features": f_feats}, "type": "line", "color": "rgba(0, 0, 0, 0.8)", "line": {"width": 3}})
        except: pass
    if show_transit:
        try:
            with open('data/transit_lines.geojson', encoding='utf-8') as f:
                t_json = json.load(f)
            for feat in t_json['features']:
                layers.append({"sourcetype": "geojson", "source": feat, "type": "line", "color": feat['properties']['color'], "line": {"width": 4}, "opacity": 0.5})
        except: pass

    fig_map.update_layout(mapbox_layers=layers, margin={"r":0,"t":0,"l":0,"b":0}, showlegend=False)
    map_event = st.plotly_chart(fig_map, use_container_width=True, on_select="rerun")
    if map_event and "selection" in map_event and map_event["selection"]["points"]:
        point = map_event["selection"]["points"][0]
        if point.get("curve_number") == 0: st.session_state.selected_id = filtered_data.iloc[point["point_index"]]['id']

    st.markdown("---")
    st.subheader("Listing Inspector")
    if not reviews_data.empty:
        filtered_data['display_name'] = filtered_data['name'] + " (ID: " + filtered_data['id'].astype(str) + ")"
        display_names = filtered_data['display_name'].tolist()
        idx = display_names.index(filtered_data[filtered_data['id'] == st.session_state.selected_id]['display_name'].values[0]) if st.session_state.selected_id else 0
        selected_display = st.selectbox("Select property to view feedback:", display_names, index=idx)
        new_id = int(selected_display.split("ID: ")[1].replace(")", ""))
        if new_id != st.session_state.selected_id:
            st.session_state.selected_id = new_id
            st.rerun()
        l_reviews = reviews_data[reviews_data['listing_id'] == st.session_state.selected_id].sort_values(by='date', ascending=False).head(5)
        for _, row in l_reviews.iterrows(): st.info(f"**{row['date'].strftime('%Y-%m-%d')}**: {row['comments']}")

# TAB 4: RANKINGS
with tab4:
    st.header("Top 10 Bang-for-your-Buck Rankings")
    if not filtered_data.empty:
        top_10_df = filtered_data.nlargest(10, 'value_index').sort_values('value_index', ascending=True)
        fig_top10 = px.bar(top_10_df, x='value_index', y='name', orientation='h', color='value_index', 
                           color_continuous_scale='Bluered', height=500, template="plotly_white",
                           labels={'value_index': 'Value Index Score', 'name': 'Listing Name'})
        fig_top10.update_layout(coloraxis_showscale=False)
        bar_event = st.plotly_chart(fig_top10, use_container_width=True, on_select="rerun")
        if bar_event and "selection" in bar_event and bar_event["selection"]["points"]:
            st.session_state.selected_id = top_10_df.iloc[bar_event["selection"]["points"][0]["point_index"]]['id']

# TAB 5: STATISTICAL PROOF (Proximity & Spread)
with tab5:
    st.header("Market Distribution Analysis")
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Dynamic Proximity Premium")
        target_st = st.selectbox("Select hub to measure distance against:", list(stations_dict.keys()), index=0)
        filtered_data['dynamic_hub_dist'] = filtered_data.apply(lambda r: calculate_distance(r['latitude'], r['longitude'], stations_dict[target_st][0], stations_dict[target_st][1]), axis=1)
        trend_mode = "ols" if HAS_STATSMODELS else None
        fig_scatter = px.scatter(filtered_data, x="dynamic_hub_dist", y="price", color="neighbourhood",
                                 labels={"dynamic_hub_dist": "Distance to Hub (km)", "price": "Price (Yen)", "neighbourhood": "Ward"},
                                 height=450, template="plotly_white", trendline=trend_mode)
        st.plotly_chart(fig_scatter, use_container_width=True)
    with col_b:
        st.subheader("Price Spread by Ward and Room Type")
        fig_box = px.box(filtered_data, x="neighbourhood", y="price", color='room_type', color_discrete_map=ROOM_COLOR_MAP,
                        labels={"neighbourhood": "Ward", "price": "Price (Yen)", "room_type": "Room Type"}, height=515, template="plotly_white")
        st.plotly_chart(fig_box, use_container_width=True)