"""Small source-preserving workfile exporter. No retrieval or legal conclusions."""
import hashlib
import json
import re
import zipfile
from pathlib import Path, PurePosixPath

KINDS = {'assessor_card', 'assessor_map', 'recorded_deed', 'recorded_plan', 'zoning', 'flood_map', 'permit'}


def validate(root, records):
    root = Path(root).resolve()
    seen = set()
    checked = []
    for original in records:
        r = dict(original)
        ident = r.get('id', '')
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', ident) or ident in seen:
            raise ValueError('Invalid or duplicate document id')
        seen.add(ident)
        if r.get('kind') not in KINDS:
            raise ValueError('Unknown document type')
        if r.get('status') not in {'available', 'manual_required', 'not_found'}:
            raise ValueError('Invalid retrieval status')
        if r.get('zoning_verified', False):
            raise ValueError('This demonstration cannot certify zoning conclusions')
        if r['status'] != 'available':
            if r.get('path') or r.get('sha256'):
                raise ValueError('Unavailable records cannot contain substitute files')
            checked.append((r, None))
            continue
        rel = PurePosixPath(r.get('path', ''))
        if not r.get('path') or rel.is_absolute() or '..' in rel.parts or '\\' in str(rel):
            raise ValueError('Unsafe document path')
        p = (root / str(rel)).resolve()
        if not p.is_relative_to(root) or not p.is_file():
            raise ValueError('Document outside source root or missing')
        if not r.get('source_url') or not r.get('retrieved_at'):
            raise ValueError('Missing provenance')
        data = p.read_bytes()
        if hashlib.sha256(data).hexdigest() != r.get('sha256'):
            raise ValueError('Original document hash mismatch')
        checked.append((r, data))
    return checked


def export_workfile(root, records, destination):
    checked = validate(root, records)
    manifest = {'synthetic_demo': True, 'documents': [r for r, _ in checked],
                'limitations': 'No live connectors, zoning certification, document authenticity verification or title opinion.'}
    # Exclusive creation prevents silently replacing a prior workfile.
    with zipfile.ZipFile(destination, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for r, data in checked:
            if data is not None:
                archive.writestr('originals/' + r['id'] + '/' + PurePosixPath(r['path']).name, data)
        archive.writestr('manifest.json', json.dumps(manifest, indent=2))
    return {'available': sum(data is not None for _, data in checked),
            'unresolved': sum(data is None for _, data in checked), 'destination': str(destination)}
