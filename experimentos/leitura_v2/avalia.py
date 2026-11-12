import cv2, numpy as np, sys
from leitura import *
def fechar(b, k):
    """Preenche buracos curtos (< k min) na barra de atividade."""
    b = b.copy(); idx = np.nonzero(b)[0]
    for a, c in zip(idx[:-1], idx[1:]):
        if 1 < c - a <= k: b[a:c] = True
    return b
print('odômetro disco A (fotos 1-11): 204941-204780 = 161 km')
for i in map(int, sys.argv[1:]):
    bgr = cv2.imread(f'../../amostras/{i}.jpg'); p = polar(retificar(bgr), N)
    zero, _ = orientar(p)
    vt, vm, at, _ = extrair(p, zero)
    mov = fechar(at > 0.15, 4)
    km_med = vm[mov].sum()/60; km_top = vt[mov].sum()/60
    print(f'foto {i:2d}: 00h na linha {zero:4d} | dirigindo {mov.sum()/60:4.1f} h | km mediana {km_med:5.1f} | km envelope {km_top:5.1f} | vmax(p99) {np.percentile(vt[mov],99):5.1f}')
