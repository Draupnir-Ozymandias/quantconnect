"""Finite paced localhost reader comparison; never public acquisition or trading."""
import argparse
from copy import deepcopy
from datetime import timedelta
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from execution_truth.contracts import ContractError, payload_hash, verify_artifact_hash
from execution_truth.market_stream import collect_market_stream, stream_plan, verify_stream_log
from execution_truth.receive_adapter import ObservedSocket, _load_library
from execution_truth.receive_path import ReceivePathTracker, declare, sample_clock, validate_delivery
from execution_truth.rolling_stream import persist
from execution_truth.stream_freshness import statistics
from execution_truth.binance_source import _time

POLICY = {"schema_version": "qcrl.paced_reader_comparison_policy.v1", "rates": [100, 500, 1000],
          "duration_seconds": 2, "rounds": 3, "modes": ["bare", "receive", "recorder"],
          "mode_order": "rotating_latin_order_by_round", "pacing": "absolute_deadlines_no_message_drops",
          "producer_clock": "before_serialization_and_send_not_wire_arrival",
          "producer_and_consumer": "same_process_shared_cgroup_not_isolated_consumer_cpu",
          "synthetic_timestamp": "fixture_utc_at_producer_application_begin", "book_period_messages": 65,
          "receive_policy": "v2", "limits": {"max_queue": 16, "max_size": 262144, "close_timeout": 5},
          "validation_outside_timed_reader": True, "orders_authorized": False}


def load_corpus(path):
    corpus = json.loads(Path(path).read_text())
    verify_artifact_hash(corpus, "corpus_sha256", "comparison corpus")
    if (corpus.get("schema_version") != "qcrl.archived_reader_comparison_corpus.v1"
            or corpus.get("synthetic_retimestamping") is not True or len(corpus.get("price_templates", [])) != 64):
        raise ContractError("unsupported bounded comparison corpus")
    for template in [corpus["book_template"], *corpus["price_templates"]]:
        if not isinstance(template, str) or len(template.encode()) > 128000:
            raise ContractError("comparison template size/type exceeds budget")
        events = json.loads(template)
        if not all(isinstance(e, dict) for e in (events if isinstance(events,list) else [events])):
            raise ContractError("templates require object events")
    return corpus


def prepare_message(corpus, sequence, mono, utc):
    index = sequence % 65
    raw = corpus["book_template"] if index == 0 else corpus["price_templates"][index-1]
    data = json.loads(raw)
    for event in data if isinstance(data,list) else [data]:
        event["timestamp"] = str(int(utc.timestamp()*1000))
        event["_qcrl_probe"] = {"sequence": sequence, "producer_begin_monotonic": mono}
    return json.dumps(data, separators=(",", ":"))


