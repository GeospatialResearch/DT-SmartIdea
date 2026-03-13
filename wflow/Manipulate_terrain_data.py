import rioxarray as rxr
import geopandas as gpd
import os


def value_change(
        shapefile_func,
        file_need_changing_func,
        value_func,
        inside=True
):
    """
    A function to change pixel values inside or outside polygons

    Parameters
    ----------
    shapefile_func: str
        Path to shapefile that cover the area that needs changing
    file_need_changing_func: str
        Name and path of changed file
    value_func: float
        Replaced value
    inside (boolean):
        If True, change values inside, else, change values outside
    """
    # Set up value changing command
    if inside:
        # Change values inside polygons
        inside_command = fr"gdal_rasterize -burn {value_func} {shapefile_func} {file_need_changing_func}"
        os.system(inside_command)
    else:
        # Change values outside polygons
        outside_command = fr"gdal_rasterize -i -burn {value_func} {shapefile_func} {file_need_changing_func}"
        os.system(outside_command)


class TerrainFilter:
    def __init__(
            self,
            path: str,
            origin_crs: int = 2193,
            converted_crs: int = 4326,
            roughness: bool = True,
            sea_value: float = -9999,
            nodata_value: float = -9999
    ):
        """
        A class to filter terrain data for wflow

        Parameters
        -----------
        path: str
            Path to raster that needs manipulating
        origin_crs : int = 2193
            Original CRS (default is 2193)
        converted_crs : int = 4326
            Converted CRS (default is 4326)
        roughness : bool
            Whether to print out roughness and DEM. Default is True
        sea_value: float = -9999
            Value for the sea data. Default is -9999
        nodata_value: float = -9999
            Value for the nodata. Default is -9999
        """
        self.path = path
        self.origin_crs = origin_crs
        self.converted_crs = converted_crs
        self.roughness = roughness
        self.sea_value = sea_value
        self.nodata_value = nodata_value

    def dem_crs_conversion(self):
        """
        Convert DEM CRS. Here default is to convert DEM CRS from 2193 to 4326
        """
        # Get DEM
        dem = rxr.open_rasterio(fr"{self.path}\8m_geofabric.nc")

        # Ensure the origin CRS is attached
        dem_origin_crs = dem.rio.write_crs(f"EPSG:{self.origin_crs}", inplace=True)

        # Reproject the crs to converted crs
        dem_converted_crs = dem_origin_crs.rio.reproject(f"EPSG:{self.converted_crs}")

        # Save as tif
        if self.roughness:
            dem_converted_crs['z'].rio.to_raster(fr"{self.path}\dem_converted_crs.tif")
            dem_converted_crs['zo'].rio.to_raster(fr"{self.path}\roughness_converted_crs.tif")
        else:
            dem_converted_crs.rio.to_raster(fr"{self.path}\dem_converted_crs.tif")


    def remove_sea(self):
        """
        Clip sea area mainly in DEM and roughness
        """
        # Get New Zealand shapefile
        nz_shapefile = fr"{self.path}\nz_coastline_4326.shp"

        # Files need changing
        dem = fr"{self.path}\dem_converted_crs.tif"
        roughness = fr"{self.path}\roughness_converted_crs.tif"

        # Remove sea by changing sea area into -9999
        value_change(nz_shapefile, dem, self.sea_value, False)
        value_change(nz_shapefile, roughness, self.sea_value, False)


    def nodata_filling(self):
        """
        Fill nodata value with -9999
        """
        # Fill the nodata value
        dem_nosea = rxr.open_rasterio(fr"{self.path}\dem_converted_crs.tif")
        dem_replace_nodata = dem_nosea.fillna(self.nodata_value)
        dem_write_nodata = dem_replace_nodata.rio.write_nodata(self.nodata_value)
        dem_write_nodata.rio.to_raster(fr"{self.path}\dem_for_wflow.tif")

        roughness_nosea = rxr.open_rasterio(fr"{self.path}\roughness_converted_crs.tif")
        roughness_replace_nodata = roughness_nosea.fillna(self.nodata_value)
        roughness_write_nodata = roughness_replace_nodata.rio.write_nodata(self.nodata_value)
        roughness_write_nodata.rio.to_raster(fr"{self.path}\roughness_for_wflow.tif")


    def filter_dem_for_wflow(self):
        """
        Convert DEM into version that can be used by wflow
        """
        # Convert DEM and roughness CRS (default: 2193 --> 4326)
        self.dem_crs_conversion()

        # Remove sea
        self.remove_sea()

        # Fill nodata
        self.nodata_filling()