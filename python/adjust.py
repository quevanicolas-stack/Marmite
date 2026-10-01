# Ajustements de portions (féculents) appliqués aux données brutes
def r10(x): return float(int(round(x/10.0))*10)
def adj(person, ing, q):
    if person=='N':
        if ing=='Pommes de terre': return r10(q*1.2)
        if ing=='Patates douces': return r10(q*1.2)
    else:
        if ing=='Pommes de terre': return r10(q*1.15)
        if ing=='Patates douces': return r10(q*1.15)
        if ing=='Riz (sec)' and q==40: return 45.0
        if ing=='Haricots verts' and q==300: return 280.0
        if ing=='Yaourt nature' and q==100: return 125.0
    return q
