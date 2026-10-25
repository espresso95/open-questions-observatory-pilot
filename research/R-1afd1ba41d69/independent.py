import json
from pathlib import Path
data=json.loads(Path(__file__).with_name('results.json').read_text())
import json,time
from sympy import isprime
from sympy.combinatorics import Permutation,PermutationGroup
start=time.monotonic();accepted=0;proper=0
for row in data['rows']:
 for record in row['entries']:
  n,m,k=(record[x] for x in ('n','m','k'))
  gs=[Permutation(list(range(q-1,-1,-1))+list(range(q,n))) for q in (n,m,k)]
  group=PermutationGroup(gs)
  if record['classification']=='symmetric':
   assert group.is_primitive(randomized=False)
   assert any(g.is_odd for g in gs)
   word=Permutation(list(range(n)))
   for i in record['word']:word=word*gs[i]
   isolated=word**record['exponent'];cs=isolated.cyclic_form
   assert len(cs)==1 and len(cs[0])==record['prime'] and isprime(len(cs[0])) and len(cs[0])<=n-3
   accepted+=1
  elif record['classification']=='proper':
   if record['reason']=='intransitive':assert not group.is_transitive()
   elif record['reason']=='imprimitive':assert not group.is_primitive(randomized=False)
   elif record['reason']=='all_generators_even':assert all(g.is_even for g in gs)
   else:raise ValueError('Unknown obstruction')
   proper+=1
  else:raise ValueError('Unvalidated unknown')
print(json.dumps({'all_certificates_valid':True,'symmetric_certificates_checked':accepted,'proper_group_obstructions_checked':proper,'independent_library':'SymPy 1.14.0','primitive_test':'deterministic stabilizer and minimal-block method','cycle_word_check':'independent SymPy permutation multiplication and exponentiation','theorem':'Jordan prime cycle theorem plus odd generator','general_conjecture_proved':False,'wall_seconds':time.monotonic()-start}))
