#!/usr/bin/env python3
"""Move RealityScan's COLMAP export into ODM's map frame (east, north, up in meters from ODM's GPS
origin) with ONE rigid transform measured from the cameras themselves.

RealityScan kept every ODM camera exactly (poses were locked) but wrote them in its own frame:
the same cameras, shifted and turned 1.13 degrees. Fitting the 2,222 exported camera centers to
ODM's gives scale 1.000000 and a residual of 0.0000 m, so this is a change of frame only.

    python3 colmap-to-map-frame.py <colmap_in> <xmp_dir> <odm_reconstruction.json> <colmap_out>
Writes cameras.txt (copied), images.txt and points3D.txt (transformed) and frame.txt.
"""
import glob, json, math, os, re, shutil, sys
import numpy as np

cin, xdir, recon, cout = sys.argv[1:5]
os.makedirs(cout, exist_ok=True)
r = json.load(open(recon))[0]

def rot(v):
    v = np.asarray(v, float); a = np.linalg.norm(v); k = v / a
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + math.sin(a) * K + (1 - math.cos(a)) * K @ K

A, B = [], []
for p in sorted(glob.glob(os.path.join(xdir, '*.xmp'))):
    s = open(p).read(); n = os.path.basename(p)[:-4] + '.JPG'
    m = re.search(r'xcr:Position="([^"]+)"', s) or re.search(r'<xcr:Position>([^<]+)<', s)
    A.append([float(x) for x in m.group(1).split()])
    Ro = rot(r['shots'][n]['rotation']); B.append(-Ro.T @ np.asarray(r['shots'][n]['translation'], float))
A, B = np.array(A), np.array(B)
ma, mb = A.mean(0), B.mean(0); a, b = A - ma, B - mb
U, S, Vt = np.linalg.svd(b.T @ a); D = np.diag([1, 1, np.sign(np.linalg.det(U @ Vt))])
M = U @ D @ Vt; s = (S * np.diag(D)).sum() / (a ** 2).sum(); T = mb - s * M @ ma
res = np.linalg.norm((s * (M @ A.T)).T + T - B, axis=1)
assert abs(s - 1) < 1e-4 and res.max() < 0.01, (s, res.max())

def q2R(w, x, y, z):
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
def R2q(R):
    w = math.sqrt(max(0, 1 + R[0, 0] + R[1, 1] + R[2, 2])) / 2
    x = math.copysign(math.sqrt(max(0, 1 + R[0, 0] - R[1, 1] - R[2, 2])) / 2, R[2, 1] - R[1, 2])
    y = math.copysign(math.sqrt(max(0, 1 - R[0, 0] + R[1, 1] - R[2, 2])) / 2, R[0, 2] - R[2, 0])
    z = math.copysign(math.sqrt(max(0, 1 - R[0, 0] - R[1, 1] + R[2, 2])) / 2, R[1, 0] - R[0, 1])
    q = np.array([w, x, y, z]); return q / np.linalg.norm(q)

shutil.copy(os.path.join(cin, 'cameras.txt'), os.path.join(cout, 'cameras.txt'))
lines = open(os.path.join(cin, 'images.txt')).read().split('\n'); out = []; i = 0; worst = 0
while i < len(lines):
    L = lines[i]
    if L.startswith('#') or not L.strip():
        out.append(L); i += 1; continue
    f = L.split()
    R = q2R(*map(float, f[1:5])); t = np.array(list(map(float, f[5:8])))
    Rn = R @ M.T; tn = t - Rn @ T               # world X_new = M X + T, scale 1
    out += [' '.join([f[0]] + ['%.15g' % v for v in R2q(Rn)] + ['%.15g' % v for v in tn] + f[8:]), lines[i + 1]]
    C_new = -Rn.T @ tn
    worst = max(worst, np.min(np.linalg.norm(B - C_new, axis=1)))
    i += 2
open(os.path.join(cout, 'images.txt'), 'w').write('\n'.join(out))
with open(os.path.join(cin, 'points3D.txt')) as fi, open(os.path.join(cout, 'points3D.txt'), 'w') as fo:
    for L in fi:
        if L.startswith('#'): fo.write(L); continue
        f = L.split(); X = M @ np.array(list(map(float, f[1:4]))) + T
        fo.write(' '.join([f[0]] + ['%.6f' % v for v in X] + f[4:]) + '\n')
ang = math.degrees(math.acos((np.trace(M) - 1) / 2))
open(os.path.join(cout, 'frame.txt'), 'w').write(
    f'Frame: ODM map frame (x east, y north, z up, meters) from origin {json.dumps(json.load(open(os.path.join(os.path.dirname(recon), "reference_lla.json"))))}\n'
    f'Applied to the RealityScan export: rotation {ang:.4f} deg, translation {T.round(4).tolist()} m, scale {s:.6f}\n'
    f'Fit over {len(A)} cameras: residual max {res.max():.6f} m\n')
print(f'rotation {ang:.4f} deg, fit residual max {res.max():.6f} m, worst camera after transform {worst:.6f} m from ODM')
