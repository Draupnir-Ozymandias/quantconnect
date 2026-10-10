"""Isolated pinned observer adapter; not imported by deployed/frozen launchers."""
import time
from copy import deepcopy
from execution_truth.contracts import ContractError,payload_hash
from infra.stream.receive_loop_validity_observer import ObserverCore
from infra.stream.receive_loop_pinned_counter import PinnedCounterReader

METHOD=dict(schema_version='qcrl.pinned_observer_method.v1',
            reader='expected_identity_pinned_descriptors_before_after_path_checks',
            cadence='unchanged_external_absolute_grid',
            first_pin_cost='inside_first_counter_acquisition',
            cleanup='before_observer_ack_inside_observer_cpu_window',
            cost_accepted=False)


class PinnedObserverCore(ObserverCore):
    def __init__(self,lane,target,*,execute=False,capacity=512,
                 monotonic=time.monotonic,sleep=time.sleep,
                 proc_root='/proc',cgroup_root='/sys/fs/cgroup'):
        # Validate barriers with a control core before constructing any reader.
        if lane not in ('control','pacing','full'):raise ContractError('declared lane required')
        super().__init__('control',target,execute=execute,capacity=capacity,
                         monotonic=monotonic,sleep=sleep)
        self.lane=lane
        self.reader=(PinnedCounterReader(target,capacity,execute=True,proc_root=proc_root,
                     cgroup_root=cgroup_root,monotonic=monotonic) if lane=='full' else None)
        self.cleanup_receipt=None

    def tick(self,deadline):
        if self.cleanup_receipt is not None:raise ContractError('observer cleaned; no further ticks')
        try:return super().tick(deadline)
        except Exception:
            if self.reader is not None:self.reader.close()
            raise

    def cleanup(self):
        if self.cleanup_receipt is None:
            if self.reader is not None:self.reader.close()
            errors=[] if self.reader is None else list(self.reader.close_errors)
            self.cleanup_receipt=dict(method=deepcopy(METHOD),reader_present=self.reader is not None,
                remaining_owned_fds=0 if self.reader is None else len(self.reader.fds),
                errors=errors,cleanup_complete=not errors and (self.reader is None or not self.reader.fds))
        return self.cleanup_receipt

    def finish(self):
        cleanup=self.cleanup()
        result=super().finish();result.pop('report_sha256')
        result.update(schema_version='qcrl.pinned_observer_core.v1',observer_method=deepcopy(METHOD),
                      cleanup=cleanup,complete=result['complete'] and cleanup['cleanup_complete'])
        result['report_sha256']=payload_hash(result)
        return result
