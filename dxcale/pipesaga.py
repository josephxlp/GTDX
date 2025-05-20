import os
import time 
from glob import glob
from sagadxcale import gwrdownxcale,bcor_sub
from ensembles import ensemble_prediction
from uvars import edemH_fn_tls,geoid_fn_tls,gdemh_fn_tts,gdemH_fn_tls
from uvars import ypath_tile,geoid_fn_tile,xpath_tile

mode = "dev"
name = 'GWRd__'
out_dpath = "/home/ljp238/Downloads/SAGA_DEV/TESTing"

if mode == "dep":
    expname = "TLS"
    geoid_fn = geoid_fn_tls
    xpath = edemH_fn_tls
    ypath = gdemH_fn_tls
    bcor_sub(fine_path=gdemh_fn_tts, coarse_path=geoid_fn, output_path=gdemH_fn_tls)

elif mode == "dev":
    ypath = ypath_tile
    geoid_fn = geoid_fn_tile
    xpath = xpath_tile
    expname = xpath.split('/')[-2]



dw_weighting_list = [0,1,2,3]
outdir = f"{out_dpath}/{expname}"
os.makedirs(outdir, exist_ok=True)
opath =  os.path.join(outdir,f'{expname}_{name}.tif')
overwrite= True#True  # only the 1st time 
aux_files = True 
clean = False
model_out = 1# d:0
#avge: bool = True, opte: bool = True,overwrite: bool = True

ti = time.perf_counter()
for dw_weighting in dw_weighting_list:
    gwrdownxcale(xpath, ypath, opath, geoid_fn, overwrite=False, oaux=False, 
                 epsg_code=4979, clean=True, search_range=0, search_radius=10, 
                 dw_weighting=dw_weighting, dw_idw_power=2.0, dw_bandwidth=1.0,
                 logistic=0, model_out=0, grid_system=None, 
                 fmin_fn_run=True, bcor_fn_run=False, fminbcor_fn_run=False)


pfiles = glob(f"{outdir}/*fmin.tif")  #f'{expname}_{name}
rfile = xpath
assert len(pfiles) >= 1, "No file found for Prediction files..."
assert os.path.isfile(rfile), "reference file NoT Found..."

#init_points = 5#10
#n_iter= 15 #100

init_points = 50
n_iter= 500
avg_raster, opt_raster = ensemble_prediction(pfiles, rfile,init_points, n_iter)

tf = time.perf_counter() - ti 
print(f'RUN.TIME {tf/60} min(s)')
print(f'pfiles: \n{pfiles}')
print(f'rfiles: \n{rfile}')
print(f' ############# {expname} #############')
