# SPDX-License-Identifier: GPL-2.0-only
import io
import json
import socket
import tempfile
import threading
import unittest
from pathlib import Path

from fieldguide import link

FIXTURES=Path(__file__).parent/'fixtures'


class LinkTests(unittest.TestCase):
    def setUp(self):
        self.data=(FIXTURES/'transport.json').read_bytes()

    def test_golden_vector_matches(self):
        frame=bytes.fromhex((FIXTURES/'transport.frame.hex').read_text())
        self.assertEqual(link.encode_frame(self.data),frame)
        self.assertEqual(link.read_frame(io.BytesIO(frame)),self.data)

    def test_fragmented_stream_reads_exactly(self):
        class Fragmented(io.BytesIO):
            def read(self,n=-1):return super().read(min(n,3))
        self.assertEqual(link.read_frame(Fragmented(link.encode_frame(self.data))),self.data)

    def test_bad_magic_size_checksum_and_truncation(self):
        frame=link.encode_frame(self.data)
        bad=bytearray(frame);bad[39]^=1
        for payload in (b'NOPE'+frame[4:],frame[:4]+b'\xff'*4+frame[8:],bytes(bad),frame[:-1]):
            with self.assertRaises(ValueError):link.read_frame(io.BytesIO(payload))

    def test_non_bundle_and_invalid_records_are_rejected(self):
        for data in (b'{}',b'not JSON',b'{"kind":"field-library-share-v1","documents":[]}',json.dumps({'kind':'field-library-share-v1','documents':[{'title':'','text':'body'}]}).encode()):
            with self.assertRaises(ValueError):link.validate_bundle(data)

    def test_real_tcp_delivery_and_acknowledgement(self):
        listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(1);listener.settimeout(5)
        received=[]
        def serve():
            with listener:
                with listener.accept()[0] as connection:
                    connection.settimeout(5)
                    with connection.makefile('rb') as stream:received.append(link.read_frame(stream))
                    connection.sendall(b'\x06')
        thread=threading.Thread(target=serve);thread.start()
        try:link.send('127.0.0.1',listener.getsockname()[1],self.data)
        finally:thread.join(6)
        self.assertFalse(thread.is_alive());self.assertEqual(received,[self.data])

    def test_receiver_refuses_to_overwrite_a_file(self):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'received.json';output.write_bytes(b'keep me')
            with self.assertRaises(ValueError):link.listen('127.0.0.1',0,output,timeout=1)
            self.assertEqual(output.read_bytes(),b'keep me')

    def test_public_destination_is_rejected(self):
        with self.assertRaises(ValueError):link.send('8.8.8.8',link.PORT,self.data)


if __name__=='__main__':unittest.main()
