"""Bounded opt-in completion witnesses; prototype only, no acceptance evaluator."""
from copy import deepcopy
import gzip
import json
import math
import os
from pathlib import Path
import platform
import threading

from execution_truth.acquisition import utc_text
from execution_truth.contracts import ContractError, payload_hash, verify_artifact_hash
from execution_truth.stream_segments import file_hash

POLICY = dict(schema_version='qcrl.recorder_completion_policy.v1',
              max_frames=65536,max_barriers=65536,max_encoded_bytes=32*1024**2,
              append_boundary='gzip_writer_write_return_not_flush_or_durable',
              barrier_boundary='file_fsync_success_after_writer_and_file_flush',
              publication='separate_post_collection_sideband_not_self_attesting_row',
              prototype_only=True,acceptance_demonstrated=False,orders_authorized=False)


def _sources():
    root=Path(__file__).resolve().parents[2]
    names=('infra/stream/recorder_completion.py','infra/stream/recorder_completion_lane.py',
           'execution_truth/market_stream.py',
           'execution_truth/stream_segments.py','execution_truth/contracts.py',
           'execution_truth/acquisition.py')
    return {name:file_hash(root/name) for name in names}


class CompletionWitnesses:
    def __init__(self,spec,clock_domain,*,clock,monotonic,execute=False,
                 capacity=65536,barrier_capacity=65536):
        if (execute is not True or type(capacity) is not int or not 1<=capacity<=POLICY['max_frames']
                or type(barrier_capacity) is not int or not 1<=barrier_capacity<=POLICY['max_barriers']
                or not isinstance(clock_domain,str) or not 1<=len(clock_domain)<=128):
            raise ContractError('explicit bounded prototype and clock domain required')
        self.spec_sha256=payload_hash(spec);self.domain=clock_domain
        self.clock,self.monotonic=clock,monotonic
        self.capacity,self.barrier_capacity=capacity,barrier_capacity
        self.owner=threading.get_ident();self.sources=_sources()
        self.frames=[];self.barriers=[];self.pending=None;self.active_barrier=None
        self.failure=None;self.last=None;self.started=False;self.closed=False

    def validate_spec(self,spec):
        if (threading.get_ident()!=self.owner or self.started or self.closed
                or self.failure or payload_hash(spec)!=self.spec_sha256):
            raise ContractError('single-use matching completion observer required')
        self.started=True

    def disable(self,reason):
        if self.failure is None:self.failure=str(reason)[:128]

    def _now(self):
        if threading.get_ident()!=self.owner:raise ContractError('completion observer thread changed')
        value=self.monotonic()
        if type(value) not in (int,float) or not math.isfinite(value) or value<0:
            raise ContractError('finite nonnegative monotonic stamp required')
        if self.last is not None and value<self.last:raise ContractError('completion clock regressed')
        self.last=value
        return value

    def application_return(self,frame,connection):
        if self.failure or self.closed:return
        try:
            before=self._now();utc=utc_text(self.clock());after=self._now()
            if self.pending is not None:raise ContractError('unlinked prior application return')
            if len(self.frames)>=self.capacity:raise ContractError('completion frame capacity exhausted')
            if type(connection) is not int or connection<1:raise ContractError('connection required')
            raw=frame[0] if isinstance(frame,tuple) and len(frame)==2 else frame
            self.pending=dict(raw=raw,connection=connection,
                              returned=dict(before=before,utc=utc,after=after))
        except Exception as exc:self.disable(type(exc).__name__+':'+str(exc))

    def boundary(self,event,**fields):
        if self.failure or self.closed:return
        try:
            now=self._now()
            if event=='append_complete':
                row=fields['row']
                if row['kind']=='frame':
                    p=self.pending
                    if (p is None or not isinstance(p['raw'],str)
                            or row['payload']['raw_text']!=p['raw']
                            or row['payload']['connection']!=p['connection']):
                        raise ContractError('raw occurrence/connection linkage differs')
                    self.frames.append(dict(sequence=len(self.frames),connection=p['connection'],
                                            ordinal=row['ordinal'],record_sha256=row['record_sha256'],
                                            returned=p['returned'],append_completed=now))
                    self.pending=None
            elif event=='sync_begin':
                if self.active_barrier is not None:raise ContractError('overlapping sync barriers')
                if len(self.barriers)>=self.barrier_capacity:raise ContractError('completion barrier capacity exhausted')
                self.active_barrier=dict(sequence=len(self.barriers),begin=now,
                                         ordinal=fields['ordinal'],record_sha256=fields['record_sha256'])
            elif event=='sync_complete':
                if self.active_barrier is None:raise ContractError('sync completion without begin')
                self.barriers.append(dict(self.active_barrier,end=now));self.active_barrier=None
            elif event in ('sync_failed','append_failed'):
                self.disable(event+':'+fields['error'])
            else:raise ContractError('unknown completion boundary')
        except Exception as exc:self.disable(type(exc).__name__+':'+str(exc))

    def snapshot(self,root):
        if self.closed:raise ContractError('completion snapshot is single-use')
        self.closed=True
        root=Path(root)
        if self.pending is not None:self.disable('unlinked_application_return')
        if self.active_barrier is not None:self.disable('unfinished_sync_barrier')
        manifest=root/'manifest.json'
        ended=manifest.is_file() and json.loads(manifest.read_text()).get('session_end_present') is True
        report=dict(schema_version='qcrl.recorder_completion_witnesses.v1',policy=deepcopy(POLICY),
                    spec_sha256=self.spec_sha256,clock_domain=self.domain,sources=self.sources,
                    capacity=self.capacity,barrier_capacity=self.barrier_capacity,
                    frames=self.frames,barriers=self.barriers,failure=self.failure,
                    unlinked_return=None if self.pending is None else
                        {k:self.pending[k] for k in ('connection','returned')},
                    unfinished_barrier=self.active_barrier,
                    runtime=dict(python=platform.python_version(),platform=platform.platform(),
                                 pid=os.getpid(),thread_id=self.owner),
                    complete=self.started and self.failure is None and ended,
                    manifest_file_sha256=file_hash(manifest) if manifest.is_file() else None,
                    acceptance_demonstrated=False,orders_authorized=False)
        report['completion_sha256']=payload_hash(report)
        if len(json.dumps(report,sort_keys=True).encode())>POLICY['max_encoded_bytes']:
            # Never publish a truncated witness set as complete.
            raise ContractError('completion encoded sideband capacity exceeded; retain raw archive')
        return report


