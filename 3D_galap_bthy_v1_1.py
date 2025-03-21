# -*- coding: utf-8 -*-
"""
Created on Fri Mar 21 12:51:27 2025

@author: kw24171
"""

import dash
from dash import html, dcc
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import os

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
urls = {
    "chl_log": "https://www.dropbox.com/scl/fi/yrpyq75j5mky1l4yj9tzu/chl_log.npy?rlkey=zu7osjr41uz82matcf96hxq5o&st=uzht8bdz&dl=1",
    "corals": "https://www.dropbox.com/scl/fi/1oycf677oxyie6lrtnq74/corals.csv?rlkey=9qibrb6348irh6s19lr38emzp&st=kausdzf9&dl=1",
    "elev": "https://www.dropbox.com/scl/fi/lg4zvnex8jfa2mx7mdv0d/elev_cropped.npy?rlkey=v7u36a1434cjknbvoamj9cjfn&st=2btu3v17&dl=1",
    "land": "https://www.dropbox.com/scl/fi/su6nnm3as2ng58a2uorjw/land_elev.npy?rlkey=sbcild64c7w2scawcl92zgvsa&st=t7jgfo4y&dl=1",
    "lat": "https://www.dropbox.com/scl/fi/bizejcjeovjje2fzwf6hn/lat_cropped.npy?rlkey=vk2ao8ugohlt537trgcrvnh7f&st=giw4zdi8&dl=1",
    "lon": "https://www.dropbox.com/scl/fi/6benhekucshvah4clj290/lon_cropped.npy?rlkey=snxq4awe9lyjgvvkzb7qag9ev&st=7pfep1ey&dl=1"
}

# === Download and load data ===
lon_cropped = download_and_load_npy(urls["lon"], "lon_cropped.npy")
lat_cropped = download_and_load_npy(urls["lat"], "lat_cropped.npy")
elev_cropped = download_and_load_npy(urls["elev"], "elev_cropped.npy")
land_elev = download_and_load_npy(urls["land"], "land_elev.npy")
chl_log = download_and_load_npy(urls["chl_log"], "chl_log.npy")

df = download_and_load_csv(urls["corals"], "corals.csv")
residuals_log = np.log10(np.where(df['Residuals_Avg'] > 0, df['Residuals_Avg'], np.nan))

# === Plotting layers ===
scatter_layer = go.Scatter3d(
    x=df['Longitude (⁰E)'], 
    y=df['Latitude (⁰N)'], 
    z=df['Depth (m)'], 
    mode='markers',
    marker=dict(
        size=5, 
        color=residuals_log,
        colorscale='Peach',
        opacity=0.8,
        colorbar=dict(
            title="Barium<br>Residuals",
            tickvals=[np.log10(v) for v in [0.01, 0.1, 1, 10]],
            ticktext=['0.01', '0.1', '1', '10']
        )
    ),
    text=df['J_ID'],
    hoverinfo='skip',
    name=""
)

scatter_layer_invisible = go.Scatter3d(
    x=df['Longitude (⁰E)'], 
    y=df['Latitude (⁰N)'], 
    z=df['Depth (m)'], 
    mode='markers',
    marker=dict(size=40, color='rgba(0,0,0,0)'),
    text=df['hover_text'],
    hoverinfo='text',
    name=""
)

bathymetry_surface = go.Surface(
    z=elev_cropped,
    x=lon_cropped,
    y=lat_cropped,
    surfacecolor=chl_log,
    colorscale='Viridis',
    cmin=np.nanmin(chl_log), 
    cmax=np.nanmax(chl_log),
    colorbar=dict(
        title="Chlorophyll-a (mg/m³)",
        x=-0.15,
        len=0.75,
        tickvals=[np.log10(v) for v in [0.01, 0.1, 1, 10]],
        ticktext=['0.01', '0.1', '1', '10']
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
    title="Galapagos",
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
app.layout = html.Div([
    html.H1("3D Bathymetric Map of the Galapagos", style={'textAlign': 'center'}),
    dcc.Graph(figure=fig, style={'height': '90vh'})
])

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port, debug=False)

