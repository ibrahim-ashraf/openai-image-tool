import base64
import csv
import urllib.request
from datetime import datetime

from .config import (
    COST_LOG,
    DEFAULT_USD_EGP,
    IMAGE_CACHED_INPUT_PRICE,
    IMAGE_INPUT_PRICE,
    IMAGE_OUTPUT_PRICE,
    IMAGE_TEXT_INPUT_PRICE,
    OUTPUT_DIR,
    VISION_CACHED_INPUT_PRICE,
    VISION_INPUT_PRICE,
    VISION_OUTPUT_PRICE,
)

def attr(obj, name, default=None):
    if obj is None:
        return default

    if isinstance(obj, dict):
        return obj.get(name, default)

    return getattr(obj, name, default)


def usage_dict(usage):
    if usage is None:
        return {}

    names = [
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "input_image_tokens",
        "output_image_tokens",
        "cached_tokens",
        "cached_input_tokens",
    ]

    result = {}

    for name in names:
        value = attr(usage, name, None)

        if value is not None:
            result[name] = value

    return result


def cost_image(usage):
    if not usage:
        return 0.0

    input_image = usage.get("input_tokens_details", {}).get("image_tokens", 0)
    output_image = usage.get("output_tokens_details", {}).get("image_tokens", 0)
    input_text = usage.get("input_text_tokens", 0)

    cached = usage.get(
        "cached_input_tokens",
        usage.get("cached_tokens", 0)
    )

    normal_image = max(
        input_image - cached,
        0
    )
    print(f"Normal image tokens: {normal_image}, Cached tokens: {cached}, Output image tokens: {output_image}, Input text tokens: {input_text}")
    return (
        normal_image / 1_000_000 * IMAGE_INPUT_PRICE
        + cached / 1_000_000 * IMAGE_CACHED_INPUT_PRICE
        + output_image / 1_000_000 * IMAGE_OUTPUT_PRICE
        + input_text / 1_000_000 * IMAGE_TEXT_INPUT_PRICE
    )


def cost_vision(usage):
    if not usage:
        return 0.0

    input_tokens = usage.get(
        "input_tokens",
        0
    )

    output_tokens = usage.get(
        "output_tokens",
        0
    )

    cached = usage.get(
        "cached_input_tokens",
        usage.get("cached_tokens", 0)
    )

    normal_input = max(
        input_tokens - cached,
        0
    )

    return (
        normal_input / 1_000_000 * VISION_INPUT_PRICE
        + cached / 1_000_000 * VISION_CACHED_INPUT_PRICE
        + output_tokens / 1_000_000 * VISION_OUTPUT_PRICE
    )


def get_usd_egp():
    urls = [
        "https://api.frankfurter.app/latest?from=USD&to=EGP",
        "https://open.er-api.com/v6/latest/USD",
    ]

    for url in urls:
        try:
            with urllib.request.urlopen(
                url,
                timeout=5
            ) as response:
                data = response.read().decode(
                    "utf-8"
                )

            data = __import__("json").loads(data)

            if "rates" in data:
                rate = data["rates"].get("EGP")

                if rate:
                    return float(rate)

        except Exception:
            continue

    return DEFAULT_USD_EGP


def log_cost(
    operation,
    model,
    cost_usd,
    usage,
    exchange_rate
):
    new_file = not COST_LOG.exists()

    with COST_LOG.open(
        "a",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        writer = csv.writer(file)

        if new_file:
            writer.writerow([
                "التاريخ",
                "العملية",
                "النموذج",
                "التكلفة بالدولار",
                "سعر الدولار",
                "التكلفة بالجنيه",
                "الاستخدام"
            ])

        writer.writerow([
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            operation,
            model,
            f"{cost_usd:.8f}",
            f"{exchange_rate:.4f}",
            f"{cost_usd * exchange_rate:.6f}",
            str(usage)
        ])


def decode_image(item):
    b64 = attr(
        item,
        "b64_json"
    )

    if b64:
        return base64.b64decode(b64)

    url = attr(
        item,
        "url"
    )

    if url:
        with urllib.request.urlopen(url) as response:
            return response.read()

    return None


def save_image(
    data,
    extension,
    filename_prefix=None
):
    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    if filename_prefix is None:
        filename_prefix = "صورة"
    else:
        filename_prefix = "".join(
            character
            for character in filename_prefix
            if character not in '<>:"/\\|?*'
            and ord(character) >= 32
        ).strip(" .")

        if not filename_prefix:
            filename_prefix = "صورة"

        filename_prefix = filename_prefix[:120]

    path = OUTPUT_DIR / (
        f"{filename_prefix}_{timestamp}.{extension}"
    )

    path.write_bytes(data)

    return path


def extension_from_format(fmt):
    return {
        "PNG": "png",
        "JPEG": "jpeg",
        "WebP": "webp",
    }[fmt]
