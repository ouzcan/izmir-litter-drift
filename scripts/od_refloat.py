"""Kıyıya oturma + yeniden yüzdürme — OceanDrift üstüne ince katman (duyarlılık varyantı `rf`).

Taban koşuda kıyıya değen parçacık kalıcı vurur (`coastline_action: stranding`). Bu modelde:
  - kıyıya değen parçacık OpenDrift'in 'previous' davranışıyla kıyı çizgisindeki su tarafına alınır ve DONDURULUR
    (`elements.moving = 0`; akıntı, rüzgâr ve difüzyon onu oynatmaz — `update_positions` ve `horizontal_diffusion`
    `moving` çarpanına saygılı);
  - oturma anında üstel dağılımdan (ortalama `refloat_days` gün, Onink vd. 2021'deki λ_R) bir bekleme süresi çekilir;
    süre dolunca parçacık yeniden yüzer ve sürüklenmeye devam eder; yeniden değerse yeni süre çekilir;
  - `p_perm` olasılıkla (varsayılan 0) ilk temasta kalıcı vurur (taban davranışı); salım anında karada olan parçacık
    tabanla aynı hesaba girsin diye her zaman kalıcı vurar (t = 0);
  - izleme sonunda karada oturan parçacık `stranded` sayılır — bulunduğu bölgeye yazılır;
  - `t_first_beach` (s): ilk kıyı temasının yaşı. Tabanda "vurma süresi" = ilk temas olduğundan, karşılaştırma bu
    değişkenle yapılır (`od_agg.endpoints_from_result` varsa bunu kullanır).

Onink vd. (2021, Environ. Res. Lett. 16, 064053) λ_R = 69 gün (Hinata vd. 2017, Mar. Pollut. Bull.) kullanır;
30–45 günlük izlemede bu tabandan ayırt edilemez. Duyarlılık bandı bu yüzden kısa ömürle (5 gün) çizilir —
"en çok yeniden yüzdürme" ucu; taban (hiç yüzdürme) öteki uç.

Kullanım: `RefloatDrift(loglevel=30, refloat_days=5, p_perm=0.0, seed=0)` — gerisi OceanDrift ile aynı.
"""
from __future__ import annotations
import numpy as np
from opendrift.models.oceandrift import OceanDrift, Lagrangian3DArray


class RefloatElement(Lagrangian3DArray):
    variables = Lagrangian3DArray.add_variables([
        ("beached", {"dtype": np.int32, "units": "1", "default": 0}),
        ("refloat_at", {"dtype": np.float32, "units": "s", "default": -1.0}),      # yeniden yüzme yaşı (s)
        ("t_first_beach", {"dtype": np.float32, "units": "s", "default": -1.0}),   # ilk kıyı temasının yaşı (s), -1 = hiç
    ])


class RefloatDrift(OceanDrift):
    ElementType = RefloatElement

    def __init__(self, *args, refloat_days: float = 5.0, p_perm: float = 0.0, seed: int = 0, **kwargs):
        super().__init__(*args, **kwargs)
        self.refloat_s = float(refloat_days) * 86400.0
        self.p_perm = float(p_perm)
        self.rng = np.random.default_rng(int(seed))
        self.set_config("general:coastline_action", "previous")

    def interact_with_coastline(self, final=False, **kw):
        el = self.elements
        if final:
            b = np.asarray(el.beached == 1)
            if b.any():
                self.deactivate_elements(b, reason="stranded")   # izleme sonunda karada oturan = kıyıya vurmuş
            return super().interact_with_coastline(final=final, **kw)
        if self.num_elements_active() == 0 or not hasattr(self, "environment") or not hasattr(self.environment, "land_binary_mask"):
            return super().interact_with_coastline(final=final, **kw)
        lm = self.environment.land_binary_mask
        age = el.age_seconds
        hit = np.asarray((lm == 1) & (el.beached == 0))
        if hit.any():
            idx = np.where(hit)[0]
            first = el.t_first_beach[idx] < 0
            el.t_first_beach[idx[first]] = age[idx[first]]
            perm = (self.rng.random(idx.size) < self.p_perm) | (age[idx] <= 0)   # salımda karada → tabanla aynı: kalıcı
            if perm.any():
                m = np.zeros(lm.size, dtype=bool); m[idx[perm]] = True
                self.deactivate_elements(m, reason="stranded")
                lm[idx[perm]] = 0            # super() suya geri taşımasın; kıyıda kalsın (taban davranışı)
            t = idx[~perm]
            if t.size:
                el.beached[t] = 1; el.moving[t] = 0
                el.refloat_at[t] = age[t] + self.rng.exponential(self.refloat_s, t.size)
        due = np.asarray((el.beached == 1) & (age >= el.refloat_at))
        if due.any():
            el.beached[due] = 0; el.moving[due] = 1; el.refloat_at[due] = -1.0
        super().interact_with_coastline(final=final, **kw)   # 'previous': karada görünenleri kıyı çizgisinin su tarafına alır
