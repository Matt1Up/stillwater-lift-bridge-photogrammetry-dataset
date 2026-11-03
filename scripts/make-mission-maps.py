#!/usr/bin/env python3
"""Draw the four mission maps: where every photo was taken, over the scan itself.
Adapted from the Plymouth survey dataset's scripts/make-mission-maps.py (same look and method).

usage: python3 make-mission-maps.py <images.csv> <missions.csv> <points3D.txt> <out_dir>

  missions-grids.png    GL and GW, the two straight-down grids
  missions-orbits.png   bridge orbits 01-16 and large orbits L1-L5
  missions-towers.png   the two lift towers (T-1, T-2) and the ring around both (T-3), zoomed in
  missions-sides.png    the six side passes, north side then south

Camera positions are each photo's own GPS fix (EXIF). The base map is the dataset's own tie points
(poses/colmap/points3D.txt) seen from straight above, in the same frame (x east, y north, meters,
origin 45.056708, -92.802381): no satellite or map imagery is used. Needs numpy, matplotlib.
"""
import csv, math, os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch

images_csv, missions_csv, points_txt, out_dir = sys.argv[1:5]
os.makedirs(out_dir, exist_ok=True)
LAT0, LON0 = 45.056708315665425, -92.80238136113078
K = 6378137.0 * math.pi / 180

PAGE, INK, INK2, MUTED = "#0d0d0d", "#f0efec", "#c3c2b7", "#898781"
BLUE, ORANGE, GREEN, GOLD = "#3987e5", "#d95926", "#199e70", "#d9a21b"
plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": INK, "axes.edgecolor": PAGE})


def xy(lat, lon):
    return (lon - LON0) * K * math.cos(math.radians(LAT0)), (lat - LAT0) * K


photos = []
for r in csv.DictReader(open(images_csv)):
    x, y = xy(float(r["lat"]), float(r["lon"]))
    photos.append(dict(t=r["datetime"], code=r["mission_code"], x=x, y=y, z=float(r["rel_alt_m"])))
photos.sort(key=lambda p: p["t"])
mrow = {m["code"]: m for m in csv.DictReader(open(missions_csv))}
by = {c: [p for p in photos if p["code"] == c] for c in mrow}

# ── base map from the tie points ────────────────────────────────────────────────────────────
pts = []
with open(points_txt) as f:
    for line in f:
        if line[0] != "#":
            v = line.split()
            pts.append((float(v[1]), float(v[2]), float(v[3]), int(v[4]), int(v[5]), int(v[6])))
P = np.array(pts, dtype=np.float64)
zmed = np.median(P[:, 2])
P = P[(P[:, 2] > zmed - 40) & (P[:, 2] < zmed + 60)]
P = P[np.argsort(P[:, 2])]                       # low first, so the steel draws over the water


def base_image(ext, res):
    x0, x1, y0, y1 = ext
    Q = P[(P[:, 0] > x0) & (P[:, 0] < x1) & (P[:, 1] > y0) & (P[:, 1] < y1)]
    H, W = int((y1 - y0) / res), int((x1 - x0) / res)
    img = np.zeros((H, W, 3), np.float32)
    ii = ((y1 - Q[:, 1]) / res).astype(int); jj = ((Q[:, 0] - x0) / res).astype(int)
    for di in (0, 1):
        for dj in (0, 1):
            img[np.clip(ii + di, 0, H - 1), np.clip(jj + dj, 0, W - 1)] = Q[:, 3:6] / 255.0
    gray = img.mean(2, keepdims=True)
    return (0.55 * img + 0.45 * gray) * 0.62