def run_case(corpus, root, declaration_hash, *, mode, rate, duration=2):
    from websockets.sync.client import connect
    from websockets.sync.server import serve
    from websockets.exceptions import ConnectionClosed
    _load_library()
    if mode not in POLICY["modes"] or rate not in POLICY["rates"] or not 0 < duration <= 2:
        raise ContractError("unsupported finite comparison case")
    count = max(2, int(rate*duration))
    root = Path(root)
    origin = time.monotonic()
    spec = stream_plan(corpus["bundle"], segmented=True, profiling=True, resilient=True, receive_path=True,
                       freshness_telemetry=True, receive_policy="v2", source_plan_sha256=declaration_hash,
                       max_seconds=15, max_frames=count)
    base = _time(spec["event_start_at_utc"])
    def clock(): return base+timedelta(seconds=time.monotonic()-origin)
    sent, producer_times, deliveries, records, diagnostics = [], [], [], [], []
    failures = []
    producer_cpu = []
    done = threading.Event()

    def handler(conn):
        cpu_start = time.thread_time()
        try:
            if json.loads(conn.recv(timeout=5)) != spec["subscription"]:
                raise ContractError("unexpected local subscription")
            pacing_start = time.monotonic()+.02
            for sequence in range(count):
                deadline = pacing_start+sequence/rate
                time.sleep(max(0,deadline-time.monotonic()))
                begin = time.monotonic()
                message = prepare_message(corpus,sequence,begin,clock())
                send_start = time.monotonic()
                conn.send(message)
                end = time.monotonic()
                sent.append(message)
                producer_times.append({"sequence": sequence, "deadline": deadline, "begin": begin,
                                       "send_start": send_start, "send_end": end})
            try: conn.recv(timeout=20)
            except ConnectionClosed: pass
        except Exception as exc:
            failures.append(type(exc).__name__)
        finally:
            producer_cpu.append(time.thread_time()-cpu_start)
            done.set()

    tracker = ReceivePathTracker(declare(declaration_hash,"localhost.comparison",stream_spec_sha256=payload_hash(spec),policy_version="v2"))
    raws = []
    summary = verification = None
    start_cpu = time.process_time()
    reader_cpu_start = time.thread_time()
    with serve(handler,"127.0.0.1",0,compression=None,ping_interval=None,close_timeout=1) as server:
        thread = threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        uri = "ws://127.0.0.1:"+str(server.socket.getsockname()[1])
        client = None
        try:
            if mode == "recorder":
                def connector(t, number, **kwargs):
                    nonlocal client
                    client = ObservedSocket(uri,t,number,**kwargs)
                    class Traced:
                        reset = client.reset
                        def send(self,message): return client.send(message)
                        def recv(self,timeout):
                            raw,record = client.recv(timeout)
                            raws.append(raw); records.append(record)
                            deliveries.append(record.get("application_delivery"))
                            return raw,record
                        def close(self): return client.close()
                    return Traced()
                summary = collect_market_stream(corpus["bundle"],spec,root/"stream",connector=connector,
                    clock=clock,monotonic=time.monotonic,clock_domain="localhost.comparison")
            else:
                client = (ObservedSocket(uri,tracker,1,clock=clock) if mode == "receive" else
                    connect(uri,compression=None,ping_interval=None,proxy=None,max_queue=16,max_size=262144,close_timeout=5))
                client.send(json.dumps(spec["subscription"]))
                for _ in range(count):
                    if mode == "receive":
                        raw,record = client.recv(15)
                        records.append(record)
                        stamp = record.get("application_delivery")
                    else:
                        raw = client.recv(timeout=15)
                        stamp = sample_clock(clock,time.monotonic,"localhost.comparison")
                        assembler = client.recv_messages
                        with assembler.mutex:
                            diagnostics.append({"library_queue_depth": None if assembler.closed else assembler.frames.qsize(),
                                                "library_backpressure_active": assembler.paused})
                    raws.append(raw); deliveries.append(stamp)
        finally:
            if client is not None: client.close()
            done.wait(3)
            server.shutdown(); thread.join(3)
        if thread.is_alive() or not done.is_set(): raise ContractError("local producer did not terminate")
    measured_cpu = time.process_time()-start_cpu
    reader_cpu = time.thread_time()-reader_cpu_start
    if failures or len(raws)!=count or raws!=sent:
        raise ContractError("comparison incomplete or raw sequence changed: "+repr(failures))
    if mode == "recorder":
        verification = verify_stream_log(root/"stream")
        if verification["frames"]!=count or summary["status"]!="frame_limit":
            raise ContractError("recorder comparison hit another bound")
    if mode == "receive":
        for raw,record in zip(raws,records): validate_delivery(record,tracker.contract,raw)
    # All modes preserve raw sequence and producer observations outside the timed
    # reader. Full recorder costs intentionally include its hashing/storage work.
    producer_artifact = {"messages": producer_times,"raw_messages_sha256":payload_hash(sent)}
    producer_artifact['producer_sha256'] = payload_hash(producer_artifact)
    delivery_artifact = {"stamps": deliveries,"receive_records":records,"bare_queue_samples":diagnostics}
    delivery_artifact['delivery_sha256'] = payload_hash(delivery_artifact)
    persist(root/"producer.json",producer_artifact)
    persist(root/"deliveries.json",delivery_artifact)
    delivery_age, callback_age, lateness, send_block = [], [], [], []
    for index,(producer,stamp) in enumerate(zip(producer_times,deliveries)):
        lateness.append(producer["begin"]-producer["deadline"])
        send_block.append(producer["send_end"]-producer["send_start"])
        if stamp is not None: delivery_age.append(stamp["monotonic_after"]-producer["begin"])
        if records and records[index].get("receive_marker"):
            r = records[index]
            if r["first_observation_to_delivery"]["timing_eligible"] and r["last_observation_to_delivery"]["timing_eligible"]:
                callback_age.append(r["receive_marker"]["last_receive_observation"]["monotonic_after"]-producer["begin"])
    first,last = producer_times[0]['begin'],producer_times[-1]['begin']
    known = [s for s in deliveries if s is not None]
    q = records if records else diagnostics
    result = {"schema_version":"qcrl.paced_reader_case.v1","mode":mode,"rate":rate,"messages":count,
        "raw_messages_unchanged":True,"raw_messages_sha256":payload_hash(raws),
        "producer_sha256": producer_artifact['producer_sha256'], "delivery_sha256": delivery_artifact['delivery_sha256'],
        "payload_bytes": {"min": min(len(raw.encode()) for raw in raws), "max": max(len(raw.encode()) for raw in raws),
                          "mean": sum(len(raw.encode()) for raw in raws)/count},
        "producer_attained_messages_per_second":(count-1)/(last-first),
        "receiver_messages_per_second":(count-1)/(known[-1]['monotonic_after']-known[0]['monotonic_after']) if len(known)>1 else None,
        "producer_deadline_lateness":statistics(lateness),"producer_send_call_seconds":statistics(send_block),
        "producer_begin_to_delivery_upper":statistics(delivery_age),"eligible_producer_begin_to_callback_upper":statistics(callback_age),
        "missing_delivery_stamps":count-len(known),"unknown_receive_records":sum(not r.get('receive_marker') for r in records),
        "max_sampled_queue_depth":max((r['library_queue_depth'] for r in q if r.get('library_queue_depth') is not None),default=None),
        "paused_delivered_samples":sum(r.get('library_backpressure_active') is True for r in q),
        "whole_process_timed_cpu_seconds":measured_cpu,"reader_thread_timed_cpu_seconds":reader_cpu,
        "producer_thread_cpu_seconds":producer_cpu[0],"verification":verification,
        "orders_authorized":False,"public_network_capture":False}
    result['report_sha256']=payload_hash(result)
    persist(root/"report.json",result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus',type=Path,required=True)
    parser.add_argument('--root',type=Path,required=True)
    args=parser.parse_args()
    corpus=load_corpus(args.corpus)
    declaration={'schema_version':'qcrl.paced_reader_comparison.v1','policy':deepcopy(POLICY),
                 'corpus_sha256':corpus['corpus_sha256'],'orders_authorized':False,'public_network_capture':False}
    declaration['plan_sha256']=payload_hash(declaration)
    persist(args.root/'declaration.json',declaration)
    persist(args.root/'corpus.json',corpus)
    results=[]
    for round_ in range(POLICY['rounds']):
        order=POLICY['modes'][round_:]+POLICY['modes'][:round_]
        for rate in POLICY['rates']:
            for mode in order:
                case=args.root/(str(round_)+'-'+str(rate)+'-'+mode)
                result=run_case(corpus,case,declaration['plan_sha256'],mode=mode,rate=rate)
                results.append({'round':round_,'case':case.name,**result})
                print(json.dumps({'case':case.name,'rate_attained':result['producer_attained_messages_per_second'],
                                  'delivery_age':result['producer_begin_to_delivery_upper']}),flush=True)
    sources={}
    for name in ('infra/stream/reader_comparison.py','execution_truth/receive_adapter.py','execution_truth/receive_path.py',
                 'execution_truth/market_stream.py','execution_truth/connection_freshness.py','execution_truth/stream_segments.py'):
        path=Path(__file__).resolve().parents[2]/name
        sources[name]=hashlib.sha256(path.read_bytes()).hexdigest()
    report={'schema_version':'qcrl.paced_reader_comparison_result.v1','declaration_sha256':declaration['plan_sha256'],
            'library':version('websockets'),'python':platform.python_version(),'platform':platform.platform(),
            'sources':sources,'cases':results,'orders_authorized':False,'public_network_capture':False}
    report['report_sha256']=payload_hash(report)
    persist(args.root/'comparison.json',report)
    print('report_sha256='+report['report_sha256'],flush=True)


if __name__=='__main__': main()
