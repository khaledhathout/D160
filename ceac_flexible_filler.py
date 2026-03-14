#!/usr/bin/env python3
"""مرشد تعبئة CEAC بشكل مرن مع ترقيم خطوات وحفظ HTML لكل خطوة.

الفكرة:
- تبدأ من أي خطوة عبر --start-step.
- كل خطوة لها رقم واضح ويمكن إعادة التشغيل منها.
- بعد كل خطوة يتم تنزيل HTML في مجلد dumps/ لتحليل الحقول لاحقًا.
- يدعم إدخال الكابتشا يدويًا مع مراقبة الثبات قبل الضغط على Start.
"""

from __future__ import annotations

import argparse
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Optional

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait


DEFAULT_URL = "https://ceac.state.gov/genniv/"
LOCATION_ID = "ctl00_SiteContentPlaceHolder_ucLocation_ddlLocation"
CAPTCHA_ID = "ctl00_SiteContentPlaceHolder_ucLocation_IdentifyCaptcha1_txtCodeTextBox"
START_BUTTON_ID = "ctl00_SiteContentPlaceHolder_lnkNew"
AGREE_CHECKBOX_ID = "ctl00_SiteContentPlaceHolder_chkbxPrivacyAct"
CAPTCHA_ERROR_TEXT = "The code entered does not match the code displayed on the page."


@dataclass
class Context:
    driver: webdriver.Chrome
    wait: WebDriverWait
    dump_dir: Path
    location_text: str
    url: str
    last_captcha_value: str = ""


StepFunc = Callable[[Context], None]


def save_html_dump(ctx: Context, step_no: int, label: str) -> None:
    """يحفظ HTML الحالي بصيغة مرقمة: 03_after_location.html"""
    ctx.dump_dir.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^a-zA-Z0-9_\-]+", "_", label.strip().lower())
    filename = f"{step_no:02d}_{safe}.html"
    output_file = ctx.dump_dir / filename
    output_file.write_text(ctx.driver.page_source, encoding="utf-8")
    print(f"[HTML] تم الحفظ: {output_file}")


def step_1_open_site(ctx: Context) -> None:
    print("\n=== [1] فتح الصفحة ===")
    ctx.driver.get(ctx.url)
    ctx.driver.maximize_window()
    save_html_dump(ctx, 1, "opened_home")


def step_2_select_location(ctx: Context) -> None:
    print("\n=== [2] اختيار موقع التقديم ===")
    location_dropdown = Select(
        ctx.wait.until(EC.presence_of_element_located((By.ID, LOCATION_ID)))
    )
    location_dropdown.select_by_visible_text(ctx.location_text)
    print(f"✅ تم اختيار الموقع: {ctx.location_text}")
    save_html_dump(ctx, 2, "after_location_selection")


def wait_for_stable_captcha_value(captcha_input, min_len: int = 5, stable_for_sec: float = 2.0) -> str:
    """يراقب الحقل حتى يصبح الإدخال ثابتًا لفترة معينة."""
    while True:
        current_value = (captcha_input.get_attribute("value") or "").strip()
        if len(current_value) >= min_len:
            stable_value = current_value
            stable_start = time.time()
            while True:
                time.sleep(0.3)
                new_value = (captcha_input.get_attribute("value") or "").strip()
                if new_value != stable_value:
                    stable_value = new_value
                    stable_start = time.time()
                if time.time() - stable_start >= stable_for_sec:
                    return stable_value
        time.sleep(0.3)


def step_3_captcha_and_start(ctx: Context) -> None:
    print("\n=== [3] الكابتشا + Start (يدوي/تلقائي) ===")
    while True:
        captcha_input = ctx.wait.until(EC.presence_of_element_located((By.ID, CAPTCHA_ID)))
        start_button = ctx.wait.until(EC.presence_of_element_located((By.ID, START_BUTTON_ID)))

        print("✍️ اكتب الكابتشا يدويًا، وسأنتظر ثبات الإدخال ثم أضغط Start.")
        final_value = wait_for_stable_captcha_value(captcha_input)

        if final_value == ctx.last_captcha_value:
            continue

        print(f"🔎 الكابتشا المعتمدة: {final_value}")
        captcha_input.send_keys(Keys.TAB)
        time.sleep(1)

        ctx.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", start_button)
        time.sleep(1)
        ctx.driver.execute_script("arguments[0].click();", start_button)
        print("🚀 تم الضغط على Start An Application")
        time.sleep(4)

        save_html_dump(ctx, 3, "after_start_attempt")

        if CAPTCHA_ERROR_TEXT in ctx.driver.page_source:
            print("❌ الكابتشا غير صحيحة. اكتب كابتشا جديدة.")
            ctx.last_captcha_value = final_value
            continue

        print("✅ تم تجاوز صفحة البداية بنجاح.")
        break


