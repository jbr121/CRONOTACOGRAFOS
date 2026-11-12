import cv2, numpy as np

def canal_brancura(bgr):
    """Papel branco: brilho alto e saturação baixa. Fundo colorido/escuro some."""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    s = hsv[..., 1].astype(np.int16); v = hsv[..., 2].astype(np.int16)
    return np.clip(v - s, 0, 255).astype(np.uint8)

def _candidatos_hough(canal):
    h, w = canal.shape
    esc = 480.0 / max(h, w)
    peq = cv2.resize(canal, None, fx=esc, fy=esc, interpolation=cv2.INTER_AREA)
    peq = cv2.GaussianBlur(peq, (5, 5), 1.5)
    m = min(peq.shape)
    cs = cv2.HoughCircles(peq, cv2.HOUGH_GRADIENT, dp=1.5, minDist=max(4, m // 20),
                          param1=80, param2=30, minRadius=int(m * 0.25), maxRadius=int(m * 0.75))
    if cs is None:
        return []
    return [(x / esc, y / esc, r / esc) for x, y, r in cs[0][:10]]

def _candidatos_contorno(canal):
    """Arcos longos de borda viram elipses candidatas (robusto quando o Hough falha)."""
    h, w = canal.shape
    m = min(h, w)
    borda = cv2.Canny(cv2.GaussianBlur(canal, (5, 5), 0), 30, 90)
    borda = cv2.dilate(borda, np.ones((3, 3), np.uint8))
    cs, _ = cv2.findContours(borda, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    out = []
    for c in sorted(cs, key=len, reverse=True)[:25]:
        if len(c) < 150:
            break
        (ex, ey), (A, B), _ = cv2.fitEllipse(c)
        r = (A + B) / 4
        if m * 0.25 <= r <= m * 0.75 and min(A, B) / max(A, B) > 0.6:
            out.append((ex, ey, r))
    return out

def _refinar_elipse(canal, x, y, r, n=360):
    g = cv2.GaussianBlur(canal, (5, 5), 0).astype(np.float32)
    h, w = g.shape
    pts = []
    rs = np.arange(r * 0.8, r * 1.2, 1.0)
    for t in np.linspace(0, 2 * np.pi, n, endpoint=False):
        xs = x + rs * np.cos(t); ys = y + rs * np.sin(t)
        ok = (xs >= 1) & (xs < w - 1) & (ys >= 1) & (ys < h - 1)
        if ok.sum() < 10:
            continue
        perfil = cv2.remap(g, xs[ok].astype(np.float32).reshape(1, -1),
                           ys[ok].astype(np.float32).reshape(1, -1), cv2.INTER_LINEAR)[0]
        d = perfil[:-4] - perfil[4:]
        i = int(np.argmax(d))
        if d[i] < 12:
            continue
        rr = rs[ok][i + 2]
        pts.append((x + rr * np.cos(t), y + rr * np.sin(t)))
    if len(pts) < 60:
        return None
    pts = np.array(pts, np.float32)
    for _ in range(3):
        (ex, ey), (A, B), ang = cv2.fitEllipse(pts)
        c, s = np.cos(np.deg2rad(ang)), np.sin(np.deg2rad(ang))
        dx, dy = pts[:, 0] - ex, pts[:, 1] - ey
        u = (dx * c + dy * s) / (A / 2); v = (-dx * s + dy * c) / (B / 2)
        res = np.abs(np.sqrt(u * u + v * v) - 1)
        if (res < 0.02).sum() > 40:
            pts = pts[res < 0.02]
    return cv2.fitEllipse(pts), len(pts) / n

def _pontuar(canal, el):
    """Contraste dentro x fora da elipse (anel logo antes e logo depois da borda)."""
    (ex, ey), (A, B), ang = el
    if min(A, B) / max(A, B) < 0.6:
        return -1
    m_in = np.zeros(canal.shape, np.uint8); m_out = np.zeros(canal.shape, np.uint8)
    cv2.ellipse(m_in, ((ex, ey), (A * 0.97, B * 0.97), ang), 255, -1)
    cv2.ellipse(m_in, ((ex, ey), (A * 0.80, B * 0.80), ang), 0, -1)
    cv2.ellipse(m_out, ((ex, ey), (A * 1.15, B * 1.15), ang), 255, -1)
    cv2.ellipse(m_out, ((ex, ey), (A * 1.03, B * 1.03), ang), 0, -1)
    if cv2.countNonZero(m_out) < 100:
        return -1
    dentro = cv2.mean(canal, m_in)[0]; fora = cv2.mean(canal, m_out)[0]
    return dentro - fora

def achar_disco(bgr, debug=False):
    canal = canal_brancura(bgr)
    cinza = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    melhor, ms = None, -1e9
    cands = (_candidatos_hough(canal) + _candidatos_hough(cinza)
             + _candidatos_contorno(canal) + _candidatos_contorno(cinza))
    for c in cands:
      for base in (canal, cinza):
        r = _refinar_elipse(base, *c)
        if r is None:
            continue
        el, suporte = r
        contraste = max(_pontuar(canal, el), _pontuar(cinza, el), 0)
        sc = contraste * suporte ** 2
        if debug: print('   cand', [round(v) for v in c], 'el', [round(v) for v in (*el[0], *el[1])], 'sup', round(suporte,2), 'contr', round(contraste,1))
        if sc > ms:
            melhor, ms = el, sc
    return melhor, ms
