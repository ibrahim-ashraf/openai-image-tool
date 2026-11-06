from pathlib import Path
import os

import keyring
from openai import OpenAI

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
COST_LOG = BASE_DIR / "cost_log.csv"
OUTPUT_DIR.mkdir(exist_ok=True)

KEYRING_SERVICE = "openai-image-tool"
KEYRING_USERNAME = "openai-api-key"
API_KEY = None
client = None


IMAGE_MODELS = {
    "GPT Image 2.5 Sunburst": "gpt-image-2.5-sunburst",
    "GPT Image 2.5 Flare": "gpt-image-2.5-flare",
}
VISION_MODEL = "gpt-5.6-luna"

IMAGE_INPUT_PRICE = 8.0
IMAGE_CACHED_INPUT_PRICE = 2.0
IMAGE_OUTPUT_PRICE = 30.0
IMAGE_TEXT_INPUT_PRICE = 5.0
IMAGE_TEXT_CACHED_PRICE = 1.25
VISION_INPUT_PRICE = 0.20
VISION_CACHED_INPUT_PRICE = 0.02
VISION_OUTPUT_PRICE = 1.20
DEFAULT_USD_EGP = 52.0


def _credential_store():
    try:
        store = keyring.get_keyring()
    except Exception as exc:
        raise RuntimeError(
            "تعذر الوصول إلى مخزن بيانات الاعتماد الآمن."
        ) from exc

    if getattr(store, "priority", 0) <= 0:
        raise RuntimeError(
            "لا يتوفر مخزن آمن لبيانات الاعتماد في هذا النظام."
        )

    return store


def get_stored_api_key():
    try:
        return _credential_store().get_password(
            KEYRING_SERVICE,
            KEYRING_USERNAME
        )
    except Exception as exc:
        raise RuntimeError(
            "تعذر قراءة المفتاح من مخزن بيانات الاعتماد الآمن."
        ) from exc


def get_api_key():
    environment_key = os.getenv("OPENAI_API_KEY")

    try:
        stored_key = get_stored_api_key()
    except RuntimeError:
        if environment_key:
            return environment_key
        raise

    return stored_key or environment_key


def has_api_key():
    return bool(get_api_key())


def initialize_client():
    global API_KEY, client

    API_KEY = get_api_key()
    client = OpenAI(api_key=API_KEY) if API_KEY else None
    return client


def set_api_key(api_key):
    global API_KEY, client

    normalized_key = api_key.strip()

    if not normalized_key:
        raise ValueError("أدخل مفتاح OpenAI أولًا.")

    new_client = OpenAI(api_key=normalized_key)

    try:
        _credential_store().set_password(
            KEYRING_SERVICE,
            KEYRING_USERNAME,
            normalized_key
        )
    except Exception as exc:
        raise RuntimeError(
            "تعذر حفظ المفتاح في مخزن بيانات الاعتماد الآمن."
        ) from exc

    API_KEY = normalized_key
    client = new_client


def clear_api_key():
    global API_KEY, client

    if not get_stored_api_key():
        raise ValueError(
            "لا يوجد مفتاح محفوظ في مخزن التطبيق."
        )

    try:
        _credential_store().delete_password(
            KEYRING_SERVICE,
            KEYRING_USERNAME
        )
    except Exception as exc:
        raise RuntimeError(
            "تعذر حذف المفتاح من مخزن بيانات الاعتماد الآمن."
        ) from exc

    initialize_client()


def get_client():
    if client is None:
        raise RuntimeError(
            "لم يتم إعداد مفتاح OpenAI. افتح إعدادات التطبيق وأضف مفتاحك."
        )

    return client
