import cv2, numpy as np
from disco import achar_disco
R = 600

def pontos_elipse(el, n=360):
    (ex, ey), (A, B), ang = el
    t = np.linspace(0, 2*np.pi, n, endpoint=False); a = np.deg2rad(ang)
    x = A/2*np.cos(t); y = B/2*np.sin(t)
    return np.stack([ex + x*np.cos(a) - y*np.sin(a), ey + x*np.sin(a) + y*np.cos(a)], 1)

def conica(el):
    p = pontos_elipse(el, 60)
    x, y = p[:,0], p[:,1]
    D = np.stack([x*x, x*y, y*y, x, y, np.ones_like(x)], 1)
    a, b, c, d, e, f = np.linalg.svd(D)[2][-1]
    return np.array([[a, b/2, d/2], [b/2, c, e/2], [d/2, e/2, f]])

def homografia(el, centro):
    """Homografia que leva a elipse da borda a um círculo de raio R em (R,R),
    com 'centro' (ponto da imagem) indo para o centro do círculo."""
    C = conica(el)
    l = C @ np.array([centro[0], centro[1], 1.0])     # reta polar do centro = imagem da reta no infinito
    Ha = np.array([[1, 0, 0], [0, 1, 0], [l[0]/l[2], l[1]/l[2], 1]])
    p = pontos_elipse(el).astype(np.float64)
    q = cv2.perspectiveTransform(p.reshape(-1,1,2), Ha).reshape(-1,2)
    (ex, ey), (A, B), ang = cv2.fitEllipse(q.astype(np.float32))
    t = np.deg2rad(ang)
    rot = np.array([[np.cos(t), -np.sin(t)], [np.sin(t), np.cos(t)]])
    M2 = rot @ np.diag([2*R/A, 2*R/B]) @ rot.T
    cq = cv2.perspectiveTransform(np.array([[[centro[0], centro[1]]]], np.float64), Ha)[0,0]
    off = np.array([R, R]) - M2 @ cq           # centro vai exatamente para (R,R)
    Af = np.eye(3); Af[:2,:2] = M2; Af[:2,2] = off
    return Af @ Ha

def polar(img, n_ang=1440):
    return cv2.warpPolar(img, (R, n_ang), (R, R), R, cv2.WARP_POLAR_LINEAR + cv2.INTER_LINEAR)

def nitidez_aneis(cinza, el, centro, r0=0.55, r1=0.97):
    H = homografia(el, centro)
    ret = cv2.warpPerspective(cinza, H, (2*R, 2*R), flags=cv2.INTER_LINEAR, borderValue=255)
    p = polar(ret, 360).astype(np.float32)[:, int(r0*R):int(r1*R)]
    perfil = np.median(p, axis=0)            # anéis concêntricos => perfil com vales nítidos
    return float(np.abs(np.diff(perfil)).sum())

def achar_centro(cinza, el):
    (ex, ey), (A, B), _ = el
    rr = (A + B) / 4
    melhor = (nitidez_aneis(cinza, el, (ex, ey)), ex, ey)
    passo = rr * 0.08
    cx, cy = ex, ey
    while passo > 0.5:
        melhorou = False
        for dx, dy in ((passo,0),(-passo,0),(0,passo),(0,-passo),(passo,passo),(-passo,-passo),(passo,-passo),(-passo,passo)):
            s = nitidez_aneis(cinza, el, (cx+dx, cy+dy))
            if s > melhor[0]:
                melhor = (s, cx+dx, cy+dy); melhorou = True
        if melhorou: cx, cy = melhor[1], melhor[2]
        else: passo /= 2
    return (cx, cy), melhor[0]

if __name__ == '__main__':
    import sys
    for i in map(int, sys.argv[1:]):
        bgr = cv2.imread(f'../../amostras/{i}.jpg'); cinza = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        el, _ = achar_disco(bgr)
        s0 = nitidez_aneis(cinza, el, el[0])
        c, s = achar_centro(cinza, el)
        print(i, 'centro elipse', [round(v) for v in el[0]], 'centro real', [round(v) for v in c], 'nitidez', round(s0), '->', round(s))
        H = homografia(el, c)
        ret = cv2.warpPerspective(bgr, H, (2*R, 2*R), flags=cv2.INTER_CUBIC, borderValue=(0,0,0))
        cv2.imwrite(f'ret_{i}.png', ret)
        cv2.imwrite(f'polar_{i}.png', cv2.rotate(polar(ret), cv2.ROTATE_90_COUNTERCLOCKWISE))
