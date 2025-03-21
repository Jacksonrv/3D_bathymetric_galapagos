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
from netCDF4 import Dataset
import requests
import os

def download_from_gdrive(file_id, destination):
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    r = requests.get(url)
    with open(destination, 'wb') as f:
        f.write(r.content)
        

chl_url = "https://dl.dropboxusercontent.com/scl/fi/9i08sk6dgsjyjd9ipf3hb/AQUA_MODIS.20110704_20110804.L3m.R32.CHL.chlor_a.4km.nc?rlkey=vypjr1nfjtml8217d3vnq2pvk&st=wtvbnbbi"
bthy_url = "https://dl.dropboxusercontent.com/scl/fi/14xl41vbgab0u9zyz5hp7/galapagos_1_isl_2016.nc?rlkey=eo8dc3sfqta06orjmykjrrd33&st=ff2nzvlv"
excel_url = "https://drive.google.com/uc?export=download&id=10lriwNKZz9fqeUsOVP_z2YADJephbBdG"

r = requests.get(bthy_url)
with open("bathymetry.nc", "wb") as f:
    f.write(r.content)

r = requests.get(chl_url)
with open("chlorophyll.nc", "wb") as f:
    f.write(r.content)









df = pd.read_excel(excel_url, sheet_name='Hydrographic_data')
df['Depth (m)'] = -df['Depth (m)']
df_te = pd.read_excel(r"C:\Users\kw24171\OneDrive - University of Bristol\Desktop\Python\Excel\delete.xlsx", sheet_name='Sheet_name_1')
df_te = df_te.set_index('ID')

residuals_avg_dict = {}
badict = {}
for i, row in df.iterrows():
    matching_indices = [ind for ind in df_te.index if row['J_ID'] in ind]
    
    residual_values = df_te.loc[matching_indices, 'Residuals'].values
    residuals_avg_dict[i] = residual_values.mean() if len(residual_values) > 0 else pd.NA

    ba_values = df_te.loc[matching_indices, 'Ba/Ca'].values
    temp_dict = {'Ba/Ca - '+ind.split('-')[1]: val for ind, val in zip(matching_indices, ba_values)}
    badict[i] = temp_dict

df['Residuals_Avg'] = pd.Series(residuals_avg_dict)

ba_df = pd.DataFrame.from_dict(badict, orient='index').fillna(pd.NA)
df = df.join(ba_df)

df = df.loc[np.array(~df['J_ID'].str.contains('Too small')), :]

df['hover_text'] = df.apply(lambda row: f"J_ID: {row['J_ID']}<br>"
                                        f"O2: {row['[O2] (μmol/kg)']:.2f} μmol/kg<br>"
                                        f"Ba/Ca {row['J_ID']}-1: {row['Ba/Ca - 1']:.2f}<br>"
                                        f"Ba/Ca {row['J_ID']}-2: {row['Ba/Ca - 2']:.2f}<br>"
                                        f"Ba/Ca {row['J_ID']}-t: {row['Ba/Ca - t']:.2f}<br>"
                                        f"Species: {row['Species (Stylasterid_by_Jess_orange_July_2024)']:}<br>", axis=1)
residuals = pd.to_numeric(df['Residuals_Avg'], errors='coerce')
residuals = abs(residuals)
residuals_log = np.log10(np.where(residuals > 0, residuals, np.nan))













ds = xr.open_dataset("bathymetry.nc", engine="netcdf4")

#Convert to float32 to reduce memory consumption
lon = ds['lon'].values.astype(np.float32)  
lat = ds['lat'].values.astype(np.float32)
elev = ds['Band1'].values.astype(np.float32)  

#Downsample data for further memory efficiency
step = 20  #Increase to reduce memory usage
lon = lon[::step]
lat = lat[::step]
elev = elev[::step, ::step]

lon_grid, lat_grid = np.meshgrid(lon, lat)



#Filter to remove unecessary areas of the map
mask = (lat_grid <= 1) & (lon_grid <= -88.6)  

lon_cropped = lon_grid.copy()
lat_cropped = lat_grid.copy()
elev_cropped = elev.copy()

