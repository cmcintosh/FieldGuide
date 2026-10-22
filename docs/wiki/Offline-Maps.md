# Offline maps

## Implemented

FieldGuide reads local **raster MBTiles** containing PNG, JPEG or WebP tiles. It converts browser XYZ requests to the MBTiles standard TMS row convention. The viewer pans, zooms and shows declared attribution. Saved waypoints are stored separately in SQLite and included in backups and selected peer bundles.

```bash
python app.py serve --map /path/region.mbtiles --map /path/another-region.mbtiles
```

Open Offline maps. Tap to choose waypoint coordinates or type latitude/longitude directly. The location button requests permission from the browser only when clicked. Permission, sensor availability and offline location behavior depend on the device and must be tested. A Pi normally needs a separate location source. Location is not automatically shared with peers.

## Map preparation

Obtain a raster MBTiles export from a provider permitting offline use, or prepare one from licensed data with a tool such as QGIS. Verify that it contains raster images: many downloadable `.mbtiles` files instead contain vector PBF data, which this version rejects. Preserve map source, date, attribution and content license.

No map data, downloader, geocoder or routing engine is included. Missing tiles stay blank and never trigger internet downloads. More zoom detail requires more stored tiles. Do not bulk scrape OpenStreetMap's public standard tile servers; their [tile policy](https://operations.osmfoundation.org/policies/tiles/) prohibits prefetch/bulk download.

## Planned

Regional vector PMTiles/MBTiles, complete local styles/fonts/sprites, POI search, tracks and GPX import/export. MapLibre Native is a candidate for the eventual Android app. Turn-by-turn routing needs a routing engine and graph data; displaying roads does not implement navigation.

Map files are not transferred by the small-record peer protocol. Copy large map archives separately until resumable pack transfer is implemented.
