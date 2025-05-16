#[] try doing this as multi-variate : maybe the results will improve 
import os 
import sys
#os.chdir('..') only for notebooks
import time 
import logging
from glob import glob
from os.path import isfile
from utilenames import tilenames_tls
from uinterp import riofill
from ufuncs import get_raster_info, gdal_regrid,mosaic,fmin_postprocessing,subtract_rasters
from uvars import gdsm_v_fn, gdtm_v_fn, egm08_fn, outdir, indir
from uvars import topoxcale_dir
sys.path.append(topoxcale_dir)
#from topoxcale.mlxcale import mldownxcale
from topoxcale.sagaxcale import gwrdownxcale


def notify_after_delay(title="Reminder", 
                       message="10 minutes have passed", 
                       delay_sec=3):
    time.sleep(delay_sec)
    os.system(f'notify-send "{title}" "{message}"')



logging.basicConfig(
    level= logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler('xblock_hgdem.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

# add the ML version two, and chose both or either 

varname = "edem_egm"
stmethod = "GWR"
xres, yres = 0.01057350068885258912, -0.01057350068885258912
t_epsg = 'EPSG:4326'
mode = "num"
si = 0 
block_names = ["TLS"]#["MKD","TLS","RGN"]
block_tiles = [tilenames_tls]#[tilenames_mkd,tilenames_tls,tilenames_rgn]
block_dir = "/media/ljp238/12TBWolf/BRCHIEVE/GDEM/BLOCK"

seeds = ['S1','S2','S3','S4','S5']

if __name__ == '__main__':
    ty = time.perf_counter()
    

    for seed in seeds:
        logging.info(f'0. Started Seed {seed}')
    
        assert len(block_names) == len(block_tiles)
        logging.info('1. Loading main variables')
        for i in range(len(block_names)):
            ta = time.perf_counter()
            logging.info('2. Selecting baseline dem')
            block_name = block_names[i]
            notify_after_delay(title="Started", message=f"Running @{block_name}", delay_sec=5)
            roitilenames = block_tiles[i]
            block_roi_dir = f"{block_dir}/{varname}/{block_name}"
            os.makedirs(block_roi_dir, exist_ok=True)
            varpath = f"{indir}/*/*{varname}.tif"
            varfiles = glob(varpath)
            roivarfiles = [fi for fi in varfiles for t in roitilenames if t in fi]
            print(f"{block_name} {len(roivarfiles)}")
            block_dem = f"{block_roi_dir}/{block_name}_{varname}.tif"
            if not isfile(block_dem):
                logging.info(f'mosaicing Gdtm @{block_name}...')
                mosaic(input_files=roivarfiles, output_file=block_dem)
            tb = time.perf_counter()
            logging.info(f'mosaicing time: {(tb - ta)/60:.2f} min')
            logging.info('3. mosaicing dems')

            block_gdtmv = f"{block_roi_dir}/gdtmv.tif"
            if not os.path.isfile(block_gdtmv):
                logging.info(f'regriding Gdtm  @{block_name}...')
                _, _, _, xmin, xmax, ymin, ymax, _, _ = get_raster_info(block_dem)
                gdal_regrid(gdtm_v_fn, block_gdtmv, xmin, ymin, xmax, ymax, xres, yres, mode, t_epsg, overwrite=False)

            tc = time.perf_counter()
            logging.info(f'regriding time: {(tc - tb)/60:.2f} min')
            logging.info('4. regriding by mosaic dem')


            block_gdtmf = f"{block_roi_dir}/gdtmf_{si}.tif"
            if not isfile(block_gdtmf):
                logging.info(f'riofilling... @{block_name}...')
                riofill(block_gdtmv, block_gdtmf, si=si)
                
            td = time.perf_counter()
            logging.info(f'filling time: {(td- tc)/60:.2f} min')
            logging.info('5. filled by mosaic gdem')

            logging.info(f'Style Transfer Started using {stmethod}...')
            xpath = block_dem
            ypath = block_gdtmf
            out_path = ypath.replace('.tif', f'_{stmethod}_h_{seed}.tif')
            if not isfile(out_path):
                logging.info(f"GWR downscaling (gdtm): {block_name}")
                gwrdownxcale(xpath, ypath, out_path, oaux=False, epsg_code=4979, clean=False)
            
            te = time.perf_counter()
            logging.info(f'6.GWR  time: {(te - td)/60:.2f} min')

            logging.info('PostProcessing Started ...')
            block_geoid = f"{block_roi_dir}/EGM08c.tif" # out_path: fine
            if not os.path.isfile(block_geoid):
                logging.info(f'regriding egm08  @{block_name}...')
                _, _, _, xmin, xmax, ymin, ymax, _, _ = get_raster_info(block_dem) #out_path
                gdal_regrid(egm08_fn, block_geoid, xmin, ymin, xmax, ymax, 
                        xres, yres, mode, t_epsg, overwrite=False)
                
            fine_raster = out_path
            coarse_raster = block_geoid
            bcor_tif = fine_raster.replace('.tif', f"__bcor_{seed}.tif")
            subtract_rasters(fine_raster, coarse_raster, bcor_tif)
            tf = time.perf_counter()
            logging.info(f'7. bcor  time: {(tf - te)/60:.2f} min')

            fmin_tif = bcor_tif.replace('.tif', f'_fmin_{seed}.tif')
            if not os.path.isfile(fmin_tif):
                logging.info(f"running fmin_postprocessing....: {block_name}")
                fmin_postprocessing(xpath, bcor_tif, fmin_tif)

            tg = time.perf_counter()
            logging.info(f'8. fmin_postprocessing  time: {(tg - tf)/60:.2f} min')

            tz = time.perf_counter()
            # make it silent
            logging.info(f'RUN.TIME: {(tz - ty)/60:.2f} min')
            notify_after_delay(title="Finished", message=f"Running @{block_name}", delay_sec=1)

    logging.info(f'00. FINISHED Seeds {len(seed)}:: {seeds}')
    notify_after_delay(title="Finished", message=f'00. FINISHED Seeds {len(seed)}:: {seeds}', delay_sec=1)


