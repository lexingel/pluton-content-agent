# Plüton PDRM — Otomatik İçerik Botu + Onay Paneli

İçerik üretimi otomatik (günlük veya elle tetiklenebilir); yayınlama ise
sizin web panelinizden onayınıza bağlı. E-posta yerine, üretilen içeriği
tarayıcıda önizleyip **Onayla** veya **Reddet** diyorsunuz.

## Nasıl çalışır

Üç ayrı GitHub Actions workflow'u var. Hepsi **sadece panelden tetiklendiğinde**
çalışır — otomatik zamanlama (schedule) kapalı, tamamen sizin kontrolünüzde.

**1. `fetch-trends.yml`** — panelden "Trendleri Yenile" ile çalıştırıldığında:
   - Claude'un web araması özelliğini kullanarak (ekstra API key gerekmez,
     mevcut Anthropic key'inizle) psikoloji/çocuk gelişimi/ebeveynlik
     alanında güncel 6-8 konu bulur
   - `panel/data/trends.json` olarak sitenize yükler
   - Ayrıca `topics.json` sabit listesini de panele senkronize eder

**2. `generate-content.yml`** — panelden "Yeni İçerik Üret" ile
   çalıştırıldığında (isteğe bağlı seçtiğiniz bir konuyla):
   - Konu seçilmediyse `topics.json`'daki sıradaki konuyu otomatik alır
   - Claude API ile blog yazısı + Instagram caption üretir
   - fal.ai (FLUX.1 dev) ile illüstrasyon üretir, sitenize yükler
   - Her şeyi `panel/data/pending.json` olarak yükler (henüz YAYINLAMAZ)

**3. `publish-approved.yml`** — sadece panelde "Onayla" butonuna
   bastığınızda çalışır:
   - `pending.json`'ı okur, blogu Plesk'e yükler, `/blog/index.html`'i
     günceller, Instagram'da paylaşır
   - `pending.json`'ı siler, `panel/data/history.json`'a bir kayıt ekler

**Panel** (`plutonpdrm.com.tr/panel/`): şifreyle korumalı. Ana sayfada ya
bekleyen bir içerik incelemenizi bekler (Onayla/Reddet), ya da "Yeni
İçerik Üret" menüsü gösterilir — burada güncel trendlerden, standart konu
listesinden birini seçebilir, ya da kendi konunuzu yazabilirsiniz. Üretim
ve yayınlama sırasında sayfa 15 saniyede bir otomatik yenilenir, böylece
elle yenilemeniz gerekmez. Onayladıktan hemen sonra panel otomatik olarak
"Yeni İçerik Üret" menüsüne döner (arka planda yayınlama devam eder).
"Geçmiş" sayfası, yayınlanan tüm içeriklerin bir kaydını tutar.

## Kurulum

