"""Normalize source question text without inventing answers."""
import re

def text(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return '\n'.join(filter(None, (text(v) for v in value)))
    if isinstance(value, dict):
        if 'text' in value:
            return str(value['text'])
        if 'runs' in value:
            return ''.join(text(v) for v in value['runs'])
        return '\n'.join(text(value[k]) for k in ['heading', 'items', 'paragraphs', 'blocks'] if k in value)
    return ''


def mask_passage(q):
    source = q.get('stimulusText') or ''
    out, cursor, matches = [], 0, []
    for index, slot in enumerate(q.get('slots') or [], 1):
        word = slot.get('originalWord') or ''
        found = re.search(r'\b' + re.escape(word) + r'\b', source[cursor:], re.I)
        if not found:
            raise ValueError('Cannot locate fill slot: ' + q['id'] + ' / ' + word)
        start, end = cursor + found.start(), cursor + found.end()
        out.append(source[cursor:start])
        missing = slot.get('missingLength') or len(slot.get('acceptedAnswer') or '')
        display = f"[{index}] {slot.get('visiblePrefix', '')}{'_' * missing}{slot.get('visibleSuffix', '')}"
        out.append(display)
        matches.append({'slot': slot['key'], 'word': word, 'start': start, 'end': end})
        cursor = end
    out.append(source[cursor:])
    return ''.join(out), matches


def answer(q):
    scoring = q.get('scoring') or {}
    choices = {c['key']: c for c in q.get('choices') or []}
    if q['questionType'] == 'complete_words':
        return '\n'.join(f"{i}. {s.get('acceptedAnswer') or s.get('correctAnswer')} → {s.get('originalWord')}" for i, s in enumerate(scoring.get('slots') or q['slots'], 1))
    if scoring.get('correctChoiceKeys'):
        return '\n'.join(f"{chr(65 + list(choices).index(k))}. {choices[k]['label']}" for k in scoring['correctChoiceKeys'])
    if scoring.get('answerSentence'):
        return scoring['answerSentence']
    if q['questionType'] == 'ordered_tokens' and scoring.get('acceptedOrders'):
        order = scoring['acceptedOrders'][0]
        labels = {t['key']: t['label'] for t in q.get('tokens') or scoring.get('tokens') or []}
        targets = q.get('targets') or []
        template = re.sub(r'\[\[IMAGE:.*?\]\]', '', q.get('promptTemplate') or '')
        def fill(match):
            index = int(match.group(1)) - 1
            token = labels[order[index]]
            if index < len(targets) and targets[index].get('capitalizeFirstLetter'):
                token = token[:1].upper() + token[1:]
            return token
        if template:
            sentence = re.sub(r'\[\[BLANK:(\d+):[^\]]+\]\]', fill, template)
            return re.sub(r'\s+([.,?!;:])', r'\1', re.sub(r'\s+', ' ', sentence)).strip()
        return ' '.join(labels[key] for key in order)
    if q['questionType'] == 'repeat_response':
        return q.get('referenceText') or scoring.get('modelAnswer') or ''
    return scoring.get('sampleEssay') or scoring.get('modelAnswer') or ''


def question_content(q):
    out = []
    for key in ['articleTitle', 'promptText', 'leadText', 'stimulusText', 'imageText', 'paragraphs']:
        value = text(q.get(key))
        if key == 'stimulusText' and q.get('paragraphs'):
            continue
        if key == 'paragraphs' and q.get('paragraphs'):
            value = '\n\n'.join(f'Paragraph {i}\n{text(paragraph)}' for i, paragraph in enumerate(q['paragraphs'], 1))
            value = re.sub(r'\{\{MARK:(\d+)\}\}', r'【位置 \1】', value)
        if key == 'stimulusText' and q['questionType'] == 'complete_words':
            value = mask_passage(q)[0]
        if value and value not in [v for _, v in out]:
            # leadText often duplicates promptText.
            out.append((key, value))
    if q.get('emailMeta'):
        out.append(('email', 'To: ' + q['emailMeta'].get('to', '') + '\nSubject: ' + q['emailMeta'].get('subject', '')))
    if q.get('professorPrompt') and q['professorPrompt'] not in '\n'.join(v for _, v in out):
        out.append(('professor', (q.get('professorName') or 'Professor') + ': ' + q['professorPrompt']))
    for post in q.get('discussionPosts') or []:
        out.append(('post', post.get('name', '') + ': ' + post.get('text', '')))
    if q.get('promptTemplate'):
        template = re.sub(r'\[\[IMAGE:.*?\]\]', '', q['promptTemplate'])
        template = re.sub(r'\[\[BLANK:(\d+):[^\]]+\]\]', r'[\1] ______', template)
        out.append(('template', template.strip()))
    if q.get('tokens'):
        out.append(('tokens', '词块：' + ' / '.join(t['label'] for t in q['tokens'])))
    if q.get('highlightTerms') or q.get('highlightTerm'):
        words = q.get('highlightTerms') or [q['highlightTerm']]
        out.append(('highlights', '题目中标记的词语：' + ', '.join(words)))
    return out


def email_task(q):
    """Keep the source email scenario, task bullets and closing instructions distinct."""
    if not q.get('emailMeta'):
        return None
    blocks = q.get('leftBlocks') or []
    bullet_index = next((i for i, block in enumerate(blocks) if block.get('type') == 'bullets'), None)
    if bullet_index is None:
        return None
    task = blocks[bullet_index]
    return {
        'scenario': '\n\n'.join(text(block) for block in blocks[:bullet_index]),
        'heading': text(task.get('heading')),
        'requirements': [text(item) for item in task.get('items') or []],
        'note': '\n\n'.join(text(block) for block in blocks[bullet_index + 1:]),
        'translation': q.get('leftBlocksTextZh') or '',
    }


def translation(q):
    values = []
    for key in ['promptTextZh', 'leadTextZh', 'stimulusTextZh', 'imageTextZh', 'paragraphsZh', 'leftBlocksTextZh', 'professorPromptZh']:
        value = text(q.get(key))
        if value and value not in values:
            values.append(value)
    values.extend(post.get('name', '') + ': ' + post['textZh'] for post in q.get('discussionPosts') or [] if post.get('textZh'))
    return '\n\n'.join(values)


def explanations(q):
    s = q.get('scoring') or {}
    values = []
    for key in ['explanation', 'correctOrderExplanation', 'translationZh', 'sentenceType']:
        if s.get(key):
            values.append(s[key])
    for i, c in enumerate(q.get('choices') or []):
        if c.get('reviewExplanationZh'):
            values.append(f"{chr(65 + i)}. {c['reviewExplanationZh']}")
    return '\n\n'.join(values)


