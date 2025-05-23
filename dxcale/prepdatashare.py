import tarfile
import os

def create_tar_gz(folder_path, output_filename):
    """
    Compress a folder into a .tar.gz archive.

    Parameters:
    - folder_path (str): Path to the folder to compress.
    - output_filename (str): Output tar.gz file name.
    e.g. create_tar_gz("my_folder", "my_archive.tar.gz")
    """
    with tarfile.open(output_filename, "w:gz") as tar:
        tar.add(folder_path, arcname=os.path.basename(folder_path))
    print(f"Created: {output_filename}")

def extract_tar_gz(tar_path, extract_path="."):
    """
    Extract a .tar.gz archive.

    Parameters:
    - tar_path (str): Path to the .tar.gz archive.
    - extract_path (str): Directory to extract files into (default: current dir).
    e.g. extract_tar_gz("my_archive.tar.gz", "output_folder")
    """
    with tarfile.open(tar_path, "r:gz") as tar:
        tar.extractall(path=extract_path)
    print(f"Extracted to: {extract_path}")


data_nc ="/home/ljp238/Downloads/SAGA_DEV/TESTing/TLS"
data_yc = f"{data_nc}.tar.gz"
create_tar_gz(folder_path=data_nc, output_filename=data_yc)
print('data ready to share!')