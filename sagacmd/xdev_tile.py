import os
import time 
from glob import glob
from s_downxcale import gwrdownxcale
from s_ensemble import ensemble_prediction

# remove the excess d0 
# add on prep data into blocks 

out_dpath = "/home/ljp238/Downloads/SAGA_DEV"
ypath = "/media/ljp238/12TBWolf/BRCHIEVE/GDEM/TILES/N13E103/N13E103_gdtm_riofill0_egm.tif"
geoid_fn = "/media/ljp238/12TBWolf/BRCHIEVE/TILES12/N13E103/N13E103_egm08.tif"
xpath = "/media/ljp238/12TBWolf/BRCHIEVE/TILES12/N13E103/N13E103_edem_egm.tif"
#expname = "tile_dev" # TLS like ROI
expname = xpath.split('/')[-2]
name = 'GWRd_svs'

dw_weighting_list = [0,1,2,3]
outdir = f"{out_dpath}/{expname}"
os.makedirs(outdir, exist_ok=True)
opath =  os.path.join(outdir,f'{expname}_{name}.tif')
overwrite=False
#avge: bool = True, opte: bool = True,overwrite: bool = True

ti = time.perf_counter()
for dw_weighting in dw_weighting_list:
    # add logic if file already exist : grab the logic that modifies the file
    outpaths = gwrdownxcale(xpath, ypath, opath,geoid_fn, overwrite=overwrite,
                            oaux=False, epsg_code=4979, clean=True,
                            search_range=0, search_radius=10, 
                            dw_weighting=dw_weighting, dw_idw_power=2.0, dw_bandwidth=1.0,
                            logistic=0, model_out=0, grid_system=None)


pfiles = glob(f"{outdir}/*fmin.tif")  #f'{expname}_{name}
rfile = xpath
assert len(pfiles) >= 1, "No file found for Prediction files..."
assert os.path.isfile(rfile), "reference file NoT Found..."

init_points = 2#5#10
n_iter=4#5 #100
avg_raster, opt_raster = ensemble_prediction(pfiles, rfile,init_points, n_iter)

tf = time.perf_counter() - ti 
print(f'RUN.TIME {tf/60} min(s)')
print(f'pfiles: \n{pfiles}')
print(f'rfiles: \n{rfile}')




