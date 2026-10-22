# SPDX-License-Identifier: GPL-2.0-only
"""Local web interface and command-line importer; Python 3.10+ required."""
import argparse
import base64
import ipaddress
import json
import sqlite3
import secrets
import time
import urllib.parse
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import storage as core
from . import maps, peer, audio

ROOT = Path(__file__).resolve().parent
MAX_BODY = 8 * 1024 * 1024


class Handler(BaseHTTPRequestHandler):
    server_version = "FieldGuide/0.3"

    def log_message(self, format, *args):
        # Do not log searches or document text.
        pass

    def send(self, status, value, content_type="application/json; charset=utf-8"):
        payload = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; media-src 'self' blob:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        try:
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def valid_host(self):
        hostname = urllib.parse.urlsplit("http://" + self.headers.get("Host", "")).hostname
        if hostname == "localhost":
            return True
        try:
            ip = ipaddress.ip_address(hostname or "")
            return ip.is_loopback or (self.server.lan and ip.is_private)
        except ValueError:
            return False

    def do_GET(self):
        try:
            if not self.valid_host():
                return self.send(403, {"error": "Use localhost or the device's private IP address."})
            url = urllib.parse.urlsplit(self.path)
            params = urllib.parse.parse_qs(url.query)
            if url.path in ('/peer/manifest','/peer/bundle'):
                shared = self.server.shared
                code = self.headers.get('Authorization', '').removeprefix('Bearer ')
                if not shared or time.time() >= shared['expires'] or not secrets.compare_digest(code, shared['code']):
                    return self.send(403, {'error':'Share code is invalid, expired or revoked.'})
                return self.send(200, shared['manifest'] if url.path.endswith('manifest') else shared['data'])
            if not ipaddress.ip_address(self.client_address[0]).is_loopback:
                return self.send(403, {'error':'Private workspace is local-only. Use peer exchange with a share code.'})
            if url.path in ("/", "/app.js", "/style.css", "/map.js", "/license"):
                filename = {"/": "index.html", "/app.js": "app.js", "/style.css": "style.css", "/map.js":"map.js", "/license":"LICENSE.txt"}[url.path]
                mime = {"index.html": "text/html; charset=utf-8", "app.js": "text/javascript; charset=utf-8", "style.css": "text/css; charset=utf-8", "map.js":"text/javascript; charset=utf-8", "LICENSE.txt":"text/plain; charset=utf-8"}[filename]
                return self.send(200, (ROOT / "static" / filename).read_bytes(), mime)
            if url.path == "/api/status":
                return self.send(200, {**core.stats(self.server.db), "ai_enabled": bool(self.server.endpoint), "model": self.server.model, "version": "0.3.0", 'sharing_enabled':self.server.lan})
            if url.path == '/api/maps':
                return self.send(200, [m.info(i) for i,m in enumerate(self.server.maps)])
            if url.path.startswith('/api/tiles/'):
                pieces=url.path.split('/')
                if len(pieces)!=7:
                    raise ValueError('Invalid tile route.')
                index,z,x,y=map(int,pieces[3:])
                if not 0<=index<len(self.server.maps):
                    return self.send(404, {'error':'Map not installed'})
                tile=self.server.maps[index].tile(z,x,y)
                return self.send(200,tile[0],tile[1]) if tile else self.send(404,{'error':'Tile not stored locally'})
            if url.path == '/api/waypoints':
                return self.send(200, peer.waypoints(self.server.db))
            if url.path == '/api/peer/choices':
                with core.connect(self.server.db) as db:
                    documents=[dict(r) for r in db.execute('SELECT id,title,source FROM documents ORDER BY title')]
                return self.send(200, {'documents':documents, 'waypoints':peer.waypoints(self.server.db), 'sharing_enabled':self.server.lan})
            if url.path == "/api/search":
                return self.send(200, core.retrieve(self.server.db, params.get("q", [""])[0][:1000]))
            if url.path == "/api/document":
                with core.connect(self.server.db) as db:
                    row = db.execute("SELECT * FROM documents WHERE id=?", (int(params.get("id", [0])[0]),)).fetchone()
                return self.send(200 if row else 404, dict(row) if row else {"error": "Document not found"})
            if url.path in ("/api/inventory", "/api/notes"):
                return self.send(200, core.list_table(self.server.db, url.path.rsplit("/", 1)[1]))
            if url.path == "/api/backup":
                return self.send(200, core.export_backup(self.server.db))
            return self.send(404, {"error": "Not found"})
        except (ValueError, TypeError) as error:
            return self.send(400, {"error": str(error)})
        except Exception:
            return self.send(500, {"error": "Local storage request failed. Check disk space and the database path."})

    def do_POST(self):
        try:
            if not ipaddress.ip_address(self.client_address[0]).is_loopback:
                return self.send(403, {'error':'Workspace writes are local-only.'})
            if not self.valid_host():
                return self.send(403, {"error": "Invalid Host"})
            origin = self.headers.get("Origin")
            if origin and origin != "http://" + self.headers.get("Host", ""):
                return self.send(403, {"error": "Cross-origin writes are disabled"})
            if self.headers.get("X-Field-Library") != "1" or self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                return self.send(403, {"error": "JSON and X-Field-Library: 1 are required"})
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= MAX_BODY:
                return self.send(413, {"error": "Use JSON requests under 8 MiB; use the CLI for larger imports"})
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError("Expected a JSON object")
            if self.path == "/api/ask":
                return self.send(200, core.ask(self.server.db, payload.get("question", ""), self.server.endpoint, self.server.model))
            if self.path == '/api/audio/encode':
                return self.send(200,audio.encode(str(payload.get('text','')),payload.get('profile','ultrasonic')),'audio/wav')
            if self.path == '/api/audio/decode':
                data=base64.b64decode(payload.get('wav',''),validate=True)
                return self.send(200,{'text':audio.decode(data,payload.get('profile','ultrasonic'))})
            if self.path == '/api/waypoints':
                with core.connect(self.server.db) as db:
                    count=peer.add_waypoint(db,payload)
                return self.send(201, {'added':count})
            if self.path == '/api/peer/offer':
                if not self.server.lan:
                    raise ValueError('Restart with --host 0.0.0.0 to allow incoming peer transfers.')
                self.server.shared=peer.offer(self.server.db,payload.get('document_ids',[]),payload.get('waypoint_ids',[]))
                shared=self.server.shared
                return self.send(200, {'code':shared['code'],'expires':shared['expires'], **shared['manifest']})
            if self.path == '/api/peer/revoke':
                self.server.shared=None
                return self.send(200, {'revoked':True})
            if self.path == '/api/peer/receive':
                return self.send(200, peer.receive(self.server.db,payload.get('address',''),payload.get('code','')))
            if self.path == '/api/share/export':
                data=peer.create_bundle(self.server.db,payload.get('document_ids',[]),payload.get('waypoint_ids',[]))
                return self.send(200, data)
            if self.path == '/api/share/import':
                return self.send(200, peer.merge_bundle(self.server.db,json.dumps(payload).encode()))
            if self.path == "/api/import":
                records = payload.get("documents", [])
                if not isinstance(records, list) or not records or len(records) > 1000:
                    raise ValueError("Import between 1 and 1,000 documents per request")
                return self.send(200, {"imported": core.import_records(self.server.db, records)})
            if self.path == "/api/inventory":
                return self.send(201, {"id": core.add_inventory(self.server.db, payload)})
            if self.path == "/api/notes":
                return self.send(201, {"id": core.add_note(self.server.db, payload)})
            if self.path == "/api/restore":
                return self.send(200, {"documents_imported": core.restore_backup(self.server.db, payload)})
            return self.send(404, {"error": "Not found"})
        except (ValueError, TypeError, AttributeError, sqlite3.IntegrityError) as error:
            return self.send(400, {"error": str(error)[:400]})
        except (urllib.error.URLError, TimeoutError):
            return self.send(502, {'error':'Peer is unreachable, the code is invalid, or the share has expired.'})
        except Exception:
            return self.send(500, {"error": "Local operation failed; no generated answer is available."})


