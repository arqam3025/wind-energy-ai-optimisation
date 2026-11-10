"""Preservation fixtures are isolated temporary files, never frozen artifacts."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from publication_v2.integrity import PreservationError, capture_baseline, digest, inside, verify_preservation


class PreservationTests(unittest.TestCase):
    def test_junction_ancestor_refused_even_when_it_resolves_inside_repository(self):
        root=Path.cwd().resolve()
        with patch.object(Path,'is_junction',autospec=True,side_effect=lambda p:p==root/'data'):
            with self.assertRaisesRegex(PreservationError,'junction'): inside(root,'data/raw/T1.csv')

    def test_snapshot_detects_change_and_missing_in_ignored_research_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); path=root/'results/original.csv';path.parent.mkdir();path.write_text('original')
            baseline=capture_baseline(root);verify_preservation(root,baseline)
            path.write_text('altered')
            with self.assertRaises(PreservationError):verify_preservation(root,baseline)
            path.unlink()
            with self.assertRaises(PreservationError):verify_preservation(root,baseline)

    def test_traversal_windows_drive_and_empty_baseline_rejected(self):
        for name in ('../outside','C:\\outside','/outside'):
            with self.subTest(name=name),self.assertRaises(PreservationError):inside(Path.cwd(),name)
        with self.assertRaises(PreservationError):verify_preservation(Path.cwd(),{'files':{}})

    def test_new_extension_excluded_from_protected_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'results').mkdir();(root/'results/frozen').write_text('protected')
            (root/'publication_v2').mkdir();(root/'publication_v2/new').write_text('new')
            self.assertEqual(set(capture_baseline(root)['files']),{'results/frozen'})

    def test_preservation_survives_python_optimized_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path=root/'protected';path.write_text('original')
            baseline={'files':{'protected':digest(path)}};path.write_text('corrupt')
            code='from pathlib import Path; from publication_v2.integrity import verify_preservation; verify_preservation(Path('+repr(tmp)+'),'+repr(baseline)+')'
            result=subprocess.run([sys.executable,'-B','-O','-c',code],capture_output=True,text=True,cwd=Path(__file__).resolve().parents[2])
            self.assertNotEqual(result.returncode,0)
            self.assertIn('Protected artifact changed',result.stderr)


if __name__=='__main__':unittest.main()
