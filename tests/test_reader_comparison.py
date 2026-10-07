import json
from pathlib import Path
import tempfile
import unittest

from execution_truth.contracts import payload_hash, ContractError, verify_artifact_hash
from infra.stream.reader_comparison import run_case, prepare_message, load_corpus
from tests.test_taker_replay import raw_bundle
from tests.test_market_stream import book
from execution_truth.market_stream import stream_plan
from tests.test_receive_adapter import AVAILABLE

def corpus():
    raw=raw_bundle()
    spec=stream_plan(raw)
    books=json.dumps([book(spec,a) for a in spec['asset_ids']])
    price=json.dumps({'event_type':'price_change','market':spec['condition_id'],
                     'price_changes':[{'asset_id':a,'price':'0.5','size':'2','side':'BUY'} for a in spec['asset_ids']],
                     'timestamp':'1777938600000'})
    value={'schema_version':'qcrl.archived_reader_comparison_corpus.v1','synthetic_retimestamping':True,
           'bundle':raw,'book_template':books,'price_templates':[price]*64}
    value['corpus_sha256']=payload_hash(value)
    return value

class ReaderComparisonTests(unittest.TestCase):
    def test_generator_keeps_templates_unchanged_and_embeds_monotonic_identity(self):
        from datetime import datetime,timezone
        c=corpus(); before=payload_hash(c)
        generated=json.loads(prepare_message(c,0,12.5,datetime(2026,1,1,tzinfo=timezone.utc)))
        self.assertEqual(generated[0]['_qcrl_probe']['producer_begin_monotonic'],12.5)
        self.assertEqual(generated[0]['_qcrl_probe']['sequence'],0)
        self.assertEqual(payload_hash(c),before)

    def test_corpus_hash_and_size_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'corpus.json'; c=corpus(); p.write_text(json.dumps(c))
            self.assertEqual(load_corpus(p),c)
            c['price_templates']=[]; p.write_text(json.dumps(c))
            with self.assertRaises(ContractError): load_corpus(p)

    @unittest.skipUnless(AVAILABLE,'pinned optional WebSocket library required')
    def test_all_three_modes_preserve_raw_sequence_and_recorder_integrity(self):
        with tempfile.TemporaryDirectory() as tmp:
            for mode in ('bare','receive','recorder'):
                with self.subTest(mode=mode):
                    result=run_case(corpus(),Path(tmp)/mode,'a'*64,mode=mode,rate=100,duration=.05)
                    verify_artifact_hash(result,'report_sha256','case')
                    self.assertEqual(result['messages'],5)
                    self.assertTrue(result['raw_messages_unchanged'])
                    self.assertEqual(result['producer_begin_to_delivery_upper']['count'],5)
                    self.assertEqual(result['missing_delivery_stamps'],0)
                    if mode=='recorder':
                        self.assertTrue(result['verification']['freshness_verification']['all_final_snapshots_present'])
                        self.assertEqual(result['verification']['frames'],5)
                    with self.assertRaises(FileExistsError):
                        run_case(corpus(),Path(tmp)/mode,'a'*64,mode=mode,rate=100,duration=.05)

if __name__=='__main__': unittest.main()
