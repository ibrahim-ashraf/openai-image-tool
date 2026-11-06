import base64
import mimetypes
from pathlib import Path
import threading

import wx

from ... import config
from ...services import (
    attr,
    cost_vision,
    get_usd_egp,
    log_cost,
    usage_dict,
)
from ..widgets import BasePage, FileSelector

class DescribePage(BasePage):

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

        self.files = FileSelector(
            self,
            "الصور التي تريد وصفها:",
            (
                "صور (*.png;*.jpg;*.jpeg;*.webp;*.gif)|"
                "*.png;*.jpg;*.jpeg;*.webp;*.gif"
            )
        )

        sizer.Add(
            self.files,
            1,
            wx.EXPAND | wx.ALL,
            8
        )

        self.names = wx.CheckBox(
            self,
            label="إرسال أسماء الملفات إلى النموذج"
        )

        self.names.SetValue(True)

        sizer.Add(
            self.names,
            0,
            wx.ALL,
            8
        )

        sizer.Add(
            wx.StaticText(
                self,
                label="المطلوب من النموذج:"
            ),
            0,
            wx.LEFT | wx.RIGHT | wx.TOP,
            8
        )

        self.prompt = wx.TextCtrl(
            self,
            value=(
                "صف الصور وصفًا دقيقًا ومفصلًا باللغة العربية. "
                "إذا أرسلت أسماء الملفات، فاستخدم اسم الملف "
                "لتمييز كل صورة عن الأخرى."
            ),
            style=wx.TE_MULTILINE
        )

        sizer.Add(
            self.prompt,
            1,
            wx.EXPAND | wx.ALL,
            8
        )

        self.button = wx.Button(
            self,
            label="وصف الصور"
        )

        sizer.Add(
            self.button,
            0,
            wx.EXPAND | wx.ALL,
            10
        )

        sizer.Add(
            wx.StaticText(
                self,
                label="النتيجة:"
            ),
            0,
            wx.LEFT | wx.RIGHT | wx.TOP,
            8
        )

        self.result = wx.TextCtrl(
            self,
            style=(
                wx.TE_MULTILINE |
                wx.TE_READONLY
            )
        )

        sizer.Add(
            self.result,
            1,
            wx.EXPAND | wx.ALL,
            8
        )

        self.SetSizer(sizer)

        self.button.Bind(
            wx.EVT_BUTTON,
            self.describe
        )

    def describe(self, event):

        files = self.files.get_files()

        if not files:
            self.error(
                "اختر صورة واحدة على الأقل."
            )
            return

        self.button.Disable()

        self.result.SetValue(
            "جارٍ تحليل الصور..."
        )

        threading.Thread(
            target=self.worker,
            args=(files,),
            daemon=True
        ).start()

    def worker(self, files):

        try:

            content = []

            if self.names.GetValue():

                names = "\n".join(
                    f"- الصورة {i}: {Path(path).name}"
                    for i, path in enumerate(
                        files,
                        start=1
                    )
                )

                content.append({
                    "type": "input_text",
                    "text": (
                        "الصور المرفقة مرتبة كما يلي:\n"
                        + names
                    )
                })

            content.append({
                "type": "input_text",
                "text": self.prompt.GetValue()
            })

            for index, path in enumerate(
                files,
                start=1
            ):

                mime = (
                    mimetypes.guess_type(path)[0]
                    or "image/png"
                )

                with open(
                    path,
                    "rb"
                ) as file:

                    encoded = base64.b64encode(
                        file.read()
                    ).decode("ascii")

                content.append({
                    "type": "input_text",
                    "text": (
                        f"هذه هي الصورة رقم {index}"
                        + (
                            f" واسم ملفها "
                            f"هو {Path(path).name}."
                            if self.names.GetValue()
                            else "."
                        )
                    )
                })

                content.append({
                    "type": "input_image",
                    "image_url": (
                        f"data:{mime};base64,{encoded}"
                    )
                })

            response = config.get_client().responses.create(
                model=config.VISION_MODEL,
                input=[
                    {
                        "role": "user",
                        "content": content
                    }
                ]
            )

            result = attr(
                response,
                "output_text",
                ""
            )

            usage = usage_dict(
                attr(response, "usage")
            )

            cost = cost_vision(usage)
            rate = get_usd_egp()

            log_cost(
                "وصف صورة",
                config.VISION_MODEL,
                cost,
                usage,
                rate
            )

            wx.CallAfter(
                self.finished,
                result,
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
        result,
        cost,
        rate
    ):

        self.button.Enable()

        self.result.SetValue(
            result
            + "\n\n"
            + "--------------------------------\n"
            + f"التكلفة: ${cost:.6f}\n"
            + f"بالجنيه المصري: "
            f"{cost * rate:.4f} جنيه."
        )

    def failed(self, message):

        self.button.Enable()

        self.result.SetValue(
            "حدث خطأ:\n\n"
            + message
        )
