#!/usr/bin/env python3
"""Verify the completed intro has not changed while gameplay evolves."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def verify(content=None):
    contract=json.loads((ROOT/'docs/INTRO_FROZEN.json').read_text())
    for name,expected in contract['sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=expected:
            raise ValueError('frozen intro changed: '+name)
    entry=contract['entry_prg']
    if hashlib.sha256((ROOT/entry['path']).read_bytes()).hexdigest()!=entry['sha256']:
        raise ValueError('frozen intro entry PRG changed')
    if content is not None:
        for name,expected in contract['private_content_sha256'].items():
            if hashlib.sha256((Path(content)/name).read_bytes()).hexdigest()!=expected:
                raise ValueError('frozen intro content changed: '+name)
    return len(contract['sha256'])
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--content',type=Path);a=p.parse_args()
    print(f'Frozen intro: {verify(a.content)} source/assets and entry PRG unchanged'+('; private content checked'if a.content else''))
