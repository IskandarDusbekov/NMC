# NMC Construction Management

`NMC` bu Django asosidagi qurilish kompaniyasi boshqaruv tizimi. Loyiha `namuna_uchun_dizayn.html` dagi light SaaS dashboard uslubidan ilhomlangan bo`lib, Telegram-only auth, company va manager walletlar, obyekt analytics, salary flow, audit log va hisobot qatlamlarini bitta monolit ilova ichida birlashtiradi.

## Asosiy imkoniyatlar

- Telegram-only auth: login sahifasi yo`q, kirish `access` token yoki Telegram Mini App verify orqali bajariladi.
- Ikki darajali moliya: `company` global balance va har bir `manager` uchun alohida operatsion wallet.
- UZS / USD alohida yuritiladi, majburiy konvertatsiya qilinmaydi.
- Obyektlarda real pul saqlanmaydi, ular analytic entity sifatida ishlaydi.
- Salary payment company yoki manager walletdan berilishi mumkin.
- Dashboard, manager hisoblari, audit log va Excel-friendly report export mavjud.

## Loyiha tuzilmasi

```text
apps/
  accounts/   Telegram auth, custom user, access token
  core/       shared mixins, layout context, seed command
  dashboard/  overview analytics
  finance/    ledger, manager wallet, transfer, exchange rate
  logs/       audit log
  objects/    construction object va work item
  reports/    filtered reports va export
  workforce/  worker va salary payment
config/
  settings/   base, dev, prod
templates/    Django templates
static/       CSS va minimal JS
```

## Ishga tushirish

1. Virtual environment yarating va aktiv qiling.
2. Dependency o`rnating:

```bash
pip install -r requirements.txt
```

3. `.env.example` dan nusxa olib `.env` yarating va qiymatlarni to`ldiring.

4. Migration yarating va qo`llang:

```bash
python manage.py makemigrations
python manage.py migrate
```

5. Demo ma`lumot kiritish ixtiyoriy:

```bash
python manage.py seed_demo
```

6. Development server:

```bash
python manage.py runserver
```

## Telegram auth

Tizimda oddiy username/password login sahifasi ishlatilmaydi. Asosiy endpointlar:

- `/accounts/telegram/`
- `/accounts/access/<token>/`
- `/accounts/telegram/verify/`
- `/accounts/telegram/webhook/`

Kerakli `.env` qiymatlari:

- `APP_BASE_URL`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_BOT_USERNAME`
- `TELEGRAM_WEBAPP_URL`
- `TELEGRAM_AUTH_MAX_AGE`
- `TELEGRAM_WEBHOOK_SECRET`

## Telegram bot

Bot oqimi:

1. User botga `/start` yuboradi.
2. Agar Telegram ID avvaldan userga bog`langan bo`lsa, bot darhol bir martalik kirish linkini yuboradi.
3. Agar bog`lanmagan bo`lsa, bot contact so`raydi.
4. Contact bazadagi `phone` bilan mos tushsa, user Telegram bilan bog`lanadi va kirish linki yuboriladi.
5. Bot `Saytga kirish` va `Mini App ochish` tugmalarini chiqaradi.

Lokalda polling bilan ishga tushirish:

```bash
python manage.py run_telegram_bot
```

Bir marta sinab ko`rish uchun:

```bash
python manage.py run_telegram_bot --once
```

Production uchun webhook endpoint tayyor:

```text
/accounts/telegram/webhook/
```

Shared hostingda polling botni terminal yopilgandan keyin ham orqada ishlatish:

```bash
mkdir -p logs
nohup python manage.py run_telegram_bot > logs/telegram_bot.log 2>&1 &
```

Bot ishlab turganini tekshirish:

```bash
ps aux | grep run_telegram_bot
tail -f logs/telegram_bot.log
```

Botni to`xtatish kerak bo`lsa `ps aux` dan chiqqan `PID` ni olib:

```bash
kill PID
```

Bot ichida ishlatiladigan commandlar:

- `/start`
- `/token`
- `/help`

## Moliya logikasi

### Company balance

- Company ledger faqat `COMPANY` wallet transactionlaridan hisoblanadi.
- `COMPANY_INCOME` balansni oshiradi.
- `COMPANY_EXPENSE` balansni kamaytiradi.
- `TRANSFER_TO_MANAGER` company balansdan ayriladi.
- `MANAGER_RETURN` company balansga qaytadi.

### Manager balance

- Har bir manager uchun `ManagerAccount` ochiladi.
- Director/Admin company balansdan managerga transfer qiladi.
- Manager expense faqat manager walletdan ayriladi.
- Manager expense company balansga qayta ta`sir qilmaydi.

## Kurs va backup

USD kursini CBU API orqali qo`lda yangilash:

```bash
python manage.py update_exchange_rate
```

Kursni hostingda avtomatik yangilash uchun cron jobga shunga o`xshash buyruq qo`ying:

```bash
0 */3 * * * cd /home/USER/NMC && /home/USER/virtualenv/NMC/3.12/bin/python manage.py update_exchange_rate --quiet
```

JSON backup olish:

```bash
python manage.py backup_data
```

Admin panelda ham yuqorida `JSON backup yuklab olish` tugmasi bor. Shu tugma bazani `.json` qilib yuklab beradi, keyin tiklash uchun:

```bash
python manage.py restore_data backups/nmc-backup-YYYYMMDD-HHMMSS.json
```

Har kuni avtomatik JSON backup saqlash uchun cron:

```bash
30 2 * * * cd /home/USER/NMC && /home/USER/virtualenv/NMC/3.12/bin/python manage.py backup_data --output-dir backups
```

## Demo seed

`python manage.py seed_demo` quyidagilarni yaratadi:

- `admin_demo`
- `director_demo`
- `manager_demo`
- namunaviy obyekt va work item
- company income
- manager transfer
- manager expense
- manager walletdan salary payment

Seed command qayta ishlatilsa mavjud yozuvlarni imkon qadar qayta ishlatadi.

## Testlar

Asosiy test qatlamlari yozilgan:

- transaction create va balance calculation
- manager transfer va manager expense flow
- salary payment transaction yaratishi
- object analytics
- role permissionlar

Ishga tushirish:

```bash
python manage.py test
```

## Production eslatmalar

- `config.settings.prod` dan foydalaning.
- HTTPS bilan ishlang.
- `DJANGO_SECRET_KEY` ni real qiymatga almashtiring.
- PostgreSQL uchun `DB_ENGINE=postgresql` ni yoqing.
- Telegram Mini App hash verify production token bilan tekshiriladi.
