"""Fetch Hancom's official Automation module into the test workspace only."""
from pathlib import Path
import hashlib
import io
import urllib.parse
import urllib.request
import zipfile

root = Path(__file__).resolve().parent.parent / "_workspace" / "hancom"
root.mkdir(parents=True, exist_ok=True)
url = "https://raw.githubusercontent.com/hancom-io/devcenter-archive/main/hwp-automation/" + urllib.parse.quote("보안모듈(Automation).zip")
data = urllib.request.urlopen(url, timeout=30).read()
with zipfile.ZipFile(io.BytesIO(data)) as archive:
    entry = next(n for n in archive.namelist() if n.lower().endswith("filepathcheckermoduleexample.dll"))
    dll = archive.read(entry)
    (root / "FilePathCheckerModuleExample.dll").write_bytes(dll)
print("Official Hancom module SHA256:", hashlib.sha256(dll).hexdigest())