def step_4_check_privacy(ctx: Context) -> None:
    print("\n=== [4] تحديد I AGREE ===")
    agree_checkbox = ctx.wait.until(
        EC.presence_of_element_located((By.ID, AGREE_CHECKBOX_ID))
    )

    if not agree_checkbox.is_selected():
        ctx.driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});", agree_checkbox
        )
        time.sleep(1)
        ctx.driver.execute_script("arguments[0].click();", agree_checkbox)
        print("✅ تم تحديد I AGREE")
    else:
        print("ℹ️ I AGREE محدد مسبقًا")

    save_html_dump(ctx, 4, "after_agree")


def step_5_extract_app_id(ctx: Context) -> None:
    print("\n=== [5] استخراج Application ID ===")
    time.sleep(2)
    page_text = ctx.driver.page_source
    match = re.search(r"Your Application ID is:\s*([A-Z0-9]+)", page_text)

    if match:
        application_id = match.group(1)
        print(f"🆔 Application ID: {application_id}")
    else:
        print("⚠️ لم يتم استخراج Application ID تلقائيًا. راجع الصفحة.")

    save_html_dump(ctx, 5, "after_application_id")


def build_steps() -> Dict[int, StepFunc]:
    return {
        1: step_1_open_site,
        2: step_2_select_location,
        3: step_3_captcha_and_start,
        4: step_4_check_privacy,
        5: step_5_extract_app_id,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="تعبئة CEAC بخطوات مرقمة مع إمكانية البدء من أي خطوة وحفظ HTML"
    )
    parser.add_argument("--start-step", type=int, default=1, help="رقم الخطوة التي يبدأ منها")
    parser.add_argument(
        "--end-step",
        type=int,
        default=5,
        help="آخر خطوة يتم تنفيذها (مفيد للتجربة التدريجية)",
    )
    parser.add_argument("--dump-dir", default="dumps", help="مجلد حفظ ملفات HTML")
    parser.add_argument("--location", default="SAUDI ARABIA, RIYADH", help="نص موقع التقديم")
    parser.add_argument("--url", default=DEFAULT_URL, help="رابط صفحة البداية")
    parser.add_argument("--timeout", type=int, default=20, help="مهلة الانتظار بالثواني")
    parser.add_argument(
        "--keep-open",
        action="store_true",
        help="يبقي المتصفح مفتوحًا بعد التنفيذ حتى تضغط Enter",
    )
    return parser.parse_args()


def validate_step_range(start_step: int, end_step: int, available_steps: Dict[int, StepFunc]) -> None:
    valid_numbers = sorted(available_steps.keys())
    min_step, max_step = valid_numbers[0], valid_numbers[-1]

    if start_step < min_step or end_step > max_step or start_step > end_step:
        raise ValueError(
            f"نطاق خطوات غير صحيح. المسموح من {min_step} إلى {max_step} مع شرط start <= end"
        )


def main() -> None:
    args = parse_args()
    steps = build_steps()
    validate_step_range(args.start_step, args.end_step, steps)

    driver = webdriver.Chrome()
    wait = WebDriverWait(driver, args.timeout)
    ctx = Context(
        driver=driver,
        wait=wait,
        dump_dir=Path(args.dump_dir),
        location_text=args.location,
        url=args.url,
    )

    try:
        for step_no in sorted(steps.keys()):
            if args.start_step <= step_no <= args.end_step:
                steps[step_no](ctx)

        print("\n🎉 انتهى التنفيذ بنجاح.")
        if args.keep_open:
            input("اضغط Enter لإغلاق المتصفح...")

    except TimeoutException as exc:
        print(f"❌ Timeout أثناء التنفيذ: {exc}")
        save_html_dump(ctx, 99, "timeout_debug")
        raise
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
