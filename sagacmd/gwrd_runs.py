
import os
import time 
from sagacmd.s_downxcale import gwrdownxcale
outdir = "/home/ljp238/Downloads/SAGA_DEV/"
# remove the excess d0 
name = 'GWRd_svs'
ypath = "/media/ljp238/12TBWolf/BRCHIEVE/GDEM/TILES/N13E103/N13E103_gdtm_riofill0_egm.tif"
#/media/ljp238/12TBWolf/BRCHIEVE/TILES12/N13E103/N13E103_gedilow.tif
geoid_fn = "/media/ljp238/12TBWolf/BRCHIEVE/TILES12/N13E103/N13E103_egm08.tif"

xpath = "/media/ljp238/12TBWolf/BRCHIEVE/TILES12/N13E103/N13E103_edem_egm.tif"
#/media/ljp238/12TBWolf/BRCHIEVE/TILES12/N13E103/N13E103_s1.tif
#/media/ljp238/12TBWolf/BRCHIEVE/TILES12/N13E103/N13E103_tdem_hem.tif
tname = xpath.split('/')[-2]
opath =  os.path.join(outdir,f'{tname}_{name}.tif')

dw_weighting_list = [0,1,2,3]
ti = time.perf_counter()

for dw_weighting in dw_weighting_list:
    outpaths = gwrdownxcale(xpath, ypath, opath,geoid_fn, 
                            oaux=False, epsg_code=4979, clean=True,
                            search_range=0, search_radius=10, 
                            dw_weighting=dw_weighting, dw_idw_power=2.0, dw_bandwidth=1.0,
                            logistic=0, model_out=0, grid_system=None)
    
tf = time.perf_counter() - ti 
print(f'RUN.TIME {tf/60} min(s)')