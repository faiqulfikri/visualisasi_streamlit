#!/usr/bin/env python
# coding: utf-8

import streamlit as st
st.set_page_config(layout="wide")
import pandas as pd
import folium
from streamlit_folium import st_folium
from matplotlib import cm, colors
import json
import matplotlib.pyplot as plt
from folium import Map, CircleMarker, LayerControl, GeoJson

# --- CSS Styling ---
st.markdown("""
    <style>
        .main-map-container {
            position: relative;
            width: 95%;
            margin: 0 auto;
            border: 1px solid #ddd;
            border-radius: 8px;
            overflow: hidden;
        }
        .folium-map {
            width: 100% !important;
            height: 70vh !important;
        }
        .summary-overlay-container {
            position: absolute;
            top: 15px;
            right: 15px;
            z-index: 1000;
            width: 280px;
            max-height: 70vh;
            overflow-y: auto;
        }
        .summary-overlay {
            background-color: rgba(255, 255, 255, 0.85);
            padding: 12px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        .summary-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.85rem;
        }
        .summary-table th, .summary-table td {
            padding: 4px 8px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }
        .summary-table th {
            background-color: #f8f9fa;
        }
        .compass-overlay {
            position: absolute;
            bottom: 15px;
            left: 15px;
            z-index: 1000;
            background-color: rgba(255,255,255,0.85);
            padding: 8px 10px;
            border-radius: 8px;
            font-weight: bold;
            font-size: 13px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            border: 1px solid #ccc;
            text-align: center;
            line-height: 1.2;
        }
        .block-container {
            padding-bottom: 0rem !important;
        }
        footer {visibility: hidden;}
        section.main > div:empty {
            display: none;
        }
    </style>
""", unsafe_allow_html=True)

st.title("Sebaran Stasiun BMKG")

# --- Load Data ---
file_path = "Tugas BMKG_Data Peta.xlsx"
xls = pd.ExcelFile(file_path)
sheets_to_plot = ['PHOBS', 'ARG', 'AWS', 'AAWS', 'ASRS', 'IKLIMMIKRO', 'SOIL']

# Ambil dan gabungkan data dari semua sheet
dfs = {
    sheet: xls.parse(sheet)[[
        'NO STASIUN', 'LINTANG', 'BUJUR', 'DESA', 'KECAMATAN', 'KAB/KOTA', 'PROVINSI'
    ]].dropna(subset=['LINTANG', 'BUJUR']).assign(JENIS=sheet)
    for sheet in sheets_to_plot
}

# Normalisasi nama provinsi
def normalize_provinsi(name):
    if not isinstance(name, str):
        return None
    name = name.upper().strip()
    replacements = {
        'NANGGROE ACEH DARUSSALAM': 'ACEH',
        'NANGGROE ACEH DARUSALAM': 'ACEH',
        'KEP. RIAU': 'KEPULAUAN RIAU',
        'KEP. BANGKA BELITUNG': 'KEPULAUAN BANGKA BELITUNG',
        'DI YOGYAKARTA': 'DI YOGYAKARTA',
        'PAPUA BARAT DAYA': 'PAPUA BARAT DAYA'
    }
    return replacements.get(name, name)

# Terapkan normalisasi
for sheet in dfs:
    dfs[sheet]['PROVINSI'] = dfs[sheet]['PROVINSI'].apply(normalize_provinsi)
    for col in dfs[sheet].select_dtypes(include='object').columns:
        dfs[sheet][col] = dfs[sheet][col].str.upper()

# Gabungkan semua data
df_awal = pd.concat(dfs.values(), ignore_index=True)

# Simpan kembali ke dfs berdasarkan JENIS
dfs = {
    jenis: df_awal[df_awal['JENIS'] == jenis].copy()
    for jenis in df_awal['JENIS'].unique()
}
all_data = pd.concat(dfs.values(), ignore_index=True)
all_center = [-2.5489, 119.0149]

