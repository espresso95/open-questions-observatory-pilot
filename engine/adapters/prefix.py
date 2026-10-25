"""Exact finite certificates; failed certificate search is unknown, never a counterexample.

Jordan's theorem: a primitive degree-n group containing a prime p-cycle with
p <= n-3 contains A_n. An odd generator then establishes S_n. Randomness is
used only to locate a finite word; every accepted word is checked exactly.
"""
import json
import math
import random
import sys


def generators(n,m,k):
    return [tuple(range(q-1,-1,-1))+tuple(range(q,n)) for q in (n,m,k)]

def compose(a,b):return tuple(a[b[i]] for i in range(len(a)))

def cycles(p):
    seen=set();out=[]
    for i in range(len(p)):
        if i in seen:continue
        c=[];x=i
        while x not in seen:seen.add(x);c.append(x);x=p[x]
        if x!=i:raise ValueError('Not a permutation')
        out.append(c)
    return out

def orbit(gens):
    reached={0};todo=[0]
    for x in todo:
        for g in gens:
            if g[x] not in reached:reached.add(g[x]);todo.append(g[x])
    return sorted(reached)

def minimal_partition(gens,a,b):
    n=len(gens[0]);parent=list(range(n));size=[1]*n
    def find(x):
        while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
        return x
    pending=[]
    def union(x,y):
        x,y=find(x),find(y)
        if x==y:return
        if size[x]<size[y]:x,y=y,x
        parent[y]=x;size[x]+=size[y];pending.append((x,y))
    union(a,b)
    for x,y in pending:
        for g in gens:union(g[x],g[y])
    classes={}
    for i in range(n):classes.setdefault(find(i),[]).append(i)
    return sorted(classes.values(),key=lambda c:c[0])

def prime(p):return p>=2 and all(p%d for d in range(2,math.isqrt(p)+1))

def power(p,e):
    out=tuple(range(len(p)))
    while e:
        if e&1:out=compose(p,out)
        p=compose(p,p);e//=2
    return out

def certify(n,m,k,words=100,seed=20261025):
    gens=generators(n,m,k);o=orbit(gens)
    if len(o)<n:return {'classification':'proper','reason':'intransitive','orbit':o}
    odd=[q for q in (n,m,k) if (q//2)%2]
    if not odd:return {'classification':'proper','reason':'all_generators_even'}
    block_sizes=[]
    for j in range(1,n):
        part=minimal_partition(gens,0,j);block_sizes.append(len(part[0]))
        if len(part)>1:return {'classification':'proper','reason':'imprimitive','partition':part}
    rng=random.Random(seed+n*1000000+m*1000+k)
    for trial in range(words):
        p=tuple(range(n));word=[];last=None
        for step in range(96):
            choices=[i for i in range(3) if i!=last]
            last=choices[rng.randrange(len(choices))];word.append(last);p=compose(gens[last],p)
            if step%8!=7:continue
            lengths=[len(c) for c in cycles(p)]
            for length in sorted(set(lengths)):
                if not prime(length) or length>n-3 or lengths.count(length)!=1:continue
                other=[x for x in lengths if x!=length]
                exponent=math.lcm(*other) if other else 1
                if exponent%length==0:continue
                isolated=power(p,exponent);nontrivial=[c for c in cycles(isolated) if len(c)>1]
                if len(nontrivial)==1 and len(nontrivial[0])==length:
                    return {'classification':'symmetric','reason':'Jordan_prime_cycle_and_odd_generator',
                      'word':word,'exponent':exponent,'prime':length,'isolated_cycle':nontrivial[0],
                      'minimal_block_sizes':block_sizes,'odd_generator_indices':odd,'search_trial':trial}
    return {'classification':'unknown','reason':'certificate_search_budget','words':words}

def candidate_rows(k,count):
    primes=[p for p in range(k+2,k+150) if prime(p) and (k+p)%4==3 and k+p>100]
    return [k+p for p in primes[:count]]

def run(plan):
    rows=[];witnesses=[]
    for k in plan['parameters']['k_values']:
        for n in candidate_rows(k,plan['parameters']['max_rows_per_k']):
            entries=[]
            for m in range(k+1,n):
                entry={'n':n,'m':m,'k':k,**certify(n,m,k,plan['parameters']['words_per_triple'],plan['parameters']['seed'])}
                entries.append(entry)
                print(json.dumps({'event':'checkpoint','entry':entry},sort_keys=True),flush=True)
            row={'k':k,'n':n,'entries':entries,'symmetric_count':sum(x['classification']=='symmetric' for x in entries),
              'proper_count':sum(x['classification']=='proper' for x in entries),'unknown_count':sum(x['classification']=='unknown' for x in entries)}
            rows.append(row)
            if row['symmetric_count']==k+1 and row['unknown_count']==0:
                witnesses.append({'k':k,'n':n,'count':k+1});break
    return {'adapter':'prefix','rows':rows,'attainment_witnesses':witnesses,
      'claim_scope':'Finite checked instances beyond n=100. No proof of the conjecture for all k or of an asymptotic formula.',
      'all_selected_k_attained':len(witnesses)==len(plan['parameters']['k_values'])}

if __name__=='__main__':print(json.dumps(run(json.load(open(sys.argv[1]))),sort_keys=True))
