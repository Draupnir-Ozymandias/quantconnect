"""Isolated descriptor prototype; Linux pseudo-file behavior/cost unverified."""
import os
from pathlib import Path
import stat
import threading
import time

from execution_truth.contracts import ContractError
from infra.stream.receive_loop_validity import CounterSample
from infra.stream.receive_loop_validity_probe import CounterRead, process_start, unified_cgroup, parse_cpu_stat


class PinnedCounterReader:
    def __init__(self, expected, capacity=128, *, execute=False, proc_root='/proc',
                 cgroup_root='/sys/fs/cgroup', monotonic=time.monotonic):
        if execute is not True or type(capacity) is not int or not 1<=capacity<=1024:
            raise ContractError('explicit bounded prototype execution required')
        if not isinstance(expected,dict) or set(expected)!={'boot_id','pid','process_start_id','cgroup'}:
            raise ContractError('explicit expected worker identity required')
        CounterSample(**expected,read_begin=0,read_end=0,counters=()).validate()
        unified_cgroup('0::'+expected['cgroup'])
        self.expected=dict(expected);self.capacity=capacity;self.clock=monotonic
        self.proc,self.mount=Path(proc_root),Path(cgroup_root)
        self.owner=threading.get_ident();self.fds=[];self.anchors={};self.files={}
        self.rows=[None]*capacity;self.count=0
        self.closed=self.failed=self.overflow=False
        self.close_errors=[]

    @staticmethod
    def fingerprint(value):return value.st_dev,value.st_ino,stat.S_IFMT(value.st_mode)

    def _keep(self,fd):
        if len(self.fds)>=64:
            os.close(fd);raise ContractError('descriptor capacity exceeded')
        self.fds.append(fd);return fd

    def _directory(self,path):
        if not path.is_absolute() or path.resolve(strict=True)!=path:
            raise ContractError('canonical non-symlink root required')
        fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        self._keep(fd);current=Path('/')
        self.anchors[str(current)]=self.fingerprint(os.fstat(fd))
        for part in path.parts[1:]:
            fd=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
            self._keep(fd);current=current/part
            value=self.fingerprint(os.fstat(fd))
            old=self.anchors.get(str(current))
            if old is not None and old!=value:raise ContractError('directory identity changed during pinning')
            self.anchors[str(current)]=value
        return fd

    def _pin(self,key,path):
        parent=self._directory(path.parent)
        fd=os.open(path.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
        self._keep(fd)
        value=self.fingerprint(os.fstat(fd))
        if value[2]!=stat.S_IFREG:raise ContractError('regular pseudo-file or fixture required')
        self.anchors[str(path)]=value;self.files[key]=fd

    def _paths(self):
        for path,expected in self.anchors.items():
            if self.fingerprint(os.stat(path,follow_symlinks=False))!=expected:
                raise ContractError('pinned path/inode identity changed')
        for fd in self.fds:
            if os.fstat(fd).st_nlink==0:raise ContractError('pinned inode deleted')

    def _text(self,key):
        data=os.pread(self.files[key],4097,0)
        if len(data)>4096:raise ContractError('bounded pseudo-file read exceeded')
        return data.decode('ascii')

    def _identity(self):
        return dict(boot_id=self._text('boot').strip(),pid=self.expected['pid'],
                    process_start_id=process_start(self._text('stat'),self.expected['pid']),
                    cgroup=unified_cgroup(self._text('group')))

    def _open(self):
        self._pin('boot',self.proc/'sys/kernel/random/boot_id')
        self._pin('stat',self.proc/str(self.expected['pid'])/'stat')
        self._pin('group',self.proc/str(self.expected['pid'])/'cgroup')
        self._pin('counter',self.mount/self.expected['cgroup'].lstrip('/')/'cpu.stat')
        self._paths()

    def close(self):
        # Explicit resource release is idempotent; reporting remains single-use.
        self.closed=True
        while self.fds:
            fd=self.fds.pop()
            try:os.close(fd)
            except OSError as exc:
                # Do not retry close: descriptor numbers may already be reused.
                self.close_errors.append(dict(fd=fd,error=type(exc).__name__))

    def read(self):
        if self.closed or self.failed:raise ContractError('closed/failed reader; no replay')
        if self.count==self.capacity:
            self.overflow=True;self.close()
            raise ContractError('counter capacity exceeded before I/O')
        try:
            if threading.get_ident()!=self.owner:raise ContractError('reader owner thread changed')
            begin=self.clock()
            if not self.files:self._open()
            self._paths()
            if self._identity()!=self.expected:raise ContractError('worker identity differs before counter read')
            counters=parse_cpu_stat(self._text('counter'))
            if self._identity()!=self.expected:raise ContractError('worker identity differs after counter read')
            self._paths()
            sample=CounterSample(**self.expected,read_begin=begin,read_end=self.clock(),counters=counters)
            sample.validate();result=CounterRead(sample,None)
        except Exception as exc:
            result=CounterRead(None,type(exc).__name__);self.failed=True;self.close()
        self.rows[self.count]=result;self.count+=1
        return result

    def finish(self):
        if getattr(self,'reported',False):raise ContractError('single-use finish')
        self.reported=True;self.close()
        return dict(reads=tuple(self.rows[:self.count]),overflow=self.overflow,
                    complete=bool(self.count) and not self.failed and not self.overflow and not self.close_errors,
                    cleanup_errors=list(self.close_errors),
                    prototype_only=True,native_linux_verified=False,probe_cost_verified=False)

    def __enter__(self):return self
    def __exit__(self,*args):self.close()
