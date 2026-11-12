"""Read-only checks for the documentation/design stage; not a security audit."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
design = ROOT / 'Медицинский-портал-FamilyDent'
manifest = json.loads((design / 'DESIGN-MANIFEST.json').read_text())
for name in manifest['sourceFiles']['all']:
    assert (design / name).is_file(), f'Missing design source: {name}'
for path in design.glob('*.json'):
    json.loads(path.read_text())
audit = (ROOT / 'familydent_imaging_codex/docs/PHASE_0_AUDIT.md').read_text()
entries = re.findall(r'^([a-f0-9]{64})  (.+)$', audit, re.M)
assert len(entries) == 19, 'Missing design baseline checksums'
for digest, name in entries:
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
for name in filter(None, tracked):
    path = Path(name)
    assert path.suffix.lower() not in {'.dcm', '.dicom', '.zip', '.pem', '.key', '.dump', '.bak'}, f'Forbidden artifact: {name}'
    assert not (path.name.startswith('.env') and path.name != '.env.example'), name
print('PASS: manifest, JSON, 19 immutable design sources, tracked artifact policy')
print('Secret scanning and application tests will be added with application tooling.')
