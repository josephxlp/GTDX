import logging
from utilenames import tilenames_mkd, tilenames_tls, tilenames_rgn
from os.path import join, isfile
from os import makedirs
from glob import glob
from uinterp import riofill
from ufuncs import get_raster_info, gdal_regrid
from uvars import gdsm_v_fn, gdtm_v_fn, egm08_fn, outdir, indir
import sys
from uvars import topoxcale_dir
sys.path.append(topoxcale_dir)
from topoxcale.mlxcale import mldownxcale
from topoxcale.sagaxcale import gwrdownxcale
from ugeoid import ellipsoid2orthometric
from ufuncs import calculate_dod,min_rasters
import time

# do tiles, do blocks 

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("processing.log"), # add date to this 
        logging.StreamHandler(sys.stdout)
    ]
)

ti = time.perf_counter()
#tilenames #N13E103 #'N10E105','S01W063'
logging.info('Loading main variables')
#tilenames = ['N13E103']#tilenames_mkd + tilenames_tls + tilenames_rgn
tilenames = tilenames_mkd + tilenames_tls + tilenames_rgn
varname = "tdem_dem" # use EDEM #deps: filling methos for my DEMs
roitilenames = tilenames
makedirs(outdir, exist_ok=True)
xres, yres = 0.01057350068885258912, -0.01057350068885258912
t_epsg = 'EPSG:4326'
mode = "num"

varpath = f"{indir}/*/*{varname}.tif"
varfiles = glob(varpath)
roivarfiles = [fi for fi in varfiles for t in roitilenames if t in fi]

ta = time.perf_counter()
gdsmf_tiles = []
gdtmf_tiles = []
geoid_tiles = []
logging.info(f'setting baseline dem as {varname}')

si = 0 
for fi in roivarfiles:
    tilename = fi.split('/')[-2]
    tile_dir = join(outdir, 'TILES', tilename)
    makedirs(tile_dir, exist_ok=True)
    logging.info(f"Processing tile: {tilename}")
    _, _, _, xmin, xmax, ymin, ymax, _, _ = get_raster_info(fi)
    
    gdsmv_tile = f"{tile_dir}/{tilename}_gdsm_void.tif"
    gdtmv_tile = f"{tile_dir}/{tilename}_gdtm_void.tif"
    geoid_tile = f"{tile_dir}/{tilename}_egm08.tif"
    logging.info(f'regriding GDSM @{tilename}...')
    gdal_regrid(gdtm_v_fn, gdtmv_tile, xmin, ymin, xmax, ymax, xres, yres, mode, t_epsg, overwrite=False)
    logging.info(f'regriding GDTM  @{tilename}...')
    gdal_regrid(gdsm_v_fn, gdsmv_tile, xmin, ymin, xmax, ymax, xres, yres, mode, t_epsg, overwrite=False)

    logging.info(f'regriding GEOID  @{tilename}...')
    gdal_regrid(egm08_fn, geoid_tile, xmin, ymin, xmax, ymax, xres, yres, mode, t_epsg, overwrite=False)

    gdsmf_tile = gdsmv_tile.replace('void.tif', f'riofill{si}.tif')
    gdtmf_tile = gdtmv_tile.replace('void.tif', f'riofill{si}.tif')

    logging.info(f'tFilling GDSM @{tilename}...')
    riofill(gdtmv_tile, gdtmf_tile, si=si)
    logging.info(f'tFilling GDSM @{tilename}...')
    riofill(gdsmv_tile, gdsmf_tile, si=si)
    
    gdsmf_tiles.append(gdsmf_tile)
    gdtmf_tiles.append(gdtmf_tile)
    geoid_tiles.append(geoid_tile)

tb = time.perf_counter()
logging.info(f'Void filling time: {(tb - ta)/60:.2f} min')

for i in range(len(gdsmf_tiles)):
    print(i)

    gdsm_tile = gdsmf_tiles[i]
    gdsm_tile_egm = gdsm_tile.replace('.tif', '_egm.tif')

    gdtm_tile = gdtmf_tiles[i]
    gdtm_tile_egm = gdtm_tile.replace('.tif', '_egm.tif')

    geoid_tile = geoid_tiles[i]
    dod_tile = gdsm_tile.replace('gdsm_riofill0', 'dod')
    dod_tile_egm = gdsm_tile_egm.replace('gdsm_riofill0', 'dod')

    ellipsoid2orthometric(gdsm_tile,geoid_tile,gdsm_tile_egm)
    ellipsoid2orthometric(gdtm_tile,geoid_tile,gdtm_tile_egm)

    _ = calculate_dod(gdtm_tile_egm, gdsm_tile_egm, dod_tile_egm)
    _ = calculate_dod(gdtm_tile, gdsm_tile, dod_tile)

    varname = "edem_egm"#tdem_dem
    varpath = f"{indir}/*/*{varname}.tif"
    varfiles = glob(varpath)
    roivarfiles = [fi for fi in varfiles for t in roitilenames if t in fi]
    roivarfiles

    sfix = "GWR"
    logging.info(f'Style Transfer Started using {sfix}...')
    xpath = roivarfiles[i] #gdtm_tile_egm,gdtm_tile
    ypath = gdtm_tile_egm
    out_path = ypath.replace('.tif', f'_{sfix}.tif')
    if not isfile(out_path):
        logging.info(f"GWR downscaling (gdtm): {tilename}")
        gwrdownxcale(xpath, ypath, out_path, oaux=False, epsg_code=4979, clean=False)
    tc = time.perf_counter()
    logging.info(f'GWR downscaling (gdtm) time: {(tc - tb)/60:.2f} min')

    xpath = roivarfiles[i] #gdtm_tile_egm,gdtm_tile
    out_path = ypath.replace('.tif', f'_{sfix}.tif')
    ps_tile = out_path.replace(f'_{sfix}.tif', '_fmin.tif')
    min_rasters(xpath, out_path, ps_tile)

