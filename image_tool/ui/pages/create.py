import threading

import wx

from ... import config
from ...services import (
    attr,
    cost_image,
    decode_image,
    extension_from_format,
    get_usd_egp,
    log_cost,
    save_image,
    usage_dict,
)
from ..widgets import BasePage, ChoiceRow

class CreatePage(BasePage):

    def __init__(
        self,
        parent,
        main
    ):
        super().__init__(
            parent,
            main
        )

        sizer = wx.BoxSizer(
            wx.VERTICAL
        )

        self.model = ChoiceRow(
            self,
            "النموذج:",
            list(config.IMAGE_MODELS.keys())
        )

        sizer.Add(
            self.model,
            0,
            wx.EXPAND | wx.ALL,
            8
        )

        sizer.Add(
            wx.StaticText(
                self,
                label="وصف الصورة:"
            ),
            0,
            wx.LEFT | wx.RIGHT | wx.TOP,
            8
        )

        self.prompt = wx.TextCtrl(
            self,
            style=wx.TE_MULTILINE
        )

        sizer.Add(
            self.prompt,
            1,
            wx.EXPAND | wx.ALL,
            8
        )

        self.size = ChoiceRow(
            self,
            "الحجم والاتجاه:",
            [
                "تلقائي",
                "مربع 1024 × 1024",
                "عمودي 1024 × 1536",
                "أفقي 1536 × 1024",
            ]
        )

        sizer.Add(
            self.size,
            0,
            wx.EXPAND | wx.ALL,
            8
        )

        self.quality = ChoiceRow(
            self,
            "الجودة:",
            [
                "تلقائي",
                "عالٍ",
                "متوسط",
                "منخفض",
                "أقصى",
                "فائق"
            ]
        )

        sizer.Add(
            self.quality,
            0,
            wx.EXPAND | wx.ALL,
            8
        )

        row = wx.BoxSizer(
            wx.HORIZONTAL
        )

        row.Add(
            wx.StaticText(
                self,
                label="عدد الصور:"
            ),
            0,
            wx.ALIGN_CENTER_VERTICAL |
            wx.RIGHT,
            10
        )

        self.count = wx.SpinCtrl(
            self,
            min=1,
            max=10,
            initial=1
        )

        row.Add(
            self.count,
            0
        )

        sizer.Add(
            row,
            0,
            wx.ALL,
            8
        )

        self.format = ChoiceRow(
            self,
            "تنسيق الإخراج:",
            [
                "PNG",
                "JPEG",
                "WebP"
            ]
        )

        sizer.Add(
            self.format,
            0,
            wx.EXPAND | wx.ALL,
            8
        )

        self.background = ChoiceRow(
            self,
            "الخلفية:",
            [
                "تلقائي",
                "شفافة",
                "معتمة"
            ]
        )

        sizer.Add(
            self.background,
            0,
            wx.EXPAND | wx.ALL,
            8
        )

        self.moderation = ChoiceRow(
            self,
            "المراجعة:",
            [
                "تلقائي",
                "منخفض"
            ]
        )

        sizer.Add(
            self.moderation,
            0,
            wx.EXPAND | wx.ALL,
            8
        )

        self.partial = ChoiceRow(
            self,
            "الصور الجزئية:",
            [
                "لا شيء",
                "1",
                "2",
                "3"
            ]
        )

        sizer.Add(
            self.partial,
            0,
            wx.EXPAND | wx.ALL,
            8
        )

        self.button = wx.Button(
            self,
            label="إنشاء الصورة"
        )

        sizer.Add(
            self.button,
            0,
            wx.EXPAND | wx.ALL,
            10
        )

        self.status = wx.StaticText(
            self,
            label="جاهز."
        )

        sizer.Add(
            self.status,
            0,
            wx.ALL,
            8
        )

        self.SetSizer(sizer)

        self.button.Bind(
            wx.EVT_BUTTON,
            self.generate
        )

    def generate(self, event):

        prompt = self.prompt.GetValue().strip()

        if not prompt:
            self.error(
                "اكتب وصف الصورة أولًا."
            )
            self.prompt.SetFocus()
            return

        model = config.IMAGE_MODELS[
            self.model.value()
        ]

        size = {
            "تلقائي": "auto",
            "مربع 1024 × 1024": "1024x1024",
            "عمودي 1024 × 1536": "1024x1536",
            "أفقي 1536 × 1024": "1536x1024",
        }[self.size.value()]

        quality = {
            "تلقائي": "auto",
            "عالٍ": "high",
            "متوسط": "medium",
            "منخفض": "low",
            "أقصى": "max",
            "فائق": "extra_high",
        }[self.quality.value()]

        background = {
            "تلقائي": "auto",
            "شفافة": "transparent",
            "معتمة": "opaque",
        }[self.background.value()]

        moderation = {
            "تلقائي": "auto",
            "منخفض": "low",
        }[self.moderation.value()]

        partial = {
            "لا شيء": 0,
            "1": 1,
            "2": 2,
            "3": 3,
        }[self.partial.value()]

        fmt = extension_from_format(
            self.format.value()
        )

        self.button.Disable()
        self.status.SetLabel(
            "جارٍ إنشاء الصورة..."
        )

        thread = threading.Thread(
            target=self.worker,
            args=(
                model,
                prompt,
                size,
                quality,
                background,
                moderation,
                partial,
                self.count.GetValue(),
                fmt
            ),
            daemon=True
        )

        thread.start()

    def worker(
        self,
        model,
        prompt,
        size,
        quality,
        background,
        moderation,
        partial,
        count,
        fmt
    ):
        try:

            params = {
                "model": model,
                "prompt": prompt,
                "size": size,
                "quality": quality,
                "n": count,
                "output_format": fmt,
                "background": background,
                "moderation": moderation,
            }

            if partial:
                params["partial_images"] = partial

            response = config.get_client().images.generate(
                **params
            )

            usage = usage_dict(
                attr(response, "usage")
            )

            cost = cost_image(usage)
            rate = get_usd_egp()
            # print(f"Usage: {usage}, Cost: ${cost:.6f}, Rate: {rate:.4f} EGP/USD")
            log_cost(
                "إنشاء صورة",
                model,
                cost,
                usage,
                rate
            )

            files = []

            for item in attr(
                response,
                "data",
                []
            ):

                data = decode_image(item)

                if data:
                    files.append(
                        save_image(
                            data,
                            fmt
                        )
                    )

            wx.CallAfter(
                self.finished,
                files,
                cost,
                rate
            )

        except Exception as exc:

            wx.CallAfter(
                self.failed,
                str(exc)
            )

    def finished(
        self,
        files,
        cost,
        rate
    ):
        self.button.Enable()

        if not files:

            self.status.SetLabel(
                "لم تُنتج صورة."
            )

            self.error(
                "لم تُرجع الواجهة أي صورة."
            )
            return

        self.status.SetLabel(
            f"تم إنشاء {len(files)} صورة."
        )

        self.info(
            f"تم حفظ {len(files)} صورة في مجلد output.\n\n"
            f"التكلفة: ${cost:.6f}\n"
            f"بالجنيه المصري: "
            f"{cost * rate:.4f} جنيه."
        )

    def failed(self, message):

        self.button.Enable()
        self.status.SetLabel(
            "حدث خطأ."
        )

        self.error(message)
