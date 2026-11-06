from pathlib import Path

import wx

class ChoiceRow(wx.Panel):

    def __init__(
        self,
        parent,
        label,
        choices,
        default=0
    ):
        super().__init__(parent)

        sizer = wx.BoxSizer(
            wx.HORIZONTAL
        )

        self.label = wx.StaticText(
            self,
            label=label
        )

        self.choice = wx.Choice(
            self,
            choices=choices
        )

        if choices:
            self.choice.SetSelection(
                default
            )

        sizer.Add(
            self.label,
            0,
            wx.ALIGN_CENTER_VERTICAL |
            wx.RIGHT,
            10
        )

        sizer.Add(
            self.choice,
            1,
            wx.EXPAND
        )

        self.SetSizer(sizer)

    def value(self):
        return self.choice.GetStringSelection()


class FileSelector(wx.Panel):

    def __init__(
        self,
        parent,
        title,
        wildcard
    ):
        super().__init__(parent)

        self.files = []
        self.wildcard = wildcard

        sizer = wx.BoxSizer(
            wx.VERTICAL
        )

        sizer.Add(
            wx.StaticText(
                self,
                label=title
            ),
            0,
            wx.ALL,
            5
        )

        self.list = wx.ListBox(
            self,
            style=wx.LB_SINGLE
        )

        sizer.Add(
            self.list,
            1,
            wx.EXPAND | wx.ALL,
            5
        )

        buttons = wx.BoxSizer(
            wx.HORIZONTAL
        )

        self.add = wx.Button(
            self,
            label="إضافة صور"
        )

        self.remove = wx.Button(
            self,
            label="إزالة الصورة المحددة"
        )

        self.clear = wx.Button(
            self,
            label="مسح القائمة"
        )

        buttons.Add(
            self.add,
            1,
            wx.RIGHT,
            4
        )

        buttons.Add(
            self.remove,
            1,
            wx.LEFT | wx.RIGHT,
            4
        )

        buttons.Add(
            self.clear,
            1,
            wx.LEFT,
            4
        )

        sizer.Add(
            buttons,
            0,
            wx.EXPAND | wx.ALL,
            5
        )

        self.SetSizer(sizer)

        self.add.Bind(
            wx.EVT_BUTTON,
            self.on_add
        )

        self.remove.Bind(
            wx.EVT_BUTTON,
            self.on_remove
        )

        self.clear.Bind(
            wx.EVT_BUTTON,
            self.on_clear
        )

    def on_add(self, event):
        dialog = wx.FileDialog(
            self,
            "اختر الصور",
            wildcard=self.wildcard,
            style=(
                wx.FD_OPEN |
                wx.FD_FILE_MUST_EXIST |
                wx.FD_MULTIPLE
            )
        )

        if dialog.ShowModal() == wx.ID_OK:

            for path in dialog.GetPaths():

                if path not in self.files:

                    self.files.append(path)

                    # نعرض اسم الملف فقط، لا المسار الكامل.
                    self.list.Append(
                        Path(path).name
                    )

        dialog.Destroy()

    def on_remove(self, event):

        index = self.list.GetSelection()

        if index != wx.NOT_FOUND:

            self.files.pop(index)
            self.list.Delete(index)

    def on_clear(self, event):

        self.files.clear()
        self.list.Clear()

    def get_files(self):
        return list(self.files)


class BasePage(wx.Panel):

    def __init__(
        self,
        parent,
        main
    ):
        super().__init__(parent)

        self.main = main

    def error(self, message):
        self.main.error(message)

    def info(self, message):
        self.main.info(message)
