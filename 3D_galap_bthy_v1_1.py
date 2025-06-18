# -*- coding: utf-8 -*-
"""
Created on Fri Mar 21 12:51:27 2025

@author: Jackson Vaughn
"""


import dash
from dash import html, dcc
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import os
from dash import Output, Input, no_update
from flask import send_from_directory
import traceback


def download_and_load_npy(url, filename):
    if not os.path.exists(filename):
        r = requests.get(url)
        with open(filename, "wb") as f:
            f.write(r.content)
    return np.load(filename)

def download_and_load_csv(url, filename):
    if not os.path.exists(filename):
        r = requests.get(url)
        with open(filename, "wb") as f:
            f.write(r.content)
    return pd.read_csv(filename)

# === URLs for preprocessed data ===
#URLs must end with =1
urls = {
    "chl_log": "https://www.dropbox.com/scl/fi/l6r4z084e9vc7jrxwqaax/chl_log.npy?rlkey=4413078s7fjxx3kkibpx46nc2&st=p8ogpvjv&dl=1",
    "corals": "https://www.dropbox.com/scl/fi/u49xm0r9oux55odotph73/corals.csv?rlkey=hh8jc2p8v4fteqa35gogc52te&st=ivnflb2b&dl=1",
    "elev": "https://www.dropbox.com/scl/fi/pzc3ma0fxohw02acl70p2/elev_cropped.npy?rlkey=c24riiy3awxnrpnqo4n4jm6yi&st=erw70wjs&dl=1",
    "land": "https://www.dropbox.com/scl/fi/300jkfyx7tnbzqn725977/land_elev.npy?rlkey=oe6y5rdh71lqp1yh3l452bro2&st=c2sld1oy&dl=1",
    "lat": "https://www.dropbox.com/scl/fi/u0i7pctzjjz2zq3wxzk9i/lat_cropped.npy?rlkey=4rgk2ztu61wu5nbuwg8hvurc9&st=v7gniso6&dl=1",
    "lon": "https://www.dropbox.com/scl/fi/3i9nt38ysk592vbh4qulb/lon_cropped.npy?rlkey=7486zx7fupfx70zf7ejjf1bak&st=omk27lkg&dl=1"
}


# === Download and load data ===
lon_cropped = download_and_load_npy(urls["lon"], "lon_cropped.npy")
lat_cropped = download_and_load_npy(urls["lat"], "lat_cropped.npy")
elev_cropped = download_and_load_npy(urls["elev"], "elev_cropped.npy")
land_elev = download_and_load_npy(urls["land"], "land_elev.npy")
chl_log = download_and_load_npy(urls["chl_log"], "chl_log.npy")
df = download_and_load_csv(urls["corals"], "corals.csv")
# residuals_log = np.log10(np.where(df['Residuals_Avg'] > 0, df['Residuals_Avg'], np.nan))

# === Plotting layers ===
scatter_layer = go.Scatter3d(
    x=df['Longitude'], 
    y=df['Latitude'], 
    z=df['Depth'], 
    mode='markers',
    marker=dict(
        size=5, 
        color='purple',#residuals_log,
        #colorscale='Peach',
        opacity=0.9,
        # colorbar=dict(
        #     title="Barium<br>Residuals",
        #     tickvals=[np.log10(v) for v in [0.01, 0.1, 1, 10]],
        #     ticktext=['0.01', '0.1', '1', '10']
        # )
    ),
    name=""
)

scatter_layer_invisible = go.Scatter3d(
    x=df['Longitude'], 
    y=df['Latitude'], 
    z=df['Depth'], 
    mode='markers',
    marker=dict(size=40, color='rgba(0,0,0,0)'),
    name=""
)

scatter_layer.update(hoverinfo="none", hovertemplate=None)
scatter_layer_invisible.update(hoverinfo="none", hovertemplate=None)


bathymetry_surface = go.Surface(
    z=elev_cropped,
    x=lon_cropped,
    y=lat_cropped,
    surfacecolor=chl_log,
    colorscale='Viridis',
    cmin=np.nanmin(chl_log), 
    cmax=np.nanmax(chl_log),
    colorbar=dict(
        title="Chlorophyll-a (mg/m³)<br>04.07.2011-04.08.2011",
        x=-0.15,
        len=0.75,
        tickvals=[np.log10(v) for v in [0.5, 1, 8]],
        ticktext=['0.5', '1', '8']
    ),
    opacity=0.5,
    name=""
)

land_surface = go.Surface(
    z=land_elev,
    x=lon_cropped,
    y=lat_cropped,
    colorscale=[[0, "black"], [1, "black"]],
    showscale=False,
    name=""
)

fig = go.Figure(data=[bathymetry_surface, land_surface, scatter_layer, scatter_layer_invisible])
fig.update_layout(
    scene=dict(
        xaxis_title="Longitude",
        yaxis_title="Latitude",
        zaxis_title="Elevation (m)",
        zaxis=dict(range=[elev_cropped.min(), elev_cropped.max()]),
        aspectmode='manual',
        aspectratio=dict(x=1, y=1, z=0.2)
    ),
    showlegend=False
)

