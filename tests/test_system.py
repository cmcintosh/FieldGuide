# SPDX-License-Identifier: GPL-2.0-only
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from fieldguide import server as app
from fieldguide import storage as core


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / 'test.db'
        core.initialize(self.db)
        core.import_records(self.db, [
            {'title':'Pump maintenance','text':'The example pump uses the blue filter cartridge. Check the model label before ordering parts.', 'source':'Example manual', 'license':'Test fixture'},
            {'title':'Notebook organization','text':'Organize documents into named content packs and keep a second copy on separate storage.'},
        ])

    def tearDown(self):
        self.temp.cleanup()

    def test_retrieves_relevant_document(self):
        results = core.retrieve(self.db, 'Which filter cartridge does the pump use?')
        self.assertEqual(results[0]['title'], 'Pump maintenance')
        self.assertIn('blue filter', results[0]['text'])

    def test_literal_queries_do_not_inject_fts_syntax(self):
        for query in ('" OR * - NEAR(', 'pump OR "', "pump'; DROP TABLE documents;--"):
            core.retrieve(self.db, query)
        self.assertEqual(core.stats(self.db)['documents'], 2)

    def test_late_words_count_for_coverage(self):
        text = ' '.join('word'+str(i) for i in range(40)) + ' zephyr cartridge'
        core.import_records(self.db, [{'title':'Long introduction','text':text}])
        result=core.retrieve(self.db, 'zephyr cartridge')[0]
        self.assertEqual(result['term_coverage'], 1)

    def test_no_sources_never_calls_model(self):
        with patch('fieldguide.storage.model_answer') as generate:
            self.assertEqual(core.ask(self.db, 'Quasar astrophysics', 'http://127.0.0.1:8081/v1/chat/completions')['mode'], 'no_sources')
        generate.assert_not_called()

    def test_search_without_model_is_explicit(self):
        result = core.ask(self.db, 'pump filter')
        self.assertEqual(result['mode'], 'retrieval_only')
        self.assertIn('AI synthesis is disabled', result['answer'])
        self.assertTrue(result['sources'])

    def test_citation_format_check_accepts_existing_reference(self):
        with patch('fieldguide.storage.model_answer', return_value='The example uses a blue cartridge [S1].'):
            result = core.ask(self.db, 'pump filter', 'http://127.0.0.1:8081/v1/chat/completions')
        self.assertEqual(result['mode'], 'generated')

    def test_missing_or_fabricated_citations_rejected(self):
        for output in ('A blue cartridge.', 'A red cartridge [S999].'):
            with patch('fieldguide.storage.model_answer', return_value=output):
                result = core.ask(self.db, 'pump filter', 'http://127.0.0.1:8081/v1/chat/completions')
            self.assertEqual(result['mode'], 'citation_rejected')
            self.assertNotIn(output, result['answer'])

    def test_failure_keeps_sources(self):
        with patch('fieldguide.storage.model_answer', side_effect=OSError('Connection refused')):
            result = core.ask(self.db, 'pump filter', 'http://127.0.0.1:8081/v1/chat/completions')
        self.assertEqual(result['mode'], 'model_unavailable')
        self.assertTrue(result['sources'])

    def test_duplicate_import_is_idempotent(self):
        row={'title':'New','text':'reference entry'}
        self.assertEqual(core.import_records(self.db,[row,row]),1)
        self.assertEqual(core.import_records(self.db,[row]),0)

    def test_failed_import_is_atomic(self):
        before=core.stats(self.db)
        with self.assertRaises(ValueError):
            core.import_records(self.db,[{'title':'valid','text':'valid'}, {'title':'invalid','text':''}])
        self.assertEqual(core.stats(self.db),before)

    def test_backup_restore_roundtrip(self):
        core.add_inventory(self.db,{'name':'Rice','quantity':2,'unit':'bag','calories_per_unit':1000})
        core.add_note(self.db,{'title':'Meeting point','text':'Example private note'})
        backup=core.export_backup(self.db)
        other=Path(self.temp.name)/'other.db'; core.initialize(other)
        core.restore_backup(other,backup)
        self.assertEqual(core.stats(self.db),core.stats(other))
        self.assertEqual(core.retrieve(other,'pump filter')[0]['source'],'Example manual')

    def test_nonfinite_and_negative_inventory_rejected(self):
        for quantity in (float('nan'),float('inf'),-1):
            with self.assertRaises(ValueError):
                core.add_inventory(self.db,{'name':'Bad','quantity':quantity})

    def test_bad_restore_rolls_back(self):
        before=core.stats(self.db)
        with self.assertRaises(ValueError):
            core.restore_backup(self.db,{'schema':1,'documents':[{'title':'would be new','text':'text'}], 'inventory':[{'name':'bad','quantity':-1}]})
        self.assertEqual(core.stats(self.db),before)

    def test_endpoint_rejects_cloud_and_nonloopback(self):
        for url in ('https://api.example.com/v1/chat/completions','http://192.168.1.1/v1/chat/completions','http://localhost/v1/chat/completions','http://127.0.0.1/not-chat'):
            with self.assertRaises(ValueError): core.validate_endpoint(url)

    def test_context_has_bounded_excerpts(self):
        results=core.retrieve(self.db,'pump filter notebook documents')
        sources,context=core.source_context(results,budget=700)
        self.assertLessEqual(len(context),700)
        self.assertTrue(sources)

    def test_chunking_preserves_tail(self):
        text=('alpha beta gamma '*400)+'FINALWORD'
        chunks=list(core.chunk_text(text))
        self.assertTrue(chunks[-1].endswith('FINALWORD'))
        self.assertTrue(all(len(c)<=1100 for c in chunks))


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / 'test.db'
        self.server=app.make_server(self.db,port=0)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.base='http://127.0.0.1:'+str(self.server.server_port)

    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join()
        self.temp.cleanup()

    def request(self,path,data=None,headers=None):
        raw=None if data is None else json.dumps(data).encode()
        request=urllib.request.Request(self.base+path,data=raw,headers=headers or {})
        return urllib.request.urlopen(request,timeout=5)

    def test_http_import_ask_and_source_read(self):
        headers={'Content-Type':'application/json','X-Field-Library':'1'}
        with self.request('/api/import',{'documents':[{'title':'Example lantern','text':'The lantern label is amber.'}]},headers) as response:
            self.assertEqual(json.load(response)['imported'],1)
        with self.request('/api/ask',{'question':'lantern label'},headers) as response:
            result=json.load(response)
        self.assertEqual(result['mode'],'retrieval_only')
        doc_id=result['sources'][0]['doc_id']
        with self.request('/api/document?id='+str(doc_id)) as response:
            self.assertEqual(json.load(response)['title'],'Example lantern')

    def test_cross_origin_mutation_is_rejected(self):
        headers={'Content-Type':'application/json','X-Field-Library':'1','Origin':'https://example.com'}
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.request('/api/notes',{'title':'bad','text':'bad'},headers)
        self.assertEqual(caught.exception.code,403)

    def test_script_like_source_is_served_as_data(self):
        core.import_records(self.db,[{'title':'<script>alert(1)</script>','text':'Literal test text'}])
        with self.request('/api/search?q=literal') as response:
            self.assertIn('application/json',response.headers['Content-Type'])
            self.assertEqual(json.load(response)[0]['title'],'<script>alert(1)</script>')

    def test_static_files_are_local(self):
        for filename in ('/','/app.js','/style.css'):
            with self.request(filename) as response:
                self.assertEqual(response.status,200)
                self.assertIn("connect-src 'self'",response.headers['Content-Security-Policy'])
        with self.assertRaises(urllib.error.HTTPError):self.request('/../core.py')


class RealClientContractTests(unittest.TestCase):
    def test_model_http_contract_against_local_fixture(self):
        received={}
        class Fixture(BaseHTTPRequestHandler):
            def do_POST(self):
                received.update(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
                payload=json.dumps({'choices':[{'message':{'content':'Example answer [S1].'}}]}).encode()
                self.send_response(200);self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
            def log_message(self,*args):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),Fixture)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            answer=core.model_answer('http://127.0.0.1:'+str(server.server_port)+'/v1/chat/completions','fixture','Question','[S1] source')
            self.assertEqual(answer,'Example answer [S1].')
            self.assertFalse(received['stream'])
            self.assertEqual(received['messages'][0]['role'],'system')
            self.assertIn('[S1] source',received['messages'][1]['content'])
        finally:
            server.shutdown();server.server_close();thread.join()


if __name__=='__main__':unittest.main()
