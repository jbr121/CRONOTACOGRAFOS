import cv2, numpy as np
from disco import achar_disco
from retifica import achar_centro, homografia, polar, R

N = 1440                   # 1 linha polar = 1 minuto
R_V0, R_V120 = 0.628, 0.960  # raio (fração) de 0 e 120 km/h  (VDO 125 km/h)
KMH_POR_R = 120 / (R_V120 - R_V0)

def retificar(bgr):
    cinza = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    el, _ = achar_disco(bgr)
    c, _ = achar_centro(cinza, el)
    H = homografia(el, c)
    return cv2.warpPerspective(bgr, H, (2*R, 2*R), flags=cv2.INTER_CUBIC, borderValue=(0,0,0))

def orientar(p):
    """Acha a linha polar da meia-noite pelo arco verde grosso impresso de 12h a 24h."""
    hsv = cv2.cvtColor(p[:, int(.945*R):int(.980*R)], cv2.COLOR_BGR2HSV)
    verde = ((hsv[...,0]>30)&(hsv[...,0]<90)&(hsv[...,1]>60)).sum(1).astype(float)
    verde = np.clip(verde - np.median(verde), 0, None)   # tira a linha fina que dá a volta toda
    # janela circular de 720 linhas (12 h) com mais verde
    s = np.convolve(np.r_[verde, verde], np.ones(N//2), 'valid')[:N]
    ini = int(np.argmax(s))              # linha onde começa o arco = 12h
    return (ini + N//2) % N, float(s[ini] / max(s.sum()/2, 1e-6))   # meia-noite = fim do arco

def extrair(p, zero):
    p = np.roll(p, -zero, axis=0)        # linha 0 = 00:00
    hsv = cv2.cvtColor(p, cv2.COLOR_BGR2HSV)
    g = hsv[...,2].astype(np.float32)
    fundo = cv2.GaussianBlur(g, (0,0), 12)
    tinta = (fundo - g > 35) & ~((hsv[...,0]>30)&(hsv[...,0]<90)&(hsv[...,1]>50))  # escuro e não-verde
    a0, a1 = int((R_V0+0.012)*R), int(0.955*R)
    zona = tinta[:, a0:a1]
    vel_top = np.zeros(N); vel_med = np.zeros(N)
    for m in range(N):
        idx = np.nonzero(zona[m])[0]
        if idx.size >= 2:
            r = (idx + a0) / R
            vel_top[m] = (np.percentile(r, 90) - R_V0) * KMH_POR_R
            vel_med[m] = (np.median(r) - R_V0) * KMH_POR_R
    # atividade: barra escura em ~0.49-0.53R
    b0, b1 = int(.485*R), int(.530*R)
    ativ = (fundo[:, b0:b1] - g[:, b0:b1] > 35).mean(1)
    return np.clip(vel_top,0,125), np.clip(vel_med,0,125), ativ, p

def hhmm(m): return f'{int(m)//60:02d}:{int(m)%60:02d}'

if __name__ == '__main__':
    import sys
    for i in map(int, sys.argv[1:]):
        bgr = cv2.imread(f'../../amostras/{i}.jpg')
        ret = retificar(bgr)
        p = polar(ret, N)
        zero, conf = orientar(p)
        vt, vm, at, pr = extrair(p, zero)
        mov = at > 0.25
        km_top = vt[mov].sum()/60; km_med = vm[mov].sum()/60
        blocos=[]; ini=None
        for m in range(N+1):
            on = m < N and mov[m]
            if on and ini is None: ini=m
            if not on and ini is not None:
                if m-ini>=3: blocos.append(f'{hhmm(ini)}-{hhmm(m)}')
                ini=None
        print(f'{i:2d} arco={conf:.2f} min_mov={mov.sum():4d} km(env90)={km_top:6.1f} km(mediana)={km_med:6.1f} vmax={np.percentile(vt[mov],99) if mov.any() else 0:5.1f}  {blocos[:8]}')
        cv2.imwrite(f'orient_{i}.png', cv2.rotate(pr, cv2.ROTATE_90_COUNTERCLOCKWISE))
