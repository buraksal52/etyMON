# etyMON Tasarım Handoff

Bu doküman, tasarımın mevcut uygulama ile birebir eşleşmesi için hazırlanmıştır.
Tasarım veya frontend agent'ı bu dosyayı uygulama sözleşmesi olarak kabul etmelidir.
Yeni route, yeni mock veri veya dokümanda olmayan bir kullanıcı akışı eklenmemelidir.

## Ürün özeti

etyMON, bir organizer'ın event oluşturduğu, task havuzu hazırladığı ve
katılımcıların QR kod veya event code ile event'e katıldığı canlı event platformudur.

Temel akış:

```text
Admin login
  -> Event oluştur
  -> Task havuzu oluştur
  -> Publish / WAITING
  -> QR veya event code paylaş
  -> Katılımcılar email ile kuyruğa girsin
  -> Admin canlı sayaçları izlesin
  -> Start / ACTIVE
  -> Her katılımcıya rastgele weighted task atansın
  -> Proof gönderilsin
  -> Admin incelesin ve onaylasın
  -> Puan / leaderboard / reimbursement
  -> End / ENDED
```

Katılımcılar önceden oluşturulmaz. QR veya event code ile ilk kez katılan email
için participant ve event membership API tarafından oluşturulur. CSV import yoktur.

## Tasarım kuralları

- Mobile-first tasarım yapılmalı; katılımcı ekranları telefonda tek elle kullanılmalı.
- Admin ekranları masaüstü ve tablet için optimize edilmeli, mobilde de kırılmamalı.
- API'den gelmeyen event, participant, task veya skor mock olarak eklenmemeli.
- Loading, empty, error, disabled ve success durumları her veri ekranında tasarlanmalı.
- Event state kullanıcıya Türkçe açıklamayla gösterilmeli:
  - `DRAFT`: Taslak
  - `WAITING`: Katılım bekleniyor
  - `ACTIVE`: Event aktif
  - `ENDED`: Event sona erdi
- Katılımcı join yalnızca `WAITING` state'inde mümkündür.
- Task alma yalnızca `ACTIVE` state'inde mümkündür.
- Organizer'ın event başlamadan önce QR ve event code'u görebilmesi gerekir.
- QR kod ve event code aynı event'e gitmelidir. Event code event slug'dır.
- Event code formatı: küçük harf, rakam ve tire. Örnek: `bltz-istanbul`.

## Route envanteri

### Public / participant route'ları

| Route | Ekran | Tasarım amacı |
|---|---|---|
| `/` | Landing | Ürüne giriş ve event'e katılma yönlendirmesi |
| `/e` | Event code girişi | Organizer'ın verdiği kodu yazıp event'e gitme |
| `/e/[slug]` | Event giriş | Event adı, açıklaması ve email ile katılım |
| `/e/[slug]/waiting` | Bekleme kuyruğu | Event başlamasını bekleme, state bilgisi |
| `/e/[slug]/task` | Aktif task | Atanan görevi, puanı, talimatı ve proof gönderimini görme |
| `/e/[slug]/progress` | İlerleme | Participant skor ve assignment özetini görme |
| `/e/[slug]/leaderboard` | Leaderboard | Event sıralamasını görme |
| `/e/[slug]/reimbursement` | Masraf | Fiş/masraf gönderme ve durum takibi |
| `/e/[slug]/ended` | Event sonu | Event bitti bilgisini gösterme |

### Admin route'ları

| Route | Ekran | Tasarım amacı |
|---|---|---|
| `/admin/login` | Admin login | Organizer email ve password ile giriş |
| `/admin` | Event listesi | Organizer'ın event'lerini listeleme, yeni event başlatma |
| `/admin/events/new` | Event oluşturma | Event adı, slug, timezone ve task deadline oluşturma |
| `/admin/events/[id]` | Event dashboard | State kontrolü, QR/code, canlı sayaçlar ve yönetim navigasyonu |
| `/admin/events/[id]/participants` | Participant listesi | QR/code ile katılanları canlı listeleme |
| `/admin/events/[id]/tasks` | Task havuzu | Task oluşturma, düzenleme, aktif/pasif ve ağırlık yönetimi |
| `/admin/events/[id]/submissions` | Submission review | Proof inceleme, approve/reject ve not ekleme |
| `/admin/events/[id]/leaderboard` | Admin leaderboard | Event skorlarını inceleme |
| `/admin/events/[id]/reimbursements` | Reimbursement review | Masraf onaylama/reddetme ve paid işaretleme |

## Participant ekranları

