"""Bounded ordered archive rescan sized by the declared case, not a smoke count."""
import gzip
import json
from pathlib import Path
import re
from execution_truth.contracts import ContractError


def archive_frames(root, count):
    if type(count) is not int or not 1 <= count <= 60000:
        raise ContractError('declared case frame count outside supported population')
    root=Path(root); frames=[]; footer=None; gaps=0; rows=0; total=0
    descriptors=sorted(root.glob('segment-*.json'))
    if not descriptors or len(descriptors)>1024:
        raise ContractError('bounded archive segments required')
    for descriptor in descriptors:
        if descriptor.is_symlink() or descriptor.stat().st_size>2*1024**2:
            raise ContractError('bounded regular segment descriptor required')
        info=json.loads(descriptor.read_bytes()); name=info['file']
        if not re.fullmatch(r'segment-[0-9]{6}\.gz',name):
            raise ContractError('canonical archive segment required')
        path=root/name
        if path.is_symlink() or not path.is_file():
            raise ContractError('regular archive segment required')
        with gzip.open(path,'rb') as handle:
            while True:
                line=handle.readline(4*1024**2+1)
                if not line:break
                rows+=1; total+=len(line)
                if len(line)>4*1024**2 or rows>count*2+1024 or total>1024**3:
                    raise ContractError('case archive scan cap exceeded')
                row=json.loads(line)
                if row['kind']=='frame':
                    if len(frames)>=count:raise ContractError('extra declared case frame')
                    frames.append(row['payload']['raw_text'])
                if row['kind']=='session_end':
                    if footer is not None:raise ContractError('duplicate archive footer')
                    footer=row['payload']
                if row['kind']=='connection_gap':gaps+=1
    if len(frames)!=count:raise ContractError('missing declared case frame')
    return frames,footer,gaps
