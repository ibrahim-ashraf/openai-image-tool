import base64
import csv
import mimetypes
import os
import sys
import urllib.request
import json
from datetime import datetime
from pathlib import Path

from openai import OpenAI


# ============================================================
# إعدادات البرنامج
# ============================================================

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

COST_LOG = OUTPUT_DIR / "cost_log.csv"

# نموذج وصف الصور
VISION_MODEL = "gpt-6-astra"

# أسعار GPT Image 2.5 الحالية
IMAGE_INPUT_PRICE = 8.00       # دولار لكل مليون image tokens
IMAGE_CACHED_PRICE = 2.00      # دولار لكل مليون cached image tokens
IMAGE_OUTPUT_PRICE = 30.00     # دولار لكل مليون image tokens

TEXT_INPUT_PRICE = 5.00        # دولار لكل مليون text tokens
TEXT_CACHED_PRICE = 1.25       # دولار لكل مليون cached text tokens

# أسعار gpt-6-astra
VISION_INPUT_PRICE = 10.00     # دولار لكل مليون input tokens
VISION_CACHED_PRICE = 1.00     # دولار لكل مليون cached input tokens
VISION_OUTPUT_PRICE = 50.00    # دولار لكل مليون output tokens

# سعر افتراضي احتياطي فقط إذا تعذر جلب سعر الصرف.
# لن نستخدمه إلا إذا وافق المستخدم.
DEFAULT_USD_EGP = 52.0

IMAGE_EXTENSIONS = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


# ============================================================
# أدوات عامة
# ============================================================

def ask_choice(title, choices, default=None):
    print()
    print(title)

    for i, (_, label) in enumerate(choices, 1):
        marker = " [الافتراضي]" if default == i else ""
        print(f"{i}. {label}{marker}")

    while True:
        value = input("اختيارك: ").strip()

        if not value and default is not None:
            return choices[default - 1][0]

        try:
            number = int(value)

            if 1 <= number <= len(choices):
                return choices[number - 1][0]

        except ValueError:
            pass

        print("اختيار غير صالح. حاول مرة أخرى.")


def ask_integer(prompt, minimum, maximum, default=None):
    while True:
        suffix = f" [{default}]" if default is not None else ""
        value = input(f"{prompt}{suffix}: ").strip()

        if not value and default is not None:
            return default

        try:
            number = int(value)

            if minimum <= number <= maximum:
                return number

        except ValueError:
            pass

        print(
            f"أدخل رقمًا صحيحًا بين {minimum} و{maximum}."
        )


def ask_existing_image(prompt):
    while True:
        path = input(prompt).strip().strip('"')

        if not path:
            print("يجب إدخال مسار الصورة.")
            continue

        file_path = Path(path)

        if not file_path.is_file():
            print("الملف غير موجود.")
            continue

        if file_path.suffix.lower() not in IMAGE_EXTENSIONS:
            print(
                "صيغة الصورة غير مدعومة. "
                "استخدم PNG أو JPEG أو WebP أو GIF."
            )
            continue

        return file_path


def ask_multiple_images():
    print()
    print("أدخل مسارات الصور واحدًا في كل سطر.")
    print("اضغط Enter في سطر فارغ عند الانتهاء.")

    images = []

    while True:
        path = input(
            f"الصورة {len(images) + 1}: "
        ).strip().strip('"')

        if not path:
            break

        file_path = Path(path)

        if not file_path.is_file():
            print("الملف غير موجود.")
            continue

        if file_path.suffix.lower() not in IMAGE_EXTENSIONS:
            print(
                "صيغة الصورة غير مدعومة."
            )
            continue

        images.append(file_path)

    return images


def file_to_data_url(path):
    mime_type = IMAGE_EXTENSIONS.get(
        path.suffix.lower(),
        mimetypes.guess_type(path.name)[0]
        or "application/octet-stream"
    )

    encoded = base64.b64encode(
        path.read_bytes()
    ).decode("ascii")

    return f"data:{mime_type};base64,{encoded}"


def save_base64_image(base64_data, path):
    path.write_bytes(
        base64.b64decode(base64_data)
    )


def output_extension(output_format):
    return {
        "png": ".png",
        "jpeg": ".jpg",
        "webp": ".webp",
    }[output_format]


# ============================================================
# خيارات الصور
# ============================================================