### `/e` — Event code girişi

İçerik:

- Event code input
- `Continue` butonu
- QR ile katılma açıklaması
- Geçersiz veya bulunamayan code için hata

Submit sonrası `/e/[slug]` route'una gidilir. Code normalize edilir: trim ve
lowercase. Kullanıcı kodu bilmiyorsa QR ile doğrudan `/e/[slug]` açılır.

### `/e/[slug]` — Event giriş

İçerik:

- Event adı
- Event açıklaması
- Email input
- `Join event` butonu
- Loading: `Checking…`
- Event bulunamadı durumu
- Katılım kabul edilmiyorsa: `Event is not accepting entries`

Başarılı join sonrası API cookie oluşturur ve `/e/[slug]/waiting?eventId=...`
route'una yönlendirilir.

### Waiting

WAITING state'inde participant'ın bekleme ekranıdır. Şunlar gösterilebilir:

- Event adı
- `Waiting for organizer to start the event`
- Kuyrukta olduğuna dair görsel durum
- Event state değiştiğinde task ekranına geçiş
- Session veya event hatası

Participant bu ekrandan task almaya çalışmamalıdır. Admin Start'a basmadan task
atanmaz.

### Task

ACTIVE state'inde `/events/{event_id}/tasks/current` ile mevcut task alınır.
Mevcut task yoksa `POST /events/{event_id}/tasks/next` çağrılır.

Task kartında:

- Task title
- Description
- Instructions
- Points
- Proof type
- Başlangıç/bitiş zamanı varsa zaman bilgisi
- Çark/weighted random atama animasyonu yalnızca görsel katmandır; gerçek seçim API'de yapılır.
- Tek çözülmemiş task varsa yeni task butonu disabled olmalıdır.
- Task yoksa `No task is currently available` empty state gösterilir.

Proof gönderme:

- `IMAGE`: dosya yükleme
- `TEXT`: metin alanı
- `URL`: URL alanı
- Gönderim sonrası success ve review bekliyor durumu

### Progress

Gösterilecek özet alanları:

- Toplam puan
- Assigned
- Submitted
- Approved
- Rejected
- Total

### Leaderboard

API'den gelen gerçek sıralama gösterilir. Mock participant veya sabit skor
kullanılmamalıdır. Loading, boş leaderboard ve event ended durumları olmalıdır.

### Reimbursement

- Amount
- Currency
- Açıklama
- Receipt upload
- Gönderim sonrası `SUBMITTED`, `APPROVED`, `REJECTED`, `PAID` durumları
- Kullanıcı yalnızca kendi reimbursement kayıtlarını görür.

## Admin ekranları

### `/admin`

Event kartlarında:

- Event adı
- Slug / event code
- State badge
- Başlangıç ve deadline bilgisi
- Dashboard'a git butonu
- Yeni event oluştur butonu

Boş durumda mock event gösterilmez; `No events yet` ve `Create event` gösterilir.

### Event oluşturma

Alanlar:

- Event name
- Slug: `[a-z0-9]+(?:-[a-z0-9]+)*`
- Timezone
- Task deadline

Oluşturulan event başlangıçta `DRAFT` olur. Oluşturma sonrası event dashboard'a
gidilir. Event katılıma açılmadan önce task havuzu doldurulmalıdır.

### Event dashboard

Üst bölüm:

- Event adı
- State badge
- `Publish` — DRAFT -> WAITING
- `Start` — WAITING -> ACTIVE
- `End` — ACTIVE -> ENDED

Katılım kartı:

- Büyük QR kod
- Event code: event slug
- QR URL
- `Copy code`
- `Copy link`
- QR okutma açıklaması

Canlı metrik kartları:

- Registered participants
- Joined participants
- Waiting participants
- Active participants
- Active tasks
- Total assignments
- Total submissions
- Approved submissions

Dashboard verisi 3 saniyede bir yenilenebilir. WAITING state'inde checked-in
participant'lar `waitingParticipants`, ACTIVE state'inde `activeParticipants`
olarak gösterilir.

Alt navigasyon:

- Participants
- Tasks
- Submissions
- Leaderboard
- Reimbursements

### Participants

Bu ekran import ekranı değildir. Katılımcılar yalnızca QR/event code ile girer.

Her satır:

- Display name veya email
- Email
- Score
- Gerekirse eligibility/state

Empty state: `Participants will appear here after joining with QR or event code.`
Liste canlı yenilenebilir.

### Tasks

Task pool yönetimi:

