#!/usr/bin/env python3
"""Make a patched copy of QGIS.app that starts on macOS 27.

QGIS 4.2.3 crashes at startup on macOS 27.2 (EXC_BREAKPOINT in
CGImageCreate, called from QgsMacNative::setIconPath) while it sets the Dock
icon. Removing the colour-space chunks (sRGB, iCCP, gAMA, cHRM) from
qgis-icon-macos.png avoids the crash. The original app is not modified.

    python3 scripts/macos_patch_qgis.py /Applications/QGIS-final-4_2_3.app ~/Applications/QGIS-4.2.3-patched.app
"""

import shutil
import struct
import subprocess
import sys
from pathlib import Path

DROP = {b"sRGB", b"iCCP", b"gAMA", b"cHRM"}


def strip_png(path):
    data = path.read_bytes()
    out, i = bytearray(data[:8]), 8
    while i < len(data):
        (length,) = struct.unpack(">I", data[i : i + 4])
        if data[i + 4 : i + 8] not in DROP:
            out += data[i : i + 12 + length]
        i += 12 + length
    path.unlink()  # cp -c clones; write a new file instead of changing the shared one
    path.write_bytes(bytes(out))


def main(src, dst):
    src, dst = Path(src), Path(dst).expanduser()
    if dst.exists():
        sys.exit(f"{dst} exists. Remove it first.")
    dst.parent.mkdir(parents=True, exist_ok=True)
    print(f"Copying {src} -> {dst}")
    if subprocess.run(["cp", "-cR", str(src), str(dst)]).returncode:
        shutil.copytree(src, dst, symlinks=True)
    icons = list(dst.glob("Contents/Resources/qgis/images/icons/qgis-icon-macos*.png"))
    for icon in icons:
        strip_png(icon)
        print(f"Patched {icon.relative_to(dst)}")
    subprocess.run(["codesign", "--force", "--deep", "--sign", "-", str(dst)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["xattr", "-dr", "com.apple.quarantine", str(dst)])
    print(f"Done. Use it with: make dev QGIS_APP='{dst}'")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(*sys.argv[1:])