def choose_image_model():
    return ask_choice(
        "اختر نموذج توليد الصور:",
        [
            (
                "gpt-image-2.5-sunburst",
                "gpt-image-2.5-sunburst - تحرير دقيق"
            ),
            (
                "gpt-image-2.5-flare",
                "gpt-image-2.5-flare - سريع وعالي الجودة"
            ),
        ],
        default=1,
    )


def choose_size():
    return ask_choice(
        "الحجم والاتجاه:",
        [
            ("auto", "تلقائي"),
            ("1024x1024", "مربع - 1024 × 1024"),
            ("1024x1536", "عمودي - 1024 × 1536"),
            ("1536x1024", "أفقي - 1536 × 1024"),
        ],
        default=1,
    )


def choose_quality():
    return ask_choice(
        "الجودة:",
        [
            ("auto", "Auto"),
            ("high", "High"),
            ("medium", "Medium"),
            ("low", "Low"),
            ("max", "Max"),
            ("xhigh", "Extra high / XHigh"),
        ],
        default=1,
    )


def choose_output_format():
    return ask_choice(
        "تنسيق الإخراج:",
        [
            ("png", "PNG"),
            ("jpeg", "JPEG"),
            ("webp", "WebP"),
        ],
        default=1,
    )


def choose_background():
    return ask_choice(
        "الخلفية:",
        [
            ("auto", "Auto"),
            ("transparent", "Transparent - شفافة"),
            ("opaque", "Opaque - معتمة"),
        ],
        default=1,
    )


def choose_moderation():
    return ask_choice(
        "Moderation:",
        [
            ("auto", "Auto"),
            ("low", "Low"),
        ],
        default=1,
    )


def choose_partial_images():
    return ask_choice(
        "Partial images:",
        [
            (0, "None - بدون صور جزئية"),
            (1, "1 صورة جزئية"),
            (2, "2 صورتان جزئيتان"),
            (3, "3 صور جزئية"),
        ],
        default=1,
    )


# ============================================================
# سعر الدولار مقابل الجنيه المصري
# ============================================================

def get_usd_egp_rate():
    """
    يحاول جلب سعر USD/EGP من خدمة عامة.

    نستخدم exchangerate.host كخيار أول.
    إذا فشل الاتصال، نرجع None.
    """

    urls = [
        "https://api.frankfurter.app/latest?from=USD&to=EGP",
        "https://open.er-api.com/v6/latest/USD",
    ]

    for url in urls:
        try:
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "OpenAI-Image-Tool/1.0"
                }
            )

            with urllib.request.urlopen(
                request,
                timeout=8
            ) as response:

                data = json.loads(
                    response.read().decode("utf-8")
                )

            if "rates" in data:
                rate = data["rates"].get("EGP")

                if rate:
                    return float(rate)

        except Exception:
            continue

    return None


def choose_egp_rate():
    print()
    print("جارٍ جلب سعر الدولار مقابل الجنيه المصري...")

    rate = get_usd_egp_rate()

    if rate:
        print(
            f"سعر الصرف المستخدم: "
            f"1 USD = {rate:.4f} EGP"
        )
        return rate

    print(
        "تعذر جلب سعر الصرف تلقائيًا."
    )

    choice = ask_choice(
        "ماذا تريد أن أفعل؟",
        [
            (
                "manual",
                "إدخال سعر الدولار يدويًا"
            ),
            (
                "default",
                f"استخدام السعر الاحتياطي "
                f"({DEFAULT_USD_EGP} جنيه)"
            ),
            (
                "none",
                "عدم عرض التكلفة بالجنيه"
            ),
        ],
        default=1,
    )

    if choice == "manual":
        while True:
            value = input(
                "أدخل سعر 1 دولار بالجنيه المصري: "
            ).strip()

            try:
                rate = float(value)

                if rate > 0:
                    return rate

            except ValueError:
                pass

            print("أدخل رقمًا صحيحًا أكبر من صفر.")

    if choice == "default":
        return DEFAULT_USD_EGP

    return None


# ============================================================
# استخراج usage من استجابة API
# ============================================================

def get_attr(obj, name, default=0):
    """
    يعمل مع كائنات OpenAI وكذلك القواميس.
    """
    if obj is None:
        return default

    if isinstance(obj, dict):
        return obj.get(name, default)

    return getattr(obj, name, default)


def get_usage_value(usage, name, default=0):
    return get_attr(usage, name, default)


