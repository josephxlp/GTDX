import os 
import sys 
from glob import glob
from uvars import gtdx_dir,mosaic_dir,barchive12tile_dir
from uvars import gdtm_v_fn
from tqdm import tqdm

sys.path.append(gtdx_dir)
from ufuncs import mosaic,get_raster_info,gdal_regrid
from uinterp import riofill
from utilenames import tilenames_tls

xres, yres = 0.01057350068885258912, -0.01057350068885258912
t_epsg = 'EPSG:4326'
mode = "num"
si = 0 
variables = ["esawc.tif", "egm08.tif", "edem_egm.tif"]

files = glob(f"{barchive12tile_dir}/*/*.tif")
print(f"files: {len(files)}")

tfiles = [fi for fi in files if any(tname in fi for tname in tilenames_tls)]
print(f"tfiles: {len(tfiles)}")

for var in tqdm(variables, total=len(variables)):
    vtfile = [fi for fi in tfiles if fi.endswith(var)]
    print(f"vfile: {len(vtfile)}")

    assert len(vtfile) == len(tilenames_tls), f"Error: {var} not found in tfiles"

    vblock_tif = f"{mosaic_dir}/{var}"
    print(f"vblock_tif: {vblock_tif}")
    if not os.path.isfile(vblock_tif):
        mosaic(input_files=vtfile, output_file=vblock_tif)

    if var == "edem_egm.tif":
        block_gdtmv = f"{mosaic_dir}/gdtmv.tif"
        print(f"Clipping... {vblock_tif}")
        _, _, _, xmin, xmax, ymin, ymax, _, _ = get_raster_info(vblock_tif)
        gdal_regrid(gdtm_v_fn, block_gdtmv, xmin, ymin, xmax, ymax, xres, yres, mode, t_epsg, overwrite=False)

        block_gdtmf = f"{mosaic_dir}/gdtmf_{si}.tif"
        if not os.path.isfile(block_gdtmf):
            print(f"Filling... {vblock_tif}")
            riofill(block_gdtmv, block_gdtmf, si=si)

    print('Done!')