# --- Color Palette for 38 Provinces ---
province_colors = {
    'ACEH': '#FF5733',
    'SUMATERA UTARA': '#33FF57',
    'SUMATERA BARAT': '#3357FF',
    'RIAU': '#F333FF',
    'JAMBI': '#33FFF5',
    'SUMATERA SELATAN': '#FF33A1',
    'BENGKULU': '#A1FF33',
    'LAMPUNG': '#33A1FF',
    'KEPULAUAN BANGKA BELITUNG': '#FF8C33',
    'KEPULAUAN RIAU': '#8C33FF',
    'DKI JAKARTA': '#FF3333',
    'JAWA BARAT': '#33FF33',
    'JAWA TENGAH': '#3333FF',
    'DI YOGYAKARTA': '#FFFF33',
    'JAWA TIMUR': '#FF33FF',
    'BANTEN': '#33FFFF',
    'BALI': '#FF9933',
    'NUSA TENGGARA BARAT': '#99FF33',
    'NUSA TENGGARA TIMUR': '#3399FF',
    'KALIMANTAN BARAT': '#FF3399',
    'KALIMANTAN TENGAH': '#9933FF',
    'KALIMANTAN SELATAN': '#33FF99',
    'KALIMANTAN TIMUR': '#FF33CC',
    'KALIMANTAN UTARA': '#33CCFF',
    'SULAWESI UTARA': '#CCFF33',
    'SULAWESI TENGAH': '#FFCC33',
    'SULAWESI SELATAN': '#33FFCC',
    'SULAWESI TENGGARA': '#CC33FF',
    'GORONTALO': '#33CCCC',
    'SULAWESI BARAT': '#CC33CC',
    'MALUKU': '#CCCC33',
    'MALUKU UTARA': '#33CC99',
    'PAPUA BARAT': '#99CC33',
    'PAPUA': '#3399CC',
    'PAPUA SELATAN': '#CC9933',
    'PAPUA TENGAH': '#9933CC',
    'PAPUA PEGUNUNGAN': '#33CC66',
    'PAPUA BARAT DAYA': '#CC6633'
}

# --- Symbol Configuration for Station Types ---
symbol_config = {
    'PHOBS': {'shape': 'circle'},
    'ARG': {'shape': 'hexagon'},
    'AWS': {'shape': 'triangle'}, 
    'AAWS': {'shape': 'square'},
    'ASRS': {'shape': 'star'},
    'IKLIMMIKRO': {'shape': 'pentagon'},
    'SOIL': {'shape': 'diamond'}
}

# --- Sidebar Filter ---
with st.expander("Filter Peta", expanded=True):
    cols = st.columns([2, 2, 2, 2, 1])
    with cols[0]:
        all_jenis = all_data['JENIS'].unique().tolist()
        selected_jenis_raw = st.multiselect("Jenis Stasiun", options=["All"] + all_jenis, default=["All"])
        selected_jenis = all_jenis if "All" in selected_jenis_raw else selected_jenis_raw
    with cols[1]:
        all_provinsi = all_data['PROVINSI'].unique().tolist()
        selected_provinsi = st.selectbox("Provinsi", options=["All"] + all_provinsi)
    with cols[2]:
        if selected_provinsi != "All":
            filtered_by_prov = all_data[all_data['PROVINSI'] == selected_provinsi]
            all_kabupaten = filtered_by_prov['KAB/KOTA'].unique().tolist()
            selected_kab = st.selectbox("Kab/Kota", options=["All"] + all_kabupaten)
        else:
            selected_kab = "All"
            st.selectbox("Kab/Kota", options=["All"], disabled=True)
    with cols[3]:
        if selected_provinsi != "All" and selected_kab != "All":
            filtered_by_kab = filtered_by_prov[filtered_by_prov['KAB/KOTA'] == selected_kab]
            all_kecamatan = filtered_by_kab['KECAMATAN'].unique().tolist()
            selected_kec = st.selectbox("Kecamatan", options=["All"] + all_kecamatan)
        else:
            selected_kec = "All"
            st.selectbox("Kecamatan", options=["All"], disabled=True)
    with cols[4]:
        st.write("")
        apply_filter = st.button("Terapkan", key="apply_button")

    if apply_filter:
        if not selected_jenis:
            st.warning("Silakan pilih minimal satu jenis stasiun sebelum menerapkan filter.")
        else:
            st.session_state['selected_jenis'] = selected_jenis
            st.session_state['selected_provinsi'] = selected_provinsi
            st.session_state['selected_kab'] = selected_kab
            st.session_state['selected_kec'] = selected_kec