def extract_image_usage(response):
    """
    استخراج استخدام GPT Image 2.5.

    نحاول أولًا الحصول على التفاصيل الدقيقة:
    image input
    text input
    cached input
    image output

    وإذا لم تتوفر التفاصيل، نستخدم القيم العامة
    بحذر ونوضح ذلك للمستخدم.
    """

    usage = get_attr(response, "usage", None)

    if usage is None:
        return {
            "image_input": 0,
            "image_cached_input": 0,
            "text_input": 0,
            "text_cached_input": 0,
            "image_output": 0,
            "available": False,
            "detailed": False,
        }

    input_details = get_attr(
        usage,
        "input_tokens_details",
        None
    )

    output_details = get_attr(
        usage,
        "output_tokens_details",
        None
    )

    image_input = get_attr(
        input_details,
        "image_tokens",
        0
    )

    text_input = get_attr(
        input_details,
        "text_tokens",
        0
    )

    cached_input = get_attr(
        input_details,
        "cached_tokens",
        0
    )

    image_output = get_attr(
        output_details,
        "image_tokens",
        0
    )

    # إذا لم تتوفر التفاصيل الفرعية،
    # نحاول قراءة total input/output.
    total_input = get_usage_value(
        usage,
        "input_tokens",
        0
    )

    total_output = get_usage_value(
        usage,
        "output_tokens",
        0
    )

    detailed = bool(
        image_input
        or text_input
        or image_output
    )

    return {
        "image_input": image_input,
        "image_cached_input": cached_input,
        "text_input": text_input,
        "text_cached_input": 0,
        "image_output": image_output,
        "total_input": total_input,
        "total_output": total_output,
        "available": True,
        "detailed": detailed,
    }


def extract_vision_usage(response):
    usage = get_attr(response, "usage", None)

    if usage is None:
        return {
            "input": 0,
            "cached_input": 0,
            "output": 0,
            "available": False,
        }

    input_tokens = get_usage_value(
        usage,
        "input_tokens",
        0
    )

    output_tokens = get_usage_value(
        usage,
        "output_tokens",
        0
    )

    details = get_attr(
        usage,
        "input_tokens_details",
        None
    )

    cached = get_attr(
        details,
        "cached_tokens",
        0
    )

    return {
        "input": input_tokens,
        "cached_input": cached,
        "output": output_tokens,
        "available": True,
    }


# ============================================================
# حساب تكلفة الصور
# ============================================================

def calculate_image_cost(usage):
    if not usage["available"]:
        return None

    image_input_cost = (
        usage["image_input"]
        / 1_000_000
        * IMAGE_INPUT_PRICE
    )

    cached_image_cost = (
        usage["image_cached_input"]
        / 1_000_000
        * IMAGE_CACHED_PRICE
    )

    text_input_cost = (
        usage["text_input"]
        / 1_000_000
        * TEXT_INPUT_PRICE
    )

    cached_text_cost = (
        usage["text_cached_input"]
        / 1_000_000
        * TEXT_CACHED_PRICE
    )

    image_output_cost = (
        usage["image_output"]
        / 1_000_000
        * IMAGE_OUTPUT_PRICE
    )

    total = (
        image_input_cost
        + cached_image_cost
        + text_input_cost
        + cached_text_cost
        + image_output_cost
    )

    return {
        "image_input_cost": image_input_cost,
        "cached_image_cost": cached_image_cost,
        "text_input_cost": text_input_cost,
        "cached_text_cost": cached_text_cost,
        "image_output_cost": image_output_cost,
        "total": total,
    }


def calculate_vision_cost(usage):
    if not usage["available"]:
        return None

    normal_input = max(
        usage["input"] - usage["cached_input"],
        0
    )

    input_cost = (
        normal_input
        / 1_000_000
        * VISION_INPUT_PRICE
    )

    cached_cost = (
        usage["cached_input"]
        / 1_000_000
        * VISION_CACHED_PRICE
    )

    output_cost = (
        usage["output"]
        / 1_000_000
        * VISION_OUTPUT_PRICE
    )

    return {
        "input_cost": input_cost,
        "cached_cost": cached_cost,
        "output_cost": output_cost,
        "total": (
            input_cost
            + cached_cost
            + output_cost
        ),
    }


# ============================================================
# عرض التكلفة
# ============================================================

