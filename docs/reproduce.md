# Reproducing the reconstruction

The images are ordinary geotagged JPEGs, so any structure-from-motion tool reads them. Below is
what to expect from *this* capture before you spend hours on it.

The scan ships solved poses for the original photos in [`../poses/bridge/`](../poses/bridge/),
so you can skip alignment and go straight to meshing or splatting. Re-align only if you want to
compare.

---

## What to expect

| | |
|---|---|
| images | 2,223 |
| solved | **2,223 / 2,223**, one model (OpenDroneMap 3.6.2); 2,222 poses published |
| solver | OpenDroneMap for the cameras; RealityScan for the mesh, with the cameras locked |

**The spans repeat.** Eight truss spans look nearly the same, and a matcher that compares every
photo with every other will find convincing matches between different spans. RealityScan, run
on these photos with default settings, split them into 9 pieces and placed a run of photos about
one span from where they were taken.

**Match by GPS neighbors.** What worked was limiting matching to each photo's nearest GPS
neighbors, so photos a span apart are rarely compared. With ODM:

```bash
docker run --rm --gpus all -v <project>:/datasets/code opendronemap/odm:gpu \
  --project-path /datasets --geo /datasets/code/geo.txt \
  --matcher-neighbors 30 --feature-quality ultra --max-concurrency 8 --end-with opensfm
```

with the photos in `<project>/images/` and [`../odm/geo.txt`](../odm/geo.txt) in `<project>/`.
It took about 6 hours 20 minutes for the camera solve alone.

**Don't trust the GPS altitude.** The drone's recorded GPS altitude shifted by up to 11.6 m over
the day, and a solver that uses it as a prior will tilt the model. `geo.txt` replaces it with the
height above takeoff (plus a constant 118.5 m), which is consistent across flights because every
flight took off from the same height.

**One photo is misplaced.** ODM put `DJI_20261031122835_0682_D.JPG` 115 m from where it was taken.
It is left out of the published poses ([`../poses/bridge/dropped.txt`](../poses/bridge/dropped.txt)).

**DJI frame numbers repeat.** The aircraft's counter wraps after 0999, so 935 frame numbers
appear more than once in this set. Match photos by their full filename (which carries the
capture time), never by the four-digit number alone.

---

## COLMAP / GLOMAP

```bash
colmap feature_extractor \
  --database_path db.db --image_path images/ \
  --ImageReader.camera_model OPENCV --ImageReader.single_camera 1

colmap spatial_matcher --database_path db.db   # GPS neighbors, not exhaustive: the spans repeat

colmap mapper --database_path db.db --image_path images/ --output_path sparse/
```

Every frame is 4096 × 3072 from the same lens at the same settings, and the published poses use
one shared calibration. COLMAP reads the GPS altitude from EXIF; as above, it is unreliable here.
This COLMAP recipe has not been run on this set — ODM is what produced the published solve.

---

## Scale

There is no scale reference in this capture. The published poses are in meters because the solve
is anchored to the photos' GPS positions — see *Coordinate frame* in the [README](../README.md)
and [`../poses/bridge/frame.txt`](../poses/bridge/frame.txt).

---

## Gaussian splatting

`poses/bridge/colmap/` is a drop-in sparse reconstruction — `cameras.txt`, `images.txt` and
`points3D.txt` (the last hosted with the images). The cameras are `FULL_OPENCV`, for the
original photos. A pipeline that reads OpenCV distortion trains on them directly; one that
accepts only pinhole cameras needs undistorted copies first:

```bash
colmap image_undistorter --image_path images/ --input_path colmap/ --output_path undistorted/
```

The `mission` and `mission_type` columns of `manifest/bridge/images.csv` let you train on part
of the capture (only the towers, only the orbits) and compare.