def frame_axes(fig, rect, ext, res, bar):
    x0, x1, y0, y1 = ext
    ax = fig.add_axes(rect)
    ax.imshow(base_image(ext, res), extent=ext, origin="upper", interpolation="bilinear")
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect("equal"); ax.axis("off")
    u = (x1 - x0) / 420
    sx, sy = x0 + 14 * u, y0 + 14 * u
    ax.plot([sx, sx + bar], [sy, sy], color=INK, lw=2.5, solid_capstyle="butt")
    for t in (0, bar / 2, bar):
        ax.plot([sx + t, sx + t], [sy, sy + 4 * u], color=INK, lw=1.5)
    ax.text(sx + bar / 2, sy + 7 * u, f"{bar:g} m", ha="center", va="bottom", fontsize=14, color=INK)
    ax.annotate("", xy=(x1 - 18 * u, y1 - 12 * u), xytext=(x1 - 18 * u, y1 - 40 * u),
                arrowprops=dict(arrowstyle="-|>", color=INK, lw=2, mutation_scale=18))
    ax.text(x1 - 18 * u, y1 - 47 * u, "N", ha="center", va="top", fontsize=16, color=INK, weight="bold")
    return ax


def side_panel(fig, title, subtitle, legend, foot):
    ax = fig.add_axes([0.625, 0.04, 0.36, 0.92]); ax.axis("off")
    ax.text(0, 1, title, fontsize=27, weight="bold", va="top", color=INK, transform=ax.transAxes, linespacing=1.15)
    ax.text(0, 0.86, subtitle, fontsize=15, va="top", color=INK2, transform=ax.transAxes, linespacing=1.5)
    y = 0.69
    for handle, label, stats in legend:
        if "markers" in handle:
            for (mx, mk) in handle["markers"]:
                ax.plot([mx], [y], transform=ax.transAxes, marker=mk, markersize=13, color=MUTED,
                        markeredgecolor=INK, markeredgewidth=2, linestyle="none", clip_on=False)
        else:
            ax.add_line(Line2D([0.0, 0.08], [y, y], transform=ax.transAxes, **handle))
        ax.text(0.12, y, label, fontsize=17, weight="bold", va="center", color=INK, transform=ax.transAxes)
        for k, s in enumerate(stats):
            ax.text(0.12, y - 0.055 - 0.045 * k, s, fontsize=14.5, va="center", color=INK2, transform=ax.transAxes)
        y -= 0.10 + 0.045 * len(stats)
    ax.text(0, 0.0, foot, fontsize=12.5, va="bottom", color=MUTED, transform=ax.transAxes, linespacing=1.5)


def arrow_along(ax, ps, k, color, size=16):
    a, b = ps[k], ps[min(k + 2, len(ps) - 1)]
    ax.add_patch(FancyArrowPatch((a["x"], a["y"]), (b["x"], b["y"]), arrowstyle="-|>",
                                 mutation_scale=size, color=color, lw=0, zorder=6))


def path(ax, ps, color, lw=1.8, ls="-", closed=False, z=4, s=10):
    X = [p["x"] for p in ps]; Y = [p["y"] for p in ps]
    if closed:
        X, Y = X + X[:1], Y + Y[:1]
    ax.plot(X, Y, color=color, lw=lw, ls=ls, alpha=0.95, zorder=z)
    ax.scatter([p["x"] for p in ps], [p["y"] for p in ps], s=s, color=color, edgecolors=PAGE, linewidths=0.5, zorder=z + 0.5)


def label(ax, x, y, text, fc, fg=INK, size=13):
    ax.text(x, y, text, fontsize=size, weight="bold", color=fg, ha="center", va="center", zorder=9,
            bbox=dict(boxstyle="round,pad=0.3", fc=fc, ec=PAGE, lw=1.5))


def n(code): return int(mrow[code]["photos"])


FOOT = ("Positions: each photo's GPS fix. Base map: the dataset's\n"
        f"own {len(pts) / 1e6:.2f} million tie points from straight above.")
DPI, FIG = 160, (16, 9)
FULL = (-205, 245, -150, 150)          # the whole bridge, landings and orbits
RECT = [0.005, 0.02, 0.60, 0.96]

