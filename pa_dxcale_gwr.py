import logging
from utilenames import tilenames_mkd, tilenames_tls, tilenames_rgn
from os.path import join, isfile
from os import makedirs
from glob import glob
from uinterp import riofill
from ufuncs import get_raster_info, gdal_regrid
from uvars import gdsm_v_fn, gdtm_v_fn, outdir, indir
import sys
from uvars import topoxcale_dir
sys.path.append(topoxcale_dir)
from topoxcale.mlxcale import mldownxcale
from topoxcale.sagaxcale import gwrdownxcale
import time

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

logging.info('Loading main variables')
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
logging.info(f'setting baseline dem as {varname}')


for fi in roivarfiles:
    tilename = fi.split('/')[-2]
    tile_dir = join(outdir, 'TILES', tilename)
    makedirs(tile_dir, exist_ok=True)
    logging.info(f"Processing tile: {tilename}")
    _, _, _, xmin, xmax, ymin, ymax, _, _ = get_raster_info(fi)
    
    gdsmv_tile = f"{tile_dir}/{tilename}_gdsm_void.tif"
    gdtmv_tile = f"{tile_dir}/{tilename}_gdtm_void.tif"
    logging.info(f'regriding GDSM @{tilename}...')
    gdal_regrid(gdtm_v_fn, gdtmv_tile, xmin, ymin, xmax, ymax, xres, yres, mode, t_epsg, overwrite=False)
    logging.info(f'regriding GDTM  @{tilename}...')
    gdal_regrid(gdsm_v_fn, gdsmv_tile, xmin, ymin, xmax, ymax, xres, yres, mode, t_epsg, overwrite=False)

    gdsmf_tile = gdsmv_tile.replace('void.tif', 'riofill.tif')
    gdtmf_tile = gdtmv_tile.replace('void.tif', 'riofill.tif')

    logging.info(f'tFilling GDSM @{tilename}...')
    riofill(gdtmv_tile, gdtmf_tile, si=0)
    logging.info(f'tFilling GDSM @{tilename}...')
    riofill(gdsmv_tile, gdsmf_tile, si=0)
    
    gdsmf_tiles.append(gdsmf_tile)
    gdtmf_tiles.append(gdtmf_tile)

tb = time.perf_counter()
logging.info(f'Void filling time: {(tb - ta)/60:.2f} min')



sfix = "GWR"
logging.info(f'Style Transfer Started using {sfix}...')
for tilename in tilenames:
    xpath = f"{indir}/{tilename}/{tilename}_tdem_dem.tif"
    ypath = f"{outdir}/TILES/{tilename}/{tilename}_gdtm_riofill_0.tif"
    out_path = ypath.replace('.tif', f'_{sfix}.tif')
    if not isfile(out_path):
        logging.info(f"GWR downscaling (gdtm): {tilename}")
        gwrdownxcale(xpath, ypath, out_path, oaux=False, epsg_code=4979, clean=False)

tc = time.perf_counter()
logging.info(f'GWR downscaling (gdtm) time: {(tc - tb)/60:.2f} min')

for tilename in tilenames:
    xpath = f"{indir}/{tilename}/{tilename}_tdem_dem.tif"
    ypath = f"{outdir}/TILES/{tilename}/{tilename}_gdsm_riofill_0.tif"
    out_path = ypath.replace('.tif', f'_{sfix}.tif')
    if not isfile(out_path):
        logging.info(f"GWR downscaling (gdsm): {tilename}")
        gwrdownxcale(xpath, ypath, out_path, oaux=False, epsg_code=4979, clean=False)

td = time.perf_counter()
logging.info(f'GWR downscaling (gdsm) time: {(td - tc)/60:.2f} min')

tf = time.perf_counter() - ti
logging.info(f'Total run time: {tf/60:.2f} min')
