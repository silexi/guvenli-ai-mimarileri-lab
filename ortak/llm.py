"""
Ortak LLM istemcisi.

Uc arka uc:

  COLAB  : Katilimcinin KENDI Colab calisma zamaninda calisan kucuk bir model.
           Paylasilan uc nokta yok, API anahtari yok, veri disari cikmiyor.
           2. gun lablarinin varsayilan yoludur.

  MOCK   : Onceden kaydedilmis cevaplar. Model indirilemezse veya calisma
           zamani yetersizse otomatik olarak buraya dusulur. Yapi aynen calisir.

  OLLAMA : Yerel Ollama sunucusu. Yalnizca egitmenin kendi makinesi icindir
           (1. gun demolariyla ayni model). Katilimci bunu kullanmaz.

Arka uc secimi:
    import os; os.environ["LAB_SAGLAYICI"] = "colab"   # veya mock / ollama
"""

import json
import os
import random
import re
import time
import urllib.request

from . import mock_cevaplar

# Colab arka ucunda kullanilacak modeller.
# GPU varsa buyugu, yoksa kucugu secilir. LAB_MODEL ile elle gecilebilir.
MODEL_GPU = "Qwen/Qwen2.5-3B-Instruct"
MODEL_CPU = "Qwen/Qwen2.5-1.5B-Instruct"

_boru_hatti = None  # tembel yuklenen (model, tokenizer, model_adi)


class Cevap:
    """Bir LLM cagrisinin sonucu."""

    def __init__(self, metin, arac_cagrilari=None, girdi_token=0,
                 cikti_token=0, sure_sn=0.0, saglayici="mock"):
        self.metin = metin
        self.arac_cagrilari = arac_cagrilari or []
        self.girdi_token = girdi_token
        self.cikti_token = cikti_token
        self.sure_sn = sure_sn
        self.saglayici = saglayici

    @property
    def toplam_token(self):
        return self.girdi_token + self.cikti_token

    def __repr__(self):
        return (f"Cevap(saglayici={self.saglayici}, "
                f"token={self.girdi_token}+{self.cikti_token}, "
                f"sure={self.sure_sn:.2f}sn)")


def _saglayici():
    return os.environ.get("LAB_SAGLAYICI", "colab").lower().strip()


def _token_tahmini(metin):
    """Kaba token tahmini. Turkce icin ~3.5 karakter/token."""
    return max(1, int(len(metin or "") / 3.5))


# --------------------------------------------------------------------------
# COLAB arka ucu: katilimcinin kendi calisma zamaninda model
# --------------------------------------------------------------------------

def model_yukle(model_adi=None, sessiz=False):
    """
    Modeli calisma zamanina yukler. Ilk cagride 1-3 dakika surer,
    sonraki cagrilarda bellekten kullanilir.
    """
    global _boru_hatti
    if _boru_hatti is not None:
        return _boru_hatti

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    gpu_var = torch.cuda.is_available()
    if model_adi is None:
        model_adi = os.environ.get("LAB_MODEL") or (MODEL_GPU if gpu_var else MODEL_CPU)

    if not sessiz:
        nerede = "GPU" if gpu_var else "CPU"
        print(f"Model yukleniyor: {model_adi}  ({nerede})")
        print("Ilk yukleme 1-3 dakika surebilir, sonraki hucreler hizli calisir.")

    tokenizer = AutoTokenizer.from_pretrained(model_adi)
    model = AutoModelForCausalLM.from_pretrained(
        model_adi,
        torch_dtype=torch.float16 if gpu_var else torch.float32,
        device_map="auto" if gpu_var else None,
    )
    if not gpu_var:
        model = model.to("cpu")
    model.eval()

    _boru_hatti = (model, tokenizer, model_adi)
    if not sessiz:
        print("Model hazir.")
    return _boru_hatti


def _cagir_colab(sistem, kullanici, sicaklik, azami_token):
    import torch

    model, tokenizer, _ = model_yukle(sessiz=True)

    mesajlar = []
    if sistem:
        mesajlar.append({"role": "system", "content": sistem})
    mesajlar.append({"role": "user", "content": kullanici})

    metin = tokenizer.apply_chat_template(
        mesajlar, tokenize=False, add_generation_prompt=True
    )
    girdiler = tokenizer([metin], return_tensors="pt").to(model.device)
    girdi_uzunluk = girdiler.input_ids.shape[-1]

    uretim = {
        "max_new_tokens": azami_token,
        "pad_token_id": tokenizer.eos_token_id,
    }
    if sicaklik and sicaklik > 0:
        uretim.update({"do_sample": True, "temperature": sicaklik, "top_p": 0.9})
    else:
        uretim["do_sample"] = False

    with torch.no_grad():
        cikti = model.generate(**girdiler, **uretim)

    yeni = cikti[0][girdi_uzunluk:]
    cevap_metni = tokenizer.decode(yeni, skip_special_tokens=True).strip()

    return Cevap(
        metin=cevap_metni,
        girdi_token=int(girdi_uzunluk),
        cikti_token=int(len(yeni)),
        saglayici="colab",
    )


