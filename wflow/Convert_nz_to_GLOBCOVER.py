# -*- coding: utf-8 -*-
"""
Created on Mon Nov 24 12:51:55 2025

@author: mng42
"""

import geopandas as gpd

nz_landcover = gpd.read_file(fr"S:\FloodRiskResearch\Martin\WRF-Hydro\landcover\landv6\lris-lcdb-v60-land-cover-database-version-60-mainland-new-zealand-SHP\lcdb-v60-land-cover-database-version-60-mainland-new-zealand.shp")

nz_to_globcover = {
    0: 210,   # Not land -> water

    # Urban & infrastructure
    1: 190,
    2: 140,
    5: 190,
    6: 200,
    10: 200,
    12: 200,
    16: 200,

    # Snow & alpine
    14: 220,
    15: 150,

    # Water
    20: 210,
    21: 210,
    22: 210,

    # Croplands
    30: 14,
    33: 20,

    # Grasslands
    40: 140,
    41: 140,
    43: 140,
    44: 140,

    # Wetlands
    45: 120,
    46: 180,
    47: 120,

    # Shrublands
    50: 130,
    51: 130,
    52: 130,
    54: 130,
    55: 130,
    56: 130,
    58: 130,
    80: 130,
    81: 130,

    # Mangrove
    70: 180,

    # Forests
    68: 60,
    69: 40,
    71: 70,
    64: 200
}

# Map NZ LCDB classes to GlobCover
nz_landcover['GlobCover_2023'] = nz_landcover['Class_2023'].map(nz_to_globcover)

# Check
nz_landcover[['Class_2023', 'GlobCover_2023']].head(10)
nz_landcover_4326 = nz_landcover.to_crs(epsg=4326)
nz_landcover_4326['GlobCover_2023'] = nz_landcover_4326['GlobCover_2023'].astype('int32')

###############################################################################

import xarray as xr
import rasterio
from rasterio.features import rasterize
from affine import Affine
import numpy as np

# Use the 4326 GeoDataFrame
gdf = nz_landcover_4326

# Define raster resolution in degrees
pixel_size = 0.000595  # ~50m, 100m: 0.0009
minx, miny, maxx, maxy = gdf.total_bounds

# Raster size
width = int((maxx - minx) / pixel_size)
height = int((maxy - miny) / pixel_size)

# Affine transform
transform = Affine.translation(minx, maxy) * Affine.scale(pixel_size, -pixel_size)

shapes = ((geom, value) for geom, value in zip(nz_landcover_4326.geometry, nz_landcover_4326['GlobCover_2023']))
out_shape = (height, width)  # your raster dimensions
transform = transform   # rasterio transform

raster = rasterize(
    shapes,
    out_shape=out_shape,
    fill=0,
    transform=transform,
    dtype=np.int32
)

with rasterio.open(
    r"H:\NZ_landcover_landuse\nz_globcover_4326_50m_003.tif",
    "w",
    driver="GTiff",
    height=raster.shape[0],
    width=raster.shape[1],
    count=1,
    dtype=raster.dtype,  # int32
    crs="EPSG:4326",
    transform=transform,
    nodata=0,            # <-- set nodata explicitly
) as dst:
    dst.write(raster, 1)



# Check
with rasterio.open(r"H:\NZ_landcover_landuse\nz_globcover_4326_50m_002.tif") as src:
    print(src.dtypes)       # should be int32
    print(src.nodata)       # should be 0
















###############################################################################


import xarray as xr
import rasterio
from rasterio.features import rasterize
from affine import Affine
import numpy as np

# Use the 4326 GeoDataFrame
gdf = nz_landcover_4326

# Define raster resolution in degrees
pixel_size = 0.000595  # ~50m, 100m: 0.0009
minx, miny, maxx, maxy = gdf.total_bounds

# Raster size
width = int((maxx - minx) / pixel_size)
height = int((maxy - miny) / pixel_size)

# Affine transform
transform = Affine.translation(minx, maxy) * Affine.scale(pixel_size, -pixel_size)

# Rasterize
shapes = ((geom, value) for geom, value in zip(gdf.geometry, gdf['GlobCover_2023']))
raster = rasterize(
    shapes=shapes,
    out_shape=(height, width),
    fill=np.nan,  # missing areas as NaN
    transform=transform,
    dtype='float32'
)

# Create x and y coordinates (center of pixels)
x = np.linspace(minx + pixel_size/2, maxx - pixel_size/2, width)
y = np.linspace(maxy - pixel_size/2, miny + pixel_size/2, height)

# Create DataArray with band dimension
da = xr.DataArray(
    raster[np.newaxis, :, :],  # add band dimension
    dims=('band', 'y', 'x'),
    coords={'band': [1], 'x': x, 'y': y},
    name='GlobCover_2023',
    attrs={'spatial_ref': 4326, 'AREA_OR_POINT': 'Area'}
)

# Save as GeoTIFF
da.rio.to_raster(r"H:\NZ_landcover_landuse\nz_globcover_4326_50m_002.tif")

print("GeoTIFF saved successfully!")



###############################################################################

ex = xr.open_dataarray(fr"C:\Users\mng42\.hydromt_data\artifact_data\v0.0.9\data.tar\globcover.tif")



