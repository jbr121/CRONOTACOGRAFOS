import cv2, numpy as np, sys
from leitura import *
for i in map(int, sys.argv[1:]):
    bgr = cv2.imread(f'../../amostras/{i}.jpg'); p = polar(retificar(bgr), N)
    zero, conf = orientar(p)
    vt, vm, at, pr = extrair(p, zero)
    img = cv2.rotate(pr, cv2.ROTATE_90_COUNTERCLOCKWISE).copy()   # x = minuto, y = R - raio
    for m in range(N):
        y = int(R - (R_V0 + vm[m]/KMH_POR_R)*R); cv2.circle(img, (m, y), 1, (0,0,255), -1)
        y = int(R - (R_V0 + vt[m]/KMH_POR_R)*R); cv2.circle(img, (m, y), 1, (255,0,255), -1)
        if at[m] > 0.25: cv2.line(img, (m, int(R-.47*R)), (m, int(R-.46*R)), (0,160,0), 1)
    cv2.imwrite(f'vis_{i}.png', img[:int(.6*R)])
    print(i, 'zero', zero, 'conf', round(conf,2))
