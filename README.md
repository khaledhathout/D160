# CEAC Flexible Selenium Runner

سكريبت Selenium مرن لتعبئة CEAC بخطوات مرقمة، مع إمكانية البدء من أي خطوة وحفظ HTML بعد كل خطوة.

## المتطلبات
- Python 3.10+
- Google Chrome
- ChromeDriver متوافق مع إصدار Chrome
- مكتبة Selenium

```bash
pip install selenium
```

## التشغيل

```bash
python ceac_flexible_filler.py --start-step 1 --end-step 5 --dump-dir dumps
```

### خيارات مهمة
- `--start-step`: يبدأ من أي خطوة (مثال: `3`)
- `--end-step`: ينتهي عند خطوة معينة
- `--dump-dir`: مجلد حفظ ملفات HTML
- `--location`: موقع السفارة/القنصلية
- `--keep-open`: إبقاء المتصفح مفتوحًا حتى تضغط Enter

## الخطوات المرقمة
1. فتح الصفحة
2. اختيار موقع التقديم
3. انتظار إدخال الكابتشا يدويًا ثم الضغط التلقائي على Start
4. تحديد مربع I AGREE
5. استخراج Application ID

> بعد كل خطوة يتم حفظ ملف HTML مثل: `03_after_start_attempt.html` لاستخدامه لاحقًا لاكتشاف الحقول وبناء تعبئة تلقائية بالمتغيرات.
