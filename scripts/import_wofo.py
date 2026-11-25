"""Import every standard Wofo TOEFL test definition and all three catalogs."""
import argparse
import collections
import json
import re
from pathlib import Path
from normalize_questions import answer, question_content, explanations, translation, email_task

PROJECT = Path(__file__).resolve().parent.parent
DEST = PROJECT / 'site'
SECTIONS = ['reading', 'listening', 'speaking', 'writing']
MEDIA_RE = re.compile(r'^/toefl/[^\s]+\.(?:m4a|mp3|wav|webp|png|jpe?g|svg|mp4)$', re.I)


def media_paths(value):
    found = []
    def walk(v):
        if isinstance(v, dict):
            for child in v.values(): walk(child)
        elif isinstance(v, list):
            for child in v: walk(child)
        elif isinstance(v, str) and MEDIA_RE.match(v):
            if any(part in v for part in ['volume_loop', 'beep-module', 'orb-texture']): return
            local = 'media' + v
            url = local if (DEST / local).is_file() else 'https://wofo.cc' + v
            if url not in found: found.append(url)
    walk(value)
    return found


def prepare(raw_path):
    raw = json.loads(Path(raw_path).read_text())
    assert not raw.get('errors'), raw.get('errors')
    assert {t['testId'] for t in raw['tests']} == {f'mock-{i}' for i in range(1, 71)}
    tests, seen_ids, all_media, missing = [], set(), set(), []
    weighted = collections.Counter()
    for original in raw['tests']:
        definition = original['definition']
        number = int(original['testId'].split('-')[-1])
        by_id = {q['id']: q for q in definition['questions']}
        test = {'id': original['testId'], 'number': number, 'kind': 'full' if number <= 50 else 'new',
                'counts': definition['sectionQuestionCounts'], 'sections': {}}
        for section in SECTIONS:
            if not definition['sectionQuestionCounts'].get(section): continue
            context, items, index = None, [], 0
            for event in definition['flow']:
                if event['section'] != section: continue
                if event['kind'] in ['media', 'scenario']:
                    data = event.get('data') or {}
                    visual = data.get('visual') or {}
                    context = {'text': data.get('title') or visual.get('directionText') or visual.get('promptText') or '',
                               'media': media_paths(data)}
                if event['kind'] != 'question': continue
                q = by_id[event['questionId']]
                if q.get('emailMeta'):
                    q['emailMeta'] = {key: value or '' for key, value in q['emailMeta'].items()}
                for post in q.get('discussionPosts') or []:
                    post['name'] = post.get('name') or ''
                    post['text'] = post.get('text') or ''
                assert q['id'] not in seen_ids, q['id']
                seen_ids.add(q['id'])
                scoring = q.get('scoring') or {}
                if q['questionType'] == 'complete_words':
                    for slot in (q.get('slots') or []) + (scoring.get('slots') or []):
                        slot['visiblePrefix'] = slot.get('visiblePrefix') or ''
                        slot['visibleSuffix'] = slot.get('visibleSuffix') or ''
                        slot['acceptedAnswer'] = slot.get('acceptedAnswer') or slot.get('correctAnswer') or ''
                        slot['missingLength'] = slot.get('missingLength') or len(slot['acceptedAnswer'])
                        slot['originalWord'] = slot.get('originalWord') or slot.get('visiblePrefix', '') + slot['acceptedAnswer'] + slot['visibleSuffix']
                weight = len(q.get('slots') or []) if q['questionType'] == 'complete_words' else 1
                label = str(index + 1) if weight == 1 else f'{index + 1}–{index + weight}'
                index += weight
                weighted[section] += weight
                content = dict(question_content(q))
                passage = '\n\n'.join(content[k] for k in ['stimulusText', 'imageText', 'paragraphs'] if content.get(k))
                choice_keys={c['key'] for c in q.get('choices') or []}
                invalid_choice=any(k not in choice_keys for k in scoring.get('correctChoiceKeys') or [])
                if any(k not in choice_keys for k in scoring.get('correctChoiceKeys') or []):
                    scoring['correctChoiceKeys']=[]
                    missing.append(q['id'] + ': source answer refers to missing choice')
                correct = '原站答案指向缺失的选项，本题暂不自动评分。' if invalid_choice else answer(q)
                if not correct: missing.append(q['id'])
                item = {
                    'id': q['id'], 'label': label, 'weight': weight, 'module': q['moduleKey'],
                    'type': q['questionType'], 'title': q.get('articleTitle') or '',
                    'prompt': q.get('promptText') or '', 'promptZh': q.get('promptTextZh') or '',
                    'passage': passage, 'content': content, 'choices': q.get('choices') or [],
                    'tokens': q.get('tokens') or [],
                    'slots': [{k: slot.get(k) for k in ['key', 'order', 'visiblePrefix', 'visibleSuffix', 'missingLength', 'acceptedAnswer', 'originalWord']} for slot in q.get('slots') or []],
                    'correctChoices': scoring.get('correctChoiceKeys') or [], 'acceptedOrders': scoring.get('acceptedOrders') or [],
                    'answer': correct or '原站暂未提供参考答案。', 'explanation': explanations(q), 'translation': translation(q),
                    'transcript': q.get('reviewTranscriptText') or '',
                    'transcriptZh': q.get('reviewTranscriptZh') or q.get('referenceTextZh') or '',
                    'media': media_paths({k: v for k, v in q.items() if k != 'scoring'}),
                    'answerMedia': media_paths(scoring), 'context': context,
                    'listenRespond': section == 'listening' and bool(q.get('pageAudioSrc')) and q.get('reviewTranscriptText') == q.get('promptText'),
                    'posts': q.get('discussionPosts') or [], 'emailMeta': q.get('emailMeta'),
                    **({'emailTask': email_task(q)} if q.get('emailMeta') else {}),
                    'responseSeconds': q.get('responseSeconds'), 'timeLimitSeconds': q.get('timeLimitSeconds')}
                for slot in item['slots']:
                    assert slot['missingLength'] == len(slot['acceptedAnswer']), (q['id'], slot)
                all_media.update(item['media'] + item['answerMedia'] + (context or {}).get('media', []))
                items.append(item)
            assert index == test['counts'][section], (test['id'], section, index)
            test['sections'][section] = items
        assert len(by_id) == sum(len(items) for items in test['sections'].values())
        tests.append(test)
    assert len(seen_ids) == sum(len(t['definition']['questions']) for t in raw['tests'])
    assert sum(weighted.values()) == sum(sum(t['definition']['sectionQuestionCounts'].values()) for t in raw['tests'])
    # Keep source omissions visible; never invent missing answers.
    catalogs = {
        'full': {'title': '完整模考', 'testIds': [f'mock-{i}' for i in range(50, 0, -1)], 'section': None, 'range': 'Mock 1—50'},
        'speaking': {'title': '口语新题', 'testIds': [f'mock-{i}' for i in range(70, 0, -1)], 'section': 'speaking', 'range': 'Mock 1—70'},
        'writing': {'title': '写作新题', 'testIds': [f'mock-{i}' for i in range(70, 0, -1)], 'section': 'writing', 'range': 'Mock 1—70'}}
    manifest = {'tests': tests, 'catalogs': catalogs,
                'meta': {'retrievedAt': raw['retrievedAt'], 'totalItems': sum(weighted.values()), 'questionGroups': len(seen_ids),
                         'sectionItems': dict(weighted), 'ordering': '原站编号倒序',
                         'localMedia': sum(not u.startswith('https:') for u in all_media),
                         'onlineMedia': sum(u.startswith('https:') for u in all_media)}}
    (DEST / 'data.json').write_text(json.dumps(manifest, ensure_ascii=False, separators=(',', ':')))
    (DEST / 'catalog-summary.json').write_text(json.dumps({'catalogs': catalogs, 'meta': manifest['meta']}, ensure_ascii=False, indent=2))
    validation = {'sets': {'full': 50, 'speaking': 70, 'writing': 70}, 'definitions': len(tests), 'questionGroups': len(seen_ids),
                  'totalItems': sum(weighted.values()), 'sectionItems': dict(weighted), 'missingAnswers': missing,
                  'media': sorted(all_media), 'originalSource': str(Path(raw_path).resolve())}
    (PROJECT / '.import-runtime').mkdir(exist_ok=True)
    (PROJECT / '.import-runtime/content-validation.json').write_text(json.dumps(validation, ensure_ascii=False, indent=2))
    print(json.dumps({k: v for k, v in validation.items() if k not in ['media', 'originalSource']}, ensure_ascii=False))
    print('Data bytes:', (DEST / 'data.json').stat().st_size, 'media:', len(all_media))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('raw_json', help='The authenticated export JSON, with mock-1 through mock-70.')
    args = parser.parse_args()
    prepare(args.raw_json)
