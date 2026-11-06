import wx

from .. import config


class APIKeyDialog(wx.Dialog):

    def __init__(self, parent):
        super().__init__(
            parent,
            title="إعداد مفتاح OpenAI",
            size=(520, 265),
            style=wx.DEFAULT_DIALOG_STYLE
        )

        root = wx.BoxSizer(wx.VERTICAL)

        key_help = wx.StaticText(
            self,
            label=(
                "أدخل مفتاح OpenAI الخاص بك. سيُحفظ في مخزن "
                "بيانات الاعتماد الآمن لنظام التشغيل، ولن يظهر "
                "في ملفات المشروع."
            )
        )
        key_help.Wrap(490)
        root.Add(
            key_help,
            0,
            wx.EXPAND | wx.ALL,
            12
        )

        privacy_help = wx.StaticText(
            self,
            label=(
                "عند إنشاء الصور أو تعديلها أو وصفها، تُرسل الصور "
                "والتعليمات إلى OpenAI مباشرة من جهازك."
            )
        )
        privacy_help.Wrap(490)
        root.Add(
            privacy_help,
            0,
            wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM,
            12
        )

        self.key = wx.TextCtrl(
            self,
            style=wx.TE_PASSWORD | wx.TE_PROCESS_ENTER
        )

        root.Add(
            self.key,
            0,
            wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM,
            12
        )

        self.status = wx.StaticText(
            self,
            label=""
        )

        root.Add(
            self.status,
            0,
            wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM,
            12
        )

        buttons = wx.BoxSizer(wx.HORIZONTAL)

        self.save = wx.Button(
            self,
            wx.ID_SAVE,
            label="حفظ المفتاح"
        )

        self.remove = wx.Button(
            self,
            label="حذف المفتاح المحفوظ"
        )

        self.cancel = wx.Button(
            self,
            wx.ID_CANCEL,
            label="إغلاق"
        )

        buttons.Add(self.save, 0, wx.RIGHT, 6)
        buttons.Add(self.remove, 0, wx.RIGHT, 6)
        buttons.Add(self.cancel, 0)

        root.Add(
            buttons,
            0,
            wx.ALIGN_RIGHT | wx.LEFT | wx.RIGHT | wx.BOTTOM,
            12
        )

        self.SetSizer(root)

        self.save.Bind(wx.EVT_BUTTON, self.on_save)
        self.key.Bind(wx.EVT_TEXT_ENTER, self.on_save)
        self.remove.Bind(wx.EVT_BUTTON, self.on_remove)

        try:
            has_key = config.has_api_key()
        except RuntimeError as exc:
            self.status.SetLabel(str(exc))
        else:
            self.status.SetLabel(
                "يوجد مفتاح مُعد لهذا التطبيق."
                if has_key
                else "لم يتم إعداد مفتاح بعد."
            )

        self.Centre()

    def on_save(self, event):
        try:
            config.set_api_key(self.key.GetValue())
        except (RuntimeError, ValueError) as exc:
            wx.MessageBox(
                str(exc),
                "تعذر حفظ المفتاح",
                wx.OK | wx.ICON_ERROR,
                self
            )
            return

        self.status.SetLabel(
            "تم حفظ المفتاح في مخزن بيانات الاعتماد للنظام."
        )
        self.key.Clear()
        self.EndModal(wx.ID_OK)

    def on_remove(self, event):
        try:
            stored_key = config.get_stored_api_key()
        except RuntimeError as exc:
            wx.MessageBox(
                str(exc),
                "تعذر الوصول إلى المفتاح",
                wx.OK | wx.ICON_ERROR,
                self
            )
            return

        if not stored_key:
            wx.MessageBox(
                "لا يوجد مفتاح محفوظ في مخزن التطبيق. "
                "إذا كان المفتاح مُعدًا كمتغير بيئة، فاحذفه من إعدادات النظام.",
                "مفتاح OpenAI",
                wx.OK | wx.ICON_INFORMATION,
                self
            )
            return

        confirmation = wx.MessageBox(
            "هل تريد حذف مفتاح OpenAI المحفوظ لهذا التطبيق؟",
            "تأكيد حذف المفتاح",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING,
            self
        )

        if confirmation != wx.YES:
            return

        try:
            config.clear_api_key()
        except (RuntimeError, ValueError) as exc:
            wx.MessageBox(
                str(exc),
                "تعذر حذف المفتاح",
                wx.OK | wx.ICON_ERROR,
                self
            )
            return

        self.status.SetLabel("تم حذف المفتاح المحفوظ.")
        self.EndModal(wx.ID_OK)
