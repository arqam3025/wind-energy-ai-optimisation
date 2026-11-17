"""Create auditable held-out copies; never modify frozen sources or outputs."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = 'b007aa5c57b5610ea75663d592b92816598c15658ed21bf0fcd99c107859895a'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def verify():
    path = ROOT / 'results/development_controller_freeze_manifest.json'
    assert digest(path) == EXPECTED, 'Freeze manifest mismatch'
    manifest = json.loads(path.read_text())
    entries = list(manifest['source_files'].values())
    for group in manifest['development_result_files'].values():
        entries.extend(group.values())
    for entry in entries:
        assert digest(ROOT / entry['path']) == entry['sha256'], entry['path']
    return manifest

def main():
    manifest = verify()
    for kind, key in [('fixed', 'fixed_controller'), ('adaptive_one_sided', 'adaptive_one_sided_controller')]:
        source = (ROOT / manifest['source_files'][key]['path']).read_text()
        source = source.replace('if not 1 <= block_id <= 18:', 'if block_id not in VALID_BLOCKS:')
        source = source.replace('raise ValueError("Block must be between 1 and 18.")', 'raise ValueError("Block is not eligible for held-out evaluation.")')
        source = source.replace('f"data/processed/controller_development_blocks/"\n    f"development_block_{block_id}.csv"', 'f"data/processed/"\n    f"evaluation_block_{block_id}.csv"')
        header = '''# Generated held-out adaptation. Optimisation and physical fallback preserved.
import os
from heldout_support import VALID_BLOCKS, preflight, output_directory
preflight()
'''
        source = header + source
        # Force frozen arguments, independent of caller defaults.
        source = source.replace('block_id = int(sys.argv[1])', 'sys.argv = [sys.argv[0], sys.argv[1], "0.5", "0.1", "1000", "100", "100"]\nblock_id = int(sys.argv[1])', 1)
        if kind == 'adaptive_one_sided':
            source = source.replace('    [calibration] + development_frames,', '    [calibration] + development_frames + heldout_history(),')
            source = source.replace('from heldout_support import VALID_BLOCKS, preflight, output_directory', 'from heldout_support import VALID_BLOCKS, preflight, output_directory, heldout_history')
            source = source.replace('"fallback_h1":', '"newest_residual_target": max(d["newest_target"] for d in uncertainty_diagnostics),\n        "fallback_h1":')
        start = source.index('output_dir = (')
        end = source.index('output_dir.mkdir', start)
        source = source[:start] + f'output_dir = output_directory("{kind}")\n' + source[end:]
        target = ROOT / f'scripts/frozen_{kind}_heldout.py'
        with target.open('x', encoding='utf-8') as handle:
            handle.write(source)
    print('Verified freeze and 59 referenced artifacts; generated two held-out implementations.')

if __name__ == '__main__':
    main()
