import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from workfile import export_workfile, validate


class WorkfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'map.txt').write_bytes(b'Original synthetic map\r\n')
        self.row = {'id': 'map', 'kind': 'assessor_map', 'status': 'available', 'path': 'map.txt',
                    'sha256': hashlib.sha256((self.root / 'map.txt').read_bytes()).hexdigest(),
                    'source_url': 'https://example.invalid/map', 'retrieved_at': '2026-10-25T00:00:00Z'}

    def test_original_bytes_preserved(self):
        export_workfile(self.root, [self.row], self.root / 'out.zip')
        with zipfile.ZipFile(self.root / 'out.zip') as z:
            self.assertEqual(z.read('originals/map/map.txt'), (self.root / 'map.txt').read_bytes())

    def test_missing_plan_not_replaced_by_assessor_map(self):
        rows = [self.row, {'id': 'plan', 'kind': 'recorded_plan', 'status': 'manual_required'}]
        result = export_workfile(self.root, rows, self.root / 'out.zip')
        self.assertEqual((result['available'], result['unresolved']), (1, 1))
        with zipfile.ZipFile(self.root / 'out.zip') as z:
            manifest = json.loads(z.read('manifest.json'))
            self.assertEqual(manifest['documents'][1], rows[1])
            self.assertFalse(any('/plan/' in name for name in z.namelist()))

    def test_tampering_rejected_before_output_creation(self):
        (self.root / 'map.txt').write_bytes(b'Changed')
        with self.assertRaises(ValueError):
            export_workfile(self.root, [self.row], self.root / 'out.zip')
        self.assertFalse((self.root / 'out.zip').exists())

    def test_duplicate_id(self):
        with self.assertRaises(ValueError): validate(self.root, [self.row, self.row])

    def test_traversal(self):
        with self.assertRaises(ValueError): validate(self.root, [dict(self.row, path='../map.txt')])

    def test_absolute_path(self):
        with self.assertRaises(ValueError): validate(self.root, [dict(self.row, path='/etc/passwd')])

    def test_backslash_path(self):
        with self.assertRaises(ValueError): validate(self.root, [dict(self.row, path='..\\map.txt')])

    def test_symlink_escape(self):
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / 'outside.txt'; target.write_text('outside')
            (self.root / 'link').symlink_to(target)
            with self.assertRaises(ValueError): validate(self.root, [dict(self.row, path='link')])

    def test_unverified_zoning(self):
        with self.assertRaises(ValueError): validate(self.root, [dict(self.row, zoning_verified=True)])

    def test_pending_cannot_claim_file(self):
        with self.assertRaises(ValueError): validate(self.root, [dict(self.row, status='manual_required')])

    def test_missing_provenance(self):
        with self.assertRaises(ValueError): validate(self.root, [dict(self.row, source_url='')])

    def test_existing_export_preserved(self):
        p = self.root / 'out.zip'; p.write_bytes(b'Existing workfile')
        with self.assertRaises(FileExistsError): export_workfile(self.root, [self.row], p)
        self.assertEqual(p.read_bytes(), b'Existing workfile')


if __name__ == '__main__': unittest.main()
