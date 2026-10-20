#!/usr/bin/env python3
"""Decode the owner's DOS resources and record evidence; writes outside the checkout by default."""
import argparse
import hashlib
import json
from pathlib import Path
from lzhuf import decompress


def recover(source, output):
    source, output = Path(source), Path(output)
    if source.resolve() == output.resolve():
        raise ValueError('output must differ from original resource directory')
    output.mkdir(parents=True, exist_ok=True)
    manifest = []
    for path in sorted(source.iterdir()):
        if not path.is_file() or path.suffix.lower() in ('.json', '.exe'):
            continue
        packed = path.read_bytes()
        plain = packed if packed.startswith(b'FORM') or path.name in ('DISK1', 'DISK2') else decompress(packed)
        kind = plain[8:12].decode('ascii') if plain.startswith(b'FORM') else 'raw'
        if kind != 'raw' and int.from_bytes(plain[4:8], 'big') + 8 != len(plain):
            raise ValueError(f'{path.name}: incorrect IFF FORM length')
        (output / path.name).write_bytes(plain)
        manifest.append(dict(file=path.name, packed_size=len(packed), size=len(plain), format=kind,
                             source_sha256=hashlib.sha256(packed).hexdigest(),
                             decoded_sha256=hashlib.sha256(plain).hexdigest()))
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dos', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    rows = recover(args.dos, args.out)
    print(f'Decoded/validated {len(rows)} files to {args.out}')
