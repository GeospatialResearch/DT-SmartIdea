from whitebox_workflows import PhotometricInterpretation, RasterDataType, WbEnvironment
from whitebox.whitebox_tools import WhiteboxTools
import math
from pathlib import Path

import xarray as xr
import rioxarray as rxr
import numpy as np
from scipy.ndimage import distance_transform_edt

import geopandas as gpd
import pandas as pd

from rasterstats import zonal_stats

from typing import Any

wbe = WbEnvironment()
wbe.verbose = True
wbe.max_procs = -1

wbt = WhiteboxTools()

class CommonVariable:
    def __init__(
            self,
            path: str
    ):
        """
        A class contains common variables

        Parameters
        -----------
        path : str
            Path to raster that needs manipulating
        """
        self.path = path


class TerrainAttributesGenerator(CommonVariable):
    def __init__(
            self,
            path: str,
            raster_name: str = 'dem'
    ):
        """
        A class to generate terrain attributes

        Parameters
        ----------
        path : str
            Path to raster that needs manipulating
        raster_name : str = 'dem'
            Name of the raster. Mostly 'dem' and 'roughness'
        """
        super().__init__(path)
        self.raster_name = raster_name


    def raster_resampling(
            self,
            resolution_crs_4326 : float = 0.00045,
            resampling_method : str = 'nn'
    ) -> None:
        """
        Resample raster to a specific resolution (good with GeoTiff file)

        Parameters
        -----------
        resolution_crs_4326 : float = 0.00045
            Resolution value in crs 4326. Default is 0.00045 (~100 m)
        resampling_method : str = 'nn'
            Resampling methods includes "nn" (nearest neighbor), 'bilinear',
            and 'cc' (cubic convolution). Default is 'nn'
        """
        if not Path(fr"{self.path}\{self.raster_name}_for_wflow_coarser.tif").is_file():
            # Resample raster
            wbt.resample(
                inputs=fr"{self.path}\{self.raster_name}_for_wflow.tif",
                output=fr"{self.path}\{self.raster_name}_for_wflow_coarser.tif",
                cell_size=resolution_crs_4326,
                method=resampling_method
            )
        else:
            print(f"'{self.raster_name}_for_wflow_coarser.tif' already exists!")


    def raster_fill_depression(
            self,
            flat_increment : float = 0.0001
    ) -> None:
        """
        Fill depressions in raster (specifically in DEM)

        Parameters
        ----------
        flat_increment : float = 0.0001
            If flat surfaces suck as lakes have the slope 0 it will act like a sink.
            This parameter will set a small slope to flat areas. Default is 0.0001.
            https://github.com/williamlidberg/Whitebox-tutorial/blob/main/streams.py
        """
        if not Path(fr"{self.path}\{self.raster_name}_for_wflow_coarser_nodeps_crs.tif").is_file():
            # Read the raster using whitebox tool
            raster_no_deps = wbe.read_raster(
                fr"{self.path}\{self.raster_name}_for_wflow_coarser.tif"
            )

            # Fill depressions in the raster
            raster_no_deps = wbe.fill_depressions(
                raster_no_deps,
                flat_increment=flat_increment
            )

            # Write out
            wbe.write_raster(
                raster_no_deps,
                fr"{self.path}\{self.raster_name}_for_wflow_coarser_nodeps.tif",
                compress=False
            )

            # Read data using rioxarray to add crs and then overwrite out
            raster_no_deps_crs = rxr.open_rasterio(fr"{self.path}\{self.raster_name}_for_wflow_coarser_nodeps.tif")
            raster_no_deps_crs = raster_no_deps_crs.rio.write_crs('EPSG:4326')
            raster_no_deps_crs.rio.to_raster(fr"{self.path}\{self.raster_name}_for_wflow_coarser_nodeps_crs.tif")



        else:
            print(f"'{self.raster_name}_for_wflow_coarser_nodeps_crs.tif' already exists!")

    def d8_pointer_generator(self) -> None:
        """
        Generate D8 pointers based on D8 algorithm (O'Callaghan and Mark, 1984) (mainly from DEM)
        https://www.whiteboxgeo.com/manual/wbw-user-manual/book/tool_help.html#d8_pointer
        """
        if not Path(fr"{self.path}\d8_pointer.tif").is_file():
            # Read the raster using whitebox tool
            raster_no_deps = wbe.read_raster(
                fr"{self.path}\{self.raster_name}_for_wflow_coarser_nodeps_crs.tif"
            )

            # Generate D8 pointer
            d8_pointer = wbe.d8_pointer(raster_no_deps)

            # Write out raster
            wbe.write_raster(
                d8_pointer,
                fr"{self.path}\d8_pointer.tif"
            )
        else:
            print(f"'d8_pointer.tif' already exists!")


    def d8_stream_generator(
            self,
            threshold: int = 25000,
            catchment_area: bool = True
    ) -> None:
        """
        Generate D8 flow accumulation based on D8 algorithm (O'Callaghan and Mark, 1984) (mainly from DEM)

        Parameters
        -----------
        threshold : int = 10000
            Minimum number of cells/upslope area required to initiate and main a channel.
        catchment_area : bool = True
            If True, flow accumulation under catchment are format will be added
            If False, only flow accumulation under cell format will be generated
        """
        if not Path(fr"{self.path}\streams_d8.tif").is_file():
            # Generate D8 flow accumulation - output is 'cell' type
            wbt.d8_flow_accumulation(
                i = fr"{self.path}\{self.raster_name}_for_wflow_coarser_nodeps_crs.tif",
                out_type = 'cells',
                output = fr'{self.path}\flow_acc_d8_cells.tif'
            )

            # Extract streams from the flow accumulation
            wbt.extract_streams(
                flow_accum = fr"{self.path}\flow_acc_d8_cells.tif",
                output = fr"{self.path}\streams_d8.tif",
                threshold = threshold
            )
        else:
            print(f"'streams_d8.tif' already exists!")

        if catchment_area:
            if not Path(fr'{self.path}\flow_acc_d8_area_m2.tif').is_file():
                # Generate D8 flow accumulation - output is 'catchment area' type
                wbt.d8_flow_accumulation(
                    i=fr"{self.path}\{self.raster_name}_for_wflow_coarser_nodeps_crs.tif",
                    out_type="catchment area",
                    output=fr'{self.path}\flow_acc_d8_area_m2.tif'
                )
            else:
                print(fr"'flow_acc_d8_area_m2.tif' already exists!")
        else:
            pass


    def strahler_stream_order_generator(self) -> None:
        """
        Generate Strahler stream order based on Strahler algorithm (Strahler, A. N., 1957)
        and convert to vector
        https://www.whiteboxgeo.com/manual/wbt_book/available_tools/stream_network_analysis.html#strahlerstreamorder
        https://www.whiteboxgeo.com/manual/wbt_book/available_tools/stream_network_analysis.html?highlight=extract%20stream#RasterStreamsToVector
        """
        # Generate stream order
        wbt.strahler_stream_order(
            d8_pntr=fr"{self.path}\d8_pointer.tif",
            streams=fr"{self.path}\streams_d8.tif",
            output=fr"{self.path}\strahler_d8.tif"
        )

        # Convert stream raster to vector shapefile
        wbt.raster_streams_to_vector(
            d8_pntr=fr"{self.path}\d8_pointer.tif",
            streams=fr"{self.path}\streams_d8.tif",
            output=fr"{self.path}\streams_d8.shp"
        )


    def raster_to_points_dataframe(
            self,
            file_name: str,
            output_name: str,
            column_name: str
    ) -> gpd.GeoDataFrame:
        """
        Convert raster values of pixels in stream network (could be area or strahler) to points

        Parameters
        -----------
        file_name : str
            Name of the file that will be used to convert to points
        output_name : str
            Name of output file that contains point shape type
        column_name : str
            Name of column that is converted from 'VALUE1' to
            Options are mostly 'upstream_area_m2' and 'strahler'

        Returns
        ---------
        points_df : gpd.GeoDataFrame
            A GeoDataFrame contains points data of 'upstream_area_m2' or 'strahler'
        """
        if file_name != 'strahler_d8':
            # Convert raster to point shapefile
            wbt.raster_to_vector_points(
                i=fr"{self.path}\streams_d8.tif",
                output=fr"{self.path}\stream_pixels_pts.shp"
            )
        else:
            pass

        # Convert raster to vector of point shape type from flow accumulation
        wbt.extract_raster_values_at_points(
            fr"{self.path}\{file_name}.tif",
            points=fr"{self.path}\stream_pixels_pts.shp"
        )

        # Convert to geopandas dataframe
        points_df = gpd.read_file(fr"{self.path}\stream_pixels_pts.shp")
        points_df = points_df.rename(columns={'VALUE1': f'{column_name}'})

        return points_df


    def roughness_to_manning(
            self,
            roughness: Any,
            h: float = 1
    ):
        """

        Parameters
        ----------
        roughness : Any
            A raster of roughness data
        h : float = 1
            Value of depth. Default is 1

        Returns
        -------

        """
        # Convert roughness length to Manning's n
        manning_n = (0.41 * (h ** (1 / 6)) * ((h / roughness) - 1)) / (np.sqrt(9.80665) * (1 + (h / roughness) * (np.log(h / roughness) - 1)))

        # Write out Manning's n
        manning_n.rio.to_raster(
            fr"{self.path}\streams_manning.tif"
        )


