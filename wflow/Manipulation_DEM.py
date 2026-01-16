
import os
import xarray as xr
import numpy as np
import geopandas as gpd

import pandas as pd

# pyflwdir
import pyflwdir

# hydromt
from hydromt import DataCatalog, flw

# plot
import matplotlib.pyplot as plt
from matplotlib import cm, colors


# FOR buller

ds_hydro_org_buller_001 = xr.open_dataarray(fr"H:\Julia\buller_folder_001\buller_nosea_4326.tif")
gdf_riv_org_buller_001 = gpd.read_file(fr"H:\NZ_merged_rec23_rec24\river_uparea_strorder.geojson")


# convert uparea column to numeric
gdf_riv_org_buller_001["uparea"] = pd.to_numeric(
    gdf_riv_org_buller_001["uparea"], errors="coerce"
)




# Derive flow directions with outlets at the edges -> this is the default
da_flwdir_buller_001 = flw.d8_from_dem(
    da_elv=ds_hydro_org_buller_001.squeeze(),
    max_depth=-1,  # max depression poir point depth; -1 means no local pits
    outlets="edge",  # option: "edge" (default), "min", "idxs_pit"
    idxs_pit=None,
    gdf_riv=gdf_riv_org_buller_001,  # user supplied river network to aid flow direction derivation
    riv_burn_method="uparea",  # options: "fixed" (default), "rivdph", "uparea"
    # riv_depth=5, # fixed river depth in meters, only used if riv_burn_method="fixed"
    # **kwargs to be passed to pyflwdir.dem.fill_depressions
)

# convert to vector for plotting based no minimum stream order
flwdir_buller_001 = flw.flwdir_from_da(da_flwdir_buller_001, ftype="infer", check_ftype=True)
gdf_riv_buller_001 = gpd.GeoDataFrame.from_features(
    flwdir_buller_001.streams(min_sto=3), crs=da_flwdir_buller_001.raster.crs
)

# Create a new ds_hydro dataset with the riverburn flow directions
ds_hydro_buller_001 = da_flwdir_buller_001.to_dataset(name="flwdir")
ds_hydro_buller_001 = ds_hydro_buller_001.raster.gdal_compliant()  # update spatial metadata
dims_buller_001 = ds_hydro_buller_001.raster.dims

# add hydrological corrected elevation based on Yamazaki et al. (2012)
elevtn_buller_001 = flwdir_buller_001.dem_adjust(elevtn=ds_hydro_org_buller_001.squeeze().values)
attrs_buller_001 = dict(_FillValue=-9999, long_name="corrected elevation", units="m")
ds_hydro_buller_001["elevtn"] = xr.Variable(dims_buller_001, elevtn_buller_001, attrs=attrs_buller_001)

# uparea (Note that this requires all upstream areas to be included.)
uparea_buller_001 = flwdir_buller_001.upstream_area(unit="km2")
attrs_buller_001 = dict(_FillValue=-9999, long_name="upstream area", units="km2")
ds_hydro_buller_001["uparea"] = xr.Variable(dims_buller_001, uparea_buller_001, attrs=attrs_buller_001)

# stream order (Note that this requires all upstream areas to be included.)
strord_buller_001 = flwdir_buller_001.stream_order()
attrs_buller_001 = dict(_FillValue=np.uint8(225), long_name="stream order", units="-")
ds_hydro_buller_001["strord"] = xr.Variable(dims_buller_001, strord_buller_001, attrs=attrs_buller_001)


# slope
slope_buller_001 = pyflwdir.dem.slope(
    elevtn=ds_hydro_buller_001["elevtn"].values,
    nodata=ds_hydro_buller_001["elevtn"].raster.nodata,
    latlon=ds_hydro_buller_001.raster.crs.is_geographic,  # True if geographic crs, False if projected crs
    transform=ds_hydro_buller_001["elevtn"].raster.transform,
)
attrs_buller_001 = dict(_FillValue=-9999, long_name="lndslp", units="m/m")
ds_hydro_buller_001["lndslp"] = xr.Variable(dims_buller_001, slope_buller_001, attrs=attrs_buller_001)

# basin at the pits locations
basins_buller_001 = flwdir_buller_001.basins(idxs=flwdir_buller_001.idxs_pit).astype(np.int32)
attrs_buller_001 = dict(_FillValue=0, long_name="basin ids", units="-")
ds_hydro_buller_001["basins"] = xr.Variable(dims_buller_001, basins_buller_001, attrs=attrs_buller_001)

# basin index file
gdf_basins_buller_001 = ds_hydro_buller_001["basins"].raster.vectorize()



### Exporting the newly created data and corresponding data catalog


# Export the gridded data as tif files in a new folder
output_path_buller_001 = r"H:\Julia\buller_folder_001\buller_merit_data"

# export the hydrography data as tif files (one per variable)
ds_hydro_buller_001.raster.to_mapstack(
    root=os.path.join(output_path_buller_001, "ds_hydro_buller_001"),
    driver="GTiff",
)

# export the basin index as geosjon
gdf_basins_buller_001.to_file(
    os.path.join(output_path_buller_001, "da_hydro_basins_buller_001.geojson"), driver="GeoJSON"
)


gdf_basins_buller_002 = gdf_basins_buller_001.copy(deep=True)

gdf_basins_buller_002 = gdf_basins_buller_002.rename(columns={'value': "basid"})

# export the basin index as geosjon
gdf_basins_buller_002.to_file(
    os.path.join(output_path_buller_001, "da_hydro_basins_buller_002.gpkg")
)


%%writefile H : /Juli a /buller_folder_00 1 /buller_merit_dat a /data_catalog.yml
ds_hydro_buller_001:
data_type: RasterDataset
driver: raster
path: . /{variable}.tif
rename:
slope: lndslp
meta:
category: topography
processing_notes: prepared from MERIT Hydro using hydromt d8_from_dem and pyflwdir
processing_script: prepare_ldd.ipynb from hydromt_wflow repository

da_hydro_new_index:
data_type: GeoDataFrame
driver: vector
path: . /da_hydro_basins_buller_001.geojson
rename:
value: basid
meta:
processing_notes: prepared from MERIT Hydro using hydromt d8_from_dem and pyflwdir
processing_script: prepare_ldd.ipynb from hydromt_wflow repository



data_catalog = DataCatalog(data_libs=r"H:\Julia\buller_folder_001\buller_merit_data\data_catalog.yml")

ds_hydro_new = data_catalog.get_rasterdataset("ds_hydro_buller_001")
ds_hydro_new