# ==== Dash App ====
app = dash.Dash(__name__)

server = app.server  # Dash wraps Flask
@server.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

@app.callback(
    Output("graph-tooltip", "show"),
    Output("graph-tooltip", "children"),
    Input("graph-3d", "hoverData"),
    Input("graph-3d", "clickData"),
    Input("device-type", "data"),
)
def display_hover_or_click(hoverData, clickData, device_type):
    try:
        if device_type == 'mobile':
            trigger_data = clickData
        else:
            trigger_data = hoverData

        if trigger_data is None:
            return False, no_update

        pt = trigger_data["points"][0]
        x = pt["x"]
        y = pt["y"]
        z = pt["z"]

        # Match row by coordinates
        match = df[
            (abs(df["Longitude"] - x) < 1e-6) &
            (abs(df["Latitude"] - y) < 1e-6) &
            (abs(df["Depth"] - z) < 1e-6)  
        ]

        if match.empty:
            print("No matching point found!")
            return False, no_update

        df_row = match.iloc[0]
        img_src = df_row['img_src']

        children = [
            html.Div([
                html.Img(src=img_src, style={"width": "100%"}),
                html.H2("Corals located here are shown in green", style={"color": "black", "overflow-wrap": "break-word", "fontSize": "10px"})
            ], style={'width': '400px', 'white-space': 'normal'})
        ]

        return True, children

    except Exception as e:
        print("ERROR IN TOOLTIP CALLBACK:", e)
        return False, no_update

app.clientside_callback(
    """
    function(n_intervals) {
        var isMobile = /iPhone|iPad|iPod|Android|webOS|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
        return isMobile ? 'mobile' : 'desktop';
    }
    """,
    Output('device-type', 'data'),
    Input('device-check-trigger', 'n_intervals')
)

app.layout = html.Div([
    html.H1("3D Bathymetric Map of the Galapagos", style={'textAlign': 'center'}),

    html.P(["Hello wonderful supervisors - this interactive plot displays stylasterid coral sample locations and satellite derived chlorophyll concentrations. ",
           "Scroll to zoom, left click to rotate, right click to pan. Hover over points to see details."],
           style={'textAlign': 'center', 'margin': '20px auto', 'maxWidth': '800px'}),
    
    dcc.Loading(
        type="circle",
        fullscreen=True,
        children=dcc.Graph(id="graph-3d", figure=fig, clear_on_unhover=True, style={'height': '90vh'})

    ),
    dcc.Tooltip(id="graph-tooltip"),

    dcc.Store(id='device-type'),
    dcc.Interval(id="device-check-trigger", interval=100, n_intervals=0, max_intervals=1),

    
    
    
    

    html.P(["Chlorophyll-a and barium residuals are log-scaled. Barium residuals are calculated as ",
           "the absolute difference between James' regression and the averaged Ba/Ca of the subsamples"],
           style={'textAlign': 'center', 'margin': '20px auto', 'maxWidth': '800px'}
           ),
    
    html.P([
    "Chlorophyll data: ",
    html.A(
        "NASA MODIS-Aqua (2022)",
        href="https://doi.org/10.5067/AQUA/MODIS/L3M/CHL/2022",
        target="_blank",
        style={"textDecoration": "underline"}
    ),
    ", hosted by NASA OB.DAAC"
    ], style={'textAlign': 'center', 'fontSize': '14px', 'marginTop': '30px'}),
        
        html.P([
        "Bathymetry data: ",
        html.A(
            "NOAA Tsunami DEM for the Galápagos region",
            href="https://www.ncei.noaa.gov/access/metadata/landing-page/bin/iso?id=gov.noaa.ngdc.mgg.dem:11516",
            target="_blank",
            style={"textDecoration": "underline"}
        ),
        ", courtesy of NOAA NCEI and the Pacific Marine Environmental Lab"
    ], style={'textAlign': 'center', 'fontSize': '14px'}),
        
        html.P("For more information please contact the developer at jackson.vaughn@bristol.ac.uk",
               style={'textAlign': 'center', 'margin': '20px auto', 'maxWidth': '800px'}),
        

        
    ])




if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port, debug=False)

#To improve:
    #Integrate NASA api so users can choose date of chlorophyll
    #Add dropdown to choose which element in tooltips and colormap
    #Add ability to choose colormap
    #Group points to display tooltips of all points there. 
    #Add at5009 bathymetry data
    #Fix loading screen
    #Add marker differences
    #Add a different marker for sediment core data, and add image in the tooltips
    #Add vertical exaggeration - or fix to true scale?
    #Add readme
    #Add background
    #Look into using yt for chlorophyll data
    #Fix to replace land values with np.nan - and go back to lower resolution
    #Look into tiling it
    
    