sel_jenis = st.session_state.get('selected_jenis', all_jenis)
sel_provinsi = st.session_state.get('selected_provinsi', "All")
sel_kab = st.session_state.get('selected_kab', "All")
sel_kec = st.session_state.get('selected_kec', "All")

filtered_data = all_data[all_data['JENIS'].isin(sel_jenis)]
if sel_provinsi != "All":
    filtered_data = filtered_data[filtered_data['PROVINSI'] == sel_provinsi]
    if sel_kab != "All":
        filtered_data = filtered_data[filtered_data['KAB/KOTA'] == sel_kab]
        if sel_kec != "All":
            filtered_data = filtered_data[filtered_data['KECAMATAN'] == sel_kec]

def create_summary_table(data, group_by_column):
    summary = data.groupby([group_by_column, 'JENIS']).size().unstack(fill_value=0)
    summary['JUMLAH'] = summary.sum(axis=1)
    jenis_order = [j for j in sheets_to_plot if j in summary.columns]
    return summary[jenis_order + ['JUMLAH']]

# --- Build Map ---
m = Map(location=all_center, zoom_start=5, control_scale=True)

geojson_path = "indonesia_provinces.geojson"
with open(geojson_path, 'r', encoding='utf-8') as f:
    geojson_data = json.load(f)

def style_function(feature):
    prov_name = feature['properties']['state'].upper()
    selected = st.session_state.get('selected_provinsi', '').upper()
    is_selected = selected != 'ALL' and prov_name == selected
    return {
        'fillOpacity': 0.3,
        'weight': 1,
        'color': 'black',
        'fillColor': '#888888' if is_selected else '#ffffff'
    }

def popup_function(feature):
    prov_name = feature['properties']['state'].upper()
    prov_data = filtered_data[filtered_data['PROVINSI'].str.upper() == prov_name]
    if prov_data.empty:
        return folium.Popup(f"<b>{prov_name}</b><br>Tidak ada data", max_width=250)
    summary = prov_data.groupby('JENIS').size().reset_index(name='JUMLAH')
    html = f"<b>{prov_name}</b><br>" + "".join(f"{r['JENIS']}: {r['JUMLAH']}<br>" for _, r in summary.iterrows())
    return folium.Popup(html, max_width=400)

for feature in geojson_data['features']:
    GeoJson(feature, style_function=style_function, tooltip=feature['properties']['state'],
            popup=popup_function(feature)).add_to(m)

