import os
import glob
import subprocess
import numpy as np
import rasterio
from rasterio.merge import merge
from rasterio.warp import reproject, Resampling
from typing import Optional, List

def resample_raster(src_path: str, match_path: str, resampling: Resampling = Resampling.bilinear):
    """Resamples a source raster to match the properties of a target raster."""
    with rasterio.open(match_path) as match_ds:
        transform = match_ds.transform
        crs = match_ds.crs
        width = match_ds.width
        height = match_ds.height
        profile = match_ds.profile.copy()
        profile.update({'height': height, 'width': width, 'transform': transform, 'dtype': 'float32'})
        data = np.empty((match_ds.count, height, width), dtype=np.float32)
        with rasterio.open(src_path) as src_ds:
            for i in range(src_ds.count):
                reproject(
                    source=rasterio.band(src_ds, i + 1),
                    destination=data[i],
                    src_transform=src_ds.transform,
                    src_crs=src_ds.crs,
                    dst_transform=transform,
                    dst_crs=crs,
                    resampling=resampling,
                )
    return data, profile

def subtract_rasters(fine_path: str, coarse_path: str, output_path: str):
    """Subtracts a resampled coarse raster from a fine raster."""
    coarse_resampled, profile = resample_raster(coarse_path, fine_path)
    with rasterio.open(fine_path) as fine_ds:
        diff = fine_ds.read().astype(np.float32) - coarse_resampled
    with rasterio.open(output_path, 'w', **profile) as dst:
        dst.write(diff)

def mosaic(input_folder: Optional[str] = None, output_file: str = '', image_format: str = 'tif', input_files: Optional[List[str]] = None, **kwargs):
    """Mosaics multiple raster files."""
    if input_folder is None and input_files is None:
        raise ValueError("Either input_folder or input_files must be provided.")
    if input_files is not None:
        sources = [rasterio.open(f) for f in input_files]
    else:
        search_criteria = f"*.{image_format}"
        sources = [rasterio.open(f) for f in sorted(glob.glob(os.path.join(input_folder, search_criteria)))]
    mosaic_data, out_trans = merge(sources, **kwargs)
    meta = sources[0].meta.copy()
    meta.update({"height": mosaic_data.shape[1], "width": mosaic_data.shape[2], "transform": out_trans})
    with rasterio.open(output_file, 'w', **meta) as outds:
        outds.write(mosaic_data)
    return output_file

def fmin_postprocessing(raster_a_path: str, raster_b_path: str, output_path: str):
    """Calculates the pixel-wise minimum of two rasters, handling NoData."""
    with rasterio.open(raster_a_path) as src_a, rasterio.open(raster_b_path) as src_b:
        a = src_a.read(1).astype(float)
        b = src_b.read(1).astype(float)
        nodata_a = src_a.nodata
        nodata_b = src_b.nodata
        a[a == nodata_a] = np.nan
        b[b == nodata_b] = np.nan
        c = np.fmin(a, b)
        nodata_out = -9999.0
        c[np.isnan(c)] = nodata_out
        profile = src_a.profile.copy()
        profile.update(dtype='float32', nodata=nodata_out)
        with rasterio.open(output_path, 'w', **profile) as dst:
            dst.write(c.astype('float32'), 1)

def calculate_dod(dem1_path: str, dem2_path: str, output_path: Optional[str] = None):
    """Calculates the Difference of DEMs (DoD)."""
    with rasterio.open(dem1_path) as src1, rasterio.open(dem2_path) as src2:
        if src1.shape != src2.shape or src1.transform != src2.transform or src1.crs != src2.crs:
            raise ValueError("Input DEMs must have the same shape, transform, and CRS.")
        dem1 = src1.read(1).astype(np.float32)
        dem2 = src2.read(1).astype(np.float32)
        mask = (dem1 == src1.nodata) | (dem2 == src2.nodata)
        dod = dem2 - dem1
        dod[mask] = np.nan
        if output_path:
            profile = src1.profile
            profile.update(dtype='float32', nodata=np.nan)
            with rasterio.open(output_path, 'w', **profile) as dst:
                dst.write(dod, 1)
    return dod

def get_raster_info(tif_path: str):
    """Extracts raster metadata."""
    with rasterio.open(tif_path) as ds:
        transform = ds.transform
        proj = str(ds.crs)
        width = ds.width
        height = ds.height
        xmin, ymax = transform[2], transform[5]
        xmax, ymin = transform[2] + transform[0] * width, transform[5] + transform[4] * height
        xres, yres = transform[0], transform[4]
    return proj, xres, yres, xmin, xmax, ymin, ymax, width, height

def get_nodata_value(raster_path: str):
    """Retrieves the NoData value of a raster."""
    with rasterio.open(raster_path) as src:
        return src.nodata

def gdal_regrid(fi: str, fo: str, xmin: float, ymin: float, xmax: float, ymax: float, xres: float, yres: float,
                mode: str, t_epsg: str = 'EPSG:4979', overwrite: bool = False):
    """Regrids a raster file using GDAL."""
    if mode == 'num':
        ndv, algo, dtype = -9999.0, 'bilinear', 'Float32'
    elif mode == 'cat':
        ndv, algo, dtype = 0, 'near', 'Byte'
    else:
        raise ValueError("Invalid mode. Use 'num' or 'cat'.")

    with rasterio.open(fi) as src:
        src_ndv = src.nodata

    overwrite_option = "-overwrite" if overwrite else ""
    cmd = (f'gdalwarp -ot {dtype} -multi {overwrite_option} '
           f'-te {xmin} {ymin} {xmax} {ymax} '
           f'-tr {xres} {abs(yres)} -r {algo} -t_srs {t_epsg} -tap '
           f'-co compress=lzw -co num_threads=all_cpus -co TILED=YES '
           f'-srcnodata {src_ndv} -dstnodata {ndv} '
           f'{fi} {fo}')
    os.system(cmd)

def build_vrt(epsg_code: int = 4326, input_list: str = "my_list.txt", output_vrt: str = "doq_index.vrt"):
    """Builds a VRT file using GDAL."""
    cmd = [
        "gdalbuildvrt",
        "-allow_projection_difference",
        "-q",
        "-a_srs", f"EPSG:{epsg_code}",
        "-input_file_list", input_list,
        output_vrt
    ]
    try:
        subprocess.run(cmd, check=True)
        print(f"✅ VRT file '{output_vrt}' created successfully.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error while building VRT: {e}")