# --------------------------------------------------------------------------
# MOCK arka ucu
# --------------------------------------------------------------------------

def _cagir_mock(sistem, kullanici, senaryo, sicaklik):
    time.sleep(random.uniform(0.1, 0.3))
    metin = mock_cevaplar.getir(senaryo=senaryo, sicaklik=sicaklik,
                                kullanici=kullanici)
    return Cevap(
        metin=metin,
        girdi_token=_token_tahmini((sistem or "") + kullanici),
        cikti_token=_token_tahmini(metin),
        saglayici="mock",
    )


# --------------------------------------------------------------------------
# OLLAMA arka ucu (yalnizca egitmen makinesi)
# --------------------------------------------------------------------------

def _cagir_ollama(sistem, kullanici, sicaklik, azami_token):
    adres = os.environ.get("LAB_OLLAMA_ADRES", "http://localhost:11434")
    model = os.environ.get("LAB_MODEL", "qwen3:30b-a3b")

    mesajlar = []
    if sistem:
        mesajlar.append({"role": "system", "content": sistem})
    mesajlar.append({"role": "user", "content": kullanici})

    govde = {
        "model": model,
        "messages": mesajlar,
        "stream": False,
        "options": {"temperature": sicaklik, "num_predict": azami_token},
    }
    istek = urllib.request.Request(
        f"{adres}/api/chat",
        data=json.dumps(govde).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(istek, timeout=300) as yanit:
        veri = json.loads(yanit.read().decode("utf-8"))

    return Cevap(
        metin=(veri.get("message", {}).get("content") or "").strip(),
        girdi_token=veri.get("prompt_eval_count", 0),
        cikti_token=veri.get("eval_count", 0),
        saglayici="ollama",
    )


# --------------------------------------------------------------------------
# Genel arayuz
# --------------------------------------------------------------------------

def sor(kullanici, sistem=None, sicaklik=0.7, azami_token=512, senaryo=None):
    """
    Modele tek bir cagri yapar.

    kullanici   : kullanici mesaji (guvenilmez girdi)
    sistem      : sistem talimati
    sicaklik    : 0 = en kararli, 0.7 = varsayilan
    senaryo     : MOCK modda hangi hazir cevabin donecegini secer.
                  Gercek arka uclarda yok sayilir.
    """
    baslangic = time.time()
    saglayici = _saglayici()

    try:
        if saglayici == "colab":
            cevap = _cagir_colab(sistem, kullanici, sicaklik, azami_token)
        elif saglayici == "ollama":
            cevap = _cagir_ollama(sistem, kullanici, sicaklik, azami_token)
        else:
            cevap = _cagir_mock(sistem, kullanici, senaryo, sicaklik)
    except Exception as hata:
        print(f"[uyari] '{saglayici}' arka ucu calismadi: {type(hata).__name__}: {hata}")
        print("[uyari] MOCK moda dusuluyor. Labin yapisi aynen calisir.")
        os.environ["LAB_SAGLAYICI"] = "mock"
        cevap = _cagir_mock(sistem, kullanici, senaryo, sicaklik)

    cevap.sure_sn = time.time() - baslangic
    return cevap


# --------------------------------------------------------------------------
# JSON ayiklama
# --------------------------------------------------------------------------

def json_ayikla(metin):
    """
    Model ciktisindan ilk JSON nesnesini ayiklar.

    Kucuk modeller JSON'u sik sik ``` citleri icinde veya aciklama
    cumleleriyle birlikte dondurur. Bu fonksiyon onu toparlar.
    Ayristirilamazsa None doner -- bu bir hata degil, Lab 1'in konusudur.
    """
    if not metin:
        return None

    citli = re.search(r"```(?:json)?\s*(.*?)```", metin, re.DOTALL)
    aday = citli.group(1).strip() if citli else metin.strip()

    basla = aday.find("{")
    if basla == -1:
        return None

    derinlik = 0
    for i in range(basla, len(aday)):
        if aday[i] == "{":
            derinlik += 1
        elif aday[i] == "}":
            derinlik -= 1
            if derinlik == 0:
                try:
                    return json.loads(aday[basla:i + 1])
                except json.JSONDecodeError:
                    return None
    return None


def durum():
    """Aktif yapilandirmayi tek satirda ozetler."""
    s = _saglayici()
    if s == "colab":
        try:
            import torch
            nerede = "GPU" if torch.cuda.is_available() else "CPU"
        except ImportError:
            nerede = "?"
        model = os.environ.get("LAB_MODEL", "(otomatik secim)")
        return f"Saglayici: COLAB (kendi calisma zamaniniz, {nerede}) | Model: {model}"
    if s == "ollama":
        return f"Saglayici: OLLAMA | Model: {os.environ.get('LAB_MODEL', 'qwen3:30b-a3b')}"
    return "Saglayici: MOCK (onceden kaydedilmis cevaplar, model gerekmez)"
