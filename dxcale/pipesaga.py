import os
import time 
from datetime import datetime
from glob import glob
from sagadownxcale import gwrdownxcale,bcor_sub
from ensembles import ensemble_prediction
from uvars import edemH_fn_tls,geoid_fn_tls,gdemh_fn_tts,gdemH_fn_tls
from uvars import ypath_tile,geoid_fn_tile,xpath_tile,out_dpath


ti = time.perf_counter()
start_time = datetime.now()

mode = "dep"#dev 
name = 'GWRd_'

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


gwrp_fn_list , fmin_fn_list = [],[]
ti = time.perf_counter()
for dw_weighting in dw_weighting_list:
    gwrp_fn, fmin_fn = gwrdownxcale(xpath, ypath, opath, geoid_fn, 
                 overwrite=False, oaux=False, epsg_code=4979, clean=True,
                 search_range=0, search_radius=10, 
                 dw_weighting=dw_weighting, dw_idw_power=2.0, dw_bandwidth=1.0,
                 logistic=0, model_out=0, grid_system=None,
                 fmin_run=True)
    gwrp_fn_list.append(gwrp_fn)
    fmin_fn_list.append(fmin_fn)

assert len(gwrp_fn_list) >= 2, "No file found for Prediction files..."
assert len(fmin_fn_list) >= 2, "No file found for Prediction files..."
print('Files check passed!!!')

"""


ensemble_prediction(ename:str, pred_paths: list[str], ref_path: str,
                        init_points: int = 10, n_iter: int = 100,
                        avge: bool = True, opte: bool = True,
                        overwrite: bool = True)
"""#check if the files areary created@@@

init_points, n_iter = 5,15 #10,90 #10,50
rfile = xpath
ename_fmin = f"{expname}_{name}_fmin"
pfiles = fmin_fn_list
print(f'Running {ename_fmin}')
avg_raster, opt_raster = ensemble_prediction(ename=ename_fmin, pred_paths=fmin_fn_list, 
                                             ref_path = xpath, 
                                             init_points=init_points, n_iter=n_iter)



ename_gwrp = f"{expname}_{name}_gwrp"
pfiles = gwrp_fn_list
print(f'Running {ename_gwrp}')
avg_raster, opt_raster = ensemble_prediction(ename=ename_gwrp, pred_paths=gwrp_fn_list, 
                                             ref_path = xpath, 
                                             init_points=init_points, n_iter=n_iter)

print('*'*32)
tf = time.perf_counter() - ti
end_time = datetime.now()
duration = end_time - start_time
print(f"stime:{start_time}\netime:{end_time}")
print(f"runtime:{tf/60}\nduration:{duration}")


# pfiles = glob(f"{outdir}/*fmin.tif")  #f'{expname}_{name}
# assert len(pfiles) >= 1, "No file found for Prediction files..."
# 

# #init_points = 5#10
# #n_iter= 15 #100

# init_points = 50
# n_iter= 500
# avg_raster, opt_raster = ensemble_prediction(name, pfiles, rfile,init_points, n_iter)

# tf = time.perf_counter() - ti 
# print(f'RUN.TIME {tf/60} min(s)')
# print(f'pfiles: \n{pfiles}')
# print(f'rfiles: \n{rfile}')
# print(f' ############# {expname} #############')
