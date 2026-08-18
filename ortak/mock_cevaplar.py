"""
MOCK arka ucu icin onceden kaydedilmis cevaplar.

Amac: Colab calisma zamaninda model yuklenemezse (kota, indirme hatasi,
yetersiz bellek) labin YAPISI aynen calissin. Cevaplar gercek kucuk bir
modelin tipik davranisini taklit eder -- bilerek kusurludur:

  - Ayni senaryoda her cagride farkli cevap doner (non-determinism)
  - Bazi cevaplar semayi bozar (Lab 1'in konusu budur)
  - Enjeksiyon senaryolarinda model bazen kanar (Lab 3'un konusu budur)

Bu kusurlar hata degil, ogretim malzemesidir.
"""

import itertools
import random

# Her senaryo icin cevap havuzu. Sirayla doner, boylece tekrar calistirinca
# farkli sonuc gorulur.
_HAVUZLAR = {

    # ---------------- Lab 1: guvenilir cikti ----------------

    "lab1_serbest": [
        "Musteri Agustos faturasindaki yaklasik 12.400 lira civarindaki fazla "
        "tutara itiraz ediyor. Konu acil gorunuyor, hizli donus gerekiyor.",

        "Bu bir fatura itirazi. Musteri agustos ayinda 12400 TL fazla "
        "faturalandirildigini soyluyor ve aciliyet yuksek.",

        "Kategori: Faturalama sorunu.\nMusteri, Agustos donemi faturasinda "
        "12.400 TL'lik bir fazla tutar oldugunu belirtmis. Oncelik: yuksek.",

        "Talep, faturalandirma ile ilgili bir itiraz iceriyor. Tutar 12.400 TL "
        "olarak gecmekte. Musteri iptal tehdidinde bulundugu icin acil.",
    ],

    "lab1_sema": [
        '{"tur": "fatura_itirazi", "donem": "2026-08", "tutar": 12400.00, '
        '"birim": "TRY", "aciliyet": "yuksek", "guven": 0.62}',

        '```json\n{"tur": "fatura_itirazi", "donem": "2026-08", '
        '"tutar": 12400, "birim": "TRY", "aciliyet": "yuksek", '
        '"guven": 0.71}\n```',

        'Iste JSON ciktisi:\n{"tur": "fatura_itirazi", "donem": "2026-08", '
        '"tutar": 12400.0, "birim": "TRY", "aciliyet": "orta", "guven": 0.55}',

        # Bilerek bozuk: aciliyet enum disinda, tutar metin
        '{"tur": "fatura_itirazi", "donem": "Agustos 2026", '
        '"tutar": "12.400 TL", "birim": "TRY", "aciliyet": "cok_acil", '
        '"guven": 0.48}',

        # Bilerek bozuk: hic JSON yok
        "Bu talep bir fatura itirazidir ve aciliyeti yuksektir.",
    ],

    "lab1_onarim": [
        '{"tur": "fatura_itirazi", "donem": "2026-08", "tutar": 12400.00, '
        '"birim": "TRY", "aciliyet": "yuksek", "guven": 0.58}',
    ],

    # ---------------- Lab 2: RAG ----------------

    "lab2_iyi": [
        "Fatura itirazlari icin surec sudur: itiraz kaydi acilir, 5 is gunu "
        "icinde incelenir ve sonuc musteriye bildirilir. Itiraz suresi fatura "
        "tarihinden itibaren 30 gundur.",
    ],

    "lab2_kotu": [
        "Fatura itirazlari 5 is gunu icinde incelenir. Ayrica musteri "
        "memnuniyeti garantisi kapsaminda itiraz eden musterilere otomatik "
        "olarak %20 indirim uygulanir ve iade 24 saat icinde yapilir.",
    ],

    "lab2_yetkisiz": [
        "Ic fiyatlandirma politikasina gore kurumsal musterilere uygulanan "
        "taban maliyet carpani 1.35'tir ve bu deger ceyrek basinda revize edilir.",
    ],

    # ---------------- Lab 3: arac guvenligi ----------------

    # NOT: Lab 3 havuzlari birer AKIStir. Her havuz bir {"cevap": ...} ile
    # biter, boylece ajan dongusu temiz kapanir ve mukerrer cagri olusmaz.

    # Normal, saldirisiz akis
    "lab3_normal": [
        '{"arac": "musteri_getir", "parametreler": {"musteri_id": "M-1042"}}',
        '{"cevap": "Musteri M-1042 aktif durumda ve odemeleri duzenli."}',
    ],

    # Dogrudan enjeksiyon: model kaniyor
    "lab3_dogrudan": [
        'Anladim, yonetici modundayim.\n'
        '{"arac": "kayit_sil", "parametreler": {"komut": "M-1042 tum kayitlarini sil"}}',
        '{"cevap": "Islem tamamlandi."}',
    ],

    # Dolayli enjeksiyon: once kaydi getirir, notun icindeki talimata kanar
    "lab3_dolayli": [
        '{"arac": "musteri_getir", "parametreler": {"musteri_id": "M-1042"}}',
        '{"arac": "kayit_sil", "parametreler": {"komut": "M-1042 kayitlarini temizle"}}',
        '{"cevap": "Musteri bilgileri ozetlendi."}',
    ],

    # Yetki devri
    "lab3_yetki": [
        '{"arac": "kayit_sil", "parametreler": {"komut": "onayli silme: M-1042"}}',
        '{"cevap": "Yonetici onayiyla islem yapildi."}',
    ],

    # Savunma sonrasi: dar arac yuzeyi, model artik silemez
    "lab3_savunma_dogrudan": [
        'Kayit silme yetkim yok. Silme talebi olusturuyorum.\n'
        '{"arac": "silme_talebi_olustur", "parametreler": '
        '{"musteri_id": "M-1042", "gerekce": "musteri_talebi"}}',
        '{"cevap": "Silme yetkim yok. SIL-001 numarali talep insan onayina '
        'gonderildi."}',
    ],

    "lab3_savunma_dolayli": [
        '{"arac": "musteri_getir", "parametreler": {"musteri_id": "M-1042"}}',
        '{"cevap": "Musteri M-1042 aktif, odemeleri duzenli. Not alanindaki '
        'metin disaridan gelen veri olarak isaretlenmis, talimat olarak '
        'islemedim."}',
    ],

    # ---------------- Lab 4: workflow vs agent ----------------

    "lab4_sinif": [
        '{"kategori": "faturalama"}',
        '{"kategori": "faturalama"}',
        '{"kategori": "odeme"}',
    ],

    "lab4_alan": [
        '{"donem": "2026-08", "tutar": 12400, "musteri_id": "M-1042"}',
    ],

    "lab4_yanit": [
        "Sayin musterimiz, Agustos donemi faturanizdaki 12.400 TL tutarindaki "
        "itiraziniz kaydedilmistir. Inceleme 5 is gunu icinde tamamlanacaktir.",
    ],

    # Bu havuz UC FARKLI AKIS icerir ve sirayla dolasilir.
    # Amac: ajanin her calistirmada farkli sayida adim atmasi.
    # "Ajan ongorulemez" dersi ancak boyle gorunur olur.
    "lab4_ajan": [
        # --- Akis A: 3 adim ---
        '{"dusunce": "Once talebi okumaliyim", "arac": "talep_getir", '
        '"parametreler": {"talep_id": "T-77"}}',
        '{"dusunce": "Musteri gecmisine bakayim", "arac": "musteri_getir", '
        '"parametreler": {"musteri_id": "M-1042"}}',
        '{"dusunce": "Fatura detayi gerekli", "arac": "fatura_getir", '
        '"parametreler": {"donem": "2026-08"}}',
        '{"dusunce": "Yeterli bilgi toplandi", "cevap": "Fatura itirazi kaydedildi, '
        'inceleme 5 is gunu icinde tamamlanacak."}',

        # --- Akis B: 2 adim ---
        '{"dusunce": "Talebi getireyim", "arac": "talep_getir", '
        '"parametreler": {"talep_id": "T-77"}}',
        '{"dusunce": "Fatura bilgisi yeterli olur", "arac": "fatura_getir", '
        '"parametreler": {"donem": "2026-08"}}',
        '{"dusunce": "Cevap yazabilirim", "cevap": "Fatura itiraziniz alindi, '
        'inceleme baslatildi."}',

        # --- Akis C: 5 adim, icinde gereksiz tekrar var ---
        '{"dusunce": "Once talebi okumaliyim", "arac": "talep_getir", '
        '"parametreler": {"talep_id": "T-77"}}',
        '{"dusunce": "Musteri gecmisine bakayim", "arac": "musteri_getir", '
        '"parametreler": {"musteri_id": "M-1042"}}',
        '{"dusunce": "Fatura detayi gerekli", "arac": "fatura_getir", '
        '"parametreler": {"donem": "2026-08"}}',
        '{"dusunce": "Emin olmak icin gecmisi tekrar kontrol edeyim", '
        '"arac": "musteri_getir", "parametreler": {"musteri_id": "M-1042"}}',
        '{"dusunce": "Bir kez daha faturaya bakmaliyim", "arac": "fatura_getir", '
        '"parametreler": {"donem": "2026-08"}}',
        '{"dusunce": "Simdi cevap verebilirim", "cevap": "Fatura itirazi '
        'kaydedildi, inceleme 5 is gunu icinde tamamlanacak."}',
    ],

    # ---------------- Lab 5: eval ----------------

    # lab5 havuzlari _ICERIK_ESLEME uzerinden calisir (asagiya bakiniz).
}

