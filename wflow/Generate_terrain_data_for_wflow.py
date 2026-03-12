import os
import xarray as xr
import numpy as np
import geopandas as gpd

import pandas as pd

# pyflwdir
import pyflwdir
from PyQt5.QtGui import QVector2D

# hydromt
from hydromt import DataCatalog, flw

from pathlib import Path

# plot
import matplotlib.pyplot as plt
from matplotlib import cm, colors


class TerrainDataWflow:
    def __init__(
            self,
            path
    ):
        """
        https://deltares.github.io/hydromt_wflow/stable/_examples/prepare_ldd.html
        Parameters
        ----------
        path
        """
        self.path = path
        self.ds_hydro_org = xr.open_dataarray(fr"{self.path}\dem_for_wflow_coarser_nodeps_crs.tif")
        self.gdf_riv_org = gpd.read_file(fr"{self.path}\streams_d8_area_strahler.shp")

        # Convert uparea column to numeric
        self.gdf_riv_org['uparea'] = pd.to_numeric(
            self.gdf_riv_org['uparea'], errors='coerce'
        )


    def d8_flow_direction_generator(self):
        """

        Returns
        -------

        """
        # Derive flow directions with outlets at the edges
        da_flwdir = flw.d8_from_dem(
            da_elv=self.ds_hydro_org.squeeze(),
            max_depth=-1,  # max depression poir point depth; -1 means no local pits
            outlets="edge",  # option: "edge" (default), "min", "idxs_pit"
            idxs_pit=None,
            gdf_riv=self.gdf_riv_org,  # user supplied river network to aid flow direction derivation
            riv_burn_method="uparea",  # options: "fixed" (default), "rivdph", "uparea"
            # riv_depth=5, # fixed river depth in meters, only used if riv_burn_method="fixed"
            # **kwargs to be passed to pyflwdir.dem.fill_depressions
        )

        # Convert to vector
        flwdir = flw.flwdir_from_da(
            da_flwdir,
            ftype='infer',
            check_ftype=True
        )

        # Create a new ds_hydro dataset with the riverburn flow directions
        ds_hydro = da_flwdir.to_dataset(name='flwdir')
        ds_hydro = ds_hydro.raster.gdal_compliant()

        # Extract dimesions
        dims = ds_hydro.raster.dims

        return flwdir, ds_hydro, dims


    def terrain_and_stream_generator(
            self,
            flwdir,
            ds_hydro,
            dims,
            long_name,
            units,
            variable_name
    ):
        """

        Returns
        -------

        """
        terrain_data = flwdir.dem_adjust(
            elevtn = self.ds_hydro_org.squeeze().values
        )
        attrs = dict(
            _FillValue = -9999,
            long_name = long_name,
            units = units
        )

        ds_hydro[f'{variable_name}'] = xr.Variable(
            dims,
            terrain_data,
            attrs=attrs
        )

        return ds_hydro


    def slope_generator(
            self,
            ds_hydro,
            dims
    ):
        """

        Returns
        -------

        """
        # Generate slope
        slope = pyflwdir.dem.slope(
            elevtn = ds_hydro['elevtn'].values,
            nodata = ds_hydro['elevtn'].raster.nodata,
            latlon = ds_hydro.raster.crs.is_geographic, # True if geographic crs, False if projected crs
            transform = ds_hydro['elevtn'].raster.transform
        )

        # Generate attributes for the slope
        attrs = dict(
            _FillValue = -9999,
            long_name = 'lndslp',
            units = 'm/m'
        )

        # Add to hydro dataset
        ds_hydro['lndslp'] = xr.Variable(
            dims,
            slope,
            attrs=attrs
        )

        return ds_hydro


    def basin_generator(
            self,
            flwdir,
            ds_hydro,
            dims
    ):
        """

        Returns
        -------

        """
        # Generate basin
        basins = flwdir.basins(
            idxs = flwdir.idxs_pit
        ).astype(np.int32)

        # Generate attributes
        attrs = dict(
            _FillValue = 0,
            long_name = 'basin ids',
            units='-'
        )

        # Add basins to the hydro dataset
        ds_hydro['basins'] = xr.Variable(
            dims,
            basins,
            attrs = attrs
        )

        # Add basins to geopandas dataframe
        gdf_basins = ds_hydro['basins'].raster.vectorize()

        return ds_hydro, gdf_basins


    def write_out_hydro_dataset(
            self,
            ds_hydro,
            gdf_basins
    ):
        # Write out hydro dataset
        ds_hydro.raster.to_mapstack(
            root = os.path.join(
                self.path,
                'merit_hydro'
            ),
            driver='GTiff'
        )

        # Rename basins column
        gdf_basins = gdf_basins.rename(
            columns = {'value': 'basid'}
        )

        # Write out basin dataframe
        gdf_basins.to_file(
            os.path.join(
                self.path,
                'da_hydro_basins.gpkg'
            )
        )


    def terrain_data_for_wflow_generator(
            self
    ):

        # Generate D8 flow direction
        flwdir, ds_hydro, dims = self.d8_flow_direction_generator()

        # Generate elevation data
        ds_elevation = self.terrain_and_stream_generator(
            flwdir,
            ds_hydro,
            dims,
            'corrected elevation',
            'm',
            'elevtn'
        )

        # Generate upstream area
        ds_upstream_area = self.terrain_and_stream_generator(
            flwdir,
            ds_elevation,
            dims,
            'upstream area',
            'km2',
            'uparea'
        )

        # Generate stream strahler order
        ds_strord = self.terrain_and_stream_generator(
            flwdir,
            ds_upstream_area,
            dims,
            'stream order',
            '-',
            'strord'
        )

        # Generate slope data
        ds_slope = self.slope_generator(
            ds_strord,
            dims
        )

        # Generate basins
        ds_basins, gdf_basins = self.basin_generator(
            flwdir,
            ds_slope,
            dims
        )

        # Write out hydro dataset
        self.write_out_hydro_dataset(
            ds_basins,
            gdf_basins
        )