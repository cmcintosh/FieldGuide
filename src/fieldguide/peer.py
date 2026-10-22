# SPDX-License-Identifier: GPL-2.0-only
"""Small, explicitly selected bundles over a manually established local link.

No discovery, internet transport, radio control, mesh forwarding or encryption.
"""
import hashlib
import ipaddress
import json
import secrets
import time
import urllib.parse
import urllib.request

from .storage import NoRedirect, connect, import_document, utcnow

MAX_BUNDLE = 7_000_000
NETWORKS = [ipaddress.ip_network(n) for n in ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16','127.0.0.0/8')]


def add_waypoint(db, record):
    import math
    name = str(record.get('name', '')).strip()[:200]
    lat, lon = float(record.get('latitude', 999)), float(record.get('longitude', 999))
    if not name or not all(math.isfinite(v) for v in (lat, lon)) or not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError('A waypoint needs a name and valid latitude/longitude.')
    uid = str(record.get('uuid') or secrets.token_hex(16))[:120]
    if not uid:
        raise ValueError('Invalid waypoint identifier.')
    values = (uid, name, lat, lon, str(record.get('note', ''))[:4000], str(record.get('updated') or utcnow())[:100])
    return db.execute('INSERT OR IGNORE INTO waypoints(uuid,name,latitude,longitude,note,updated) VALUES(?,?,?,?,?,?)', values).rowcount


def waypoints(path):
    with connect(path) as db:
        return [dict(r) for r in db.execute('SELECT * FROM waypoints ORDER BY name,uuid')]


def create_bundle(path, document_ids, waypoint_ids):
    if not isinstance(document_ids, list) or not isinstance(waypoint_ids, list):
        raise ValueError('Choose document and waypoint lists.')
    if len(document_ids) + len(waypoint_ids) > 1000 or not (document_ids or waypoint_ids):
        raise ValueError('Select 1–1,000 records to share.')
    documents, points = [], []
    with connect(path) as db:
        for ident in dict.fromkeys(document_ids):
            row = db.execute('SELECT title,text,source,license,pack,updated FROM documents WHERE id=?', (int(ident),)).fetchone()
            if row is None:
                raise ValueError('Selected document no longer exists.')
            documents.append(dict(row))
        for uid in dict.fromkeys(waypoint_ids):
            row = db.execute('SELECT * FROM waypoints WHERE uuid=?', (str(uid),)).fetchone()
            if row is None:
                raise ValueError('Selected waypoint no longer exists.')
            points.append(dict(row))
    bundle = {'kind': 'field-library-share-v1', 'created': utcnow(), 'documents': documents, 'waypoints': points}
    data = json.dumps(bundle, ensure_ascii=False, separators=(',', ':')).encode()
    if len(data) > MAX_BUNDLE:
        raise ValueError('Selected bundle exceeds 7 MB. Share fewer documents at a time.')
    return data


def merge_bundle(path, data):
    if len(data) > MAX_BUNDLE:
        raise ValueError('Share bundle is larger than 7 MB.')
    bundle = json.loads(data)
    if not isinstance(bundle, dict) or bundle.get('kind') != 'field-library-share-v1':
        raise ValueError('Unsupported share bundle.')
    documents, points = bundle.get('documents', []), bundle.get('waypoints', [])
    if not isinstance(documents, list) or not isinstance(points, list) or len(documents)+len(points)>1000:
        raise ValueError('Invalid share record counts.')
    with connect(path) as db:
        docs = sum(import_document(db, r) for r in documents)
        added = sum(add_waypoint(db, r) for r in points)
    return {'documents_added': docs, 'waypoints_added': added}


def validate_address(address):
    parsed = urllib.parse.urlsplit(address)
    if parsed.scheme != 'http' or parsed.username or parsed.password or parsed.path not in ('','/') or parsed.query or parsed.fragment:
        raise ValueError('Enter http://PRIVATE-IP:PORT without a path or credentials.')
    try:
        ip = ipaddress.ip_address(parsed.hostname or '')
        port = parsed.port
    except ValueError:
        raise ValueError('Use a numeric private IPv4 address.') from None
    if not isinstance(ip, ipaddress.IPv4Address) or not any(ip in network for network in NETWORKS) or port is None or not 1024 <= port <= 65535:
        raise ValueError('Peer must be a private IPv4 address and a port from 1024 to 65535.')
    return f'http://{ip}:{port}'


def receive(path, address, code):
    address = validate_address(address)
    if not isinstance(code, str) or not 20 <= len(code) <= 100 or not all(c.isalnum() or c in '-_' for c in code):
        raise ValueError('Enter the complete share code from the sender.')
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    def fetch(route, limit):
        request = urllib.request.Request(address + route, headers={'Authorization':'Bearer '+code})
        with opener.open(request, timeout=20) as response:
            data = response.read(limit+1)
        if len(data)>limit:
            raise ValueError('Peer response exceeded its size limit.')
        return data
    manifest = json.loads(fetch('/peer/manifest', 16000))
    size = int(manifest['bytes'])
    if not 0 < size <= MAX_BUNDLE:
        raise ValueError('Invalid peer bundle size.')
    data = fetch('/peer/bundle', MAX_BUNDLE)
    if len(data) != size or hashlib.sha256(data).hexdigest() != manifest['sha256']:
        raise ValueError('Peer bundle integrity check failed; nothing was imported.')
    return merge_bundle(path, data)


def offer(path, documents, points):
    data = create_bundle(path, documents, points)
    return {'code': secrets.token_urlsafe(24), 'expires': time.time()+15*60, 'data': data,
            'manifest': {'bytes':len(data), 'sha256':hashlib.sha256(data).hexdigest(),
                         'documents':len(set(documents)), 'waypoints':len(set(points))}}
