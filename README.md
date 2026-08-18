# Güvenli AI Mimarileri · Lab

**Yapay Zeka ile Çalışan Güvenli Mimariler Geliştirme** eğitiminin 2. gün lab ortamı.
KoçAkademi · 18-19 Ağustos 2026 · Uzaktan

---

## Hızlı başlangıç

Aşağıdaki bağlantılara tıklayın. Bilgisayarınıza **hiçbir şey kurulmuyor**:
her şey sizin Colab çalışma zamanınızda çalışır ve oturum kapanınca silinir.

| Lab | Konu | Süre |
|-----|------|------|
| [Lab 1](https://colab.research.google.com/github/silexi/guvenli-ai-mimarileri-lab/blob/main/lab1_guvenilir_cikti.ipynb) | Güvenilir çıktı: şema, doğrulama, onarım turu | 30 dk |
| [Lab 2](https://colab.research.google.com/github/silexi/guvenli-ai-mimarileri-lab/blob/main/lab2_rag_getirme.ipynb) | RAG ve getirme kalitesi, yetki filtresi | 35 dk |
| [Lab 3](https://colab.research.google.com/github/silexi/guvenli-ai-mimarileri-lab/blob/main/lab3_arac_guvenligi.ipynb) | **Araç tasarımı, prompt injection, guardrail** | 45 dk |
| [Lab 4](https://colab.research.google.com/github/silexi/guvenli-ai-mimarileri-lab/blob/main/lab4_workflow_vs_agent.ipynb) | İş akışı mı, ajan mı? | 30 dk |
| [Lab 5](https://colab.research.google.com/github/silexi/guvenli-ai-mimarileri-lab/blob/main/lab5_eval.ipynb) | Bozulmayı yakalayan minik test | 15 dk |

Her defterin ilk hücresinde **"Open in Colab"** rozeti vardır. Tıklayın, açılır.
Kendi kopyanızda çalışmak için Colab'da `Dosya → Drive'a kopya kaydet` deyin.

---

## Model nereden geliyor?

Üç seçenek var. Varsayılan olan ilkidir.

### 1. `colab` (varsayılan)

Model **sizin kendi Colab çalışma zamanınıza** iner ve orada çalışır.
Paylaşılan bir sunucu yok, API anahtarı yok, verileriniz dışarı çıkmıyor.

- GPU varsa: `Qwen/Qwen2.5-3B-Instruct`
- GPU yoksa: `Qwen/Qwen2.5-1.5B-Instruct`

GPU açmak için Colab'da: `Çalışma zamanı → Çalışma zamanı türünü değiştir → T4 GPU`.
GPU olmadan da çalışır, sadece yavaştır.

**Neden küçük bir model?** Bu lablar başarıyı değil **başarısızlık modlarını**
öğretiyor: non-determinism, şema bozulması, halüsinasyon, prompt injection.
Küçük bir model bu davranışları güvenilir biçimde gösterir. Büyük bir model
saldırılara direnip dersi görünmez kılabilir.

### 2. `mock` (yedek yol)

Model inmezse, kota dolarsa veya bellek yetmezse otomatik olarak buraya düşülür.
Önceden kaydedilmiş cevaplarla labın **yapısı aynen çalışır**. Elle geçmek için:

```python
import os
os.environ["LAB_SAGLAYICI"] = "mock"
```

### 3. `ollama` (yalnızca eğitmen)

1. günün demolarıyla aynı yerel model. Katılımcılar bunu kullanmaz.

```python
os.environ["LAB_SAGLAYICI"] = "ollama"
os.environ["LAB_MODEL"] = "qwen3:30b-a3b"
```

---

## Yerelde çalıştırmak isterseniz

```bash
git clone <repo-url>
cd guvenli-ai-mimarileri-lab
pip install -r requirements.txt
jupyter notebook
```

---

## Repo yapısı

```
ortak/
  llm.py            Üç arka uçlu LLM istemcisi + JSON ayıklama
  sema.py           Şema doğrulama ve onarım turu        (Lab 1)
  rag.py            Parçalama, getirme, yetki filtresi   (Lab 2)
  araclar.py        Araç setleri, ajan döngüsü, guardrail (Lab 3)
  mock_cevaplar.py  MOCK modun hazır cevapları
data/docs/          Türkçe politika belgeleri (Lab 2 bilgi bankası)
  genel_*.md          herkese açık
  ic_*.md             iç kullanım
  gizli_*.md          gizli (yetki filtresi testi için)
lab1..lab5.ipynb    Defterler
```

---

## Etik ve kapsam notu

**Lab 3 gerçek prompt injection örnekleri içerir.** Bu örnekler eğitim
amaçlıdır: savunmayı tasarlayabilmek için saldırının nasıl çalıştığını
anlamak gerekir. Örnekler yalnızca bu repodaki sahte veri üzerinde çalışır
ve herhangi bir gerçek sisteme yönelik değildir.

`data/docs` altındaki belgeler tamamen kurgudur. Gerçek kurumsal politika
belgesi değildir; kendi verinizle denemek isterseniz anonimleştirerek ekleyin.

---

## Her labın kanıtladığı tez

| Lab | Tez |
|-----|-----|
| 1 | Çıktıyı ayrıştırılabilir ve doğrulanabilir kılmadan sisteme sokamazsınız |
| 2 | Sorun genellikle modelde değil, ona ne verdiğinizdedir |
| 3 | Güvenlik prompt'ta değil, aracın etrafındaki deterministik sınırdadır |
| 4 | Esneklik bedava değildir; görev sabitse iş akışı kazanır |
| 5 | Ölçmezseniz bozulmayı göremezsiniz |

> Yapay zekanın başarısı modelde değil, modelin etrafına kurduğun mimaride belirlenir.
