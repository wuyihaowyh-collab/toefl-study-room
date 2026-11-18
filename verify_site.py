"""Verify static assets can be deployed under a GitHub Pages repository path."""
import json
from pathlib import Path
from urllib.parse import urlsplit

root = Path(__file__).resolve().parent / 'site'
references = set()


def inspect(value):
    if isinstance(value, dict):
        for item in value.values():
            inspect(item)
    elif isinstance(value, list):
        for item in value:
            inspect(item)
    elif isinstance(value, str) and value.startswith('media/'):
        references.add(value)


for name in ['data.json', 'lr-audio.json']:
    inspect(json.loads((root / name).read_text()))
for value in references:
    target = (root / urlsplit(value).path).resolve()
    assert target.is_relative_to(root.resolve()) and target.is_file(), value
for name in ['index.html', 'app.js', 'styles.css', 'lr-frequency.js', 'lr-frequency.json', 'lr-audio.json', 'lr-frequency-source.pdf', '.nojekyll']:
    assert (root / name).is_file(), name
for path in root.rglob('*'):
    assert not path.is_symlink(), path
    if path.is_file():
        assert path.stat().st_size < 100 * 1024 ** 2, path
        assert not path.name.startswith('.env'), path
assert not (root / '.openai').exists()
assert not (root / '.sites-runtime').exists()
print(f'Verified {len(references)} local media references for GitHub Pages.')
