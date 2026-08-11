# NURAI Dashboard — لوحة التحكم المركزية

لوحة تحكم لإدارة التنبيهات والمركبات والمحافظات العراقية ونماذج الذكاء الاصطناعي — تطبيق frontend مستقل يتصل بـ **Rasid API**.

## التشغيل السريع (Docker — المنفذ 9800)

```bash
# تأكد أن Rasid API يعمل على المنفذ 8000
docker compose up -d --build
```

افتح: **http://localhost:9800/login**

تسجيل الدخول الافتراضي (dev): `admin@aiops.com` / `admin123`

### متغيرات Docker

| المتغير | الافتراضي | الوصف |
|---------|-----------|--------|
| `API_BACKEND` | `host.docker.internal:8000` | عنوان Rasid API (بدون `http://`) |

مثال — API على خادم آخر:

```bash
API_BACKEND=192.168.1.10:8000 docker compose up -d --build
```

### أوامر مفيدة

```bash
docker compose logs -f dashboard
docker compose down
docker build -t nurai-dashboard .
docker run -p 9800:9800 -e API_BACKEND=host.docker.internal:8000 --add-host=host.docker.internal:host-gateway nurai-dashboard
```

## التطوير المحلي

```bash
npm install
cp .env.example .env.local   # اختياري
npm run dev
```

يفتح Vite على **http://localhost:5174** مع proxy إلى API.

## الميزات

- **مركز العمليات** — خريطة تكتيكية، KPIs، فلاتر، تفاصيل التنبيه
- **التنبيهات** — مصنّفة حسب الجهة (بلدية، مرور، إسعاف، …)
- **الخريطة الحية** — WebSocket للتحديث الفوري
- **الأسطول** — 10 مركبات بغداد (بيانات العرض)
- **التحليلات والتقارير**
- **مختبر AI** — اختبار YOLO على صور/فيديو
- **نماذج AI** — رفع وتفعيل `.pt` / `.onnx`

## API المطلوبة

اللوحة تتصل بـ Rasid Backend عبر:

| Endpoint | الغرض |
|----------|--------|
| `POST /api/v1/auth/login` | تسجيل الدخول |
| `GET /api/v1/control-center/{project}/overview` | KPIs |
| `GET /api/v1/road-intelligence/{project}/events` | التنبيهات |
| `WS /api/v1/ws/road-intelligence/{project}` | تحديثات حية |
| `GET /api/v1/fleet/{project}` | المركبات |
| `POST /api/v1/control-center/{project}/demo/seed` | بيانات العرض |

في Docker، nginx يوجّه `/api` و `/health` و `/uploads` و WebSocket إلى `API_BACKEND`.

## البنية

```
├── src/              # React + TypeScript + Vite
├── nginx/            # قالب nginx للإنتاج
├── Dockerfile        # بناء multi-stage
├── docker-compose.yml
└── docker-entrypoint.sh
```

## ملاحظات

- صفحة **الإعدادات** مخفية من القائمة (إدارة النظام من Rasid Console / API).
- تحميل **بيانات العرض** متاح من بانر «تحميل الآن» في النظرة العامة عند غياب البيانات.
- مركز الخريطة الافتراضي: بغداد · 18 محافظة عراقية.
