import os
import time 
from glob import glob
from s_downxcale import gwrdownxcale,bcor_sub
from s_ensemble import ensemble_prediction


geoid_fn = "/media/ljp238/12TBWolf/BRCHIEVE/GDEM/BLOCK/edem_egm/TLS/EGM08c.tif"
xpath = edemH_fn = "/media/ljp238/12TBWolf/BRCHIEVE/GDEM/BLOCK/edem_egm/TLS/TLS_edem_egm.tif"
gdemh_fn = "/media/ljp238/12TBWolf/BRCHIEVE/GDEM/BLOCK/edem_egm/TLS/gdtmf_0.tif" 

ypath = gdemH_fn = gdemh_fn.replace('.tif', '_egm.tif') # 4326 to 4979 gdemh_fn - geoid_fn
bcor_sub(fine_path=gdemh_fn, coarse_path=geoid_fn, output_path=gdemH_fn)

out_dpath = "/home/ljp238/Downloads/SAGA_DEV/TESTing"
expname = "TLS"
name = 'GWRd_'

dw_weighting_list = [0,1,2,3]
outdir = f"{out_dpath}/{expname}"
os.makedirs(outdir, exist_ok=True)
opath =  os.path.join(outdir,f'{expname}_{name}.tif')
overwrite= True#True  # only the 1st time 
aux_files = True 
#avge: bool = True, opte: bool = True,overwrite: bool = True

ti = time.perf_counter()
for dw_weighting in dw_weighting_list:
    # add logic if file already exist : grab the logic that modifies the file
    outpaths = gwrdownxcale(xpath, ypath, opath,geoid_fn, overwrite=overwrite,
                            oaux=aux_files, epsg_code=4979, clean=True,
                            search_range=0, search_radius=10, 
                            dw_weighting=dw_weighting, dw_idw_power=2.0, dw_bandwidth=1.0,
                            logistic=0, model_out=0, grid_system=None)


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


