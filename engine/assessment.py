"""Evidence and feasibility checks shared by question adapters."""
from .common import PRIVATE,digest,read_json

def check_evidence(question):
    if not question.get('source_evidence'):raise ValueError('Source evidence required')
    for e in question['source_evidence']:
        path=(PRIVATE/e['text_path']).resolve()
        if not path.is_relative_to(PRIVATE.resolve()) or path.stat().st_size>10000000:raise ValueError('Evidence path outside private source store')
        text=path.read_text()
        if not isinstance(e['start'],int) or not isinstance(e['end'],int) or not 0<=e['start']<e['end']<=len(text):raise ValueError('Invalid evidence offsets')
        if digest(text.encode())!=e['text_sha256'] or text[e['start']:e['end']]!=e['quote']:
            raise ValueError('Evidence hash or exact quotation mismatch')
    return True

def assess(question):
    check_evidence(question)
    gates=question['assessment']['gates']
    eligible=all(gates.values()) and question['statuses']['feasibility']=='pilot_ready'
    return {'eligible':eligible,'failed_gates':[k for k,v in gates.items() if not v],
      'meaning':'Readiness is distinct from scientific value, novelty and chance of a positive finding'}

def admit(question):
    result=assess(question)
    if not result['eligible']:raise ValueError('Dispatch blocked: '+', '.join(result['failed_gates']))
    if question['statuses']['literature'] not in ('no_answer_found','partial_answer'):raise ValueError('Literature check required')
    return result