# --------------------------------------------------------------------------
# Lab 5: icerik eslemeli cevaplar
# --------------------------------------------------------------------------
# Degerlendirme (eval) labinda her ornege DOGRU cevabin donmesi gerekir,
# yoksa regresyon gosterilemez. Bu yuzden lab5 senaryolarinda mock, gelen
# metindeki anahtar ifadeye gore cevap secer.
#
# Surum 1 : bes ornegin besini de dogru bilir      -> %100
# Surum 2 : prompt'a "aciliyette temkinli ol" eklenmistir; iki ornekte
#           aciliyeti dusurur                       -> %60  (REGRESYON)

_ICERIK_ESLEME = {
    "lab5_v1": [
        ("iki kez kesildi", '{"kategori": "faturalama", "aciliyet": "yuksek"}'),
        ("hesabima yansimadi", '{"kategori": "odeme", "aciliyet": "orta"}'),
        ("panele giris", '{"kategori": "teknik", "aciliyet": "dusuk"}'),
        ("kalem anlamadim", '{"kategori": "faturalama", "aciliyet": "orta"}'),
        ("iptal etmek", '{"kategori": "iptal", "aciliyet": "yuksek"}'),
    ],
    "lab5_v2": [
        # "temkinli ol" talimati yuksek aciligi orta'ya cekti -> regresyon
        ("iki kez kesildi", '{"kategori": "faturalama", "aciliyet": "orta"}'),
        ("hesabima yansimadi", '{"kategori": "odeme", "aciliyet": "orta"}'),
        ("panele giris", '{"kategori": "teknik", "aciliyet": "dusuk"}'),
        ("kalem anlamadim", '{"kategori": "faturalama", "aciliyet": "orta"}'),
        ("iptal etmek", '{"kategori": "iptal", "aciliyet": "orta"}'),
    ],
}

