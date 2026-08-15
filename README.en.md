# ReTKY2JGD

A QGIS plugin that repairs National Forest GIS data converted from **Tokyo Datum** to **JGD2000** by a simplified transformation. It reverses that conversion back to Tokyo Datum, then applies the **official TKY2JGD conversion** (the `TKY2JGD.gsb` grid correction) to produce more accurate coordinates.

[日本語 README](README.md)

![QGIS](https://img.shields.io/badge/QGIS-3.34%E2%80%933.99-green)
![Version](https://img.shields.io/badge/version-1.3.0-blue)

---

## Background

The [National Forest GIS data (published March 2025)](https://www.geospatial.jp/ckan/dataset/a45), released by the Forestry Agency of Japan through the G-Spatial Information Center, includes data that was converted to JGD2000 using a **simplified transformation** — a three-parameter Helmert approximation of each zone's origin. This method leaves residual errors ranging from a few tens of centimetres to several metres depending on the region.

A proper coordinate conversion (grid correction via `TKY2JGD.gsb`) requires reversing that shortcut back to Tokyo Datum first, then re-applying TKY2JGD from there. The official dataset may be corrected in the future, but wherever deliverables built from the original data already exist — on paper or otherwise — the same re-conversion work is needed independently.

This plugin brings that two-stage re-conversion into QGIS as a single operation. Earlier versions of this project performed the same work with QGIS Model Designer `.model3` files and an Excel macro that generated batch lists; that workflow has since been consolidated into this plugin.

---

## ⚠️ Read this before using the plugin

### 1. `TKY2JGD.gsb` is not bundled

This plugin depends on the GSI coordinate transformation grid `TKY2JGD.gsb`, but **does not redistribute it**. Obtain it legitimately from either:

- The Geospatial Information Authority of Japan ([coordinate transformation parameters page](https://www.gsi.go.jp/sokuchikijun/sokuchikijun41012.html#zahyo))
- [JapanGridShift](https://github.com/tohka/JapanGridShift), maintained by tohka (if you use this source, also review that repository's own usage notes)

Place the file in one of these locations:

- `ReTKY2JGD/data/TKY2JGD.gsb` (inside the plugin folder — recommended)
- The QGIS PROJ data directory (whatever `QgsApplication.projPath()` returns)

Either `TKY2JGD.gsb` or `tky2jgd.gsb` is detected. If no grid is found, the plugin reports an error showing the expected path.

### 2. Only one kind of input is valid

This plugin is **exclusively** for data that was converted from Tokyo Datum to JGD2000 by a simplified transformation.

- Applying it to data that was already converted correctly with TKY2JGD will **shift the coordinates a second time and corrupt them**.
- Do not apply it to data originally surveyed in JGD2000 or another world geodetic datum.

### 3. The layer's declared CRS is ignored

Whatever CRS metadata the input layer carries is **not** used. The plane rectangular CRS you pick in the dialog (EPSG:2443–2461) is assigned to the layer before processing. **Choosing the wrong zone produces wrong results.**

### 4. Seismic crustal-deformation parameters are out of scope

This plugin does exactly one thing: it undoes the simplified-conversion error and re-applies the correct TKY2JGD datum transformation. It does **not** apply correction parameters for crustal deformation caused by earthquakes — for example the 2011 Tohoku earthquake (`touhokutaiheiyouoki2011`). Its output is **not intended to be used directly as a survey deliverable**. Always cross-check against field surveys or official results before relying on it.

---

## How the conversion works

To remove the error introduced by the three-parameter simplified Helmert transformation (`x=146.414, y=-507.337, z=-680.507`), the plugin runs three explicit steps as PROJ pipelines:

| Step | Operation |
|------|-----------|
| 1 | Assign the selected plane rectangular CRS (EPSG:2443–2461) to the layer |
| 2 | Invert the transverse Mercator projection, then invert the simplified Helmert transformation to recover Tokyo Datum geographic coordinates (EPSG:4301) |
| 3 | Apply the `TKY2JGD.gsb` horizontal grid shift, then project back to plane rectangular coordinates in the same zone |

Each zone's origin latitude and longitude come from the lookup table; the scale factor is `k=0.9999`, with GRS80 as the reference ellipsoid (Bessel on the inverse side of step 2). Both `native:assignprojection` and `native:reprojectlayer` are invoked with the pipeline supplied explicitly through the `OPERATION` parameter, so results do not depend on the CRS settings of the machine running it.

---

## Requirements

| Item | Requirement |
|------|-------------|
| QGIS | 3.34 to 3.99 (LTR recommended) |
| Dependencies | None — uses only PyQGIS, PyQt and Processing |
| External file | `TKY2JGD.gsb`, from GSI Japan or [JapanGridShift](https://github.com/tohka/JapanGridShift) |

---

## Installation

1. Download the ZIP from [Releases](../../releases).
2. In QGIS, go to **Plugins → Manage and Install Plugins → Install from ZIP**.
3. Place your legitimately obtained `TKY2JGD.gsb` into `ReTKY2JGD/data/`.
4. Launch from **Plugins → 国有林ツール → TKY2JGDで再変換**, or from the **国有林ツールバー** (National Forest toolbar).

> The National Forest toolbar (internal object name `NationalForestToolbar`) is shared with related plugins. An existing toolbar is reused; otherwise a new one is created.

---

## Usage

### Choosing the zone

Pick the target coordinate system from Japan's 19 plane rectangular zones (I–XIX, EPSG:2443–2461). The dropdown shows the zone number, EPSG code, origin coordinates and the prefectures each zone covers. If the input layer already carries one of these CRSs, that zone is preselected — **always verify it**.

The zone table is read from `data/zone_parameters.csv`; the plugin raises an error unless all 19 zones are present.

### Mode A — Convert a single layer

1. **Input vector layer** — choose any vector layer in the project (the active layer is preselected).
2. **Output file** — specify a GeoPackage (`.gpkg`) or Shapefile (`.shp`). Other extensions are rejected.
3. Click **実行 (Run)**. The converted layer is added to the project automatically.

The source file is never overwritten.

### Mode B — Batch convert a directory of Shapefiles

1. **Input directory** — every `.shp` beneath it is processed recursively.
2. **Output directory** — selecting an input directory auto-fills `<input name>_converted`. It is created at run time if it does not exist.
3. **Filename suffix** — appended to each output name. Defaults to `_convert`; leave it blank to keep the original filenames.

**The input folder hierarchy is mirrored in the output**, including folders that contain no Shapefiles.

```text
Input                         Output (suffix _convert)
貸与データ/                   貸与データ_converted/
├─ A.shp                      ├─ A_convert.shp
├─ 地区1/                     ├─ 地区1/
│  └─ B.shp                   │  └─ B_convert.shp
└─ 地区2/                     └─ 地区2/
   └─ 年度別/                    └─ 年度別/
      └─ C.shp                      └─ C_convert.shp
```

Batch mode constraints:

- **The output directory cannot be inside the input directory** — this prevents converted files from being picked up as input.
- Symbolic links to directories are not followed.
- Batch results are *not* added to the QGIS project; check the output directory when the run finishes.
- Only Shapefiles are processed. Use single-layer mode for GeoPackage and other formats.

### Progress and cancellation

Batch runs display progress based on the number of target files multiplied by three steps each, along with the relative path and current step.

**Cancel** sends a cancellation request to QGIS Processing; the run stops once the executing algorithm acknowledges it, which can take a while on large datasets. Outputs that already completed successfully are kept, and the plugin attempts to delete the incomplete component files (`.shp`, `.shx`, `.dbf`, `.prj`, `.cpg`, `.qpj`) of the file that was in progress.

---

## Character encoding

Legacy Japanese datum Shapefiles almost always store attributes as Shift_JIS, so encoding is handled explicitly:

| Target | Encoding |
|--------|----------|
| Shapefile input | `Shift_JIS` — the provider encoding is set before Processing reads attributes, preventing mojibake |
| Shapefile output | DBF written as `Shift_JIS`, with a matching `.cpg` file declaring `Shift_JIS` |
| GeoPackage output | `UTF-8`, per the specification |

---

## Please verify your results

Coordinate transformation always warrants verification. Before relying on the output:

- Measure the coordinate difference before and after conversion at known control points, or on identical features.
- Confirm the shift falls within the expected range for simplified-conversion residuals (roughly a few tens of centimetres to several metres).
- Check **zone boundaries, remote islands, and any area outside the `TKY2JGD.gsb` grid extent** individually. No correction is applied outside the grid.
- In areas affected by seismic crustal deformation, TKY2JGD correction alone may not be sufficient for survey purposes. Apply the appropriate additional correction parameters where required.

`data/reference/` contains the source spreadsheet of plane rectangular origins used to build the lookup table, plus a Processing model (`.model3`) for zone XII (EPSG:2454) that documents the same workflow graphically.

---

## Repository layout

```
ReTKY2JGD/
├── __init__.py                  # classFactory
├── plugin.py                    # Core: pipeline construction, single/batch runs, output
├── dialog.py                    # Settings dialog
├── zones.py                     # Zone lookup table loader
├── metadata.txt                 # Plugin metadata
├── icon.png
└── data/
    ├── PUT_TKY2JGD_GSB_HERE.txt # Where to place the grid file
    ├── zone_parameters.csv      # Origin lat/lon and EPSG codes for all 19 zones
    └── reference/
        ├── 平面直角座標系原点.xlsx
        └── ReTKY2JGD_12系_2454.model3
```

`TKY2JGD.gsb` is not included, and should not be committed to the repository — add it to `.gitignore`.

---

## Known limitations

- There is **no automatic check** that the input really was produced by a simplified conversion; that judgement is left to the operator.
- The selected zone is not validated either.
- Batch mode handles Shapefiles only.
- Horizontal coordinates only — Z values are not transformed.
- Seismic crustal-deformation correction parameters are out of scope.
- The user interface is Japanese only.

---

## Changelog

| Version | Changes |
|---------|---------|
| 1.3.0 | Added progress reporting and cancellation; improved Shift_JIS handling |

<!-- Add earlier releases here if the history is available -->

---

## License

- **Source code (this plugin)**: [MIT License](LICENSE)
- **Derived data under `data/reference/`** (zone lookup table, model3 files, etc.): [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
  - Original data: Forestry Agency of Japan, "[National Forest GIS data (published March 2025)](https://www.geospatial.jp/ckan/dataset/a45)" (G-Spatial Information Center)
  - Adaptation: the ReTKY2JGD project
- **TKY2JGD coordinate correction parameters** (`TKY2JGD.gsb`): published by the Geospatial Information Authority of Japan under its [content usage terms](https://www.gsi.go.jp/kikakuchousei/kikakuchousei40182.html). This file is not covered by this plugin's license and is not redistributed here.

---

## Citation

If you use this repository, please cite it as:

```
ReTKY2JGD: Re-conversion from Tokyo Datum to JGD2000 with TKY2JGD
https://github.com/Txito-alpha/ReTKY2JGD
```

---

## Author

- **Txito**

Bug reports and feature requests are welcome via Issues; code and documentation improvements are welcome via Pull Requests. Contributions that help improve the accuracy of geospatial data, and the maintenance and reuse of legacy datasets, are appreciated.

---

## Disclaimer

This plugin was created to streamline internal workflows. It makes no guarantee as to the accuracy of the converted coordinates, and the author accepts no liability for any damage arising from its use. Always validate against known control points, and confirm whether seismic crustal-deformation correction is required, before treating the output as a deliverable.
