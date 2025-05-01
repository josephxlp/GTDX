import os 
from osgeo import gdal, gdalconst
import rasterio 
import subprocess
import numpy as np

gdal.UseExceptions()


def min_rasters(raster_a_path, raster_b_path, output_path):
    """
    Create a new raster where each pixel is the minimum of the corresponding pixels in two input rasters.
    Nodata values are treated as np.nan.
    
    Parameters:
        raster_a_path (str): File path to the first input raster.
        raster_b_path (str): File path to the second input raster.
        output_path (str): File path to save the output raster.
    """
    # Open raster a
    with rasterio.open(raster_a_path) as src_a:
        a = src_a.read(1).astype(float)
        a[a == src_a.nodata] = np.nan
        profile = src_a.profile.copy()

    # Open raster b
    with rasterio.open(raster_b_path) as src_b:
        b = src_b.read(1).astype(float)
        b[b == src_b.nodata] = np.nan

    # Compute pixel-wise minimum, treating np.nan properly
    c = np.fmin(a, b)

    # Set a float nodata value if needed (optional)
    nodata_value = -9999.0
    c[np.isnan(c)] = nodata_value
    profile.update(dtype='float32', nodata=nodata_value)

    # Write output raster
    with rasterio.open(output_path, 'w', **profile) as dst:
        dst.write(c.astype('float32'), 1)


def calculate_dod(dem1_path, dem2_path, output_path=None):
    """
    Calculate the Difference of DEMs (DoD) by subtracting dem1 from dem2.

    Parameters:
    - dem1_path (str): Path to the first DEM (baseline or older).
    - dem2_path (str): Path to the second DEM (newer or comparison).
    - output_path (str, optional): Path to save the output DoD raster. If None, doesn't save.

    Returns:
    - dod_array (np.ndarray): The difference array (dem2 - dem1).
    """
    with rasterio.open(dem1_path) as src1, rasterio.open(dem2_path) as src2:
        if src1.shape != src2.shape or src1.transform != src2.transform or src1.crs != src2.crs:
            raise ValueError("Input DEMs must have the same shape, transform, and CRS.")

        dem1 = src1.read(1).astype(np.float32)
        dem2 = src2.read(1).astype(np.float32)

        # Mask nodata values
        mask = (dem1 == src1.nodata) | (dem2 == src2.nodata)
        dod = dem2 - dem1
        dod[mask] = np.nan

        if output_path:
            profile = src1.profile
            profile.update(dtype='float32', nodata=np.nan)
            with rasterio.open(output_path, 'w', **profile) as dst:
                dst.write(dod, 1)

    return dod

def get_raster_info(tif_path):
    """
    Extracts raster metadata including projection, resolution, and bounding box.

    Parameters:
        tif_path (str): Path to the raster file.

    Returns:
        tuple: Raster projection, resolution, bounding box, and dimensions.
    """
    ds = gdal.Open(tif_path, gdalconst.GA_ReadOnly)
    proj = ds.GetProjection()
    geotrans = ds.GetGeoTransform()
    xres = geotrans[1]
    yres = geotrans[5]
    w, h = ds.RasterXSize, ds.RasterYSize
    xmin, ymax = geotrans[0], geotrans[3]
    xmax = xmin + (xres * w)
    ymin = ymax + (yres * h)
    ds = None
    return proj, xres, yres, xmin, xmax, ymin, ymax, w, h

def get_nodata_value(raster_path):
    """
    Retrieves the NoData value of a raster.

    Parameters:
        raster_path (str): Path to the raster file.

    Returns:
        float: NoData value.
    """
    with rasterio.open(raster_path) as src:
        return src.nodata

def gdal_regrid(fi, fo, xmin, ymin, xmax, ymax, xres, yres,
                mode, t_epsg='EPSG:4979', overwrite=False):
    """
    Regrids a raster file using GDAL.

    Parameters:
        fi (str): Input raster file path.
        fo (str): Output raster file path.
        xmin, ymin, xmax, ymax (float): Bounding box.
        xres, yres (float): Target resolution.
        mode (str): Regridding mode ('num' or 'cat').
        t_epsg (str): Target EPSG code.
        overwrite (bool): Whether to overwrite existing output.

    Returns:
        None
    """
    if mode == 'num':
        ndv, algo, dtype = num_regrid_params()
    elif mode == 'cat':
        ndv, algo, dtype = cat_regrid_params()
    else:
        raise ValueError("Invalid mode. Use 'num' or 'cat'.")

    src_ndv = get_nodata_value(fi)
    dst_ndv = ndv

    print(f"Source NoData Value: {src_ndv}")
    print(f"Destination NoData Value: {dst_ndv}")

    overwrite_option = "-overwrite" if overwrite else ""
    output_width = round((xmax - xmin) / xres)
    output_height = round((ymax - ymin) / abs(yres))

    cmd = (f'gdalwarp -ot {dtype} -multi {overwrite_option} '
           f'-te {xmin} {ymin} {xmax} {ymax} '
          # f'-ts {output_width} {output_height} '
           f'-r {algo} -t_srs {t_epsg} -tr {xres} {yres} -tap '
           f'-co compress=lzw -co num_threads=all_cpus -co TILED=YES '
           f'-srcnodata {src_ndv} -dstnodata {dst_ndv} '
           f'{fi} {fo}')

    os.system(cmd)

def cat_regrid_params():
    """
    Returns parameters for categorical regridding.

    Returns:
        tuple: NoData value, resampling algorithm, and data type.
    """
    return 0, 'near', 'Byte'

def num_regrid_params():
    """
    Returns parameters for numerical regridding.

    Returns:
        tuple: NoData value, resampling algorithm, and data type.
    """
    return -9999.0, 'bilinear', 'Float32'

def build_vrt(epsg_code=4326, input_list="my_list.txt", output_vrt="doq_index.vrt"):
    """
    Builds a VRT file using GDAL with specified parameters.

    Parameters:
        epsg_code (int): The EPSG code for spatial reference.
        input_list (str): Path to the input file list.
        output_vrt (str): Name of the output VRT file.

    Returns:
        None
    """
    cmd = [
        "gdalbuildvrt",
        "-allow_projection_difference",
        "-q",
        #"-tap",
        "-a_srs", f"EPSG:{str(epsg_code)}",
        "-input_file_list", input_list,
        output_vrt
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print(f"✅ VRT file '{output_vrt}' created successfully.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error while building VRT: {e}")