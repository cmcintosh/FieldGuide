# SPDX-License-Identifier: GPL-2.0-only
"""Experimental short-message FSK WAV codec; no microphone or automatic playback.

Original protocol, not ggwave compatible. Decoded content is never executed.
"""
import argparse
import array
import io
import math
import struct
import sys
import wave
import zlib

RATE = 48000
SYMBOL = 480
MAX_PAYLOAD = 160
PREFIX = b'\xaa' * 8 + b'FG02'
PROFILES = {'ultrasonic': (20500, 21500), 'audible': (1700, 2700)}


def bits(data):
    return ''.join(f'{byte:08b}' for byte in data)


def encode(text, profile='ultrasonic'):
    if profile not in PROFILES:
        raise ValueError('Unknown audio profile.')
    payload = text.encode('utf-8')
    if not 1 <= len(payload) <= MAX_PAYLOAD:
        raise ValueError('Audio messages must contain 1–160 UTF-8 bytes.')
    packet = PREFIX + struct.pack('>H', len(payload)) + payload + struct.pack('>I', zlib.crc32(payload))
    tones = []
    for frequency in PROFILES[profile]:
        tone = array.array('h')
        for i in range(SYMBOL):
            envelope = min(1.0, i/24, (SYMBOL-1-i)/24)
            tone.append(round(3932 * envelope * math.sin(2*math.pi*frequency*i/RATE)))
        tones.append(tone)
    pcm = array.array('h', [0]*SYMBOL)
    for bit in bits(packet):
        pcm.extend(tones[int(bit)])
    pcm.extend([0] * SYMBOL)
    if sys.byteorder != 'little':
        pcm.byteswap()
    output = io.BytesIO()
    with wave.open(output, 'wb') as stream:
        stream.setnchannels(1); stream.setsampwidth(2); stream.setframerate(RATE)
        stream.writeframes(pcm.tobytes())
    return output.getvalue()


def classify(samples, start, coefficients):
    s10 = s20 = s11 = s21 = 0.0
    c0, c1 = coefficients
    for sample in samples[start:start+SYMBOL]:
        v0 = sample + c0*s10 - s20; s20=s10; s10=v0
        v1 = sample + c1*s11 - s21; s21=s11; s11=v1
    p0=s10*s10+s20*s20-c0*s10*s20
    p1=s11*s11+s21*s21-c1*s11*s21
    return '1' if p1>p0 else '0'


def decode(data, profile='ultrasonic'):
    if profile not in PROFILES:
        raise ValueError('Unknown audio profile.')
    if len(data)>4_000_000:
        raise ValueError('Use a WAV recording under 4 MB (about 40 seconds).')
    try:
        with wave.open(io.BytesIO(data),'rb') as stream:
            if (stream.getnchannels(),stream.getsampwidth(),stream.getframerate()) != (1,2,RATE):
                raise ValueError('Use uncompressed mono 16-bit PCM WAV at 48,000 Hz.')
            if stream.getnframes()>RATE*40:
                raise ValueError('Use a recording of 40 seconds or less.')
            raw=stream.readframes(stream.getnframes())
    except (wave.Error, EOFError) as error:
        raise ValueError('Invalid PCM WAV recording.') from error
    samples=array.array('h');samples.frombytes(raw)
    if sys.byteorder!='little':samples.byteswap()
    coefficients=[2*math.cos(2*math.pi*f/RATE) for f in PROFILES[profile]]
    prefix=bits(PREFIX)
    for offset in range(0,SYMBOL,48):
        decoded=''.join(classify(samples,i,coefficients) for i in range(offset,len(samples)-SYMBOL+1,SYMBOL))
        start=decoded.find(prefix)
        while start>=0:
            body=decoded[start+len(prefix):]
            if len(body)>=16:
                length=int(body[:16],2)
                required=16+length*8+32
                if 1<=length<=MAX_PAYLOAD and len(body)>=required:
                    payload=bytes(int(body[i:i+8],2) for i in range(16,16+length*8,8))
                    checksum=int(body[16+length*8:required],2)
                    if zlib.crc32(payload)==checksum:
                        try:return payload.decode('utf-8')
                        except UnicodeDecodeError:pass
            start=decoded.find(prefix,start+1)
    raise ValueError('No valid frame passed CRC. Check profile, recording format and hardware; retry closer together.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    for command in ('encode','decode'):
        item=commands.add_parser(command);item.add_argument('file');item.add_argument('--profile',choices=tuple(PROFILES),default='ultrasonic')
        if command=='encode':item.add_argument('--text',required=True)
    args=parser.parse_args()
    if args.command=='encode':
        with open(args.file,'xb') as stream:stream.write(encode(args.text,args.profile))
        print('WAV created; playback is a separate user action:',args.file)
    else:
        with open(args.file,'rb') as stream:result=decode(stream.read(4_000_001),args.profile)
        print(result)


if __name__=='__main__':main()
