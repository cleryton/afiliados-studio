"""Bounded editorial decisions for future local films, never a virality score."""
from copy import deepcopy
import hashlib
import json
import math
import re
import statistics
import creative

VERSION = 'director-v1'


def validate_metadata(meta):
    report=meta.get('director') or {}
    scenes=[s for s in meta.get('scenes',[]) if s.get('visual')!='offer']
    digest=hashlib.sha256(json.dumps(scenes,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    if (report.get('version')!=VERSION or report.get('status')!='render_checked' or
            report.get('script_sha256')!=digest or report.get('issues')!=[] or not report.get('standalone_payoff')):
        raise ValueError('O capítulo precisa passar pela revisão editorial antes de liberar o envio.')
    return report


def policy(posts=(), now=None):
    """Only mature, sufficiently observed clips may suggest one pacing experiment.

    Thresholds are local editorial heuristics, not TikTok algorithm thresholds.
    Samples use the age at observation, never the age of a stale snapshot today.
    """
    usable = []
    from datetime import datetime
    for post in posts:
        try:
            observed = datetime.fromisoformat(post['observed_at'])
            published = datetime.fromisoformat(post['published_at'])
            if observed.tzinfo is None or published.tzinfo is None or observed < published:
                continue
            if now and (observed > now or (now - observed).total_seconds() > 14 * 86400):
                continue
            age = (observed - published).total_seconds() / 3600
            views, duration, watch = post['views'], post['duration'], post['average_watch']
            if (age < 24 or isinstance(views, bool) or not isinstance(views, int) or views < 100 or
                    any(isinstance(n, bool) or not isinstance(n, (int, float)) or not math.isfinite(n)
                        for n in (duration, watch)) or duration <= 0 or watch < 0):
                continue
            usable.append({'url':post['url'], 'ratio':min(1, watch / duration)})
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
    # Distinct URLs only; repeated cumulative snapshots are not independent clips.
    usable = list({p['url']:p for p in usable}.values())
    enough = len(usable) >= 3
    compact = enough and statistics.median(p['ratio'] for p in usable) < .4
    return {'version':VERSION, 'mode':'compact' if compact else 'balanced',
            'shot_seconds':2.5 if compact else 3.25, 'speech_rate':0,
            'sample_videos':len(usable), 'has_evidence':enough,
            'reason':('Teste editorial: reduzir a duração dos planos nos próximos vídeos; os dados não provam a causa da retenção.'
                      if compact else 'Ritmo inicial de teste; ainda não há evidência suficiente para mudar a montagem.'
                      if not enough else 'Manter o ritmo e observar novos vídeos; não há abertura ou horário vencedor comprovado.')}


def plan(story, feedback=None):
    selected = deepcopy(story)
    settings = dict(feedback or policy())
    options = selected.pop('hooks', [])
    if options:
        # Authored alternatives only: never manufacture a promise or fact.
        hook = options[0]
        if len(hook.split())>18:hook=min(options,key=lambda h:len(h.split()))
        selected['scenes'][0]['text'] = hook
    scenes = selected['scenes']
    issues = []
    if not 4 <= len(scenes) <= 8:issues.append('Use de quatro a oito cenas com progressão.')
    if len(scenes[0]['text'].split()) > 18:issues.append('Encurte a abertura para até dezoito palavras.')
    texts = [' '.join(s['text'].lower().split()) for s in scenes]
    if len(texts) != len(set(texts)):issues.append('Há uma cena repetida no roteiro.')
    if any(not t or len(t.split()) > 38 for t in texts):issues.append('Há uma cena vazia ou longa demais.')
    if scenes[-1].get('beat') != 'payoff':issues.append('O episódio precisa entregar um desfecho próprio.')
    if [s.get('beat') for s in scenes[:1]] != ['hook']:issues.append('A primeira cena precisa apresentar o conflito.')
    if any(s['visual'] not in ('drawing','room','building','key','door') for s in scenes):
        issues.append('O roteiro pede uma cena 3D que ainda não existe.')
    if any(re.search(r'curta.{0,15}compartilhe|comente.{0,15}(sim|eu quero)|garant.{0,10}(renda|lucro)', t) for t in texts):
        issues.append('Remova pedidos artificiais de interação ou promessas financeiras.')
    if issues:raise ValueError(' '.join(issues))
    digest = hashlib.sha256(json.dumps(scenes,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    return selected, {'version':VERSION, 'policy':settings, 'script_sha256':digest,
                      'hook':scenes[0]['text'], 'standalone_payoff':True, 'issues':[],
                      'status':'script_checked', 'performance_prediction':None}


def timed_cards(texts, durations, timing_rows):
    """Use actual SAPI word starts when complete; otherwise retain labeled estimates."""
    if len(texts)!=len(durations):raise ValueError('Durações e cenas não correspondem.')
    cards = []
    methods = []
    elapsed = 0
    for index, (text, duration) in enumerate(zip(texts, durations)):
        fallback = creative.subtitle_segments([text],[duration])
        rows = timing_rows[index] if index < len(timing_rows) else []
        starts = [0]
        valid = bool(rows)
        try:
            previous_time = -1
            previous_position = -1
            for row in rows:
                moment, position = row['seconds'], row['position']
                if (isinstance(moment,bool) or not isinstance(moment,(int,float)) or not math.isfinite(moment) or
                        moment < 0 or moment >= duration or moment < previous_time or type(position) is not int or
                        position < 0 or position <= previous_position):
                    raise ValueError()
                previous_time, previous_position = moment, position
            # CharacterPosition is UTF-16; Python offsets count Unicode code points.
            chunks = creative.subtitle_chunks(text)
            if not rows or rows[0]['position']!=0:raise ValueError()
            last_word=list(re.finditer(r'\S+',text))[-1]
            if rows[-1]['position'] < len(text[:last_word.start()].encode('utf-16-le'))//2:raise ValueError()
            cursor = len(chunks[0].replace('\n',' '))
            for chunk in chunks[1:]:
                match = re.search(r'\s+'.join(re.escape(w) for w in chunk.split()), text[cursor:])
                if not match:raise ValueError()
                offset = cursor + match.start()
                position = len(text[:offset].encode('utf-16-le')) // 2
                word = next((r for r in rows if r['position'] >= position), None)
                if not word or word['position'] != position:raise ValueError()
                frame = round(word['seconds'] * 24)
                if frame <= starts[-1] or frame >= round(duration*24):raise ValueError()
                starts.append(frame)
                cursor = offset + len(match.group())
            if len(starts) != len(fallback):raise ValueError()
        except (KeyError, TypeError, ValueError, StopIteration):
            valid = False
        if valid:
            for i, card in enumerate(fallback):
                card['start'] = starts[i] / 24
                card['end'] = starts[i+1] / 24 if i+1 < len(starts) else round(duration*24)/24
        methods.append('sapi_word_boundaries' if valid else 'estimated_by_text')
        for card in fallback:
            cards.append({**card,'scene':index,'start':card['start']+elapsed,'end':card['end']+elapsed})
        elapsed += round(duration*24)/24
    return cards, methods


def review(report, durations, cards, voice):
    """Stop autonomous release on measurable failures, without claiming artistic proof."""
    issues = []
    if len(voice)!=len(durations) or not all(voice):issues.append('Falta narração em pelo menos uma cena.')
    if not cards:issues.append('Faltam as legendas da montagem.')
    elif (abs(cards[0]['start'])>1/24 or abs(cards[-1]['end']-sum(durations))>1/24 or
          any(abs(a['end']-b['start'])>1/24 for a,b in zip(cards,cards[1:]))):
        issues.append('As legendas não cobrem a linha de tempo da montagem.')
    if not 25 <= sum(durations) <= 105:issues.append('A montagem deve ter entre 25 e 105 segundos.')
    if durations[0] > 7:issues.append('A abertura excedeu sete segundos; precisa ser reescrita.')
    if any(c['end'] <= c['start'] or len(c['text'].replace('\n',' ')) / (c['end']-c['start']) > 32 for c in cards):
        issues.append('Uma legenda está rápida demais para leitura confortável.')
    if issues:raise ValueError(' '.join(issues))
    return {**report, 'status':'render_checked', 'duration':round(sum(durations),3),
            'hook_duration':durations[0], 'captions_checked':len(cards), 'issues':[]}
