"""Offline source-pinned observation declaration; no hooks or capture implementation."""
import argparse
import hashlib
from importlib import import_module
from importlib.metadata import version
import inspect
import json
from pathlib import Path
import platform
import re

from execution_truth.contracts import ContractError, payload_hash, verify_artifact_hash

SOURCE_PINS = {
    'websockets.sync.connection':'02f667220b611cf92312cc43464ba9b0714432a4659c0480d5793271301b3a06',
    'websockets.sync.messages':'9ad855b650e45c322a554d1a1b18dbe84a210de6bafde6554d6c83c39799ce45',
    'websockets.sync.client':'eb75f4c8736a64630129a55561ee6cade8b2b1e5eedc2c2b892bcfa64e0985fa',
    'websockets.protocol':'172a20d44b15f31b619c9757dcc1fdf9b1db10680f442d2dab019608f2b826b8'}
METHODS = {
    'websockets.sync.connection':('Connection.__init__','Connection.recv_events',
                                  'Connection.process_event','Connection.close_socket'),
    'websockets.sync.messages':('Assembler.__init__','Assembler.maybe_pause',
                               'Assembler.maybe_resume','Assembler.put','Assembler.get','Assembler.close'),
    'websockets.sync.client':('ClientConnection.__init__',),
    'websockets.protocol':('Protocol.receive_data','Protocol.events_received')}
POLICY = {'schema_version':'qcrl.receive_loop_observation_policy.v1',
    'network':'numeric_localhost_only', 'implementation_status':'declared_not_implemented',
    'installation':'inside_overridden_recv_events_before_unchanged_parent_loop',
    'marker_cap':128, 'library_high_water_frames':16, 'library_low_water_frames':4,
    'socket_recv_bufsize':65536, 'max_read_summaries':32768, 'max_flow_edges':32768,
    'max_encoded_sideband_bytes':32*1024**2, 'sideband_write':'after_measurement_only',
    'observer_failure':'disable_observation_preserve_native_operation_and_raw_data_no_successful_attribution',
    'parent_operations':'delegate_exactly_once_preserve_return_exception_timeout_lock_order',
    'telemetry_lock':'never_held_across_native_gate_socket_or_assembler_operation',
    'assembler_callbacks':'observe_under_existing_mutex_never_reacquire_it',
    'gate_interval':'acquire_attempt_to_acquire_return_not_pure_pause_duration',
    'socket_interval':'recv_call_entry_to_return_or_exception_not_wire_arrival',
    'flow_edges':'pause_and_resume_operation_brackets_keep_assembler_closed_separate',
    'dispatch':'aggregate_frame_occurrences_per_read_iteration_not_packet_or_message_boundaries',
    'partial_order':'thread_local_order_and_operation_ids_not_global_total_order',
    'close':'closed_assembler_resume_is_not_normal_drain_recovery',
    'quota_change_authorized':False, 'public_rollout_authorized':False,
    'capture_authorized_by_contract':False, 'orders_authorized':False}


def bindings():
    if version('websockets') != '15.0.1':
        raise ContractError('receive-loop declaration requires websockets 15.0.1')
    methods = {}
    for name, digest in SOURCE_PINS.items():
        module = import_module(name)
        if hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest() != digest:
            raise ContractError('pinned receive-loop library source differs')
        for key in METHODS[name]:
            cls, method = key.split('.')
            obj = getattr(getattr(module,cls),method)
            if Path(inspect.getsourcefile(obj)).resolve() != Path(module.__file__).resolve():
                raise ContractError('receive-loop method binding differs from pinned module')
            lines, start = inspect.getsourcelines(obj)
            methods[name+'.'+key] = {'source_sha256':hashlib.sha256(''.join(lines).encode()).hexdigest(),
                                    'first_line':start, 'line_count':len(lines)}
    return methods


def runtime_receipt():
    obj = {'schema_version':'qcrl.receive_loop_source_receipt.v1','library_version':'15.0.1',
           'source_files':dict(SOURCE_PINS),'methods':bindings(),'python_version':platform.python_version(),
           'platform':platform.system(),'capture_performed':False,'orders_authorized':False}
    obj['receipt_sha256'] = payload_hash(obj)
    return obj


def validate_receipt(obj):
    verify_artifact_hash(obj,'receipt_sha256','receive-loop source receipt')
    if (set(obj) != {'schema_version','library_version','source_files','methods','python_version',
                     'platform','capture_performed','orders_authorized','receipt_sha256'}
            or obj['schema_version'] != 'qcrl.receive_loop_source_receipt.v1'
            or obj['library_version'] != '15.0.1' or obj['source_files'] != SOURCE_PINS
            or obj['methods'] != bindings() or obj['capture_performed'] is not False
            or obj['orders_authorized'] is not False
            or not isinstance(obj['python_version'],str) or len(obj['python_version']) > 32
            or obj['platform'] not in ('Darwin','Linux','Windows')):
        raise ContractError('receive-loop source receipt differs from fixed declaration')
    return obj


def declare(source_analysis_sha256, receipt):
    if not isinstance(source_analysis_sha256,str) or not re.fullmatch('[0-9a-f]{64}',source_analysis_sha256):
        raise ContractError('receive-loop declaration requires a source analysis hash')
    validate_receipt(receipt)
    obj = {'schema_version':'qcrl.receive_loop_observation_contract.v1',
           'source_analysis_sha256':source_analysis_sha256,'runtime_receipt':receipt,
           'policy':dict(POLICY),'policy_sha256':payload_hash(POLICY),
           'required_observation_categories':['gate_attempt_and_return','socket_read_return_or_error',
               'pause_and_resume_operation','dispatch_frame_counter_range'],
           'acceptance_gates':['native_semantics_equivalent_under_success_error_timeout_and_close',
               'observer_failure_never_swallows_or_repeats_native_operations',
               'no_installation_race_or_partial_start_claim','same_source_corpus_encoding_caps_and_quotas',
               'baseline_vs_instrumented_finite_localhost_overhead_measured',
               'no_sideband_budget_loss_before_successful_attribution',
               'raw_archive_and_occurrence_integrity_verified'],
           'public_rollout_authorized':False,'capture_performed':False,'orders_authorized':False}
    obj['contract_sha256'] = payload_hash(obj)
    return obj


def validate_contract(obj):
    verify_artifact_hash(obj,'contract_sha256','receive-loop observation contract')
    if obj != declare(obj.get('source_analysis_sha256'),obj.get('runtime_receipt')):
        raise ContractError('receive-loop contract differs from fixed offline policy')
    return obj


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-analysis-sha256',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    obj = declare(args.source_analysis_sha256,runtime_receipt())
    with args.output.open('x',encoding='utf-8') as handle:
        json.dump(obj,handle,sort_keys=True,indent=2); handle.write('\n')
    print(json.dumps({'contract_sha256':obj['contract_sha256'],
                      'receipt_sha256':obj['runtime_receipt']['receipt_sha256'],
                      'capture_performed':False}))


if __name__ == '__main__': main()
