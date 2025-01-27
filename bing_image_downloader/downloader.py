import os, sys
import shutil
from pathlib import Path

try:
    from bing import Bing
except ImportError:  # Python 3
    from .bing import Bing


def download(query, limit=100, output_dir='dataset', adult_filter_off=True, 
force_replace=False, timeout=60, filter="",resize=None, verbose=True):

    # engine = 'bing'
    if adult_filter_off:
        adult = 'off'
    else:
        adult = 'on'

    
    image_dir = Path(output_dir).joinpath(query).absolute()

    if force_replace:
        if Path.is_dir(image_dir):
            shutil.rmtree(image_dir)

    # Si le dossier existe déjà, on ignore
    if Path.is_dir(image_dir):
        if verbose:
            print(f"[%] Directory {str(image_dir.absolute())} already exists, skipping download")
        return
    
    # Sinon on crée le dossier
    try:
        Path.mkdir(image_dir, parents=True)
    except Exception as e:
        print('[Error]Failed to create directory.', e)
        sys.exit(1)
        
    print("[%] Downloading Images to {}".format(str(image_dir.absolute())))
    bing = Bing(query, limit, image_dir, adult, timeout, filter,resize, verbose)
    bing.run()


if __name__ == '__main__':
    download('dog', output_dir="..\\Users\\cat", limit=10, timeout=1)
