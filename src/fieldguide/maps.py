# SPDX-License-Identifier: GPL-2.0-only
"""Read local raster MBTiles without contacting a tile service."""
import math
import sqlite3
from contextlib import contextmanager
from pathlib import Path


class RasterMap:
    def __init__(self, filename):
        self.path = Path(filename).expanduser().resolve(strict=True)
        self.uri = self.path.as_uri() + '?mode=ro'
        with self.connect() as db:
            self.metadata = dict(db.execute('SELECT name,value FROM metadata'))
            self.metadata['format'] = self.metadata.get('format', '').lower()
            if self.metadata['format'] not in ('png', 'jpg', 'jpeg', 'webp'):
                raise ValueError('This preview reads raster PNG/JPEG/WebP MBTiles, not vector PBF/PMTiles.')
            if self.metadata.get('scheme', 'tms').lower() != 'tms':
                raise ValueError('MBTiles must use standard TMS tile rows.')
            zooms = db.execute('SELECT min(zoom_level),max(zoom_level) FROM tiles').fetchone()
            if zooms[0] is None or not 0 <= zooms[0] <= zooms[1] <= 22:
                raise ValueError('Map needs tiles with zoom levels between 0 and 22.')
            self.minzoom, self.maxzoom = map(int, zooms)
        self.bounds = self.numbers('bounds', '-180,-85,180,85', 4)
        west, south, east, north = self.bounds
        if not (-180 <= west <= 180 and -180 <= east <= 180 and -90 <= south <= north <= 90):
            raise ValueError('Invalid map bounds.')
        default = f'{(west+east)/2},{(south+north)/2},{self.minzoom}'
        self.center = self.numbers('center', default, 3)
        if not (-180 <= self.center[0] <= 180 and -90 <= self.center[1] <= 90):
            raise ValueError('Invalid map center.')
        self.center[2] = max(self.minzoom, min(self.maxzoom, int(self.center[2])))

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.uri, uri=True)
        try:
            db.execute('PRAGMA query_only=ON')
            db.execute('PRAGMA trusted_schema=OFF')
            yield db
        finally:
            db.close()

    def numbers(self, field, default, count):
        values = [float(v) for v in self.metadata.get(field, default).split(',')]
        if len(values) != count or not all(math.isfinite(v) for v in values):
            raise ValueError('Invalid map ' + field)
        return values

    def info(self, index):
        return {'id': index, 'name': self.metadata.get('name', self.path.stem),
                'attribution': self.metadata.get('attribution', 'Map publisher attribution not supplied'),
                'format': self.metadata['format'], 'minzoom': self.minzoom, 'maxzoom': self.maxzoom,
                'bounds': self.bounds, 'center': self.center}

    def tile(self, zoom, x, y):
        if not (self.minzoom <= zoom <= self.maxzoom and 0 <= x < 2 ** zoom and 0 <= y < 2 ** zoom):
            return None
        tms_y = 2 ** zoom - 1 - y
        with self.connect() as db:
            row = db.execute('SELECT tile_data FROM tiles WHERE zoom_level=? AND tile_column=? AND tile_row=?', (zoom, x, tms_y)).fetchone()
        if not row:
            return None
        data = bytes(row[0])
        if len(data) > 4_000_000:
            raise ValueError('Tile is larger than the preview tile limit.')
        if data.startswith(b'\x89PNG\r\n\x1a\n'):
            return data, 'image/png'
        if data.startswith(b'\xff\xd8\xff'):
            return data, 'image/jpeg'
        if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
            return data, 'image/webp'
        raise ValueError('Tile is not a supported raster image.')
