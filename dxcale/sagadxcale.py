import os
import time
from datetime import datetime
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
import numpy as np


def gwrdownxcale(xpath, ypath, opath, geoid_fn, overwrite=False, oaux=False, epsg_code=4979, clean=True,
                 search_range=0, search_radius=10, dw_weighting=0, dw_idw_power=2.0, dw_bandwidth=1.0,
                 logistic=0, model_out=0, grid_system=None, fmin_fn_run=True, bcor_fn_run=True, fminbcor_fn_run=True):
    opath_base, ext = os.path.splitext(opath)
    gwrp_fn_base = f"{opath_base}_dw{dw_weighting}{ext.replace('.sdat', '')}"
    gwrp_fn = f"{gwrp_fn_base}.tif"
    fmin_fn = f"{gwrp_fn_base}_fmin.tif"
    bcor_fn = f"{gwrp_fn_base}_bcor.tif"
    fminbcor_fn = f"{gwrp_fn_base}_fminbcor.tif"
    outpaths = [gwrp_fn, fmin_fn, bcor_fn, fminbcor_fn]

    if not overwrite and all(os.path.isfile(p) for p in outpaths):
        return outpaths

    ti = time.perf_counter()
    start_time = datetime.now()

    if not os.path.isfile(opath):
        print('gwr_grid_downscaling...')
        gwr_grid_downscaling_output = gwr_grid_downscaling(xpath, ypath, opath, oaux=oaux, epsg_code=epsg_code, clean=clean,
                                     search_range=search_range, search_radius=search_radius, dw_weighting=dw_weighting,
                                     dw_idw_power=dw_idw_power, dw_bandwidth=dw_bandwidth, logistic=logistic,
                                     model_out=model_out, grid_system=grid_system)
        gwrp_fn = gwr_grid_downscaling_output
    else:
        print('gwr_grid_downscaling already done !!!')
        gwrp_fn = f"{opath_base}_dw{dw_weighting}.tif"


    if fmin_fn_run:
        if not os.path.isfile(fmin_fn):
            print('fmin_fn...')
            fmin_get(xpath, gwrp_fn, fmin_fn)
        else:
            print('fmin_fn already done !!!')

    if bcor_fn_run:
        if not os.path.isfile(bcor_fn):
            print('bcor_fn...')
            bcor_sub(gwrp_fn, geoid_fn, bcor_fn)
        else:
            print('bcor_fn already done !!!')

    if fminbcor_fn_run:
        if not os.path.isfile(fminbcor_fn):
            print('fminbcor_fn...')
            fmin_get(xpath, bcor_fn, fminbcor_fn)
        else:
            print('fminbcor_fn already done !!!')

    tf = time.perf_counter() - ti
    end_time = datetime.now()
    duration = end_time - start_time
    minutes = int(duration.total_seconds() // 60)
    seconds = int(duration.total_seconds() % 60)
    hours = int(minutes // 60)
    remaining_minutes = int(minutes % 60)
    days = int(hours // 24)
    remaining_hours = int(hours % 24)

    time_taken_str = f'{seconds} seconds'
    if remaining_minutes > 0:
        time_taken_str = f'{remaining_minutes} minutes, ' + time_taken_str
    if remaining_hours > 0:
        time_taken_str = f'{remaining_hours} hours, ' + time_taken_str
    if days > 0:
        time_taken_str = f'{days} days, ' + time_taken_str

    print(f'Start time: {start_time.strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'End time: {end_time.strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'RUN.TIME = {time_taken_str}')

    return outpaths


def gwr_grid_downscaling(xpath, ypath, opath, oaux=False, epsg_code=4979, clean=True,
                         search_range=0, search_radius=10, dw_weighting=0, dw_idw_power=2.0, dw_bandwidth=1.0,
                         logistic=0, model_out=0, grid_system=None):
    opath_base, ext = os.path.splitext(opath)
    otif = f"{opath_base}_dw{dw_weighting}{ext.replace('.sdat', '.tif')}"
    cmd = (
        f"saga_cmd statistics_regression 14 "
        f"-PREDICTORS {xpath} "
        f"-DEPENDENT {ypath} "
        f"-REGRESSION {opath} "
        f"-SEARCH_RANGE {search_range} "
        f"-SEARCH_RADIUS {search_radius} "
        f"-DW_WEIGHTING {dw_weighting} "
        f"-DW_IDW_POWER {dw_idw_power} "
        f"-DW_BANDWIDTH {dw_bandwidth} "
        f"-LOGISTIC {logistic} "
        f"-MODEL_OUT {model_out}"
    )
    if grid_system:
        cmd += f" -GRID_SYSTEM {grid_system}"
    if oaux:
        opath_rescorr = f"{opath_base}_RESCORR_dw{dw_weighting}.sdat"
        opath_quality = f"{opath_base}_QUALITY_dw{dw_weighting}.sdat"
        opath_residuals = f"{opath_base}_RESIDUALS_dw{dw_weighting}.sdat"
        cmd += (
            f" -REG_RESCORR {opath_rescorr} "
            f"-QUALITY {opath_quality} "
            f"-RESIDUALS {opath_residuals}"
        )
    os.system(cmd)
    sdat_to_geotif(opath, otif, epsg_code)
    print("GWR Grid Downscaling completed.")
    if oaux:
        print(f"Additional outputs saved: \n{opath_rescorr.replace('.sdat', '.tif')}, \n{opath_quality.replace('.sdat', '.tif')}, \n{opath_residuals.replace('.sdat', '.tif')}")
    if clean:
        time.sleep(1)
        dirpath = os.path.dirname(opath)
        print(f'Cleaning up intermediate files...\n{dirpath}')
        for f in os.listdir(dirpath):
            if not f.endswith('.tif'):
                fo = os.path.join(dirpath, f)
                if os.path.isfile(fo):
                    print(f'Removing {fo}...')
                    os.remove(fo)
                else:
                    print(f'Skipping directory: {fo}')
    return otif


def sdat_to_geotif(sdat_path, gtif_path, epsg_code=4979):
    if not sdat_path.endswith('.sdat'):
        sdat_path = sdat_path.replace('.sgrd', '.sdat')
    if os.path.isfile(gtif_path):
        print(f'! The file "{gtif_path}" already exists.')
        return
    cmd = f'gdal_translate -a_srs EPSG:{epsg_code} -of GTiff "{sdat_path}" "{gtif_path}"'
    result = os.system(cmd)
    if result == 0:
        print(f'# Successfully converted "{sdat_path}" to "{gtif_path}".')
    else:
        print(f'! Failed to convert "{sdat_path}" to "{gtif_path}". Check the input files and GDAL installation.')


def resample_raster(src_path, match_path, resampling=Resampling.bilinear):
    with rasterio.open(match_path) as match_ds:
        match_transform = match_ds.transform
        match_crs = match_ds.crs
        match_width = match_ds.width
        match_height = match_ds.height

        with rasterio.open(src_path) as src_ds:
            data = np.empty((src_ds.count, match_height, match_width), dtype=np.float32)

            for i in range(src_ds.count):
                reproject(
                    source=rasterio.band(src_ds, i + 1),
                    destination=data[i],
                    src_transform=src_ds.transform,
                    src_crs=src_ds.crs,
                    dst_transform=match_transform,
                    dst_crs=match_crs,
                    resampling=resampling
                )

            profile = match_ds.profile.copy()
            profile.update({
                'height': match_height,
                'width': match_width,
                'transform': match_transform,
                'dtype': 'float32'
            })

            return data, profile

def bcor_sub(fine_path, coarse_path, output_path):
    coarse_resampled, profile = resample_raster(coarse_path, fine_path)
    with rasterio.open(fine_path) as fine_ds:
        fine_data = fine_ds.read().astype(np.float32)
    diff = fine_data - coarse_resampled
    with rasterio.open(output_path, 'w', **profile) as dst:
        dst.write(diff)

def fmin_get(raster_a_path, raster_b_path, output_path):
    with rasterio.open(raster_a_path) as src_a:
        a = src_a.read(1).astype(float)
        a[a == src_a.nodata] = np.nan
        profile = src_a.profile.copy()
    with rasterio.open(raster_b_path) as src_b:
        b = src_b.read(1).astype(float)
        b[b == src_b.nodata] = np.nan
    c = np.fmin(a, b)
    nodata_value = -9999.0
    c[np.isnan(c)] = nodata_value
    profile.update(dtype='float32', nodata=nodata_value)
    with rasterio.open(output_path, 'w', **profile) as dst:
        dst.write(c.astype('float32'), 1)