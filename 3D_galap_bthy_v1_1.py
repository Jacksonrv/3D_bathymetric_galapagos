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
import xarray as xr
from scipy.interpolate import griddata
import requests
import os

def download_file(url, destination):
    if not os.path.exists(destination):
        r = requests.get(url)
        with open(destination, 'wb') as f:
            f.write(r.content)

def load_excel_data(url):
    df = pd.read_excel(url, sheet_name='Hydrographic_data')
    df['Depth (m)'] = -df['Depth (m)']
    df = df.loc[~df['J_ID'].str.contains('Too small'), :]
    df['Residuals_Avg'] = np.random.rand(len(df))  # Replace with real data
    df['hover_text'] = df.apply(lambda row: f"J_ID: {row['J_ID']}<br>Depth: {row['Depth (m)']:.1f} m", axis=1)
    residuals_log = np.log10(np.where(df['Residuals_Avg'] > 0, df['Residuals_Avg'], np.nan))
    return df, residuals_log

def load_bathymetry(filename, step=20):
    ds = xr.open_dataset(filename, engine="netcdf4", decode_cf=False)
    lon = ds['lon'].values.astype(np.float32)[::step]
    lat = ds['lat'].values.astype(np.float32)[::step]
    elev = ds['Band1'].values.astype(np.float32)[::step, ::step]
    ds.close()
    lon_grid, lat_grid = np.meshgrid(lon, lat)
    mask = (lat_grid <= 1) & (lon_grid <= -88.6)
    elev_cropped = np.where(mask, elev, np.nan)
    land_elev = np.where(elev_cropped >= 0, elev_cropped, np.nan)
    lon_cropped = np.where(mask, lon_grid, np.nan)
    lat_cropped = np.where(mask, lat_grid, np.nan)
    return lon_cropped, lat_cropped, elev_cropped, land_elev

def load_chlorophyll(filename, lon_cropped, lat_cropped):
    chl_nc = xr.open_dataset(filename)
    lon_chl = chl_nc["lon"].values
    lat_chl = chl_nc["lat"].values
    chl_data = chl_nc['chlor_a'].values
    chl_nc.close()

    mask_lon = (lon_chl >= np.nanmin(lon_cropped)) & (lon_chl <= np.nanmax(lon_cropped))
    mask_lat = (lat_chl >= np.nanmin(lat_cropped)) & (lat_chl <= np.nanmax(lat_cropped))

    lon_chl_cropped = lon_chl[mask_lon]
    lat_chl_cropped = lat_chl[mask_lat]
    chl_cropped = chl_data[np.ix_(mask_lat, mask_lon)]

    points = np.column_stack(np.meshgrid(lon_chl_cropped, lat_chl_cropped)).reshape(-1, 2)
    values = chl_cropped.ravel()
    chl_interp = griddata(points, values, (lon_cropped, lat_cropped), method='linear')
    chl_log = np.log10(np.nan_to_num(chl_interp, nan=np.nanmean(values)))
    return chl_log

def build_figure(df, residuals_log, lon_cropped, lat_cropped, elev_cropped, land_elev, chl_log):
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
    return fig

# === MAIN ===
chl_url = "https://dl.dropboxusercontent.com/scl/fi/9i08sk6dgsjyjd9ipf3hb/AQUA_MODIS.20110704_20110804.L3m.R32.CHL.chlor_a.4km.nc?rlkey=vypjr1nfjtml8217d3vnq2pvk&st=wtvbnbbi"
bthy_url = "https://dl.dropboxusercontent.com/scl/fi/14xl41vbgab0u9zyz5hp7/galapagos_1_isl_2016.nc?rlkey=eo8dc3sfqta06orjmykjrrd33&st=ff2nzvlv"
excel_url = "https://drive.google.com/uc?export=download&id=10lriwNKZz9fqeUsOVP_z2YADJephbBdG"

for url, name in [(bthy_url, "bathymetry.nc"), (chl_url, "chlorophyll.nc")]:
    download_file(url, name)

df, residuals_log = load_excel_data(excel_url)
lon_cropped, lat_cropped, elev_cropped, land_elev = load_bathymetry("bathymetry.nc", step=20)
chl_log = load_chlorophyll("chlorophyll.nc", lon_cropped, lat_cropped)
fig = build_figure(df, residuals_log, lon_cropped, lat_cropped, elev_cropped, land_elev, chl_log)

app = dash.Dash(__name__)
app.layout = html.Div([
    html.H1("3D Bathymetric Map of the Galapagos", style={'textAlign': 'center'}),
    dcc.Graph(figure=fig, style={'height': '90vh'})
])

if __name__ == '__main__':
    app.run_server(debug=True)













