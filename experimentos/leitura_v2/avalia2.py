import cv2, numpy as np, sys
from leitura import *
from avalia import fechar
def km(p, zero):
    p = np.roll(p, -zero, axis=0)
    hsv = cv2.cvtColor(p, cv2.COLOR_BGR2HSV); g = hsv[...,2].astype(np.float32)
    fundo = cv2.GaussianBlur(g, (0,0), 12); d = fundo - g
    b0, b1 = int(.485*R), int(.530*R)
    at = (d[:, b0:b1] > 25).mean(1)
    mov = fechar(at > 0.15, 4)
    a0, a1 = int(0.640*R), int(0.955*R)
    tinta = d[:, a0:a1] > 30
    if (~mov).sum() > 60:
        impresso = tinta[~mov].mean(0) > 0.08          # raios com impressão fixa
    else:
        impresso = np.zeros(a1-a0, bool)
    tinta[:, impresso] = False
    v = np.zeros(N)
    for m in np.nonzero(mov)[0]:
        idx = np.nonzero(tinta[m])[0]
        if idx.size >= 3: v[m] = ((np.median(idx)+a0)/R - R_V0) * KMH_POR_R
    v = np.clip(v, 0, 125)
    return mov, v, impresso.sum()
print('odômetro disco A: 161 km')
for i in map(int, sys.argv[1:]):
    bgr = cv2.imread(f'../../amostras/{i}.jpg'); p = polar(retificar(bgr), N)
    zero, _ = orientar(p); mov, v, nimp = km(p, zero)
    print(f'foto {i:2d}: dirigindo {mov.sum()/60:4.1f} h | km {v.sum()/60:6.1f} | vmed mov {v[mov].mean():5.1f} | raios impressos removidos {nimp}')
