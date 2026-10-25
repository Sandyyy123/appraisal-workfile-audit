"""Create an entirely fictional workfile and export its original document bytes."""
import argparse
import hashlib
import json
from pathlib import Path
from workfile import export_workfile


def build_demo(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    records = []
    for ident, kind, text in [('assessment', 'assessor_card', 'Assessment card'),
                              ('tax_map', 'assessor_map', 'Tax parcel diagram — NOT a recorded plan')]:
        data = ('<svg xmlns="http://www.w3.org/2000/svg" width="900" height="600">'
                '<rect width="900" height="600" fill="white"/><text x="40" y="60" font-size="25">'
                'SYNTHETIC DEMO ONLY</text><text x="40" y="110" font-size="20">' + text +
                '</text><rect x="180" y="180" width="320" height="240" fill="#e3e8ed" stroke="black"/>'
                '<text x="190" y="470" font-size="18">Fictional parcel DEMO-001; no real property</text></svg>').encode()
        path = ident + '.svg'
        (output / path).write_bytes(data)
        records.append({'id': ident, 'kind': kind, 'status': 'available', 'path': path,
                        'sha256': hashlib.sha256(data).hexdigest(), 'source_url': 'https://example.invalid/synthetic/' + ident,
                        'retrieved_at': '2026-10-25T00:00:00Z'})
    records.extend([{'id': 'plan', 'kind': 'recorded_plan', 'status': 'manual_required'},
                    {'id': 'zoning', 'kind': 'zoning', 'status': 'manual_required'}])
    (output / 'records.json').write_text(json.dumps(records, indent=2))
    return export_workfile(output, records, output / 'workfile.zip')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='demo_output')
    args = parser.parse_args()
    print(json.dumps(build_demo(args.output), indent=2))