def verify_completion(report,root,*,expected_domain,expected_sources=None):
    """Offline archive linkage and chronology; not measured-overhead acceptance."""
    from execution_truth.market_stream import verify_stream_log
    fields={'schema_version','policy','spec_sha256','clock_domain','sources','capacity',
            'barrier_capacity','frames','barriers','failure','complete','manifest_file_sha256',
            'acceptance_demonstrated','orders_authorized','completion_sha256',
            'unlinked_return','unfinished_barrier','runtime'}
    if not isinstance(report,dict) or set(report)!=fields:raise ContractError('completion schema differs')
    verify_artifact_hash(report,'completion_sha256','completion witness')
    if (report['schema_version']!='qcrl.recorder_completion_witnesses.v1' or report['policy']!=POLICY
            or report['clock_domain']!=expected_domain or report['sources']!=(expected_sources or _sources())
            or report['acceptance_demonstrated'] is not False or report['orders_authorized'] is not False
            or report['complete'] is not True or report['failure'] is not None
            or report['unlinked_return'] is not None or report['unfinished_barrier'] is not None):
        raise ContractError('incomplete or unsupported completion contract')
    runtime=report['runtime']
    if (not isinstance(runtime,dict) or set(runtime)!={'python','platform','pid','thread_id'}
            or any(not isinstance(runtime[k],str) or not runtime[k] for k in ('python','platform'))
            or any(type(runtime[k]) is not int or runtime[k]<=0 for k in ('pid','thread_id'))):
        raise ContractError('completion runtime identity differs')
    if (not isinstance(report['frames'],list) or not isinstance(report['barriers'],list)
            or type(report['capacity']) is not int or not 1<=report['capacity']<=POLICY['max_frames']
            or type(report['barrier_capacity']) is not int
            or not 1<=report['barrier_capacity']<=POLICY['max_barriers']
            or len(report['frames'])>report['capacity'] or len(report['barriers'])>report['barrier_capacity']
            or len(json.dumps(report,sort_keys=True).encode())>POLICY['max_encoded_bytes']):
        raise ContractError('completion bounds differ')
    root=Path(root);archive=verify_stream_log(root)
    if (not archive['manifest_present'] or not archive['session_end_present']
            or file_hash(root/'manifest.json')!=report['manifest_file_sha256']):
        raise ContractError('completion archive incomplete or manifest differs')
    rows={};header=None
    # Bounded stream verification runs first; only referenced row metadata is retained.
    for f in report['frames']:
        if (not isinstance(f,dict) or type(f.get('ordinal')) is not int or f['ordinal']<0
                or type(f.get('connection')) is not int or f['connection']<1):
            raise ContractError('completion frame identity invalid')
    for b in report['barriers']:
        if not isinstance(b,dict) or type(b.get('ordinal')) is not int or b['ordinal']<0:
            raise ContractError('completion watermark invalid')
    wanted={f['ordinal'] for f in report['frames']}|{b['ordinal'] for b in report['barriers']}
    frame_rows=[]
    for segment in sorted(root.glob('segment-*.json')):
        descriptor=json.loads(segment.read_text())
        with gzip.open(root/descriptor['file'],'rt') as handle:
            for line in handle:
                row=json.loads(line)
                if row['kind']=='session_start':header=row['payload']
                if row['ordinal'] in wanted:
                    rows[row['ordinal']]={k:row[k] for k in ('record_sha256','local_monotonic_seconds')}
                if row['kind']=='frame':
                    frame_rows.append((row['ordinal'],row['record_sha256'],row['payload']['connection']))
                    if len(frame_rows)>report['capacity']:raise ContractError('archive frame population exceeds witness bound')
    if header is None or header['spec_sha256']!=report['spec_sha256']:
        raise ContractError('completion stream spec differs')
    if len(frame_rows)!=len(report['frames']):raise ContractError('completion occurrence population differs')
    previous=0;latencies=[]
    for index,(f,raw) in enumerate(zip(report['frames'],frame_rows)):
        if (set(f)!={'sequence','connection','ordinal','record_sha256','returned','append_completed'}
                or type(f['sequence']) is not int or f['sequence']!=index
                or (f['ordinal'],f['record_sha256'],f['connection'])!=raw
                or set(f['returned'])!={'before','utc','after'}):
            raise ContractError('completion FIFO/hash/connection differs')
        from execution_truth.contracts import _utc_text
        _utc_text(f['returned']['utc'],'application return UTC')
        values=(f['returned']['before'],f['returned']['after'],f['append_completed'])
        if any(type(v) not in (int,float) or not math.isfinite(v) or v<0 for v in values):
            raise ContractError('invalid completion clock')
        before,after,end=values
        if not previous<=before<=after<=rows[f['ordinal']]['local_monotonic_seconds']<=end:
            raise ContractError('completion clock enclosure/order differs')
        previous=end;latencies.append(dict(ordinal=f['ordinal'],append_upper_seconds=end-before))
    previous_end=0;previous_ordinal=-1
    for index,b in enumerate(report['barriers']):
        if (set(b)!={'sequence','begin','end','ordinal','record_sha256'} or type(b['sequence']) is not int
                or b['sequence']!=index or type(b['ordinal']) is not int or b['ordinal'] not in rows
                or rows[b['ordinal']]['record_sha256']!=b['record_sha256']
                or any(type(b[k]) not in (int,float) or not math.isfinite(b[k]) for k in ('begin','end'))
                or not previous_end<=b['begin']<=b['end'] or b['ordinal']<previous_ordinal
                or rows[b['ordinal']]['local_monotonic_seconds']>b['begin']):
            raise ContractError('durable watermark/hash/chronology differs')
        previous_end=b['end'];previous_ordinal=b['ordinal']
    barrier_index=0
    for f,latency in zip(report['frames'],latencies):
        while barrier_index<len(report['barriers']):
            b=report['barriers'][barrier_index]
            if b['ordinal']>=f['ordinal'] and b['begin']>=f['append_completed']:break
            barrier_index+=1
        if barrier_index==len(report['barriers']):raise ContractError('frame has no successful durable watermark')
        latency['durable_upper_seconds']=report['barriers'][barrier_index]['end']-f['returned']['before']
    return dict(schema_version='qcrl.recorder_completion_verification.v1',frames=len(frame_rows),
                barriers=len(report['barriers']),latencies=latencies,archive_verified=True,
                completion_linkage_verified=True,acceptance_demonstrated=False,orders_authorized=False)
