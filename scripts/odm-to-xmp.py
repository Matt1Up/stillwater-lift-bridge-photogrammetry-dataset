#!/usr/bin/env python3
"""Write RealityScan XMP camera files from ODM's solve, poses locked, lens as a starting guess.
This is how ODM's cameras were brought into RealityScan for meshing.

    python3 odm-to-xmp.py <reconstruction.json> <images_dir> <out_dir> [--drop name,...]

Conventions, checked against RealityScan's own XMPs for this bridge (2,047 cameras):
  xcr:Rotation = world->camera matrix, row-major, same camera axes as OpenSfM (0.07 deg median);
  xcr:Position = camera centre; FocalLength35mm = OpenSfM focal (normalised by the long side) x 36;
  brown3 k1 k2 k3 agree in size and sign with RealityScan's own fit.
Tangential p1/p2 (~1-2 px at the corners) are not written; the calibration is left as a prior that
RealityScan refines while the poses stay locked. Each photo is hard-linked next to its XMP in
<out_dir>, which is the folder to add in RealityScan (turn off "Use camera priors for georeferencing").
"""
import json, math, os, sys
import numpy as np
recon, imgs, out = sys.argv[1:4]
DROP = set(sys.argv[sys.argv.index('--drop') + 1].split(',')) if '--drop' in sys.argv else set()
r = json.load(open(recon))[0]
cam = next(iter(r['cameras'].values()))
def rot(v):
    v = np.asarray(v, float); a = np.linalg.norm(v); k = v / a
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + math.sin(a) * K + (1 - math.cos(a)) * K @ K
shots = {}
for n, s in r['shots'].items():
    if n in DROP: continue
    R = rot(s['rotation']); shots[n] = (R, -R.T @ np.asarray(s['translation'], float))
names = sorted(shots)
os.makedirs(out, exist_ok=True)
for n in names:
    R, c = shots[n]; base = os.path.splitext(n)[0]
    xmp = f'''<x:xmpmeta xmlns:x="adobe:ns:meta/">
  <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
    <rdf:Description xcr:Version="3" xcr:PosePrior="locked" xcr:Coordinates="absolute"
       xcr:DistortionModel="brown3" xcr:FocalLength35mm="{cam['focal_x'] * 36:.10f}"
       xcr:Skew="0" xcr:AspectRatio="1" xcr:PrincipalPointU="{cam['c_x']:.10f}"
       xcr:PrincipalPointV="{cam['c_y']:.10f}" xcr:CalibrationPrior="initial"
       xcr:CalibrationGroup="1" xcr:DistortionGroup="1" xcr:InTexturing="1" xcr:InMeshing="1"
       xmlns:xcr="http://www.capturingreality.com/ns/xcr/1.1#">
      <xcr:Rotation>{' '.join('%.15f' % v for v in R.ravel())}</xcr:Rotation>
      <xcr:Position>{' '.join('%.10f' % v for v in c)}</xcr:Position>
      <xcr:DistortionCoeficients>{cam['k1']:.12f} {cam['k2']:.12f} {cam['k3']:.12f} 0 0 0</xcr:DistortionCoeficients>
    </rdf:Description>
  </rdf:RDF>
</x:xmpmeta>
'''
    open(f'{out}/{base}.xmp', 'w').write(xmp)
    dst = f'{out}/{n}'
    if not os.path.exists(dst): os.link(f'{imgs}/{n}', dst)   # hard link: no copy, original untouched
print(len(names), 'cameras written to', out)
