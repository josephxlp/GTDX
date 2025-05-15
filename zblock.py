import os
import time
import logging
from utilenames import tilenames_mkd, tilenames_tls, tilenames_rgn
from os.path import join, isfile
from os import makedirs
from glob import glob
from uinterp import riofill
from ufuncs import get_raster_info, gdal_regrid,mosaic,fmin_postprocessing
from uvars import gdsm_v_fn, gdtm_v_fn, egm08_fn, outdir, indir
from ugeoid import ellipsoid2orthometric
import sys
from uvars import topoxcale_dir
sys.path.append(topoxcale_dir)
#from topoxcale.mlxcale import mldownxcale
from topoxcale.sagaxcale import gwrdownxcale


def notify_after_delay(title="Reminder", message="10 minutes have passed", delay_sec=600):
    time.sleep(delay_sec)
    os.system(f'notify-send "{title}" "{message}"')


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("processing.log"), # add date to this 
        logging.StreamHandler(sys.stdout)
    ]
)


ti = time.perf_counter()
varname = "edem_egm"#tdem_dem:
#varname = "tdem_dem" #:testing (should be egm08 for fmim_postprocessing)
stmethod = "GWR"

xres, yres = 0.01057350068885258912, -0.01057350068885258912
t_epsg = 'EPSG:4326'
mode = "num"
block_names = ["MKD","TLS","RGN"]
block_tiles = [tilenames_mkd,tilenames_tls,tilenames_rgn]
si = 0 
block_dir = "/media/ljp238/12TBWolf/BRCHIEVE/GDEM/BLOCK"
logging.info('Loading main variables')
assert len(block_names) == len(block_tiles)

block_tif_list = []
gdtmf_tiles = []
geoid_tiles = []
logging.info(f'setting baseline dem as {varname}')

for i in range(len(block_names)):
   
    ta = time.perf_counter()
    
    block_name = block_names[i]
    notify_after_delay(title="Started", message=f"Running @{block_name}", delay_sec=5)

    roitilenames = block_tiles[i]
    block_roi_dir = f"{block_dir}/{varname}/{block_name}"
    os.makedirs(block_roi_dir, exist_ok=True)
    logging.info(f"Processing tile: {block_name}")

    varpath = f"{indir}/*/*{varname}.tif"
    varfiles = glob(varpath)
    roivarfiles = [fi for fi in varfiles for t in roitilenames if t in fi]
    print(f"{block_name} {len(roivarfiles)}")
    block_dem = f"{block_roi_dir}/{block_name}_{varname}.tif"
    if not os.path.isfile(block_dem):
        mosaic(input_files=roivarfiles, output_file=block_dem)

    block_tif_list.append(block_dem)
    block_geoid = f"{block_roi_dir}/egm08.tif"
    block_gdtmv = f"{block_roi_dir}/gdtmv.tif"
    block_gdtmf = f"{block_roi_dir}/gdtmf_{si}.tif"

    logging.info(f'regriding GDTM  @{block_name}...')
    _, _, _, xmin, xmax, ymin, ymax, _, _ = get_raster_info(block_dem)
    gdal_regrid(gdtm_v_fn, block_gdtmv, xmin, ymin, xmax, ymax, 
                xres, yres, mode, t_epsg, overwrite=False)
    
    gdal_regrid(egm08_fn, block_geoid, xmin, ymin, xmax, ymax, 
                xres, yres, mode, t_epsg, overwrite=False)
    
    logging.info(f'tFilling GDTM @{block_name}...')
    riofill(block_gdtmv, block_gdtmf, si=si)
    tb = time.perf_counter()
    logging.info(f'Void filling time: {(tb - ta)/60:.2f} min')

    logging.info(f'Geoid Transform @{block_name}...')
    block_gdtmf_egm = block_gdtmf.replace('.tif', '_egm.tif')
    if not os.path.isfile(block_gdtmf_egm):
        ellipsoid2orthometric(block_gdtmf,block_geoid,block_gdtmf_egm)

    logging.info(f'Style Transfer Started using {stmethod}...')
    xpath = block_dem
    ypath = block_gdtmf_egm
    out_path = ypath.replace('.tif', f'_{stmethod}.tif')
    if not isfile(out_path):
        logging.info(f"GWR downscaling (gdtm): {block_name}")
        gwrdownxcale(xpath, ypath, out_path, oaux=False, epsg_code=4979, clean=False)
    tc = time.perf_counter()
    logging.info(f'GWR downscaling (gdtm) time: {(tc - tb)/60:.2f} min')

    gdtmf_tiles.append(block_gdtmf)
    geoid_tiles.append(block_geoid)

    td = time.perf_counter()
    ps_tile = out_path.replace(f'_{stmethod}.tif', '_fmin.tif')
    if not os.path.isfile(ps_tile):
        fmin_postprocessing(xpath, out_path, ps_tile)

    logging.info(f'Postprocessing time: {(td - tc)/60:.2f} min')
    notify_after_delay(title="Finished", message=f"Running @{block_name}", delay_sec=5)

tf = time.perf_counter() - ti 
logging.info(f'Postprocessing time: {tf/60:.2f} min')

#notify_after_delay(title="Finished Running", message="10 minutes have passed", delay_sec=1)



# food [x]
# emails [x]
# :: check the properies of the data i want to operate 
# rolf finish V4 : 
# # could not find it, but this is the best i did to rplicate the results
## the models are probabilistic so expect some variations
##@ >[]> find the other codes as well 
##@@ []
##@@ []do the mlxcale version as well

# mldownscale using the other paper that includes over stuff
# add another variables to both methods and see the results

# dem,hem,
# dem,hem,s1
# if V4 works, right a paper for tml and iml just for TLS showing potential
