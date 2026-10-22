# SPDX-License-Identifier: GPL-2.0-only
"""Bounded one-shot FGT1 transfers for the Android companion and local TCP links.

Receive writes a reviewed-later file, never automatically imports it. This
development wire protocol provides integrity checks, not peer authentication.
"""
import argparse
import hashlib
import json
import socket
import struct
from pathlib import Path

from .peer import MAX_BUNDLE, validate_address

MAGIC = b'FGT1'
PORT = 43721


def validate_bundle(data):
    if not 0 < len(data) <= MAX_BUNDLE:
        raise ValueError('Bundle must contain 1–7,000,000 bytes.')
    bundle = json.loads(data)
    if not isinstance(bundle, dict) or bundle.get('kind') != 'field-library-share-v1':
        raise ValueError('Choose an exported FieldGuide selected-share JSON file.')
    documents, points = bundle.get('documents', []), bundle.get('waypoints', [])
    if not isinstance(documents, list) or not isinstance(points, list) or not 1 <= len(documents)+len(points) <= 1000:
        raise ValueError('Bundle must contain 1–1,000 selected records.')
    for document in documents:
        if not isinstance(document, dict) or not isinstance(document.get('title'), str) or not isinstance(document.get('text'), str):
            raise ValueError('Invalid document record.')
        if not document['title'].strip() or not document['text'].strip() or len(document['text']) > 2_000_000:
            raise ValueError('Invalid document title or text length.')
    for point in points:
        # Validate independently without persisting anything.
        import math
        if not isinstance(point, dict) or not isinstance(point.get('name'), str) or not point['name'].strip():
            raise ValueError('Invalid waypoint name.')
        lat, lon = float(point.get('latitude', 999)), float(point.get('longitude', 999))
        if not all(math.isfinite(v) for v in (lat, lon)) or not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError('Invalid waypoint coordinates.')
    return {'documents':len(documents), 'waypoints':len(points)}


def read_exact(stream, size):
    chunks = bytearray()
    while len(chunks)<size:
        part=stream.read(size-len(chunks))
        if not part:
            raise ValueError('Transfer ended before the complete frame arrived.')
        chunks.extend(part)
    return bytes(chunks)


def encode_frame(data):
    validate_bundle(data)
    return MAGIC+struct.pack('>I',len(data))+hashlib.sha256(data).digest()+data


def read_frame(stream):
    header=read_exact(stream,40)
    if header[:4]!=MAGIC:
        raise ValueError('Unsupported transfer protocol.')
    size=struct.unpack('>I',header[4:8])[0]
    if not 0<size<=MAX_BUNDLE:
        raise ValueError('Declared transfer size is outside the 7 MB limit.')
    data=read_exact(stream,size)
    if hashlib.sha256(data).digest()!=header[8:40]:
        raise ValueError('Transfer checksum failed.')
    validate_bundle(data)
    return data


def send(host, port, data):
    address=validate_address(f'http://{host}:{port}')
    from urllib.parse import urlsplit
    host=urlsplit(address).hostname
    frame=encode_frame(data)
    with socket.create_connection((host,port),timeout=10) as connection:
        connection.settimeout(30)
        connection.sendall(frame)
        if connection.recv(1)!=b'\x06':
            raise ValueError('Receiver did not acknowledge a valid frame.')


def listen(bind, port, output, timeout=120):
    # The caller explicitly chooses the listening interface. No data is imported.
    if Path(output).exists():
        raise ValueError('Output file already exists; choose a new filename.')
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        listener.bind((bind,port));listener.listen(1);listener.settimeout(timeout)
        print(f'Waiting for one transfer on {bind}:{listener.getsockname()[1]} (maximum {timeout}s)',flush=True)
        with listener.accept()[0] as connection:
            connection.settimeout(30)
            with connection.makefile('rb') as stream:
                data=read_frame(stream)
            with open(output,'xb') as file:
                file.write(data)
            connection.sendall(b'\x06')
    return validate_bundle(data)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    tx=commands.add_parser('send');tx.add_argument('--host',required=True);tx.add_argument('--port',type=int,default=PORT);tx.add_argument('--input',required=True)
    rx=commands.add_parser('listen');rx.add_argument('--bind',default='127.0.0.1');rx.add_argument('--port',type=int,default=PORT);rx.add_argument('--output',required=True)
    args=parser.parse_args()
    if args.command=='send':
        with open(args.input,'rb') as file:data=file.read(MAX_BUNDLE+1)
        send(args.host,args.port,data);print('Frame delivered for recipient review.')
    else:
        result=listen(args.bind,args.port,args.output)
        print('Saved selected-share file for review:',args.output,result)


if __name__=='__main__':main()