### 1) Anthropic API key
console.anthropic.com → API Keys → yeni key oluşturun. (Workspace bazlı
identity-linked key sorunu yaşarsanız, workspace ID'nizi de
`ANTHROPIC_WORKSPACE_ID` secret'ı olarak ekleyin.)

### 1b) Logo dosyasını sitenize yükleyin
Projede `logo.png` dosyası var. Plesk Dosyalar bölümünden sitenizin
köküne (`httpdocs/logo.png`) yükleyin.

### 2) fal.ai key (görsel üretimi için)
fal.ai/dashboard/keys → hesap açıp key alın. (~$0.025-0.03/görsel)

### 3) Plesk FTP bilgileri
Plesk panelinizde: domain → Bağlantı bilgisi → host/kullanıcı adı/şifre.
Not: SSH kapalıysa (çoğu paylaşımlı hosting'te öyledir) kod düz FTP
(port 21) kullanır, ek bir şey yapmanıza gerek yok.

### 4) Instagram + Meta Developer kurulumu
1. Instagram hesabınızı **Business hesabına** çevirin
2. Bir **Facebook Sayfası** oluşturun ve Instagram hesabınızı bağlayın
3. developers.facebook.com → yeni app (tür: Business) → **Instagram Graph API** ekleyin
4. Graph API Explorer'da Sayfanız için `instagram_basic`,
   `instagram_content_publish`, `pages_show_list` izinleriyle bir
   **Page Access Token** alın, sonra **long-lived token**'a çevirin (60 gün)
5. Instagram Business Account ID'nizi `me/accounts` → sayfanız →
   `instagram_business_account` alanından alın

### 5) GitHub Secrets ekleyin
Repo → Settings → Secrets and variables → **Actions**:
- `ANTHROPIC_API_KEY`, `ANTHROPIC_WORKSPACE_ID` (gerekirse)
- `FAL_KEY`
- `SFTP_HOST`, `SFTP_USER`, `SFTP_PASSWORD`, `SFTP_REMOTE_BLOG_DIR`
- `IG_BUSINESS_ACCOUNT_ID`, `IG_ACCESS_TOKEN`

(Eski `GMAIL_*` / `NOTIFY_TO_ADDRESS` secret'larına artık gerek yok —
panel bildirimi üstleniyor. Silmenize gerek yok, kullanılmıyor sadece.)

### 6) Paneli Plesk'e yükleyin
`admin-panel/` klasörünü **sitenizin köküne `panel/` adıyla** yükleyin
(örn. `httpdocs/panel/`), böylece `plutonpdrm.com.tr/panel/` adresinden
erişilir. Klasör içindeki `data/` alt klasörünün yazılabilir olduğundan
emin olun (Plesk'te varsayılan izinler genelde yeterlidir).

### 7) Panel config'ini oluşturun
1. `config.example.php`'yi kopyalayıp `config.php` yapın (aynı klasörde)
2. `GITHUB_OWNER`, `GITHUB_REPO` değerlerini kendi repo'nuza göre düzenleyin
3. Bir **GitHub Personal Access Token** oluşturun:
   github.com → Settings → Developer settings → Fine-grained tokens →
   Generate new token → sadece bu repo'ya erişim → Permissions:
   **Actions: Read and write**, **Contents: Read-only** → oluşturun,
   token'ı kopyalayıp `config.php` içindeki `GITHUB_TOKEN`'a yapıştırın
4. Şifrenizi belirlemek için: `plutonpdrm.com.tr/panel/generate_hash.php?password=GercekSifreniz`
   adresini açın, çıkan hash'i `config.php` içindeki `ADMIN_PASSWORD_HASH`'e
   yapıştırın, **sonra `generate_hash.php` dosyasını sunucudan silin**
5. `ADMIN_USERNAME`'i de dilediğiniz gibi değiştirin

### 8) Test edin
`plutonpdrm.com.tr/panel/` adresine gidip giriş yapın, "Yeni İçerik Üret"
butonuna basın, 1-2 dakika sonra sayfayı yenileyip içeriği inceleyin,
Onayla veya Reddet ile deneyin.

## Panel dosyaları (ayrı, git'e dahil değil)

`admin-panel/` klasörü bilinçli olarak bu repo'nun workflow'ları
tarafından yönetilmiyor — doğrudan Plesk'e elle yüklüyorsunuz, çünkü
içinde şifreniz ve GitHub token'ınız gibi hassas bilgiler var
(`config.php`). Panel kodunu güncellemem gerektiğinde size ayrı bir
zip olarak vereceğim.

**Önemli:** panel kodunu güncellerken sadece kod dosyalarını
(`index.php`, `includes/`, `actions/`, `style.css`, `history.php`) üzerine
yazın — `config.php` ve `data/` klasörünü ASLA yeni bir zip ile
üzerine yazmayın, çünkü `config.php` sizin gerçek şifre/token'ınızı,
`data/` klasörü ise gerçek bekleyen/geçmiş içeriklerinizi tutuyor.

`data/` klasöründeki dosyalar (`pending.json`, `history.json`,
`trends.json`, `topics.json`, `*.flag`) otomatik olarak workflow'lar
tarafından oluşturulup güncellenir — elle bir şey yapmanıza gerek yok.

## Aylık maliyet tahmini

- Claude API (metin): ~$1-3/ay
- fal.ai / FLUX.1 [dev] (görsel): ~$0.75-1/ay
- GitHub Actions: private repo'da ayda 2.000 dakika ücretsiz — artık
  workflow'lar beklemeden (sleep) çalıştığı için bu kota fazlasıyla yeterli
- **Toplam: ~$2-4/ay**