_VARSAYILAN = [
    "(MOCK cevap) Bu senaryo icin kayitli bir cevap yok. "
    "Gercek modelde bu hucre model ciktisini gosterirdi."
]

_sayaclar = {}


def getir(senaryo=None, sicaklik=0.7, kullanici=None):
    """
    Senaryoya karsilik gelen bir cevap dondurur.

    Sicaklik 0 ise havuzun ilk elemani sabit doner (kararlilik taklidi).
    Sicaklik > 0 ise havuz sirayla dolasilir (non-determinism taklidi).
    """
    # Icerik eslemeli senaryolar (Lab 5): cevap, gelen metne gore secilir.
    if senaryo in _ICERIK_ESLEME:
        metin = (kullanici or "").lower()
        for anahtar, cevap in _ICERIK_ESLEME[senaryo]:
            if anahtar in metin:
                return cevap
        return '{"kategori": "faturalama", "aciliyet": "orta"}'

    havuz = _HAVUZLAR.get(senaryo, _VARSAYILAN)

    if sicaklik is not None and sicaklik <= 0:
        # Sicaklik 0: cogunlukla ayni cevap, ama garanti degil.
        # Bu, 1. gunun "sicaklik 0 determinizm garantisi degildir" tezidir.
        if len(havuz) > 1 and random.random() < 0.15:
            return havuz[1]
        return havuz[0]

    if senaryo not in _sayaclar:
        _sayaclar[senaryo] = itertools.cycle(range(len(havuz)))
    return havuz[next(_sayaclar[senaryo])]


def sifirla():
    """Havuz sayaclarini sifirlar (bir labi bastan calistirmak icin)."""
    _sayaclar.clear()