def show_image_cost(
    model,
    usage,
    generated_count,
    partial_images=0
):
    print()
    print("=" * 60)
    print("تكلفة العملية")
    print("=" * 60)

    print()
    print(f"النموذج: {model}")

    if not usage["available"]:
        print()
        print(
            "لم تُرجع الاستجابة معلومات usage."
        )
        print(
            "لذلك لا يمكن حساب التكلفة الفعلية "
            "لهذه العملية بدقة من الاستجابة."
        )
        print("=" * 60)
        return None

    print()
    print(
        f"Image input tokens : "
        f"{usage.get('image_input', 0):,}"
    )

    print(
        f"Cached image input : "
        f"{usage.get('image_cached_input', 0):,}"
    )

    print(
        f"Text input tokens  : "
        f"{usage.get('text_input', 0):,}"
    )

    print(
        f"Image output tokens: "
        f"{usage.get('image_output', 0):,}"
    )

    if partial_images:
        print(
            f"Partial images     : "
            f"{partial_images}"
        )

    cost = calculate_image_cost(usage)

    if cost is None:
        return None

    print()
    print(
        f"تكلفة image input : "
        f"${cost['image_input_cost']:.6f}"
    )

    print(
        f"تكلفة cached image: "
        f"${cost['cached_image_cost']:.6f}"
    )

    print(
        f"تكلفة text input  : "
        f"${cost['text_input_cost']:.6f}"
    )

    print(
        f"تكلفة image output: "
        f"${cost['image_output_cost']:.6f}"
    )

    print("-" * 60)

    print(
        f"إجمالي تكلفة العملية: "
        f"${cost['total']:.6f}"
    )

    if generated_count > 0:
        average = (
            cost["total"]
            / generated_count
        )

        print(
            f"متوسط تكلفة الصورة: "
            f"${average:.6f}"
        )

    rate = choose_egp_rate()

    if rate:
        egp_total = cost["total"] * rate

        print()
        print(
            f"إجمالي التكلفة بالجنيه: "
            f"{egp_total:.4f} جنيه"
        )

        if generated_count > 0:
            print(
                f"متوسط تكلفة الصورة: "
                f"{egp_total / generated_count:.4f} جنيه"
            )

    print("=" * 60)

    return cost


def show_vision_cost(
    usage,
    image_count
):
    print()
    print("=" * 60)
    print("تكلفة تحليل الصور")
    print("=" * 60)

    if not usage["available"]:
        print(
            "لم تتوفر معلومات usage؛ "
            "لا يمكن حساب التكلفة الفعلية."
        )
        print("=" * 60)
        return None

    print()
    print(
        f"عدد الصور المدخلة: "
        f"{image_count}"
    )

    print(
        f"Input tokens : "
        f"{usage['input']:,}"
    )

    print(
        f"Cached input : "
        f"{usage['cached_input']:,}"
    )

    print(
        f"Output tokens: "
        f"{usage['output']:,}"
    )

    cost = calculate_vision_cost(usage)

    print()
    print(
        f"تكلفة الإدخال: "
        f"${cost['input_cost']:.6f}"
    )

    print(
        f"تكلفة الإدخال المخزن: "
        f"${cost['cached_cost']:.6f}"
    )

    print(
        f"تكلفة الإخراج: "
        f"${cost['output_cost']:.6f}"
    )

    print("-" * 60)

    print(
        f"إجمالي تكلفة الوصف: "
        f"${cost['total']:.6f}"
    )

    rate = choose_egp_rate()

    if rate:
        egp = cost["total"] * rate

        print(
            f"بالجنيه المصري: "
            f"{egp:.4f} جنيه"
        )

    print("=" * 60)

    return cost


# ============================================================
# سجل التكاليف
# ============================================================

