import os 
import sys 
from glob import glob
from uvars import gtdx_dir,mosaic_dir,barchive12tile_dir
from tqdm import tqdm

sys.path.append(gtdx_dir)
from ufuncs import mosaic
from utilenames import tilenames_tls


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








