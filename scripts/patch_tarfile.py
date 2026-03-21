import tarfile as _tarfile
import shutil as _shutil
import os as _os
import site

_orig_extractall = _tarfile.TarFile.extractall

def _fast_extractall(self, path=".", members=None, **kwargs):
    prebuilt = "/tmp/hostpython3.11_ready"
    if _os.path.isdir(prebuilt) and "hostpython3.11" in str(path):
        print(f"نسخ من المفكوك مسبقاً إلى {path}")
        if _os.path.exists(path):
            _shutil.rmtree(path)
        _shutil.copytree(prebuilt, path)
        print("تم النسخ السريع")
        return
    _orig_extractall(self, path, members, **kwargs)

_tarfile.TarFile.extractall = _fast_extractall

site_pkg = site.getsitepackages()[0]
dest = _os.path.join(site_pkg, "sitecustomize.py")
with open(__file__) as src, open(dest, "a") as dst:
    dst.write(src.read())
print(f"تم تطبيق الـ patch على {dest}")
