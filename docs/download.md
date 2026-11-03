# Downloading

Images, the ZIP, the tie points and ODM's full reconstruction are hosted on Hugging Face, not
GitHub — this repo holds documentation, manifests, checksums, the small pose files and the
small ODM files.

**→ https://huggingface.co/datasets/Matt1up/stillwater-lift-bridge-photogrammetry**

```
bridge/images/      2,223 images                    20.06 GB
zip/                the same 2,223, one file        20.06 GB
bridge/poses/       poses and tie points             0.10 GB
odm/                the OpenDroneMap solve           0.35 GB
```

## Two ways to take the images

**One ZIP.** Simplest if your connection is good. Stored, not compressed: the JPEGs inside are
the published files, byte for byte, in sorted (capture) order under one folder,
`stillwater-lift-bridge-images/`.

```bash
curl -LO https://huggingface.co/datasets/Matt1up/stillwater-lift-bridge-photogrammetry/resolve/main/zip/stillwater-lift-bridge-images.zip
sha256sum stillwater-lift-bridge-images.zip      # must print the line below
unzip stillwater-lift-bridge-images.zip
```

```
9f3f692a70e9fb5e9f9a2cf25df04c01a98d40a7d593e13d1a29e8ca3560d689  stillwater-lift-bridge-images.zip
20,060,468,980 bytes
```

If it stops part-way, `curl -C - -LO <same URL>` resumes. To check every image after
unzipping:

```bash
./scripts/verify.sh --unzipped stillwater-lift-bridge-images
```

**File by file.** Better on a flaky connection: each file is resumable and checksummed on its
own, and you can take part of the set.

```bash
pip install -U huggingface_hub

./scripts/download.sh --images   # 20.06 GB
./scripts/download.sh --zip      # 20.06 GB
./scripts/download.sh --poses    # poses and tie points, 0.10 GB
./scripts/download.sh --odm      # the ODM solve, 0.35 GB
./scripts/download.sh --all      # everything, 40.58 GB — the images twice, loose and zipped
./scripts/verify.sh
```

Raw CLI, without the wrapper. Run it again if it stops — finished files are skipped.

```bash
hf download Matt1up/stillwater-lift-bridge-photogrammetry --repo-type dataset --local-dir ./data --include 'bridge/images/*'
```

To take one part of the capture only, pick the filenames from `manifest/bridge/images.csv` by
its `mission_type` column (`tower`, `tower-both`, `orbit-small`, `orbit-large`, `grid-length`,
`grid-width`, `side`) or its `mission_code` column, and download those.

## What's where

```
bridge/images/               the photos, original aircraft filenames, EXIF intact (350 face/plate-blurred)
bridge/poses/colmap/         cameras.txt, images.txt, points3D.txt (the 1,768,660 tie points)
bridge/poses/xmp/            RealityScan XMP sidecars, one per posed image, named after it
bridge/poses/frame.txt       the coordinate frame and the transform from RealityScan's export
bridge/poses/dropped.txt     the one photo left out of the poses
odm/                         the ODM command, GPS file, configuration and reconstruction
zip/                         all images in one stored ZIP
preview/                     renders of the reconstructed model and the mission maps
```

Everything in `bridge/poses/` except `points3D.txt` is also committed to this repo under
`poses/bridge/`, and everything in `odm/` except `reconstruction.json` under `odm/`, so you can
read the camera parameters without downloading anything. `points3D.txt` (0.09 GB) and
`reconstruction.json` (0.35 GB) are on Hugging Face only.

## Verifying

```bash
./scripts/verify.sh
```

Checks SHA-256 for every file you actually have and ignores the rest, so partial downloads
verify cleanly. The lists are `manifest/bridge/checksums.sha256` (per image),
`manifest/bridge/poses.sha256` (poses and ODM files) and `manifest/zip.sha256`.

`manifest/bridge/images.csv` carries filename, battery, mission, mission code, mission type,
size, SHA-256, dimensions, capture time, GPS, GPS altitude, height above takeoff, gimbal pitch,
gimbal yaw and whether the image was edited (blurred) for every image.
`manifest/bridge/missions.csv` has one row per mission: its code, type, battery, photos, first
and last frame and time, height above takeoff and gimbal pitch range.