class StreamTopologyGenerator(CommonVariable):
    def __init__(
            self,
            path: str
    ):
        """
        A class that generates stream topology: 'upstream_area_m2' and 'strahler'

        Parameters
        ----------
        path : str
            Path to raster that needs manipulating
        """
        super().__init__(path)
        self.stream_topology_data = TerrainAttributesGenerator(self.path, 'dem')


    def merge_stream_topology_points(self) -> gpd.GeoDataFrame:
        """
        Generate point dataframe that merges upstream catchment area and strahler order.
        This dataframe already removes the rows with same FIDs.

        Returns
        --------
        agg_upstream_area_and_strahler : gpd.GeoDataFrame
            A geopandas dataframe that contains both 'upstream_area_m2' and 'strahler'.
            There is no rows with the same FIDs
        """
        # Generate points that include upstream area under geopandas dataframe
        points_area_m2 = self.stream_topology_data.raster_to_points_dataframe(
            'flow_acc_d8_area_m2',
            'stream_pixels_pts_from_flow_acc',
            'upstream_area_m2'
        )

        # Generate points that include strahler order under geopandas dataframe
        points_strahler_order = self.stream_topology_data.raster_to_points_dataframe(
            'strahler_d8',
            'stream_pixels_pts_from_strahler',
            'strahler'
        )

        # Merge two points geopandas dataframe
        points_merge = points_area_m2.merge(
            points_strahler_order[['FID', 'strahler']],
            on='FID',
            how='left'
        )

        # After raster-to-point conversions and merging, duplicate FIDs are produced
        # which leads to multiple rows with the same FID in the merged dataframe.
        # Hence, the agg function is used to select the max values for both
        # 'upstream_area_m2' and 'strahler'.
        # - For 'upstream_area_m2', as flow accumulation
        # increases downstream, the largest upstream area corresponds to the true
        # accumulate catchment area at that point. Hence, the maximum upstream area
        # preserves the most hydrologically meaningful value.
        # - For 'strahler', as strahler order increases when tributatires merge,
        # the maximum order ensures the feature keeps the correct stream hierarchy classification.
        agg_upstream_area_and_strahler = (
            points_merge.groupby('FID')
                .agg(
                    upstream_area = ('upstream_area_m2', 'max'),
                    strahler = ('strahler', 'max')
            )
            .reset_index()
        )

        return agg_upstream_area_and_strahler


    def merge_upstream_area_strahler_stream_geometry(
            self,
            agg_upstream_area_and_strahler
    ):
        """
        Merge dataframes of 'upstream_area_m2' and 'strahler' with 'geometry' of stream using FID
        and write out the merged dataframe
        """
        # Read D8 stream dataframe
        streams = gpd.read_file(fr"{self.path}\streams_d8.shp")

        # Merge the aggregated dataframe with stream dataframe
        streams = streams.merge(
            agg_upstream_area_and_strahler,
            on='FID',
            how='left'
        )

        # Convert from km2 to m2
        streams['upstream_area'] = streams['upstream_area'] * 1e6

        # Rename columns
        streams_rename = streams.rename(
            columns={
                'upstream_area': 'uparea',
                'strahler': 'strord'
            }
        )

        # Add crs
        streams_rename = streams_rename.set_crs(4326)

        # Write out
        streams_rename.to_file(
            fr"{self.path}\streams_d8_area_strahler.shp"
        )


    def dataframe_upstream_area_strahler_geometry_generator(
            self,
    ) -> None:
        """
        Generate geodataframe of 'upstream_area_m2' and 'strahler'
        """
        # Resample raster
        self.stream_topology_data.raster_resampling(
            0.00045,
            'nn'
        )

        # Fill depression
        self.stream_topology_data.raster_fill_depression(0.0001)

        # Generate D8 pointer
        self.stream_topology_data.d8_pointer_generator()

        # Generate D8 stream generator
        self.stream_topology_data.d8_stream_generator(
            25000,
            True
        )

        # Generate strahler order
        self.stream_topology_data.strahler_stream_order_generator()

        # Collect dataframe of 'upstream_area_m2' and 'strahler'
        df_upstream_area_strahler = self.merge_stream_topology_points()

        # Merge dataframe of 'upstream_area_m2' and 'strahler'
        # with dataframe of stream geometry and write out
        self.merge_upstream_area_strahler_stream_geometry(df_upstream_area_strahler)


