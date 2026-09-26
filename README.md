# etyMON

![etyMON — The room is waiting for you](docs/assets/etyMON-hero.svg)

> QR veya event code ile katıl. Bekleme kuyruğuna gir. Organizer event'i
> başlattığında rastgele task'ını al.

etyMON; organizer'ların event oluşturduğu, task havuzu hazırladığı ve
katılımcıların QR kod veya event code ile canlı event akışına katıldığı,
mobile-first bir platformdur.

## İçindekiler

- [Ürün akışı](#ürün-akışı)
- [Admin ve katılımcı farkı](#admin-ve-katılımcı-farkı)
- [Mimari](#mimari)
- [Local kurulum](#local-kurulum)
- [Canlı demo](#canlı-demo)
- [Route haritası](#route-haritası)
- [API özeti](#api-özeti)
- [Vercel ve Railway deploy](#vercel-ve-railway-deploy)
- [Monad ödül altyapısı](#monad-ödül-altyapısı)
- [Test ve güvenlik](#test-ve-güvenlik)
- [Dokümantasyon](#dokümantasyon)

## Ürün akışı

```mermaid
flowchart TD
    A[Admin login] --> B[Event oluştur]
    B --> C[Task havuzu oluştur]
    C --> D[Publish: DRAFT → WAITING]
    D --> E[QR + event code paylaş]
    E --> F[Katılımcı QR tarar veya code girer]
    F --> G[Email ile join]
    G --> H[Waiting queue]
    H --> I{Admin Start?}
    I -- Hayır --> H
    I -- Evet --> J[ACTIVE]
    J --> K[Weighted random task]
    K --> L[Proof gönder]
    L --> M[Admin review]
    M --> N[Approve / Reject]
    N --> O[Skor + leaderboard]
    O --> P[Event End]
```

Temel kurallar:

- Katılımcı önceden oluşturulmaz; ilk join sırasında kayıt edilir.
- QR ve event code aynı event slug'ını çözer.
- Yeni katılım yalnızca `WAITING` durumunda açıktır.
- Task alma yalnızca `ACTIVE` durumunda açıktır.
- Task seçimi backend tarafından weighted random yapılır.
- CSV import veya mock participant/event/task yoktur.

## Admin ve katılımcı farkı

```mermaid
flowchart LR
    subgraph ADMIN[Organizer / Admin]
        A1[Login] --> A2[Event oluştur] --> A3[Task havuzu]
        A3 --> A4[QR + code] --> A5[Canlı sayaç] --> A6[Start / End]
        A6 --> A7[Proof review] --> A8[Leaderboard / reimbursement]
    end
    subgraph USER[Participant]
        P1[QR tara veya code gir] --> P2[Email ile katıl]
        P2 --> P3[Waiting] --> P4[Random task] --> P5[Proof gönder]
        P5 --> P6[Progress / leaderboard]
    end
    A4 -. paylaşır .-> P1
    A6 -. event başlar .-> P4
    P5 -. submission .-> A7
```

| Admin | Katılımcı |
|---|---|
| Event ve task havuzu oluşturur | QR veya event code ile girer |
| Event'i publish eder | Email ile kuyruğa katılır |
| QR/code paylaşır | Event başlayana kadar bekler |
| Sayaçları izler | Backend'in atadığı task'ı yapar |
| Event'i başlatır/bitirir | Proof gönderir |
| Submission ve masraf inceler | Progress ve leaderboard görür |

## Mimari

```mermaid
flowchart TB
    B[Browser: Next.js] --> V[Vercel]
    B --> API[FastAPI API]
    API --> R[Railway]
    R --> DB[(Railway PostgreSQL)]
    API --> S[(S3-compatible Storage)]
    API -. opsiyonel reward .-> M[(Monad RewardPool)]
```

| Katman | Teknoloji | Sorumluluk |
|---|---|---|
| Web | Next.js, React, TypeScript | Admin ve participant ekranları |
| API | FastAPI, Python | Auth, event state, task, proof, review |
| Database | PostgreSQL, SQLAlchemy, Alembic | Kalıcı domain verisi |
| Storage | S3-compatible provider | Proof ve receipt dosyaları |
| Blockchain | Solidity, Foundry, Web3.py | Opsiyonel native MON ödülü |
| Hosting | Vercel + Railway | Web, API, DB ve storage |

## Local kurulum

### Gereksinimler

- Node.js 24+
- npm 11+
- Python 3.12+
- Docker Desktop
- Foundry — yalnız Monad contract işlemleri için

### Kurulum

```bash
git clone https://github.com/buraksal52/etyMON.git
cd etyMON
npm install
docker compose up -d postgres
python3 -m venv apps/api/.venv
source apps/api/.venv/bin/activate
pip install -r apps/api/requirements.txt
cp .env.example .env
./scripts/migrate.sh
```

`.env` için local temel değerler:

```env
APP_ENV=development
APP_URL=http://localhost:3000
ALLOWED_ORIGINS=http://localhost:3000
DATABASE_URL=postgresql+psycopg://platform:platform@localhost:5432/platform
NEXT_PUBLIC_API_URL=http://localhost:8000
STORAGE_PROVIDER=local
```

Seed komutu demo veri eklemez; yalnızca mevcut sayıları raporlar:

```bash
apps/api/.venv/bin/python apps/api/seed.py
```

### Gerçek admin oluşturma

```bash
python scripts/create_admin.py \
  --email admin@example.com \
  --name "Event Admin"
```

Komut password'u terminalde sorar. Admin hesabı seed ile oluşturulmaz.

### Servisleri başlatma

API terminali:

```bash
uvicorn app.main:app --app-dir apps/api --reload --port 8000
```

Web terminali:

```bash
npm run dev:web
```

Kontroller:

```text
API health: http://localhost:8000/health
Admin:      http://localhost:3000/admin/login
Code giriş: http://localhost:3000/e
```

## Canlı demo rehberi

### Admin adımları

1. `/admin/login` üzerinden giriş yap.
2. `Create event` ile event oluştur.
3. Event name, küçük harfli slug, timezone ve task deadline gir.
4. `Tasks` ekranından task havuzunu oluştur.
5. `Publish` seç. Event durumu `WAITING` olur.
6. Dashboard'daki QR kodu veya event code'u paylaş.
7. Waiting ve joined participant sayaçlarını izle.
8. Hazır olduğunda `Start` seç. Event durumu `ACTIVE` olur.
9. Submission geldikçe `Submissions` ekranından incele.
10. Approve veya reject kararı ver.
11. Event sonunda `End` seç.

### Katılımcı adımları

1. QR kodu tara veya `/e` sayfasını aç.
2. Organizer'ın verdiği event code'u yaz.
3. Event ekranında email adresini gir.
4. `Join event` seçeneğine bas.
5. Event başlayana kadar waiting ekranında kal.
6. Admin Start'a bastığında task ekranına geç.
7. Task'ı tamamla ve proof gönder.
8. Progress ve leaderboard ekranlarından durumunu takip et.

Geçerli event code örneği:

```text
bltz-istanbul
```

Slug yalnızca küçük harf, rakam ve tire içermelidir. `bltz istanbul` geçerli
değildir.

## Route haritası

### Participant route'ları

```text
/                         Landing
/e                        Event code girişi
/e/[slug]                 Email ile event girişi
/e/[slug]/waiting         Bekleme ekranı
/e/[slug]/task            Aktif task ve proof
/e/[slug]/progress        Participant progress
/e/[slug]/leaderboard     Participant leaderboard
/e/[slug]/reimbursement   Masraf gönderimi
/e/[slug]/ended           Event sonu
```

### Admin route'ları

```text
/admin                            Event listesi
/admin/login                      Admin login
/admin/events/new                 Event oluşturma
/admin/events/[id]                Event dashboard
/admin/events/[id]/participants   Katılımcılar
/admin/events/[id]/tasks          Task havuzu
/admin/events/[id]/submissions    Submission review
/admin/events/[id]/leaderboard    Admin leaderboard
/admin/events/[id]/reimbursements Masraf review
```

Dashboard'da event state, Publish/Start/End, QR, event code ve şu canlı
metrikler bulunur: registered, joined, waiting, active participants, active
tasks, assignments, submissions ve approved submissions.

## API özeti

Frontend `NEXT_PUBLIC_API_URL` üzerinden FastAPI'ye bağlanır. Cookie tabanlı
session için credentials korunur.

### Participant

```text
GET  /events/{slug}
GET  /events/code/{code}
POST /events/{slug}/join
POST /events/code/{code}/join
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

### Admin

```text
POST  /admin/login
GET   /admin/events
POST  /admin/events
GET   /admin/events/{event_id}
PATCH /admin/events/{event_id}
GET   /admin/events/{event_id}/qr
POST  /admin/events/{event_id}/start
POST  /admin/events/{event_id}/end
GET   /admin/events/{event_id}/participants
POST  /admin/events/{event_id}/tasks
GET   /admin/events/{event_id}/tasks
PATCH /admin/tasks/{task_id}
DELETE /admin/tasks/{task_id}
GET   /admin/events/{event_id}/submissions
POST  /admin/submissions/{submission_id}/review
GET   /admin/events/{event_id}/leaderboard
GET   /admin/events/{event_id}/reimbursements
POST  /admin/reimbursements/{reimbursement_id}/review
POST  /admin/reimbursements/{reimbursement_id}/paid
```

## Vercel ve Railway deploy

### Vercel

Vercel project root olarak repository root veya `apps/web` kullanılabilir.
Build command her iki durumda da:

```text
npm run build
```

Install command:

```text
npm install
```

Production environment variable:

```env
NEXT_PUBLIC_API_URL=https://<railway-api-domain>
```

Bu değer build sırasında frontend'e gömüldüğü için değişiklikten sonra
redeploy gerekir. `localhost` production frontend'den çalışmaz.

### Railway

Railway repository root'tan build edilmelidir. `railway.toml` Dockerfile,
migration, healthcheck ve start command'ı tanımlar.

```env
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

Railway `PORT` değerini otomatik sağlar. Deploy loglarında Alembic migration
ve `/health` için `200 OK` görülmelidir. `APP_URL` production'da localhost
olmamalıdır; QR URL'si bu değerden üretilir. Vercel domain'i `ALLOWED_ORIGINS`
içinde birebir bulunmalıdır.

## Monad ödül altyapısı

Monad opsiyoneldir; event, task, submission ve leaderboard akışı blockchain
olmadan da çalışır.

```text
Network:  Monad Testnet
Chain ID: 10143
RPC:      https://testnet-rpc.monad.xyz
Explorer: https://testnet.monadscan.com
Faucet:   https://faucet.monad.xyz
```

Contract test ve deploy:

```bash
forge test --root packages/contracts
export MONAD_RPC_URL="https://testnet-rpc.monad.xyz"
export MONAD_CHAIN_ID="10143"
export DEPLOYER_PRIVATE_KEY="<local-only-private-key>"

forge script packages/contracts/script/DeployRewardPool.s.sol:DeployRewardPool \
  --rpc-url "$MONAD_RPC_URL" \
  --private-key "$DEPLOYER_PRIVATE_KEY" \
  --broadcast
```

Deploy sonrası RewardPool'a native MON yatırılır ve backend signer authorized
yapılır. Private key frontend'e, Git'e, README'ye veya sohbet mesajına yazılmaz.

## Test ve güvenlik

```bash
PYTHONPATH=apps/api apps/api/.venv/bin/pytest -q
npm run build:web
forge test --root packages/contracts
git diff --check
```

Minimum demo doğrulaması:

1. API `/health` 200 döner.
2. Admin login çalışır.
3. Admin event oluşturur.
4. Task havuzu oluşturulur.
5. Event publish edilir.
6. QR ve event code aynı event'i açar.
7. Katılımcı waiting ekranına girer.
8. Admin start edince task atanır.
9. Proof gönderilir.
10. Admin submission'ı review eder.

Gizli dosyalar commit edilmez: `.env`, private key, session secret, Railway
credentials, `broadcast/` ve `cache/`.

## Dokümantasyon

- [Tasarım handoff](docs/DESIGN_HANDOFF.md)
- [Teknik spesifikasyon](docs/TECHNICAL_SPEC.md)
- [Proje özeti](docs/PROJECT_BRIEF.md)
- [Agent execution plan](docs/AGENT_EXECUTION_PLAN.md)
