import threading
from contextlib import ExitStack
from pathlib import Path

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
from ..widgets import BasePage, ChoiceRow, FileSelector


DESIGN_SIZES = {
    "مربع": "1024x1024",
    "أفقي": "1536x1024",
    "عمودي": "1024x1536",
    "تلقائي": "auto",
}


def parse_designs(text):
    designs = []

    for line_number, line in enumerate(
        text.splitlines(),
        start=1
    ):
        line = line.strip()

        if not line:
            continue

        parts = [
            part.strip()
            for part in line.split("|", 2)
        ]

        if len(parts) != 3 or not all(parts):
            raise ValueError(
                f"السطر {line_number} غير مكتمل. "
                "استخدم الصيغة: المنصة | الاتجاه | وصف التصميم."
            )

        platform, orientation, prompt = parts

        if orientation not in DESIGN_SIZES:
            raise ValueError(
                f"اتجاه غير معروف في السطر {line_number}: "
                "استخدم مربع أو أفقي أو عمودي أو تلقائي."
            )

        designs.append(
            (
                platform,
                DESIGN_SIZES[orientation],
                prompt
            )
        )

    if not designs:
        raise ValueError(
            "أضف تصميمًا واحدًا على الأقل، كل تصميم في سطر."
        )

    return designs


class EditPage(BasePage):

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
            "الصور التي تريد تعديلها:",
            "صور (*.png;*.jpg;*.jpeg;*.webp)|*.png;*.jpg;*.jpeg;*.webp"
        )

        sizer.Add(
            self.files,
            1,
            wx.EXPAND | wx.ALL,
            8
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

        self.mode = ChoiceRow(
            self,
            "طريقة التعديل:",
            [
                "كل صورة على حدة",
                "الصور معًا في نتيجة مشتركة",
                "تصاميم متعددة من صور مرجعية"
            ]
        )

        sizer.Add(
            self.mode,
            0,
            wx.EXPAND | wx.ALL,
            8
        )

        self.mode_help = wx.StaticText(
            self,
            label=(
                "المنفصل يرسل طلبًا لكل صورة؛ "
                "والمشترك يرسل الصور كلها في طلب واحد."
            )
        )

        sizer.Add(
            self.mode_help,
            0,
            wx.LEFT | wx.RIGHT,
            8
        )

        count_row = wx.BoxSizer(
            wx.HORIZONTAL
        )

        count_row.Add(
            wx.StaticText(
                self,
                label="عدد النتائج لكل طلب:"
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

        count_row.Add(
            self.count,
            0
        )

        sizer.Add(
            count_row,
            0,
            wx.ALL,
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

        self.prompt_label = wx.StaticText(
            self,
            label="وصف التعديل المطلوب:"
        )

        sizer.Add(
            self.prompt_label,
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

        self.format = ChoiceRow(
            self,
            "تنسيق الصورة الناتجة:",
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

        self.button = wx.Button(
            self,
            label="تنفيذ التعديل"
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
            self.edit
        )

        self.mode.choice.Bind(
            wx.EVT_CHOICE,
            self.mode_changed
        )

    def mode_changed(self, event):
        mode = self.mode.choice.GetSelection()

        if mode == 2:
            self.prompt_label.SetLabel(
                "وصف كل تصميم (سطر مستقل لكل منصة):"
            )
            self.mode_help.SetLabel(
                "اختر صورة مرجعية واحدة أو أكثر. ستُستخدم الصور "
                "كلها في كل تصميم. اكتب كل سطر هكذا: "
                "المنصة | مربع/أفقي/عمودي/تلقائي | وصف التصميم. "
                "الأحجام: مربع 1024×1024، أفقي 1536×1024، "
                "عمودي 1024×1536، أو تلقائي؛ وهذه ليست "
                "مقاسات دقيقة خاصة بكل منصة."
            )
            self.mode_help.Wrap(760)
        elif mode == 1:
            self.prompt_label.SetLabel(
                "وصف التعديل المطلوب:"
            )
            self.mode_help.SetLabel(
                "يرسل الصور كلها معًا في طلب واحد للحصول على نتيجة مشتركة."
            )
        else:
            self.prompt_label.SetLabel(
                "وصف التعديل المطلوب:"
            )
            self.mode_help.SetLabel(
                "يرسل طلبًا مستقلًا لكل صورة."
            )

        self.Layout()

    def edit(self, event):

        files = self.files.get_files()

        if not files:
            self.error(
                "اختر صورة واحدة على الأقل."
            )
            return

        prompt = self.prompt.GetValue().strip()

        if not prompt:
            self.error(
                "اكتب وصف التعديل المطلوب."
            )
            self.prompt.SetFocus()
            return

        model = config.IMAGE_MODELS[
            self.model.value()
        ]

        fmt = extension_from_format(
            self.format.value()
        )

        send_names = self.names.GetValue()
        mode = self.mode.choice.GetSelection()
        count = self.count.GetValue()
        designs = []

        if mode == 2:
            if len(files) > 16:
                self.error(
                    "يمكن استخدام 16 صورة مرجعية كحد أقصى لكل تصميم."
                )
                return

            try:
                designs = parse_designs(prompt)
            except ValueError as exc:
                self.error(str(exc))
                self.prompt.SetFocus()
                return

        if (
            mode == 1
            and len(files) > 16
        ):
            self.error(
                "يمكن إرسال 16 صورة كحد أقصى في طلب التعديل المشترك."
            )
            return

        self.button.Disable()
        self.status.SetLabel(
            "جارٍ تعديل الصور..."
        )

        threading.Thread(
            target=self.worker,
            args=(
                files,
                prompt,
                model,
                fmt,
                send_names,
                mode,
                count,
                designs
            ),
            daemon=True
        ).start()

    def worker(
        self,
        files,
        prompt,
        model,
        fmt,
        send_names,
        mode,
        count,
        designs
    ):

        saved = []
        cost_total = 0.0
        rate = 0.0

        try:
            rate = get_usd_egp()

            if mode == 2:
                jobs = [
                    (
                        files,
                        f"تصميم لمنصة {platform}.\n{design_prompt}",
                        size,
                        platform
                    )
                    for platform, size, design_prompt in designs
                ]
            else:
                batches = (
                    [files]
                    if mode == 1
                    else [[path] for path in files]
                )
                jobs = [
                    (batch, prompt, None, None)
                    for batch in batches
                ]

            for job_index, (
                batch,
                job_prompt,
                size,
                design_name
            ) in enumerate(jobs, start=1):
                wx.CallAfter(
                    self.status.SetLabel,
                    f"جارٍ تعديل التصميم {job_index} من {len(jobs)}..."
                )

                final_prompt = job_prompt

                if send_names:
                    names_text = "\n".join(
                        f"- الصورة {i}: {Path(path).name}"
                        for i, path in enumerate(
                            batch,
                            start=1
                        )
                    )

                    final_prompt = (
                        "أسماء الصور المرسلة:\n"
                        + names_text
                        + "\n\n"
                        + "تعليمات التصميم أو التعديل:\n"
                        + job_prompt
                    )

                with ExitStack() as stack:
                    handles = [
                        stack.enter_context(open(path, "rb"))
                        for path in batch
                    ]

                    edit_params = {
                        "model": model,
                        "image": handles,
                        "prompt": final_prompt,
                        "n": count,
                        "output_format": fmt
                    }

                    if size is not None:
                        edit_params["size"] = size

                    response = config.get_client().images.edit(
                        **edit_params
                    )

                usage = usage_dict(
                    attr(response, "usage")
                )
                cost = cost_image(usage)
                cost_total += cost

                if mode == 2:
                    prefix = f"{design_name}_تصميم"
                elif mode == 1:
                    prefix = (
                        Path(files[0]).stem + "_تعديل_مشترك"
                        if len(files) == 1
                        else "صور_مجتمعة_تعديل"
                    )
                else:
                    prefix = Path(batch[0]).stem + "_تعديل"

                for item in attr(response, "data", []):
                    data = decode_image(item)

                    if data:
                        saved.append(
                            save_image(
                                data,
                                fmt,
                                filename_prefix=prefix
                            )
                        )

                log_cost(
                    "تعديل صورة",
                    model,
                    cost,
                    usage,
                    rate
                )

            wx.CallAfter(
                self.finished,
                saved,
                cost_total,
                rate
            )

        except Exception as exc:

            wx.CallAfter(
                self.failed,
                str(exc),
                saved,
                cost_total,
                rate
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
                "لم تُرجع الواجهة صورة."
            )
            return

        self.status.SetLabel(
            f"اكتمل التعديل. تم حفظ {len(files)} صورة."
        )

        self.info(
            f"تم حفظ {len(files)} صورة في مجلد output.\n\n"
            "أسماء الملفات:\n"
            + "\n".join(
                f"- {Path(path).name}"
                for path in files[:8]
            )
            + (
                f"\n- و{len(files) - 8} ملفات أخرى."
                if len(files) > 8
                else ""
            )
            + "\n\n"
            f"التكلفة: ${cost:.6f}\n"
            f"بالجنيه المصري: "
            f"{cost * rate:.4f} جنيه."
        )

    def failed(
        self,
        message,
        files=None,
        cost=0.0,
        rate=0.0
    ):

        self.button.Enable()

        self.status.SetLabel(
            "حدث خطأ."
        )

        if files:
            message += (
                f"\n\nتم حفظ {len(files)} ناتج جزئيًا في مجلد output."
            )

        if cost:
            message += (
                f"\n\nتكلفة الطلبات المكتملة: ${cost:.6f}"
            )

            if rate:
                message += (
                    f" ({cost * rate:.4f} جنيه مصري)."
                )

        self.error(message)