# Set unwanted values to NaN instead of removing them (keeps 2D shape)
lon_cropped[~mask] = np.nan
lat_cropped[~mask] = np.nan
elev_cropped[~mask] = np.nan

#lon_cropped = lon_cropped[mask]
#lat_cropped = lat_cropped[mask]
#elev_cropped = elev_cropped[mask] #could do this method but need to fix array shapes

#Seperate land values to plot as black. Could consider doing this with higher res data
land_elev = elev_cropped.copy()
ocean_mask = elev_cropped < 0  
land_elev[ocean_mask] = np.nan







chl_nc = xr.open_dataset("chlorophyll.nc")

lon_chl = chl_nc["lon"].values
lat_chl = chl_nc["lat"].values
chl_data = chl_nc['chlor_a'].values

lon_min, lon_max = np.nanmin(lon_cropped), np.nanmax(lon_cropped)
lat_min, lat_max = np.nanmin(lat_cropped), np.nanmax(lat_cropped)

# Mask chlorophyll data to only include this range
mask_lon = (lon_chl >= lon_min) & (lon_chl <= lon_max)
mask_lat = (lat_chl >= lat_min) & (lat_chl <= lat_max)

# Apply the mask to crop chlorophyll data
lon_chl_cropped = lon_chl[mask_lon]
lat_chl_cropped = lat_chl[mask_lat]
chl_cropped = chl_data[np.ix_(mask_lat, mask_lon)]

lon_chl_mesh, lat_chl_mesh = np.meshgrid(lon_chl_cropped, lat_chl_cropped)

# Flatten for interpolation
points = np.column_stack((lon_chl_mesh.ravel(), lat_chl_mesh.ravel()))
values = chl_cropped.ravel()

# Interpolate chlorophyll data onto the bathymetric grid
chl_interp = griddata(points, values, (lon_cropped, lat_cropped), method='linear')

# Replace NaN values with zero or mean chlorophyll value if needed
chl_interp = np.nan_to_num(chl_interp, nan=np.nanmean(values))
chl_log = np.log10(np.where(chl_interp > 0, chl_interp, np.nan))












#Plot coral points
scatter_layer = go.Scatter3d(
    x=df['Longitude (⁰E)'], 
    y=df['Latitude (⁰N)'], 
    z=df['Depth (m)'], 
    mode='markers',
    marker=dict(
        size=5, 
        color=residuals_log,
        colorscale='Peach',  # or another valid Plotly colorscale
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

#Plot invisible larger points for corals so that they stick out of map for tool tips
scatter_layer_invisible = go.Scatter3d(
    x=df['Longitude (⁰E)'], 
    y=df['Latitude (⁰N)'], 
    z=df['Depth (m)'], 
    mode='markers',
    marker=dict(size=40, color='rgba(0,0,0,0)'),
    text=df['hover_text'],  # Attach J_ID for hover text
    hoverinfo='text',
    name=""
)

#Plot bathymetry
bathymetry_surface = go.Surface(
    z=elev_cropped,
    x=lon_cropped,
    y=lat_cropped,
    surfacecolor=chl_log,  # <- log-scaled data
    colorscale='Viridis',
    cmin=np.nanmin(chl_log), 
    cmax=np.nanmax(chl_log),
    colorbar=dict(
        title="Chlorophyll-a (mg/m³)",
        x=-0.15,
        len=0.75,
        tickvals=[np.log10(v) for v in [0.01, 0.1, 1, 10]],  # Original scale values
        ticktext=['0.01', '0.1', '1', '10']  # Label them nicely
    ),
    opacity=0.5,
    name=""
)




#Overlay black land
land_surface = go.Surface(
    z=land_elev, x=lon_cropped, y=lat_cropped,
    colorscale=[[0, "black"], [1, "black"]],  # Solid black land
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


# ==== Build the Dash app ====
app = dash.Dash(__name__)
app.layout = html.Div([
    html.H1("3D Bathymetric Map of the Galapagos", style={'textAlign': 'center'}),
    dcc.Graph(figure=fig, style={'height': '90vh'})
])

if __name__ == '__main__':
    app.run_server(debug=True)























