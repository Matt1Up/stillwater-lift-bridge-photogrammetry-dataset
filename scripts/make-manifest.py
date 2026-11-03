#!/usr/bin/env python3
"""Build manifest/bridge/{images.csv, checksums.sha256, missions.csv, summary.json} for the
Stillwater Lift Bridge dataset. Same columns as the Plymouth survey's manifest, plus
mission_code (the mission's name on the controller) and blurred.

    python3 make-manifest.py <dataset_images_dir> <missions_images.csv> <blurred.txt> <out_dir>

  battery   from the controller's five flight logs (take-offs 10:41:53, 11:19:42, 12:15:00,
            12:47:30, 13:26:18), not from time gaps: three side passes on one battery were
            4 minutes apart.
  mission   1-34 in flight order. Each tower was flown as two missions back to back (three lower
            rings, then two upper rings), so a 5-ring tower is two mission numbers, one code.
  sha256    of the file as published: for the 350 blurred photos, the blurred file.
"""
import csv, hashlib, json, os, subprocess, sys

img_dir, mis_csv, blurred_txt, out = sys.argv[1:5]
os.makedirs(out, exist_ok=True)
FLIGHTS = ["10:41:53", "11:19:42", "12:15:00", "12:47:30", "13:26:18"]
blurred = {l.strip() for l in open(blurred_txt) if l.strip()}
src = sorted(csv.DictReader(open(mis_csv)), key=lambda r: (r["datetime"], r["filename"]))

ex = {}
cmd = ["exiftool", "-n", "-T", "-FileName", "-ImageWidth", "-ImageHeight", "-AbsoluteAltitude",
       "-GimbalYawDegree", "-ext", "JPG", img_dir]
for line in subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.splitlines():
    f = line.split("\t"); ex[f[0]] = f[1:]
assert sorted(ex) == sorted(r["filename"] for r in src), "image folder and mission table differ"

# mission numbers: split each code's run where photos are more than 20 s apart inside a tower code
rows, mission, last_code, last_t = [], 0, None, None
from datetime import datetime
for r in src:
    t = datetime.strptime(r["datetime"], "%Y:%m:%d %H:%M:%S")
    gap = (t - last_t).total_seconds() if last_t else 1e9
    if r["mission_code"] != last_code or (r["mission_code"] in ("T-1", "T-2") and gap > 20):
        mission += 1
    last_code, last_t = r["mission_code"], t
    h = hashlib.sha256(open(os.path.join(img_dir, r["filename"]), "rb").read()).hexdigest()
    w, hh, alt, yaw = ex[r["filename"]]
    lat, lon = float(r["lat"]), float(r["lon"])
    rows.append(dict(filename=r["filename"], battery=sum(r["datetime"][11:] >= f for f in FLIGHTS),
                     mission=mission, mission_code=r["mission_code"], mission_type=r["mission_type"],
                     bytes=os.path.getsize(os.path.join(img_dir, r["filename"])), sha256=h, width=w, height=hh,
                     datetime=r["datetime"], lat=r["lat"], lon=r["lon"], alt_m=alt, rel_alt_m=r["rel_alt_m"],
                     gimbal_pitch=r["gimbal_pitch"], gimbal_yaw=yaw,
                     gps_valid=str(abs(lat) > 1e-6 and abs(lon) > 1e-6).lower(),
                     blurred=str(r["filename"] in blurred).lower()))
assert mission == 34, mission
with open(os.path.join(out, "images.csv"), "w", newline="") as f:
    wr = csv.DictWriter(f, fieldnames=list(rows[0])); wr.writeheader(); wr.writerows(rows)
with open(os.path.join(out, "checksums.sha256"), "w") as f:
    for r in sorted(rows, key=lambda r: r["filename"]):
        f.write(f"{r['sha256']}  bridge/images/{r['filename']}\n")

ms = []
for m in range(1, 35):
    R = [r for r in rows if r["mission"] == m]
    pit = [float(r["gimbal_pitch"]) for r in R]; z = [float(r["rel_alt_m"]) for r in R]
    ms.append(dict(mission=m, code=R[0]["mission_code"], type=R[0]["mission_type"], battery=R[0]["battery"],
                   photos=len(R), first=R[0]["filename"], last=R[-1]["filename"], start=R[0]["datetime"][11:],
                   end=R[-1]["datetime"][11:], rel_alt_m=f"{min(z):.1f}" if max(z) - min(z) < 1.5 else f"{min(z):.1f}..{max(z):.1f}",
                   gimbal_pitch=f"{min(pit):.1f}..{max(pit):.1f}"))
with open(os.path.join(out, "missions.csv"), "w", newline="") as f:
    wr = csv.DictWriter(f, fieldnames=list(ms[0])); wr.writeheader(); wr.writerows(ms)
tot = sum(r["bytes"] for r in rows)
json.dump(dict(images=len(rows), bytes=tot, gb=round(tot / 1e9, 2), blurred=len(blurred),
               camera_originals=len(rows) - len(blurred), batteries=5, missions=34,
               gps_invalid=sum(r["gps_valid"] == "false" for r in rows)),
          open(os.path.join(out, "summary.json"), "w"), indent=2)
print(f"{len(rows)} images, {tot:,} bytes ({tot / 1e9:.2f} GB), {len(blurred)} blurred, 34 missions")