# ── 1 · grids ───────────────────────────────────────────────────────────────────────────────
fig = plt.figure(figsize=FIG, dpi=DPI, facecolor=PAGE)
ax = frame_axes(fig, RECT, FULL, 0.3, 100)
for code, c, z in (("GL", BLUE, 3), ("GW", ORANGE, 4)):
    ps = by[code]; path(ax, ps, c, lw=2.0, z=z, s=12)
    zm = 10 if code == "GL" else 8          # GL's start sits under GW's end: draw it on top
    ax.scatter([ps[0]["x"]], [ps[0]["y"]], s=150, marker="o", color=c, edgecolors=INK, linewidths=2, zorder=zm)
    ax.scatter([ps[-1]["x"]], [ps[-1]["y"]], s=150, marker="s", color=c, edgecolors=INK, linewidths=2, zorder=zm)
    for k in range(4, len(ps) - 3, 22):
        arrow_along(ax, ps, k, INK, 14)
gl, gw = mrow["GL"], mrow["GW"]
side_panel(fig, "Two grids,\nstraight down",
           "40 m above takeoff, camera at −90°.\nOne along the bridge, one across it.",
           [(dict(color=BLUE, lw=5), "GL · lengthwise", [f"{gl['photos']} photos · 3 lines along the bridge", f"photo every {gl['spacing']} m"]),
            (dict(color=ORANGE, lw=5), "GW · crosswise", [f"{gw['photos']} photos · back and forth across it", "flown after a battery swap"]),
            (dict(markers=[(0.015, "o"), (0.065, "s")]), "Start  ·  end", ["white arrows: direction of flight"])],
           FOOT)
fig.savefig(os.path.join(out_dir, "missions-grids.png"), facecolor=PAGE, dpi=DPI); plt.close(fig)

