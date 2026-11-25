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
for name in ['index.html', 'app.js', 'styles.css', 'mobile.css', 'lr-frequency.js', 'lr-frequency.json', 'lr-audio.json', 'lr-frequency-source.pdf', '.nojekyll']:
    assert (root / name).is_file(), name
for path in root.rglob('*'):
    assert not path.is_symlink(), path
    if path.is_file():
        assert path.stat().st_size < 100 * 1024 ** 2, path
        assert not path.name.startswith('.env'), path
assert not (root / '.openai').exists()
assert not (root / '.sites-runtime').exists()
print(f'Verified {len(references)} local media references for GitHub Pages.')

# Every catalog link and source answer must resolve to an imported item.
data = json.loads((root / 'data.json').read_text())
tests = {test['id']: test for test in data['tests']}
question_ids = set()
weighted_total = 0
for catalog in data['catalogs'].values():
    assert len(catalog['testIds']) == len(set(catalog['testIds']))
    for test_id in catalog['testIds']:
        assert test_id in tests, test_id
        if catalog['section']:
            assert tests[test_id]['sections'].get(catalog['section'])
for test in tests.values():
    for section, questions in test['sections'].items():
        assert sum(q['weight'] for q in questions) == test['counts'][section]
        for q in questions:
            assert q['id'] not in question_ids, q['id']
            question_ids.add(q['id'])
            weighted_total += q['weight']
            assert set(q['correctChoices']) <= {c['key'] for c in q['choices']}, q['id']
assert weighted_total == data['meta']['totalItems']
assert len(question_ids) == data['meta']['questionGroups']
print(f'Verified {len(tests)} tests, {len(question_ids)} unique groups, {weighted_total} items.')
