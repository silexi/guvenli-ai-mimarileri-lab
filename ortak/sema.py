"""
Lab 1 icin sema dogrulama.

Harici bir kutuphaneye (pydantic, jsonschema) bagimli olmamak icin
kucuk ve okunur bir dogrulayici yazdik. Amac kutuphane ogretmek degil,
"model ciktisi sisteme girmeden once dogrulanir" fikrini gostermek.
"""


class SemaHatasi(Exception):
    """Model ciktisi semaya uymadiginda atilir."""


# --------------------------------------------------------------------------
# Turkce normalizasyon
# --------------------------------------------------------------------------
# Model "yuksek" degil "yüksek" yazar. Buyuk/kucuk harf de degisir.
# Tam esleme (==) ile karsilastirirsaniz gecerli her cevap BASARISIZ gorunur.
#
# Bu, RAG ve siniflandirma sistemlerinde en sik yasanan sessiz hatalardan
# biridir: model dogru cevabi vermistir, sizin karsilastirmaniz yanlistir.
# Normalizasyon da bir guardrail katmanidir.

_TR_HARITA = str.maketrans(
    "çğıöşüÇĞİıÖŞÜ",
    "cgiosuCGIiOSU",
)


def normalize(deger):
    """
    Turkce metni karsilastirilabilir hale getirir.

    'Yüksek', 'YÜKSEK', 'yuksek', ' yüksek ' -> hepsi 'yuksek'
    Metin olmayan degerler oldugu gibi doner.
    """
    if not isinstance(deger, str):
        return deger
    return deger.translate(_TR_HARITA).lower().strip()


def esit(a, b):
    """Iki degeri Turkce duyarsiz karsilastirir."""
    return normalize(a) == normalize(b)


# Destek talebi cikarim semasi
TALEP_SEMASI = {
    "tur": {
        "tip": str,
        "izinli": {"fatura_itirazi", "teknik_sorun", "iptal_talebi", "bilgi_talebi"},
        "zorunlu": True,
    },
    "donem": {
        "tip": str,
        "bicim": r"^\d{4}-\d{2}$",     # 2026-08
        "zorunlu": True,
    },
    "tutar": {
        "tip": (int, float),
        "en_az": 0,
        "zorunlu": False,
    },
    "birim": {
        "tip": str,
        "izinli": {"TRY", "USD", "EUR"},
        "zorunlu": False,
    },
    "aciliyet": {
        "tip": str,
        "izinli": {"dusuk", "orta", "yuksek"},
        "zorunlu": True,
    },
    "guven": {
        "tip": (int, float),
        "en_az": 0.0,
        "en_cok": 1.0,
        "zorunlu": True,
    },
}


def dogrula(veri, sema=TALEP_SEMASI):
    """
    Veriyi semaya gore dogrular.

    Basarili olursa temizlenmis sozlugu dondurur.
    Basarisiz olursa SemaHatasi atar -- sessizce yanlis davranmaz.
    """
    import re

    if veri is None:
        raise SemaHatasi("Cikti JSON olarak ayristirilamadi")

    if not isinstance(veri, dict):
        raise SemaHatasi(f"Beklenen nesne, gelen {type(veri).__name__}")

    hatalar = []
    temiz = {}

    for alan, kural in sema.items():
        if alan not in veri:
            if kural.get("zorunlu"):
                hatalar.append(f"'{alan}' alani eksik")
            continue

        deger = veri[alan]

        if not isinstance(deger, kural["tip"]):
            beklenen = getattr(kural["tip"], "__name__", str(kural["tip"]))
            hatalar.append(
                f"'{alan}' tipi yanlis: beklenen {beklenen}, "
                f"gelen {type(deger).__name__} ({deger!r})"
            )
            continue

        if "izinli" in kural:
            # Turkce duyarsiz eslestirme: model "Yüksek" yazsa da kabul edilir,
            # ama sisteme KANONIK deger ("yuksek") yazilir. Boylece asagi akista
            # herkes ayni degeri gorur.
            eslesen = None
            for izinli_deger in kural["izinli"]:
                if normalize(deger) == normalize(izinli_deger):
                    eslesen = izinli_deger
                    break

            if eslesen is None:
                hatalar.append(
                    f"'{alan}' degeri izinli listede yok: {deger!r} "
                    f"(izinli: {sorted(kural['izinli'])})"
                )
                continue

            deger = eslesen

        if "bicim" in kural and not re.fullmatch(kural["bicim"], str(deger)):
            hatalar.append(
                f"'{alan}' bicimi yanlis: {deger!r} "
                f"(beklenen bicim: {kural['bicim']})"
            )
            continue

        if "en_az" in kural and deger < kural["en_az"]:
            hatalar.append(f"'{alan}' cok kucuk: {deger}")
            continue

        if "en_cok" in kural and deger > kural["en_cok"]:
            hatalar.append(f"'{alan}' cok buyuk: {deger}")
            continue

        temiz[alan] = deger

    if hatalar:
        raise SemaHatasi("; ".join(hatalar))

    return temiz


def sema_metni(sema=TALEP_SEMASI):
    """Semayi prompt'a konulacak okunur bir tarife cevirir."""
    satirlar = []
    for alan, kural in sema.items():
        parcalar = []
        if "izinli" in kural:
            parcalar.append("su degerlerden biri: " + " | ".join(sorted(kural["izinli"])))
        elif "bicim" in kural:
            parcalar.append("bicim: YYYY-AA")
        else:
            tip_adi = "sayi" if kural["tip"] != str else "metin"
            parcalar.append(tip_adi)
        if "en_az" in kural and "en_cok" in kural:
            parcalar.append(f"{kural['en_az']} ile {kural['en_cok']} arasinda")
        zorunlu = "zorunlu" if kural.get("zorunlu") else "istege bagli"
        satirlar.append(f'  "{alan}": {", ".join(parcalar)}  ({zorunlu})')
    return "{\n" + "\n".join(satirlar) + "\n}"


def onarim_istemi(ham_cikti, hata_mesaji, sema=TALEP_SEMASI):
    """
    Onarim turu istemi.

    Sema bozuldugunda bastan uretmek yerine hatayi modele geri verip
    tek turda duzelttirmek hem ucuz hem daha basarilidir.
    """
    return (
        "Onceki ciktin sema dogrulamasindan gecmedi.\n\n"
        f"Onceki cikti:\n{ham_cikti}\n\n"
        f"Dogrulama hatasi:\n{hata_mesaji}\n\n"
        f"Beklenen sema:\n{sema_metni(sema)}\n\n"
        "Yalnizca duzeltilmis JSON nesnesini dondur. Aciklama yazma."
    )
