"""
Lab 2 icin basit ve SEFFAF bir RAG motoru.

Amac hizli veya sofistike olmak degil; getirme katmaninin her adimini
gorunur kilmak. Katilimci hangi parcanin neden getirildigini gorebilmeli.

Gomme (embedding) yerine TF-IDF kullaniyoruz: model indirmesi gerekmez,
aninda calisir ve getirme kalitesi dersini vermek icin fazlasiyla yeterlidir.
"""

import os
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class Parca:
    """Getirilebilir tek bir metin parcasi."""

    def __init__(self, metin, kaynak, gizlilik="genel"):
        self.metin = metin
        self.kaynak = kaynak
        self.gizlilik = gizlilik   # "genel" | "ic" | "gizli"
        self.puan = 0.0

    def __repr__(self):
        onizleme = self.metin[:60].replace("\n", " ")
        return f"<Parca {self.kaynak} [{self.gizlilik}] puan={self.puan:.3f} '{onizleme}...'>"


# --------------------------------------------------------------------------
# Parcalama (chunking)
# --------------------------------------------------------------------------

def parcala_paragraf(metin, kaynak, gizlilik="genel"):
    """Iyi strateji: bos satira gore, anlam butunlugu korunarak."""
    parcalar = []
    for blok in re.split(r"\n\s*\n", metin):
        blok = blok.strip()
        if len(blok) > 30:
            parcalar.append(Parca(blok, kaynak, gizlilik))
    return parcalar


def parcala_sabit(metin, kaynak, gizlilik="genel", boyut=180):
    """
    Kotu strateji: sabit karakter sayisina gore, cumle ortasindan boler.
    Lab 2'de bilerek kullanilir -- parcalama bozuldugunda cevabin da
    bozuldugunu gostermek icin.
    """
    duz = re.sub(r"\s+", " ", metin).strip()
    return [
        Parca(duz[i:i + boyut], kaynak, gizlilik)
        for i in range(0, len(duz), boyut)
        if len(duz[i:i + boyut].strip()) > 30
    ]


# --------------------------------------------------------------------------
# Bilgi bankasi
# --------------------------------------------------------------------------

class BilgiBankasi:
    """Parcalari tutar ve benzerlik aramasi yapar."""

    def __init__(self, parcalar):
        self.parcalar = parcalar
        self._vektorlestirici = TfidfVectorizer(
            lowercase=True, ngram_range=(1, 2), min_df=1
        )
        self._matris = self._vektorlestirici.fit_transform(
            [p.metin for p in parcalar]
        )

    def ara(self, soru, k=3, kullanici_gizlilik_seviyesi=None):
        """
        Soruya en benzer k parcayi dondurur.

        kullanici_gizlilik_seviyesi verilirse yetki filtresi GETIRMEDEN ONCE
        uygulanir. Bu siralama kritiktir: once getirip sonra filtrelemek,
        veriyi zaten modele gostermis olmak demektir.
        """
        if kullanici_gizlilik_seviyesi is not None:
            izinli = _izinli_seviyeler(kullanici_gizlilik_seviyesi)
            aday_indeksler = [
                i for i, p in enumerate(self.parcalar) if p.gizlilik in izinli
            ]
        else:
            aday_indeksler = list(range(len(self.parcalar)))

        if not aday_indeksler:
            return []

        soru_vektoru = self._vektorlestirici.transform([soru])
        benzerlikler = cosine_similarity(soru_vektoru, self._matris[aday_indeksler])[0]

        sirali = sorted(
            zip(aday_indeksler, benzerlikler), key=lambda x: x[1], reverse=True
        )[:k]

        sonuc = []
        for indeks, puan in sirali:
            parca = self.parcalar[indeks]
            parca.puan = float(puan)
            sonuc.append(parca)
        return sonuc


def _izinli_seviyeler(seviye):
    merdiven = {
        "genel": {"genel"},
        "ic": {"genel", "ic"},
        "gizli": {"genel", "ic", "gizli"},
    }
    return merdiven.get(seviye, {"genel"})


# --------------------------------------------------------------------------
# Yardimcilar
# --------------------------------------------------------------------------

def belgeleri_yukle(dizin, strateji="paragraf"):
    """
    data/docs altindaki .md dosyalarini okur ve parcalar.

    Dosya adinin basindaki etiket gizlilik seviyesini belirler:
      genel_*.md, ic_*.md, gizli_*.md
    """
    parcalayici = parcala_paragraf if strateji == "paragraf" else parcala_sabit
    parcalar = []

    for ad in sorted(os.listdir(dizin)):
        if not ad.endswith(".md"):
            continue
        gizlilik = "genel"
        if ad.startswith("ic_"):
            gizlilik = "ic"
        elif ad.startswith("gizli_"):
            gizlilik = "gizli"

        with open(os.path.join(dizin, ad), encoding="utf-8") as dosya:
            parcalar.extend(parcalayici(dosya.read(), kaynak=ad, gizlilik=gizlilik))

    return parcalar


def baglam_kur(parcalar):
    """Getirilen parcalari modele verilecek baglam metnine cevirir."""
    bloklar = []
    for i, p in enumerate(parcalar, 1):
        bloklar.append(f"[Parca {i} | kaynak: {p.kaynak}]\n{p.metin}")
    return "\n\n".join(bloklar)


def parcalari_goster(parcalar, baslik="Getirilen parcalar"):
    """Getirme sonucunu okunur bicimde yazdirir."""
    print(f"\n{baslik}  ({len(parcalar)} parca)")
    print("=" * 70)
    for i, p in enumerate(parcalar, 1):
        onizleme = re.sub(r"\s+", " ", p.metin)[:90]
        print(f"{i}. [{p.puan:.3f}] {p.kaynak} ({p.gizlilik})")
        print(f"   {onizleme}...")
    print("=" * 70)
