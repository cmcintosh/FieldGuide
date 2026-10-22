# SPDX-License-Identifier: GPL-2.0-only
import array
import base64
import hashlib
import io
import json
import random
import sqlite3
import struct
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
import wave
import zlib
from pathlib import Path

from fieldguide import audio, maps, peer, server, storage


def png(rgb):
    def part(kind,data):
        return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data))
    return b'\x89PNG\r\n\x1a\n'+part(b'IHDR',struct.pack('>IIBBBBB',1,1,8,2,0,0,0))+part(b'IDAT',zlib.compress(b'\x00'+bytes(rgb)))+part(b'IEND',b'')


def fixture_map(path,fmt='png'):
    with sqlite3.connect(path) as db:
        db.executescript('CREATE TABLE metadata(name TEXT,value TEXT); CREATE TABLE tiles(zoom_level INTEGER,tile_column INTEGER,tile_row INTEGER,tile_data BLOB);')
        db.executemany('INSERT INTO metadata VALUES(?,?)',[('name','Test map'),('format',fmt),('center','0,0,1'),('bounds','-180,-85,180,85'),('attribution','Original test fixture; no geographic data')])
        db.executemany('INSERT INTO tiles VALUES(?,?,?,?)',[(1,0,0,png((255,0,0))),(1,0,1,png((0,255,0)))])


class MapTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'map.mbtiles';fixture_map(self.path)
    def tearDown(self):self.temp.cleanup()
    def test_xyz_top_row_reads_tms_top_row(self):
        source=maps.RasterMap(self.path)
        self.assertEqual(source.tile(1,0,0),(png((0,255,0)),'image/png'))
        self.assertEqual(source.tile(1,0,1)[0],png((255,0,0)))
    def test_missing_and_out_of_range_tiles_return_none(self):
        source=maps.RasterMap(self.path)
        for coords in ((1,1,0),(1,-1,0),(22,0,0),(1,0,2)):
            self.assertIsNone(source.tile(*coords))
    def test_reading_leaves_original_file_unchanged(self):
        before=hashlib.sha256(self.path.read_bytes()).digest();source=maps.RasterMap(self.path)
        source.tile(1,0,0);self.assertEqual(before,hashlib.sha256(self.path.read_bytes()).digest())
    def test_vector_pack_is_rejected_clearly(self):
        with sqlite3.connect(self.path) as db:db.execute("UPDATE metadata SET value='pbf' WHERE name='format'")
        with self.assertRaisesRegex(ValueError,'not vector'):maps.RasterMap(self.path)
    def test_attribution_retained_as_text(self):
        self.assertIn('Original test fixture',maps.RasterMap(self.path).info(0)['attribution'])


class PeerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.a=Path(self.temp.name)/'a.db';self.b=Path(self.temp.name)/'b.db'
        storage.initialize(self.a);storage.initialize(self.b)
        storage.import_records(self.a,[{'title':'Public selection','text':'An example share record.'},{'title':'Unselected','text':'Do not include this record.'}])
        storage.add_note(self.a,{'title':'Private note','text':'Not for sharing'})
        storage.add_inventory(self.a,{'name':'Private inventory','quantity':1})
        with storage.connect(self.a) as db:peer.add_waypoint(db,{'uuid':'test-point','name':'Meeting point','latitude':38,'longitude':-87})
        self.sender=server.make_server(self.a,host='0.0.0.0',port=0)
        self.thread=threading.Thread(target=self.sender.serve_forever,daemon=True);self.thread.start()
        self.base='http://127.0.0.1:'+str(self.sender.server_port)
    def tearDown(self):
        self.sender.shutdown();self.sender.server_close();self.thread.join();self.temp.cleanup()
    def offer(self):
        self.sender.shared=peer.offer(self.a,[1],['test-point']);return self.sender.shared['code']
    def test_selected_records_transfer_between_independent_databases(self):
        result=peer.receive(self.b,self.base,self.offer())
        self.assertEqual(result,{'documents_added':1,'waypoints_added':1})
        self.assertEqual(storage.stats(self.b)['notes'],0);self.assertEqual(storage.stats(self.b)['inventory'],0)
        self.assertEqual(storage.stats(self.b)['documents'],1)
    def test_repeated_receive_is_idempotent(self):
        code=self.offer();peer.receive(self.b,self.base,code)
        self.assertEqual(peer.receive(self.b,self.base,code),{'documents_added':0,'waypoints_added':0})
    def test_wrong_code_and_expiry_are_rejected(self):
        code=self.offer()
        with self.assertRaises(urllib.error.HTTPError):peer.receive(self.b,self.base,'X'*32)
        self.sender.shared['expires']=time.time()-1
        with self.assertRaises(urllib.error.HTTPError):peer.receive(self.b,self.base,code)
    def test_checksum_failure_does_not_import(self):
        code=self.offer();self.sender.shared['manifest']['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'integrity'):peer.receive(self.b,self.base,code)
        self.assertEqual(storage.stats(self.b)['documents'],0)
    def test_bundle_excludes_private_records(self):
        bundle=json.loads(peer.create_bundle(self.a,[1],['test-point']))
        self.assertNotIn('inventory',bundle);self.assertNotIn('notes',bundle)
        self.assertEqual([d['title'] for d in bundle['documents']],['Public selection'])
    def test_public_addresses_and_redirect_like_paths_rejected(self):
        for address in ('http://8.8.8.8:8765','http://example.com:8765','http://127.0.0.1:8765/other','https://192.168.1.1:8765'):
            with self.assertRaises(ValueError):peer.validate_address(address)
    def test_invalid_waypoint_rolls_back_share(self):
        bundle={'kind':'field-library-share-v1','documents':[{'title':'New','text':'Example'}],'waypoints':[{'name':'bad','latitude':999,'longitude':0}]}
        with self.assertRaises(ValueError):peer.merge_bundle(self.b,json.dumps(bundle).encode())
        self.assertEqual(storage.stats(self.b)['documents'],0)


class AudioTests(unittest.TestCase):
    def test_both_profiles_roundtrip(self):
        for profile in audio.PROFILES:
            self.assertEqual(audio.decode(audio.encode('Meet at north gate',profile),profile),'Meet at north gate')
    def test_utf8_byte_budget(self):
        text='é'*80;self.assertEqual(audio.decode(audio.encode(text)),text)
        with self.assertRaises(ValueError):audio.encode(text+'x')
    def test_leading_silence_and_low_synthetic_noise(self):
        encoded=audio.encode('Testing alignment')
        with wave.open(io.BytesIO(encoded),'rb') as stream:raw=stream.readframes(stream.getnframes())
        samples=array.array('h');samples.frombytes(raw);rng=random.Random(3)
        altered=array.array('h',[0]*123+[max(-32768,min(32767,s+rng.randrange(-80,81))) for s in samples])
        output=io.BytesIO()
        with wave.open(output,'wb') as stream:
            stream.setnchannels(1);stream.setsampwidth(2);stream.setframerate(48000);stream.writeframes(altered.tobytes())
        self.assertEqual(audio.decode(output.getvalue()),'Testing alignment')
    def test_truncated_frame_does_not_return_partial_message(self):
        encoded=audio.encode('A test message that will be truncated')
        with self.assertRaises(ValueError):audio.decode(encoded[:len(encoded)//2])
    def test_invalid_wav_and_unknown_profiles(self):
        with self.assertRaises(ValueError):audio.decode(b'not audio')
        with self.assertRaises(ValueError):audio.encode('hello','unknown')
    def test_crc_rejects_changed_payload_symbol(self):
        encoded=audio.encode('Hello')
        with wave.open(io.BytesIO(encoded),'rb') as stream:raw=stream.readframes(stream.getnframes())
        samples=array.array('h');samples.frombytes(raw)
        start=(1+(len(audio.PREFIX)+2)*8+1)*audio.SYMBOL
        samples[start:start+audio.SYMBOL]=array.array('h',[0]*audio.SYMBOL)
        output=io.BytesIO()
        with wave.open(output,'wb') as stream:
            stream.setnchannels(1);stream.setsampwidth(2);stream.setframerate(48000);stream.writeframes(samples.tobytes())
        with self.assertRaises(ValueError):audio.decode(output.getvalue())


class FeatureHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();root=Path(self.temp.name)
        self.map=root/'map.mbtiles';fixture_map(self.map)
        self.server=server.make_server(root/'data.db',port=0,map_files=[self.map])
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.base='http://127.0.0.1:'+str(self.server.server_port)
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join();self.temp.cleanup()
    def request(self,path,payload=None):
        return urllib.request.urlopen(urllib.request.Request(self.base+path,data=None if payload is None else json.dumps(payload).encode(),headers={'Content-Type':'application/json','X-Field-Library':'1'}),timeout=10)
    def test_map_metadata_and_tile_routes(self):
        with self.request('/api/maps') as response:self.assertEqual(json.load(response)[0]['name'],'Test map')
        with self.request('/api/tiles/0/1/0/0') as response:
            self.assertEqual(response.headers['Content-Type'],'image/png');self.assertEqual(response.read(),png((0,255,0)))
    def test_waypoints_survive_backup(self):
        with self.request('/api/waypoints',{'name':'Test point','latitude':38,'longitude':-87}) as response:self.assertEqual(response.status,201)
        with self.request('/api/backup') as response:self.assertEqual(json.load(response)['waypoints'][0]['name'],'Test point')
    def test_audio_routes_return_wav_and_decode_text(self):
        with self.request('/api/audio/encode',{'text':'A local HTTP audio test','profile':'ultrasonic'}) as response:
            self.assertEqual(response.headers['Content-Type'],'audio/wav');wav=response.read()
        with self.request('/api/audio/decode',{'wav':base64.b64encode(wav).decode(),'profile':'ultrasonic'}) as response:
            self.assertEqual(json.load(response)['text'],'A local HTTP audio test')
    def test_license_is_available_in_ui(self):
        with self.request('/license') as response:self.assertIn('GNU GENERAL PUBLIC LICENSE',response.read().decode())


if __name__=='__main__':unittest.main()
