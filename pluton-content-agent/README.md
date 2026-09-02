# Plüton PDRM — Otomatik İçerik Botu

Her gün otomatik olarak: blog yazısı yazar, siteye yükler, Instagram için
görsel + caption üretir ve Instagram'a paylaşır. Yayınlamadan önce size
e-posta gönderir; belirlenen süre içinde iptal etmezseniz otomatik yayınlanır.

## Nasıl çalışır

1. GitHub Actions her gün belirlenen saatte tetiklenir
2. `generate_content.py` → Claude API ile blog yazısı + Instagram caption üretir
3. `generate_image.py` → Stability AI ile illüstrasyon üretir
4. `notify.py` → size e-posta gönderir
5. **3 saat bekler** (`PUBLISH_DELAY_HOURS`, workflow dosyasında değiştirilebilir)
6. Repo köküne `CANCEL_TODAY` adlı bir dosya eklenmediyse:
   - `publish_blog.py` → blogu Plesk'e SFTP ile yükler
   - `publish_instagram.py` → Instagram'da paylaşır

## Kurulum

### 1) Anthropic API key
console.anthropic.com → API Keys → yeni key oluşturun.

### 1b) Logo dosyasını sitenize yükleyin
Projede `logo.png` dosyası var (sitenizden çıkarıldı). Plesk Dosyalar
bölümünden bunu sitenizin köküne (`httpdocs/logo.png` gibi) yükleyin, böylece
her blog sayfası aynı büyük base64 metnini tekrar tekrar taşımaz. Yükledikten
sonra `content_agent/publish_blog.py` içindeki `LOGO_URL` değerini gerçek
adresle güncelleyin (örn. `https://www.plutonpdrm.com.tr/logo.png`).

### 2) fal.ai key (görsel üretimi için — FLUX.1 [dev] modeli)
fal.ai/dashboard/keys → hesap açıp key alın. (~$0.025-0.03/görsel, günde 1
görsel için ayda ~$1)

### 3) Plesk SFTP bilgileri
Plesk panelinizde: Websites & Domains → your domain → FTP Access →
kullanıcı adı/şifre. Host genelde domain adınızla aynıdır.

### 4) Gmail App Password (bildirim e-postası için)
myaccount.google.com/apppasswords → "İçerik Botu" adında yeni bir app
password oluşturun (normal Gmail şifreniz DEĞİL).

### 5) Instagram + Meta Developer kurulumu (en meşakkatli adım)
1. Instagram hesabınızı **Business hesabına** çevirin (Ayarlar → Hesap türü)
2. Bir **Facebook Sayfası** oluşturun (yoksa) ve Instagram hesabınızı ona bağlayın
3. developers.facebook.com → "My Apps" → yeni app oluşturun (tür: Business)
4. App'e **Instagram Graph API** ürününü ekleyin
5. Graph API Explorer'da: Facebook Sayfanız için bir **Page Access Token** alın,
   izinler: `instagram_basic`, `instagram_content_publish`, `pages_show_list`
6. Bu token'ı **long-lived token**'a çevirin (60 gün geçerli; Meta dokümantasyonunda
   "Long-Lived Access Tokens" bölümüne bakın — bu yenilenmesi gereken tek adımdır)
7. Instagram Business Account ID'nizi Graph API Explorer üzerinden
   `me/accounts` → sayfanız → `instagram_business_account` alanından alın
8. Not: Meta, yalnızca kendi hesabınız için "Development Mode"da bu izinleri
   kullanmanıza genelde izin verir (kendi App Rolünüzde admin/tester olarak
   eklenmiş olmanız yeterli); genel kullanıcılara açık bir uygulama
   yapmayacağınız için tam "App Review" sürecine genelde gerek kalmaz, ama
   Meta'nın arayüzü zaman zaman değişebiliyor — güncel adımlar için
   developers.facebook.com/docs/instagram-platform sayfasına bakın.

### 6) GitHub'da Secrets ekleyin
Bu repoyu GitHub'a yükleyin → Settings → Secrets and variables → Actions →
"New repository secret" ile şunları tek tek ekleyin:

- `ANTHROPIC_API_KEY`
- `FAL_KEY`
- `SFTP_HOST`, `SFTP_USER`, `SFTP_PASSWORD`, `SFTP_REMOTE_BLOG_DIR`
- `IG_BUSINESS_ACCOUNT_ID`, `IG_ACCESS_TOKEN`
- `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`, `NOTIFY_TO_ADDRESS`

### 7) Test edin
GitHub'da Actions sekmesi → "Daily Content Post" → "Run workflow" ile elle
tetikleyip loglardan takip edebilirsiniz.

## Hâlâ yapılması gerekenler (kodda TODO olarak işaretli)

- `publish_blog.py`: `PAGE_TEMPLATE` gerçek sitenizin header/footer HTML'i ile
  değiştirilmeli (siz bana gerçek sayfa HTML'ini gönderirseniz ben güncellerim)
- `publish_blog.py`: blog index sayfasına yeni yazıyı otomatik ekleme adımı
- `main.py`: üretilen görselin herkese açık bir URL'de barınması (Instagram
  bunu görmek zorunda) — en basiti görseli blog yazısıyla birlikte
  `/ig-images/` klasörüne de yüklemek

## Aylık maliyet tahmini

- Claude API (metin): ~$1-3/ay
- fal.ai / FLUX.1 [dev] (görsel): ~$0.75-1/ay (günde 1 görsel)
- GitHub Actions: ücretsiz (public repo) veya aylık ücretsiz kotanın içinde
- **Toplam: ~$2-4/ay**
