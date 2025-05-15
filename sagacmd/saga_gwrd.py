import os
import time
from datetime import datetime

##  i want to add dw_weighting value to the outfiles inside the function
def gwrdownxcale(xpath, ypath, opath, oaux=False, epsg_code=4979, clean=True,
                 search_range=0, search_radius=10, dw_weighting=0, dw_idw_power=2.0, dw_bandwidth=1.0,
                 logistic=0, model_out=0, grid_system=None):
    ti = time.perf_counter()
    start_time = datetime.now()

    """
    Performs Geographically Weighted Regression (GWR) for grid downscaling.

    Parameters:
    - xpath (str): Path to the high-resolution DEM (predictor variable).
    - ypath (str): Path to the coarse-resolution data (dependent variable).
    - opath (str): Path to save the output SAGA grid (.sdat file).
    - oaux (bool, optional): If True, generate additional outputs like regression correction, quality, and residuals. Defaults to False.
    - epsg_code (int, optional): EPSG code for the spatial reference system of the output GeoTIFF. Defaults to 4979.
    - clean (bool, optional): If True, remove intermediate SAGA files after conversion. Defaults to True.
    - search_range (int, optional): Defines the search range for GWR.
      - 0: local
      - 1: global
      Defaults to 0 (local).
    - search_radius (int, optional): Search distance in cells for local GWR. Minimum: 1. Defaults to 10.
    - dw_weighting (int, optional): Defines the distance weighting function.
      - 0: no distance weighting
      - 1: inverse distance to a power
      - 2: exponential
      - 3: gaussian
      Defaults to 0 (no distance weighting).
    - dw_idw_power (float, optional): Power parameter for inverse distance weighting. Minimum: 0.0. Defaults to 2.0.
    - dw_bandwidth (float, optional): Bandwidth for exponential and Gaussian weighting. Minimum: 0.0. Defaults to 1.0.
    - logistic (int, optional): Enable logistic regression (Boolean: 0 for False, 1 for True). Defaults to 0.
    - model_out (int, optional): Output the model parameters (Boolean: 0 for False, 1 for True). Defaults to 0.
    - grid_system (str, optional): Path to a SAGA grid system file to be used. If None, the grid system is determined from the input data. Defaults to None.

    Returns:
    - None: Saves the output files to the specified paths.

    Documentation:
    https://saga-gis.sourceforge.io/saga_tool_doc/8.2.2/statistics_regression_14.html
    """
    gwr_grid_downscaling(xpath, ypath, opath, oaux=oaux, epsg_code=epsg_code, clean=clean,
                         search_range=search_range, search_radius=search_radius, dw_weighting=dw_weighting,
                         dw_idw_power=dw_idw_power, dw_bandwidth=dw_bandwidth, logistic=logistic,
                         model_out=model_out, grid_system=grid_system)

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


def gwr_grid_downscaling(xpath, ypath, opath, oaux=False, epsg_code=4979, clean=True,
                         search_range=0, search_radius=10, dw_weighting=0, dw_idw_power=2.0, dw_bandwidth=1.0,
                         logistic=0, model_out=0, grid_system=None):
    """
    Perform Geographically Weighted Regression (GWR) for grid downscaling.

    Parameters:
    - xpath (str): Path to the high-resolution DEM (predictor variable).
    - ypath (str): Path to the coarse-resolution data (dependent variable).
    - opath (str): Path to save the output SAGA grid (.sdat file).
    - oaux (bool, optional): If True, generate additional outputs like regression correction, quality, and residuals. Defaults to False.
    - epsg_code (int, optional): EPSG code for the spatial reference system of the output GeoTIFF. Defaults to 4979.
    - clean (bool, optional): If True, remove intermediate SAGA files after conversion. Defaults to True.
    - search_range (int, optional): Defines the search range for GWR.
      - 0: local
      - 1: global
      Defaults to 0 (local).
    - search_radius (int, optional): Search distance in cells for local GWR. Minimum: 1. Defaults to 10.
    - dw_weighting (int, optional): Defines the distance weighting function.
      - 0: no distance weighting
      - 1: inverse distance to a power
      - 2: exponential
      - 3: gaussian
      Defaults to 0 (no distance weighting).
    - dw_idw_power (float, optional): Power parameter for inverse distance weighting. Minimum: 0.0. Defaults to 2.0.
    - dw_bandwidth (float, optional): Bandwidth for exponential and Gaussian weighting. Minimum: 0.0. Defaults to 1.0.
    - logistic (int, optional): Enable logistic regression (Boolean: 0 for False, 1 for True). Defaults to 0.
    - model_out (int, optional): Output the model parameters (Boolean: 0 for False, 1 for True). Defaults to 0.
    - grid_system (str, optional): Path to a SAGA grid system file to be used. If None, the grid system is determined from the input data. Defaults to None.

    Returns:
    - None: Saves the output files to the specified paths.

    Documentation:
    https://saga-gis.sourceforge.io/saga_tool_doc/8.2.2/statistics_regression_14.html
    """

    opath_base, ext = os.path.splitext(opath)
    otif = f"{opath_base}_dw{dw_weighting}{ext.replace('.sdat', '.tif')}"

    # Construct the base SAGA command
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
        # Add optional outputs for residual correction, quality, and residuals
        opath_rescorr = f"{opath_base}_RESCORR_dw{dw_weighting}.sdat"
        opath_quality = f"{opath_base}_QUALITY_dw{dw_weighting}.sdat"
        opath_residuals = f"{opath_base}_RESIDUALS_dw{dw_weighting}.sdat"
        cmd += (
            f" -REG_RESCORR {opath_rescorr} "
            f"-QUALITY {opath_quality} "
            f"-RESIDUALS {opath_residuals}"
        )

    # Run the SAGA command
    os.system(cmd)

    # Convert the output SAGA grid to GeoTIFF
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
                if os.path.isfile(fo):  # Check if it's a file
                    print(f'Removing {fo}...')
                    os.remove(fo)
                else:
                    print(f'Skipping directory: {fo}')


def sdat_to_geotif(sdat_path, gtif_path, epsg_code=4979):
    """
    Converts a Saga .sdat file to a GeoTIFF file using GDAL.

    Parameters:
        sdat_path (str): Path to the input .sdat file.
        gtif_path (str): Path to the output GeoTIFF file.
        epsg_code (int): EPSG code for the spatial reference system. Default is 4979.
    """
    # Ensure the input file has the correct extension
    if not sdat_path.endswith('.sdat'):
        sdat_path = sdat_path.replace('.sgrd', '.sdat')

    # Check if the output file already exists
    if os.path.isfile(gtif_path):
        print(f'! The file "{gtif_path}" already exists.')
        return

    # Construct and execute the GDAL command
    cmd = f'gdal_translate -a_srs EPSG:{epsg_code} -of GTiff "{sdat_path}" "{gtif_path}"'
    result = os.system(cmd)

    if result == 0:
        print(f'# Successfully converted "{sdat_path}" to "{gtif_path}".')
    else:
        print(f'! Failed to convert "{sdat_path}" to "{gtif_path}". Check the input files and GDAL installation.')