# ── 2 · bridge orbits ──────────────────────────────────────────────────────────────────────
fig = plt.figure(figsize=FIG, dpi=DPI, facecolor=PAGE)
ax = frame_axes(fig, RECT, FULL, 0.3, 100)
for i in range(1, 6):
    ps = by[f"L{i}"]; path(ax, ps, INK, lw=1.9, ls=(0, (6, 4)), closed=True, z=3, s=12)
    arrow_along(ax, ps, len(ps) // 4, INK, 18)
for i in range(1, 17):
    code = f"{i:02d}"; ps = by[code]
    path(ax, ps, GREEN, lw=1.6, closed=True, z=5, s=8)
for i in range(1, 6):
    ps = by[f"L{i}"]; cx = float(np.mean([p["x"] for p in ps])); cy = float(np.mean([p["y"] for p in ps]))
    label(ax, cx, cy + 50, f"L{i}", INK, fg=PAGE)
for code in ("01", "16"):
    ps = by[code]; cx = float(np.mean([p["x"] for p in ps])); cy = float(np.mean([p["y"] for p in ps]))
    label(ax, cx, cy - 31, code, GREEN)
small = [mrow[f"{i:02d}"] for i in range(1, 17)]
side_panel(fig, "21 orbits down\nthe length",
           "The small rings each overlap the last by\nhalf, west to east, camera on the bridge.",
           [(dict(color=GREEN, lw=5), "01–16 · bridge orbits", [f"{sum(int(m['photos']) for m in small)} photos · radius 21–24 m",
                                                                 "16 m, −25° · the two at each end 24 m, −40°"]),
            (dict(color=INK, lw=3, ls=(0, (3, 2))), "L1–L5 · large orbits", [f"{sum(n(f'L{i}') for i in range(1, 6))} photos · radius 64 m",
                                                                             "35 m above takeoff · −22°"])],
           FOOT)
fig.savefig(os.path.join(out_dir, "missions-orbits.png"), facecolor=PAGE, dpi=DPI); plt.close(fig)

# ── 3 · towers (zoomed) ────────────────────────────────────────────────────────────────────
TW = (-150, 20, -95, 40)
fig = plt.figure(figsize=FIG, dpi=DPI, facecolor=PAGE)
ax = frame_axes(fig, RECT, TW, 0.12, 20)
for code, c in (("T-3", INK), ("T-1", BLUE), ("T-2", ORANGE)):
    ps = by[code]
    ax.plot([p["x"] for p in ps], [p["y"] for p in ps], color=c, lw=1.6 if code != "T-3" else 1.9,
            ls="-" if code != "T-3" else (0, (6, 4)), alpha=0.9, zorder=4 if code != "T-3" else 3)
    ax.scatter([p["x"] for p in ps], [p["y"] for p in ps], s=12, color=c, edgecolors=PAGE, linewidths=0.5, zorder=5)
for code, c, dy in (("T-1", BLUE, 24), ("T-2", ORANGE, 24)):
    ps = by[code]; cx = float(np.mean([p["x"] for p in ps])); cy = float(np.mean([p["y"] for p in ps]))
    label(ax, cx, cy + dy, code, c)
ps = by["T-3"]; label(ax, float(np.mean([p["x"] for p in ps])), float(np.mean([p["y"] for p in ps])) - 46, "T-3", INK, fg=PAGE)
side_panel(fig, "The two\nlift towers",
           "Five stacked rings around each tower,\nthen two around both.",
           [(dict(color=BLUE, lw=5), "T-1 · west tower", [f"{mrow['T-1']['photos']} photos · 5 rings, radius 15 m", "15–37 m above takeoff"]),
            (dict(color=ORANGE, lw=5), "T-2 · east tower", [f"{mrow['T-2']['photos']} photos · 5 rings, radius 15 m", "15–37 m above takeoff"]),
            (dict(color=INK, lw=3, ls=(0, (3, 2))), "T-3 · both towers", [f"{mrow['T-3']['photos']} photos · 2 rings, radius 37 m", "19–41 m above takeoff"])],
           FOOT)
fig.savefig(os.path.join(out_dir, "missions-towers.png"), facecolor=PAGE, dpi=DPI); plt.close(fig)

# ── 4 · side passes ────────────────────────────────────────────────────────────────────────
fig = plt.figure(figsize=FIG, dpi=DPI, facecolor=PAGE)
ax = frame_axes(fig, RECT, FULL, 0.3, 100)
SIDE = [("N-45", GOLD), ("N-22", GREEN), ("N-0", BLUE), ("S-45", GOLD), ("S-22", GREEN), ("S-0", BLUE)]
for code, c in SIDE:
    ps = by[code]; path(ax, ps, c, lw=2.0, z=4, s=9)
    arrow_along(ax, ps, len(ps) // 2, INK, 16)
for code, txt, dy in (("N-45", "North side", 22), ("S-0", "South side", -22)):
    ps = by[code]; label(ax, float(np.mean([p["x"] for p in ps])), float(np.mean([p["y"] for p in ps])) + dy, txt, MUTED)
alt = {c: mrow[c]["alt"] for c, _ in SIDE}
side_panel(fig, "Six passes along\nthe sides",
           "Flown onsite, north side first, then the\nsouth: −45°, −22°, then level.",
           [(dict(color=GOLD, lw=5), "−45°", [f"{n('N-45') + n('S-45')} photos · {alt['N-45']} m north · {alt['S-45']} m south"]),
            (dict(color=GREEN, lw=5), "−22°", [f"{n('N-22') + n('S-22')} photos · {alt['N-22']} m north · {alt['S-22']} m south"]),
            (dict(color=BLUE, lw=5), "Level · 0°", [f"{n('N-0') + n('S-0')} photos · {alt['N-0']} m north · {alt['S-0']} m south"])],
           FOOT)
fig.savefig(os.path.join(out_dir, "missions-sides.png"), facecolor=PAGE, dpi=DPI); plt.close(fig)
print("wrote", ", ".join(f for f in sorted(os.listdir(out_dir)) if f.startswith("missions-")))
