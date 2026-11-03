#!/usr/bin/env python3
"""Rewrite RealityScan's original-image XMPs into the same map frame as poses/bridge/colmap
(the one rigid transform measured in colmap-to-map-frame.py: fit residual 0.0000 m).
Only xcr:Rotation and xcr:Position change; every other attribute is kept as written.

    python3 xmp-to-map-frame.py <xmp_in_dir> <odm_reconstruction.json> <xmp_out_dir>
"""
import glob, json, math, os, re, sys
import numpy as np

xin, recon, xout = sys.argv[1:4]
os.makedirs(xout, exist_ok=True)
r = json.load(open(recon))[0]

def rot(v):
    v = np.asarray(v, float); a = np.linalg.norm(v); k = v / a
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + math.sin(a) * K + (1 - math.cos(a)) * K @ K

def pos(s):
    m = re.search(r'xcr:Position="([^"]+)"', s) or re.search(r"<xcr:Position>([^<]+)<", s)
    return m, np.array([float(x) for x in m.group(1).split()])

files = sorted(glob.glob(os.path.join(xin, "*.xmp")))
A, B = [], []
for p in files:
    s = open(p, newline="").read(); n = os.path.basename(p)[:-4] + ".JPG"
    A.append(pos(s)[1]); Ro = rot(r["shots"][n]["rotation"]); B.append(-Ro.T @ np.asarray(r["shots"][n]["translation"], float))
A, B = np.array(A), np.array(B)
ma, mb = A.mean(0), B.mean(0); a, b = A - ma, B - mb
U, S, Vt = np.linalg.svd(b.T @ a); D = np.diag([1, 1, np.sign(np.linalg.det(U @ Vt))])
M = U @ D @ Vt; sc = (S * np.diag(D)).sum() / (a ** 2).sum(); T = mb - sc * M @ ma
assert abs(sc - 1) < 1e-4

worst = 0
for p, Bi in zip(files, B):
    s = open(p, newline="").read()
    m, C = pos(s); Cn = M @ C + T; worst = max(worst, np.linalg.norm(Cn - Bi))
    Rm = re.search(r"<xcr:Rotation>([^<]+)<", s)
    R = np.array([float(x) for x in Rm.group(1).split()]).reshape(3, 3); Rn = R @ M.T
    newpos = " ".join("%.15g" % v for v in Cn)
    s = s[:m.start(1)] + newpos + s[m.end(1):]
    Rm = re.search(r"<xcr:Rotation>([^<]+)<", s)
    s = s[:Rm.start(1)] + " ".join("%.15g" % v for v in Rn.ravel()) + s[Rm.end(1):]
    open(os.path.join(xout, os.path.basename(p)), "w", newline="").write(s)
print(f"{len(files)} XMPs rewritten, worst camera {worst:.6f} m from ODM")
