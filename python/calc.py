from data import NUT
from menu import DAYS, BK_N, BK_A, d
from adjust import adj
from collections import defaultdict
def dd(s,person): return {k:adj(person,k,v) for k,v in d(s).items()}
def kp(x):
    k=p=0
    for ing,q in x.items():
        b,u,kc,pr=NUT[ing]; k+=q/b*kc; p+=q/b*pr
    return k,p
tot=defaultdict(float); rows=[]
for day,dej,din,des,tag in DAYS:
    kn=pn=ka=pa=0
    for (pl,n,a) in [("PDJ",BK_N,BK_A),dej,din,des]:
        xn,xa=dd(n,'N'),dd(a,'A')
        for m in (xn,xa):
            for ing,q in m.items(): tot[ing]+=q
        k,p=kp(xn); kn+=k; pn+=p
        k,p=kp(xa); ka+=k; pa+=p
    rows.append((day,round(kn),round(pn),round(ka),round(pa),tag))
if __name__=='__main__':
    for r in rows: print(r)
    import statistics as s
    print('moy N',round(s.mean(r[1] for r in rows)),round(s.mean(r[2] for r in rows)),'A',round(s.mean(r[3] for r in rows)),round(s.mean(r[4] for r in rows)))
    for k in sorted(tot): print(k, round(tot[k]))
