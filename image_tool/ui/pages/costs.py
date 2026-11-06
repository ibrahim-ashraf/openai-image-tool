import csv
import os
import subprocess

import wx

from ...config import COST_LOG
from ..widgets import BasePage

class CostPage(BasePage):

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

        self.info_label = wx.StaticText(
            self,
            label=(
                "ملف سجل التكلفة:\n"
                + str(COST_LOG)
            )
        )

        sizer.Add(
            self.info_label,
            0,
            wx.ALL,
            10
        )

        buttons = wx.BoxSizer(
            wx.HORIZONTAL
        )

        self.refresh = wx.Button(
            self,
            label="تحديث السجل"
        )

        self.open = wx.Button(
            self,
            label="فتح ملف السجل"
        )

        buttons.Add(
            self.refresh,
            1,
            wx.RIGHT,
            5
        )

        buttons.Add(
            self.open,
            1,
            wx.LEFT,
            5
        )

        sizer.Add(
            buttons,
            0,
            wx.EXPAND | wx.ALL,
            10
        )

        self.text = wx.TextCtrl(
            self,
            style=(
                wx.TE_MULTILINE |
                wx.TE_READONLY
            )
        )

        sizer.Add(
            self.text,
            1,
            wx.EXPAND | wx.ALL,
            10
        )

        self.SetSizer(sizer)

        self.refresh.Bind(
            wx.EVT_BUTTON,
            self.load
        )

        self.open.Bind(
            wx.EVT_BUTTON,
            self.open_file
        )

        self.load(None)

    def load(self, event):

        if not COST_LOG.exists():

            self.text.SetValue(
                "لا يوجد سجل تكلفة حتى الآن."
            )

            return

        try:

            with COST_LOG.open(
                "r",
                encoding="utf-8-sig"
            ) as file:

                rows = list(
                    csv.reader(file)
                )

            if len(rows) <= 1:

                self.text.SetValue(
                    "السجل فارغ."
                )

                return

            lines = []

            total_usd = 0.0
            total_egp = 0.0

            for row in rows[1:]:

                if len(row) < 6:
                    continue

                lines.append(
                    " | ".join(row[:6])
                )

                try:
                    total_usd += float(row[3])
                    total_egp += float(row[5])
                except ValueError:
                    pass

            lines.append("")
            lines.append(
                "إجمالي التكلفة بالدولار: "
                f"${total_usd:.6f}"
            )

            lines.append(
                "إجمالي التكلفة بالجنيه: "
                f"{total_egp:.4f} جنيه"
            )

            self.text.SetValue(
                "\n".join(lines)
            )

        except Exception as exc:

            self.text.SetValue(
                "تعذر قراءة السجل:\n"
                + str(exc)
            )

    def open_file(self, event):

        if not COST_LOG.exists():

            self.main.info(
                "لم يتم إنشاء سجل تكلفة بعد."
            )

            return

        try:

            os.startfile(
                str(COST_LOG)
            )

        except Exception:

            subprocess.Popen(
                [
                    "explorer.exe",
                    str(COST_LOG)
                ]
            )