def make_server(db, host="127.0.0.1", port=8765, endpoint=None, model="local-model", map_files=None):
    if endpoint:
        core.validate_endpoint(endpoint)
    core.initialize(db)
    installed_maps = [maps.RasterMap(filename) for filename in (map_files or [])]
    server = ThreadingHTTPServer((host, port), Handler)
    server.db, server.endpoint, server.model = db, endpoint, model
    server.lan = host != "127.0.0.1"
    server.maps = installed_maps
    server.shared = None
    server.daemon_threads = True
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("serve", "import", "backup", "restore", "check"), nargs="?", default="serve")
    parser.add_argument("file", nargs="?")
    parser.add_argument("--db", default=str(Path("data") / "library.sqlite3"))
    parser.add_argument("--host", choices=("127.0.0.1", "0.0.0.0"), default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--endpoint", help="Optional loopback OpenAI-compatible /v1/chat/completions URL")
    parser.add_argument("--model", default="local-model")
    parser.add_argument("--map", action="append", default=[], dest="map_files", help="Local raster MBTiles file; repeat for multiple maps")
    args = parser.parse_args()
    core.initialize(args.db)
    if args.command == "check":
        print(json.dumps({"sqlite": sqlite3.sqlite_version, "fts5": True, **core.stats(args.db)}, indent=2))
        return
    if args.command != "serve" and not args.file:
        parser.error("This command needs a file")
    if args.command == "import":
        with open(args.file, encoding="utf-8-sig") as stream:
            records = (json.loads(line) for line in stream if line.strip())
            print("Documents imported:", core.import_records(args.db, records))
        return
    if args.command == "backup":
        # Exclusive creation protects an existing backup from accidental overwrite.
        with open(args.file, "x", encoding="utf-8") as stream:
            json.dump(core.export_backup(args.db), stream, ensure_ascii=False, indent=2)
        print("Backup created:", args.file)
        return
    if args.command == "restore":
        with open(args.file, encoding="utf-8") as stream:
            count = core.restore_backup(args.db, json.load(stream))
        print("Documents imported:", count, "(inventory and notes appended)")
        return
    server = make_server(args.db, args.host, args.port, args.endpoint, args.model, args.map_files)
    print('FieldGuide · Copyright (C) 2026 contributors · GPL-2.0-only · No warranty. See /license in the local interface.', flush=True)
    print(f"FieldGuide: http://127.0.0.1:{args.port}", flush=True)
    print("AI: " + ("local endpoint configured" if args.endpoint else "disabled; source search works"), flush=True)
    if server.lan:
        print("Peer exchange enabled. Create a 15-minute share code in the local UI; private workspace stays local-only.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