def save_cost_log(
    operation,
    model,
    cost_usd,
    cost_egp=None,
    generated_count=0,
    input_count=0
):
    file_exists = COST_LOG.exists()

    with open(
        COST_LOG,
        "a",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        writer = csv.writer(file)

        if not file_exists:
            writer.writerow([
                "التاريخ",
                "العملية",
                "النموذج",
                "الصور المدخلة",
                "الصور الناتجة",
                "التكلفة بالدولار",
                "التكلفة بالجنيه المصري",
            ])

        writer.writerow([
            datetime.now().isoformat(
                timespec="seconds"
            ),
            operation,
            model,
            input_count,
            generated_count,
            f"{cost_usd:.8f}",
            (
                f"{cost_egp:.8f}"
                if cost_egp is not None
                else ""
            ),
        ])


# ============================================================
# حفظ الصور الناتجة
# ============================================================

def save_generated_images(
    data,
    output_format
):
    extension = output_extension(
        output_format
    )

    saved = 0

    for item in data:
        base64_data = get_attr(
            item,
            "b64_json",
            None
        )

        if not base64_data:
            continue

        saved += 1

        filename = (
            OUTPUT_DIR
            / f"generated_{datetime.now():%Y%m%d_%H%M%S}_{saved}"
            f"{extension}"
        )

        save_base64_image(
            base64_data,
            filename
        )

        print(
            f"تم حفظ الصورة {saved}: "
            f"{filename}"
        )

    return saved


# ============================================================
# إنشاء الصور
# ============================================================

def generate_images(client):
    print()
    print("=" * 60)
    print("إنشاء صور جديدة")
    print("=" * 60)

    model = choose_image_model()

    prompt = input(
        "\nاكتب وصف الصورة:\n> "
    ).strip()

    if not prompt:
        print("لم يتم إدخال وصف.")
        return

    size = choose_size()
    quality = choose_quality()
    output_format = choose_output_format()
    background = choose_background()
    moderation = choose_moderation()

    n = ask_integer(
        "عدد الصور المطلوبة (1-10)",
        1,
        10,
        default=1
    )

    partial_images = choose_partial_images()

    if (
        background == "transparent"
        and output_format == "jpeg"
    ):
        print()
        print(
            "JPEG لا يدعم الخلفية الشفافة."
        )
        print(
            "سيتم تغيير التنسيق تلقائيًا إلى PNG."
        )
        output_format = "png"

    params = {
        "model": model,
        "prompt": prompt,
        "size": size,
        "quality": quality,
        "output_format": output_format,
        "background": background,
        "moderation": moderation,
        "n": n,
    }

    # partial_images يحتاج streaming.
    if partial_images > 0:
        params["partial_images"] = partial_images
        params["stream"] = True

    print()
    print("جارٍ إنشاء الصور...")
    print(f"النموذج: {model}")
    print(f"عدد الصور: {n}")

    try:

        if partial_images > 0:
            result = client.images.generate(
                **params
            )

            # حسب إصدار SDK، قد تكون الاستجابة
            # iterable عند استخدام stream.
            saved = process_stream(
                result,
                output_format
            )

            # الاستجابة النهائية قد لا تحمل usage
            # في streaming، لذلك نوضح ذلك.
            print()
            print(
                "ملاحظة: عند استخدام Partial images "
                "قد لا تتوفر usage النهائية في نفس الاستجابة."
            )

            print(
                "تم حفظ الصور الجزئية/النهائية "
                "التي أرسلها الخادم."
            )

            return

        result = client.images.generate(
            **params
        )

        data = get_attr(
            result,
            "data",
            []
        )

        saved = save_generated_images(
            data,
            output_format
        )

        usage = extract_image_usage(
            result
        )

        cost = show_image_cost(
            model,
            usage,
            saved,
            partial_images=0
        )

        if cost:
            save_cost_log(
                operation="إنشاء",
                model=model,
                cost_usd=cost["total"],
                generated_count=saved
            )

    except Exception as error:
        handle_api_error(error)


# ============================================================
# معالجة Stream / Partial images
# ============================================================

def process_stream(
    stream,
    output_format
):
    partial_counter = 0
    final_counter = 0

    for event in stream:

        event_type = get_attr(
            event,
            "type",
            ""
        )

        # صورة جزئية
        if (
            event_type
            == "image_generation.partial_image"
        ):
            partial_counter += 1

            data = get_attr(
                event,
                "b64_json",
                None
            )

            if data:
                filename = (
                    OUTPUT_DIR
                    / (
                        f"partial_"
                        f"{datetime.now():%Y%m%d_%H%M%S}_"
                        f"{partial_counter}.png"
                    )
                )

                save_base64_image(
                    data,
                    filename
                )

                print(
                    f"\nتم حفظ الصورة الجزئية "
                    f"{partial_counter}: {filename}"
                )

        # الصورة النهائية
        elif (
            event_type
            == "image_generation.completed"
        ):
            data = get_attr(
                event,
                "data",
                []
            )

            for item in data:
                b64 = get_attr(
                    item,
                    "b64_json",
                    None
                )

                if not b64:
                    continue

                final_counter += 1

                filename = (
                    OUTPUT_DIR
                    / (
                        f"generated_"
                        f"{datetime.now():%Y%m%d_%H%M%S}_"
                        f"{final_counter}"
                        f"{output_extension(output_format)}"
                    )
                )

                save_base64_image(
                    b64,
                    filename
                )

                print(
                    f"\nتم حفظ الصورة النهائية "
                    f"{final_counter}: {filename}"
                )

        elif (
            event_type
            == "image_generation.progress"
        ):
            print(
                "\rجارٍ إنشاء الصورة...",
                end="",
                flush=True
            )

    print()

    return final_counter


# ============================================================
# تعديل الصور
# ============================================================

def edit_images(client):
    print()
    print("=" * 60)
    print("تعديل صورة أو عدة صور")
    print("=" * 60)

    images = ask_multiple_images()

    if not images:
        print(
            "لم يتم اختيار أي صورة."
        )
        return

    print()
    print(
        f"عدد الصور المدخلة: "
        f"{len(images)}"
    )

    model = choose_image_model()

    prompt = input(
        "\nاكتب التعديل المطلوب:\n> "
    ).strip()

    if not prompt:
        print(
            "لم يتم إدخال تعليمات التعديل."
        )
        return

    size = choose_size()
    quality = choose_quality()
    output_format = choose_output_format()
    background = choose_background()
    moderation = choose_moderation()

    n = ask_integer(
        "عدد الصور الناتجة (1-10)",
        1,
        10,
        default=1
    )

    partial_images = choose_partial_images()

    if (
        background == "transparent"
        and output_format == "jpeg"
    ):
        print()
        print(
            "JPEG لا يدعم الخلفية الشفافة."
        )
        print(
            "سيتم تغيير التنسيق تلقائيًا إلى PNG."
        )
        output_format = "png"

    opened_files = []

    try:
        for image_path in images:
            opened_files.append(
                open(image_path, "rb")
            )

        params = {
            "model": model,
            "image": opened_files,
            "prompt": prompt,
            "size": size,
            "quality": quality,
            "output_format": output_format,
            "background": background,
            "moderation": moderation,
            "n": n,
        }

        if partial_images > 0:
            params["partial_images"] = partial_images
            params["stream"] = True

        print()
        print(
            "جارٍ تعديل الصور..."
        )

        if partial_images > 0:

            result = client.images.edit(
                **params
            )

            saved = process_stream(
                result,
                output_format
            )

            print()
            print(
                "ملاحظة: تم استخدام وضع Partial images، "
                "وقد لا تتوفر بيانات usage النهائية "
                "في الاستجابة المتدفقة."
            )

            return

        result = client.images.edit(
            **params
        )

        data = get_attr(
            result,
            "data",
            []
        )

        saved = save_generated_images(
            data,
            output_format
        )

        usage = extract_image_usage(
            result
        )

        cost = show_image_cost(
            model,
            usage,
            saved,
            partial_images=0
        )

        if cost:
            save_cost_log(
                operation="تعديل",
                model=model,
                cost_usd=cost["total"],
                generated_count=saved,
                input_count=len(images)
            )

    except Exception as error:
        handle_api_error(error)

    finally:
        for file in opened_files:
            try:
                file.close()
            except Exception:
                pass


# ============================================================
# وصف الصور
# ============================================================

def describe_images(client):
    print()
    print("=" * 60)
    print("وصف صورة أو عدة صور")
    print("=" * 60)

    images = ask_multiple_images()

    if not images:
        print(
            "لم يتم اختيار أي صورة."
        )
        return

    description_type = ask_choice(
        "نوع الوصف:",
        [
            (
                "general",
                "وصف شامل للصورة"
            ),
            (
                "detailed",
                "وصف تفصيلي جدًا"
            ),
            (
                "accessible",
                "وصف مناسب للمكفوفين"
            ),
            (
                "ocr",
                "قراءة النصوص الظاهرة"
            ),
            (
                "custom",
                "تعليمات مخصصة"
            ),
        ],
        default=1
    )

    if description_type == "general":

        instruction = (
            "صف الصور وصفًا واضحًا ومفيدًا، "
            "واذكر العناصر الرئيسية والمشهد "
            "والأشخاص والأشياء والألوان "
            "والعلاقات المكانية."
        )

    elif description_type == "detailed":

        instruction = (
            "صف الصور وصفًا تفصيليًا جدًا. "
            "اذكر الأشخاص والأشياء والخلفية "
            "والألوان والإضاءة والوضعيات "
            "والتفاصيل المكانية وأي نص ظاهر."
        )

    elif description_type == "accessible":

        instruction = (
            "اكتب وصفًا بصريًا مفصلًا مناسبًا "
            "لشخص كفيف. لا تستخدم عبارات مثل "
            "«كما ترى». اذكر العناصر المهمة "
            "ومواقعها بالنسبة لبعضها، "
            "والأشخاص وملابسهم وتعبيراتهم "
            "والألوان والنصوص الظاهرة "
            "وأي تفاصيل تساعد على تصور المشهد."
        )

    elif description_type == "ocr":

        instruction = (
            "اقرأ جميع النصوص الظاهرة في الصور "
            "بدقة، ثم اذكر مكان ظهور كل نص "
            "وفسر معناه إن أمكن."
        )

    else:

        instruction = input(
            "\nاكتب تعليمات الوصف:\n> "
        ).strip()

        if not instruction:
            print(
                "لم يتم إدخال تعليمات."
            )
            return

    detail = ask_choice(
        "مستوى تحليل الصور:",
        [
            ("auto", "Auto"),
            ("low", "Low"),
            ("high", "High"),
            ("original", "Original"),
        ],
        default=1
    )

    content = [
        {
            "type": "input_text",
            "text": instruction,
        }
    ]

    for image_path in images:

        content.append(
            {
                "type": "input_image",
                "image_url": file_to_data_url(
                    image_path
                ),
                "detail": detail,
            }
        )

    print()
    print(
        "جارٍ تحليل الصور..."
    )

    try:

        response = client.responses.create(
            model=VISION_MODEL,
            input=[
                {
                    "role": "user",
                    "content": content,
                }
            ],
        )

        print()
        print("=" * 60)
        print("الوصف")
        print("=" * 60)
        print()

        print(
            response.output_text
        )

        usage = extract_vision_usage(
            response
        )

        cost = show_vision_cost(
            usage,
            len(images)
        )

        if cost:
            save_cost_log(
                operation="وصف",
                model=VISION_MODEL,
                cost_usd=cost["total"],
                input_count=len(images)
            )

    except Exception as error:
        handle_api_error(error)


# ============================================================
# معالجة الأخطاء
# ============================================================

def handle_api_error(error):
    print()
    print("=" * 60)
    print("حدث خطأ")
    print("=" * 60)
    print()

    error_code = getattr(
        error,
        "code",
        None
    )

    status_code = getattr(
        error,
        "status_code",
        None
    )

    if status_code:
        print(
            f"HTTP Status: {status_code}"
        )

    if error_code:
        print(
            f"Error code: {error_code}"
        )

    print(
        f"نوع الخطأ: "
        f"{type(error).__name__}"
    )

    print()
    print(
        f"التفاصيل:\n{error}"
    )

    print("=" * 60)


# ============================================================
# القائمة الرئيسية
# ============================================================

def main():

    api_key = os.getenv(
        "OPENAI_API_KEY"
    )

    if not api_key:

        print()
        print(
            "لم يتم العثور على OPENAI_API_KEY."
        )

        print()
        print(
            "في PowerShell استخدم:"
        )

        print()
        print(
            '$env:OPENAI_API_KEY="ضع-مفتاحك-هنا"'
        )

        print()

        return

    client = OpenAI(
        api_key=api_key
    )

    while True:

        print()
        print("=" * 60)
        print(
            "OpenAI Image Tool"
        )
        print("=" * 60)

        print()
        print(
            "1. إنشاء صور جديدة"
        )
        print(
            "2. تعديل صورة أو عدة صور"
        )
        print(
            "3. وصف صورة أو عدة صور"
        )
        print(
            "4. الخروج"
        )

        print()

        choice = input(
            "اختر العملية: "
        ).strip()

        if choice == "1":

            generate_images(
                client
            )

        elif choice == "2":

            edit_images(
                client
            )

        elif choice == "3":

            describe_images(
                client
            )

        elif choice == "4":

            print(
                "إلى اللقاء."
            )

            break

        else:

            print(
                "اختيار غير صالح."
            )


# ============================================================
# تشغيل البرنامج
# ============================================================

if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        print(
            "\nتم إيقاف البرنامج."
        )

        sys.exit(0)