# --- Custom Markers ---
station_details = {}
for _, row in filtered_data.iterrows():
    coord_key = f"{row['LINTANG']},{row['BUJUR']}"
    station_details[coord_key] = row
    
    jenis = row['JENIS']
    provinsi = row['PROVINSI']
    config = symbol_config.get(jenis, {'shape': 'circle'})
    color = province_colors.get(provinsi, 'gray')
    
    if config['shape'] == 'circle':
        folium.CircleMarker(
            location=[row['LINTANG'], row['BUJUR']],
            radius=1,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=1,
            popup=(f"<b>Jenis:</b> {row['JENIS']}<br>"
                   f"<b>Stasiun:</b> {row['NO STASIUN']}<br>"
                   f"<b>Provinsi:</b> {provinsi}<br>"
                   f"<b>Kab/Kota:</b> {row['KAB/KOTA']}<br>"
                   f"<b>Kecamatan:</b> {row['KECAMATAN']}<br>"
                   f"<b>Desa:</b> {row['DESA']}<br>"
                   f"<a href='https://www.google.com/maps?q={row['LINTANG']},{row['BUJUR']}' target='_blank'>Lihat di Google Maps</a>")
        ).add_to(m)
    else:
        folium.RegularPolygonMarker(
            location=[row['LINTANG'], row['BUJUR']],
            number_of_sides=3 if config['shape'] == 'triangle' else 
                            4 if config['shape'] == 'square' else 
                            5 if config['shape'] == 'pentagon' else 
                            4 if config['shape'] == 'diamond' else 6,
            radius=1,
            rotation=0 if config['shape'] != 'diamond' else 45,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=1,
            popup=(f"<b>Jenis:</b> {row['JENIS']}<br>"
                   f"<b>Stasiun:</b> {row['NO STASIUN']}<br>"
                   f"<b>Provinsi:</b> {provinsi}<br>"
                   f"<b>Kab/Kota:</b> {row['KAB/KOTA']}<br>"
                   f"<b>Kecamatan:</b> {row['KECAMATAN']}<br>"
                   f"<b>Desa:</b> {row['DESA']}<br>"
                   f"<a href='https://www.google.com/maps?q={row['LINTANG']},{row['BUJUR']}' target='_blank'>Lihat di Google Maps</a>")
        ).add_to(m)

m.add_child(folium.ClickForMarker(popup='Koordinat: {lat}, {lng}'))
LayerControl().add_to(m)

# --- Layout: Peta dan Ringkasan ---
col1, col2 = st.columns([3, 1.7])
with col1:
    st.markdown("### Peta Sebaran")
    st_data = st_folium(m, width=1200, height=500, returned_objects=["last_object_clicked"], key="map")
    st.markdown("</div>", unsafe_allow_html=True)

with col2:
    coord_key = None
    if st_data and st_data.get("last_object_clicked"):
        clicked_coords = st_data["last_object_clicked"]
        coord_key = f"{clicked_coords['lat']},{clicked_coords['lng']}"

    if coord_key and coord_key in station_details:
        station = station_details[coord_key]
        st.markdown("### Detail Stasiun")
        st.markdown(f"""
                        **Jenis:** {station['JENIS']}  
                        **Nomor Stasiun:** {station['NO STASIUN']}  
                        **Provinsi:** {station['PROVINSI']}  
                        **Kab/Kota:** {station['KAB/KOTA']}  
                        **Kecamatan:** {station['KECAMATAN']}  
                        **Desa:** {station['DESA']}  
                        **Koordinat:** {station['LINTANG']:.4f}, {station['BUJUR']:.4f}  
                        [Lihat di Google Maps](https://www.google.com/maps?q={station['LINTANG']},{station['BUJUR']})
                        """)
    else:
        if sel_provinsi == "All":
            summary_table = create_summary_table(filtered_data, 'PROVINSI')
            summary_title = "Jumlah Stasiun per Provinsi"
        elif sel_kab == "All":
            summary_table = create_summary_table(filtered_data, 'KAB/KOTA')
            summary_title = f"Jumlah Stasiun per Kab/Kota di {sel_provinsi}"
        elif sel_kec == "All":
            summary_table = create_summary_table(filtered_data, 'KECAMATAN')
            summary_title = f"Jumlah Stasiun per Kecamatan di {sel_kab}"
        else:
            summary_table = create_summary_table(filtered_data, 'DESA')
            summary_title = f"Jumlah Stasiun per Desa di {sel_kec}"

        st.markdown(f"### {summary_title}")
        st.dataframe(summary_table, height=500, use_container_width=True)