class StreamHydraulicsGenerator(CommonVariable):
    def __init__(
            self,
            path: str,
            outlet_gauge_locations_file: str,
            streams_bankfull_stage: float = 1.5
    ):
        """

        Parameters
        -----------
        path : str
            Path to raster that needs manipulating
        outlet_gauge_locations_file : str
            Filename that contains locations of outlet and gauges
        streams_bankfull_stage : float = 1.5
            The stage to focus on the area that is considered as stream/river area
            or bankfull area comparing with HAND.
            Default is 1.5
        """
        super().__init__(path)
        self.streams_bankfull_stage = streams_bankfull_stage
        self.outlet_gauge_locations_file = outlet_gauge_locations_file
        self.stream_topology_data = TerrainAttributesGenerator(self.path, 'dem')
        self.roughness_data = TerrainAttributesGenerator(self.path, 'roughness')


    def watershed_generator(
            self,
            snap_dist: float = 5.0,
            filter_size: int = 5

    ) -> Any:
        """
        Generate watershed based on D8 pointer (flow direction) and list of points of outlet and gauges
        
        Parameters
        -----------
        snap_dist : float = 5.0
            Measures in map units (e.g. meters, default is meters) the given maximum distance
            between the pour points to the location coincident with the nearest stream cell.
            Default is 5 meters.
            https://www.whiteboxgeo.com/manual/wbt_book/available_tools/hydrological_analysis.html#JensonSnapPourPoints
        filter_size : int = 5
            Filter size to smooth a vector coverage of either a Polyline or Polygon base.
            It can be any integer larger than or equal to 3. Default here is 5.
            https://www.whiteboxgeo.com/manual/wbw-user-manual/book/tool_help.html#smooth_vectors

        Returns
        -------
        watershed_polygon : Any
            Watershed that leads to the outlet
        """

        # Read stream raster
        streams = wbe.read_raster(fr"{self.path}\streams_d8.tif")

        # Read D8 pointer
        d8_pointer = wbe.read_raster(fr"{self.path}\d8_pointer.tif")

        # Extract watershed for specific points of outlet and gauges
        outlet_gauge_points = wbe.read_vector(fr"{self.path}\{self.outlet_gauge_locations_file}.shp")

        # Ensure the watershed or streamlines that have points of outlet and gauges
        outlet_gauge_points_on_streams = wbe.jenson_snap_pour_points(
            outlet_gauge_points,
            streams,
            snap_dist = snap_dist
        )

        # Extract watershed of the outlet
        outlet_watershed = wbe.watershed(
            d8_pointer = d8_pointer,
            pour_points = outlet_gauge_points_on_streams
        )

        # Write out watershed raster
        wbe.write_raster(
            outlet_watershed,
            fr"{self.path}\watershed.tif",
            compress=False
        )

        # Generate watershed polygon for checking (if necessary)
        watershed_polygon = wbe.raster_to_vector_polygons(outlet_watershed)

        # Smooth the watershed map
        watershed_polygon = wbe.smooth_vectors(
            watershed_polygon,
            filter_size=filter_size
        )

        # Write out
        wbe.write_vector(
            watershed_polygon,
            fr"{self.path}\watershed.shp"
        )

        return outlet_watershed


    def stream_watershed_raster_generator(
            self,
            watershed_raster: Any
    ):
        """

        Returns
        -------

        """

        # Read stream raster
        streams = wbe.read_raster(fr"{self.path}\streams_d8.tif")

        # Read D8 pointer raster
        d8_pointer = wbe.read_raster(fr"{self.path}\d8_pointer.tif")

        # Read DEM that its depressions are filled
        dem_no_deps = wbe.read_raster(fr"{self.path}\dem_for_wflow_coarser_nodeps_crs.tif")

        # Filter to select only streams inside the watershed
        streams_watershed = streams * watershed_raster

        # Write out raster with streams within watershed
        # (this stream data just has 1 and 0 values)
        wbe.write_raster(
            streams_watershed,
            fr"{self.path}\streams_watershed.tif",
            compress=False
        )

        # Convert stream raster within watershed to vector (just geometry)
        streams_watershed_vector = wbe.raster_streams_to_vector(
            streams_watershed,
            d8_pointer
        )

        # Add more information into stream vector such as
        # reach IDs or FIDs, connectivity, stream orders, flow connectivity information, etc.
        streams_watershed_vector_more_info, _, _, _ = wbe.vector_stream_network_analysis(
            streams_watershed_vector,
            dem_no_deps
        )

        # Write out vector with streams with watershed
        # (this stream data has more information like FIDs, connectivity, etc.)
        wbe.write_vector(
            streams_watershed_vector_more_info,
            fr"{self.path}\streams_watershed_more_info.shp"
        )

        # Convert back to raster once collecting FID
        streams_watershed_raster = wbe.vector_lines_to_raster(
            streams_watershed_vector_more_info,
            'FID',
            base_raster = dem_no_deps,
            zero_background = True
        )

        return streams_watershed, streams_watershed_raster


    def hand_generator(self):
        """

        Returns
        -------

        """
        # Read streams within watershed
        streams_watershed = wbe.read_raster(fr"{self.path}\streams_watershed.tif")

        # Read DEM that its depressions are filled
        dem_no_deps = wbe.read_raster(fr"{self.path}\dem_for_wflow_coarser_nodeps_crs.tif")

        # Calculate HAND
        hand = wbe.elevation_above_stream(
            dem_no_deps,
            streams_watershed
        )

        # Write out
        wbe.write_raster(
            hand,
            fr"{self.path}\hand.tif",
            compress=False
        )

    def stream_bankfull_width_raster_generator(self):
        """

        Parameters
        -----------

        Returns
        -------

        """
        # Read streams within watershed using rioxarray
        streams_watershed = rxr.open_rasterio(fr"{self.path}\streams_watershed.tif").squeeze()

        # Read HAND raster
        hand = rxr.open_rasterio(fr"{self.path}\hand.tif").squeeze()

        # Set up bankfull
        bankfull = (hand <= self.streams_bankfull_stage)

        # Get values of bankfull and stream
        # bankfull_np tells us where the river is
        # stream_np tells us where the streamline is
        bankfull_np = bankfull.values  # Raster where river area = 1 (True) and land = 0 (False)
        stream_np = streams_watershed.values > 0  # A mask of stream centreline pixels (True = this pixel is part of the stream)

        # Calculate distance
        # Get pixel size: Each pixel represents X meters on the ground
        pixel_size = abs(hand.rio.resolution()[0])

        # Convert degrees to meters
        lat = float(bankfull.y.mean())  # Get latitude
        meters_per_degree = (
                111300 * np.cos(np.deg2rad(lat))
        )
        pixel_size_meter = pixel_size * meters_per_degree

        # Measure distance to the river bank:
        # For every river pixel, it calculates the distance to the nearest non-river pixel (the river bank)
        # It here is the function "distance_transform_edt"
        # So pixels near the bank --> small distahce
        # Pixels near the center of the river --> larger distance
        # For example: bank 1m 2m 3m 4m 3m 2m 1m bank (so near the bank --> small distance, near the middle --> larger distance)
        # ==> Logic is: How far am I from the river edge?
        distance = distance_transform_edt(bankfull_np) * pixel_size_meter

        # Filter out only the distance from the center line to a bank
        # So it will be like: bank Nan Nan 4m Nan Nan bank
        # And then double it for the other bank
        bankfull_width = 2 * distance[stream_np]

        # Put widths back into a raster
        streams_bankfull_width = np.full(stream_np.shape, np.nan)
        streams_bankfull_width[stream_np] = bankfull_width

        # Convert numpy array to xarray data array
        streams_bankfull_width_da = xr.DataArray(
            streams_bankfull_width,
            coords = hand.coords,
            dims = hand.dims,
            name = "bankfull_width"
        )

        # Add crs
        streams_bankfull_width_da.rio.write_crs(
            hand.rio.crs,
            inplace = True
        )

        # Write out
        streams_bankfull_width_da.rio.to_raster(
            fr"{self.path}\streams_bankfull_width.tif"
        )


    def buffer_streams_watershed(self):
        """
        Buffer the stream linestrings to capture stream pixels

        Returns
        -------

        """
        # Read streams within watershed using geopandas
        streams_watershed_vector_more_info = gpd.read_file(
            fr"{self.path}\streams_watershed_more_info.shp"
        )

        # Read HAND raster
        hand = rxr.open_rasterio(fr"{self.path}\hand.tif").squeeze()

        # Buffer by half raster pixel
        # To explain, linestrings have no width and might not be alligned well with the raster.
        # Hence, buffering helps to ensure the stream intersects well with the raster
        pixel_size = abs(hand.rio.resolution()[0])
        streams_watershed_buffer = streams_watershed_vector_more_info.copy()
        streams_watershed_buffer['geometry'] = streams_watershed_buffer.geometry.buffer(pixel_size / 2)

        return streams_watershed_buffer, streams_watershed_vector_more_info


    def assign_streams_hydraulic_values(
            self,
            streams_watershed_buffer,
            streams_watershed_vector_more_info,
            hydraulic_name
    ):
        """
        Assign stream hydraulic values to each stream segment in the vector network

        Returns
        -------

        """
        # Extract stream hydraulic values for each reach
        streams_hydraulic_values = zonal_stats(
            vectors = streams_watershed_buffer,
            raster = fr"{self.path}\streams_{hydraulic_name}.tif",
            stats = ['mean'],
            all_touched = True # includes all pixels by touching the buffered ones
        )

        # Convert list of dicts to dataframe
        streams_hydraulic_values_df = pd.DataFrame(streams_hydraulic_values)

        # Add stream hydraulic values to streams watershed dataframe
        streams_hydraulic_values_linestring = streams_watershed_vector_more_info.join(
            streams_hydraulic_values_df
        )
        streams_hydraulic_values_linestring[f'{hydraulic_name}'] = streams_hydraulic_values_linestring['mean']

        # Write out
        streams_hydraulic_values_linestring.to_file(
            fr"{self.path}\streams_{hydraulic_name}_linestring.shp"
        )


    def stream_bankfull_width_linestring_generator(self):
        """

        Returns
        -------

        """
        # Buffer stream linestring to capture stream pixels
        streams_watershed_buffer, streams_watershed_vector_more_info = self.buffer_streams_watershed()

        # Assign stream bankfull width to stream linestring
        self.assign_streams_hydraulic_values(
            streams_watershed_buffer,
            streams_watershed_vector_more_info,
            'bankfull_width'
        )


    def stream_manning_linestring_generator(self):
        """

        Returns
        -------

        """
        # Resample roughness raster
        self.roughness_data.raster_resampling(
            0.00045,
            'nn'
        )

        # Read coarse roughness raster
        roughness_for_wflow_coarser = rxr.open_rasterio(
            fr"{self.path}\roughness_for_wflow_coarser.tif"
        )

        # Convert roughness to manning
        self.roughness_data.roughness_to_manning(
            roughness_for_wflow_coarser,
            1
        )

        # Buffer stream linestring to capture stream pixels
        streams_watershed_buffer, streams_watershed_vector_more_info = self.buffer_streams_watershed()

        # Assign stream bankfull width to stream linestring
        self.assign_streams_hydraulic_values(
            streams_watershed_buffer,
            streams_watershed_vector_more_info,
            'manning'
        )


    def stream_slope_linestring_generator(self):
        """

        Returns
        -------

        """
        # Read DEM that its depressions are filled
        dem_no_deps = wbe.read_raster(fr"{self.path}\dem_for_wflow_coarser_nodeps_crs.tif")

        # Generate slope from DEM
        slope = wbe.slope(
            dem_no_deps,
            units='percent'
        )

        # Write out slope
        wbe.write_raster(
            slope,
            fr"{self.path}\streams_slope.tif",
            compress=False
        )

        # Buffer stream linestring to capture stream pixels
        streams_watershed_buffer, streams_watershed_vector_more_info = self.buffer_streams_watershed()

        # Assign stream bankfull width to stream linestring
        self.assign_streams_hydraulic_values(
            streams_watershed_buffer,
            streams_watershed_vector_more_info,
            'slope'
        )

    def bankfull_discharge_calculation(
            self,
            streams_bankfull_width,
            streams_slope,
            streams_manning
    ):
        """

        Returns
        -------

        """
        # Calculate cross-sectional area (rectangular)
        cross_sectional_area = streams_bankfull_width * self.streams_bankfull_stage

        # Calculate wetted perimeter
        wetted_perimeter = streams_bankfull_width + 2 * self.streams_bankfull_stage

        # Calculate hydraulic radius
        hydraulic_radius = cross_sectional_area / wetted_perimeter

        # Calculate bankfull discharge
        bankfull_discharge = (1 / streams_manning) * wetted_perimeter * (hydraulic_radius ** (2/3)) * np.sqrt(streams_slope)

        return bankfull_discharge


    def stream_bankfull_discharge_generator(self):
        """

        Returns
        -------

        """
        # Read stream bankfull width shapefile
        streams_bankfull_width = gpd.read_file(fr"{self.path}\streams_bankfull_width_linestring.shp").bankfull_w
        streams_manning = gpd.read_file(fr"{self.path}\streams_manning_linestring.shp").manning
        streams_slope = gpd.read_file(fr"{self.path}\streams_slope_linestring.shp").slope

        # Generate stream bankfull discharge
        streams_discharge = self.bankfull_discharge_calculation(
            streams_bankfull_width,
            streams_slope,
            streams_manning
        )

        return streams_discharge


    def stream_bankfull_width_discharge_generator(self):
        """

        Returns
        -------

        """
        # Generate stream bankfull discharge
        streams_bankfull_discharge = self.stream_bankfull_discharge_generator()

        # Read stream bankfull width
        streams_bankfull_width = gpd.read_file(
            fr"{self.path}\streams_bankfull_width_linestring.shp"
        )

        # Rename stream bankfull width
        streams_bankfull_width_discharge = streams_bankfull_width.rename(columns={'bankfull_w': 'rivwth'})

        # Add stream bankfull discharge
        streams_bankfull_width_discharge['qbankfull'] = streams_bankfull_discharge

        # Write out
        streams_bankfull_width_discharge.to_file(fr"{self.path}\streams_bankfull_width_discharge.gpkg")


    def dataframe_stream_bankfull_width_discharge_generator(self):
        """

        Returns
        -------

        """
        # Resample raster
        self.stream_topology_data.raster_resampling(
            0.00045,
            'nn'
        )

        # Fill depression
        self.stream_topology_data.raster_fill_depression(0.0001)

        # Generate D8 pointer
        self.stream_topology_data.d8_pointer_generator()

        # Generate D8 stream generator
        self.stream_topology_data.d8_stream_generator(
            10000,
            True
        )

        # Generate watershed raster
        watershed_polygon = self.watershed_generator(
            5, 5
        )
        self.stream_watershed_raster_generator(
            watershed_polygon
        )

        # Generate HAND raster
        self.hand_generator()

        # Generate stream bankfull width raster
        self.stream_bankfull_width_raster_generator()

        # Buffer stream linestring to capture stream pixels
        self.buffer_streams_watershed()

        # Generate stream bankfull width linestring
        self.stream_bankfull_width_linestring_generator()

        # Generate stream manning
        self.stream_manning_linestring_generator()

        # Generate stream slope
        self.stream_slope_linestring_generator()

        # Write out stream bankfull width and discharge
        self.stream_bankfull_width_discharge_generator()