- Title
- Description
- Instructions
- Points
- Proof type: IMAGE, TEXT veya URL
- Starts at
- Expires at
- Assignment weight
- Max assignments
- Active/inactive
- Create, edit, delete

Task havuzu boşsa event başlatma öncesinde uyarı gösterilmelidir. Backend task
seçimini weighted random yapar; frontend seçim sonucunu uydurmamalıdır.

### Submissions

Filtreler ve satır/karte:

- Participant
- Task
- Proof preview veya download link
- Submitted at
- Status
- Review note
- Approve
- Reject

Review kararları geri alınamaz varsayımıyla confirmation veya açık durum mesajı
gösterilmelidir.

### Leaderboard

- Sıra
- Participant
- Score
- Tie-break bilgisi backend sırasına göre korunmalı
- Gerçek API verisi dışında örnek sıra gösterilmemeli

### Reimbursements

- Participant
- Amount
- Currency
- Receipt
- Status
- Review note
- Approve / Reject
- Approved kaydı için Mark paid

## API eşleşmesi

Frontend API base URL'i `NEXT_PUBLIC_API_URL` değişkeninden alır. Cookie tabanlı
session için tüm isteklerde credentials korunmalıdır.

Participant API:

```text
GET  /events/{slug}
GET  /events/code/{code}
POST /events/{slug}/join              { email }
POST /events/code/{code}/join         { email }
GET  /events/{event_id}/status
GET  /events/{event_id}/me
GET  /events/{event_id}/progress
POST /events/{event_id}/tasks/next
GET  /events/{event_id}/tasks/current
POST /assignments/{assignment_id}/submit
GET  /events/{event_id}/leaderboard
POST /events/{event_id}/reimbursements
GET  /events/{event_id}/reimbursements/me
```

Admin API:

```text
POST /admin/login
GET  /admin/events
POST /admin/events
GET  /admin/events/{event_id}
PATCH /admin/events/{event_id}
GET  /admin/events/{event_id}/qr
POST /admin/events/{event_id}/start
POST /admin/events/{event_id}/end
GET  /admin/events/{event_id}/participants
POST /admin/events/{event_id}/tasks
GET  /admin/events/{event_id}/tasks
PATCH /admin/tasks/{task_id}
DELETE /admin/tasks/{task_id}
GET  /admin/events/{event_id}/submissions
POST /admin/submissions/{submission_id}/review
GET  /admin/events/{event_id}/leaderboard
GET  /admin/events/{event_id}/reimbursements
POST /admin/reimbursements/{reimbursement_id}/review
POST /admin/reimbursements/{reimbursement_id}/paid
```

## Deploy tasarım notları

Frontend Vercel'de, FastAPI + PostgreSQL + S3 uyumlu Railway Storage Railway'de
çalışır.

Vercel:

```text
NEXT_PUBLIC_API_URL=https://<railway-api-domain>
```

Railway:

```text
APP_ENV=production
APP_URL=https://<vercel-domain>
ALLOWED_ORIGINS=https://<vercel-domain>
DATABASE_URL=<railway-postgres-url>
SESSION_SECRET=<long-random-secret>
STORAGE_PROVIDER=railway
STORAGE_BUCKET=<bucket>
STORAGE_ENDPOINT=<s3-compatible-endpoint>
STORAGE_ACCESS_KEY=<access-key>
STORAGE_SECRET_KEY=<secret-key>
```

Railway `PORT` otomatik kullanılmalı. Migration deploy öncesi çalışır. QR'ın
yanlış localhost adresi üretmemesi için production'da `APP_URL` kesinlikle
Vercel adresi olmalıdır. Preview deployment kullanılacaksa ilgili preview
origin `ALLOWED_ORIGINS` içine ayrıca eklenmelidir.

## Agent için kesin kısıtlar

1. Mevcut route isimlerini değiştirme.
2. API field isimlerini değiştirme; özellikle `event_id` request alanları ve
   response içindeki camelCase alanları mevcut sözleşmeye göre kullan.
3. Mock participant, mock event, fake leaderboard veya sabit task ekleme.
4. CSV import ekranı veya CSV akışı ekleme.
5. QR ve event code'u ayrı event gibi ele alma; ikisi aynı slug'a gitmeli.
6. WAITING dışındaki event'lerde yeni participant join akışı gösterme.
7. ACTIVE olmadan task atama butonu gösterme.
8. Tasarımda loading, empty, error ve disabled state'leri eksik bırakma.
9. Backend'deki random task seçimini frontend'de tekrar uygulama.
10. Tasarım değişikliği sonrası `npm run build:web` ile doğrulama yap.

