import wx

from .. import config
from .api_key_dialog import APIKeyDialog

class ImageApplication(wx.App):

    def OnInit(self):

        try:
            config.initialize_client()

            if config.client is None:
                self.bootstrap_frame = wx.Frame(
                    None,
                    title="إعداد أداة الصور",
                    size=(460, 150)
                )
                panel = wx.Panel(self.bootstrap_frame)
                message = wx.StaticText(
                    panel,
                    label=(
                        "يلزم إعداد مفتاح OpenAI للمتابعة. "
                        "ستظهر نافذة إدخال المفتاح."
                    )
                )
                message.Wrap(410)
                layout = wx.BoxSizer(wx.VERTICAL)
                layout.Add(
                    message,
                    1,
                    wx.ALIGN_CENTER | wx.ALL,
                    20
                )
                panel.SetSizer(layout)
                self.bootstrap_frame.Centre()
                self.bootstrap_frame.Show()
                wx.CallAfter(self.prompt_for_api_key)
            else:
                self.show_main_window()

            return True

        except Exception as exc:

            wx.MessageBox(
                f"تعذر بدء التطبيق:\n\n{exc}",
                "خطأ في الإعداد",
                wx.OK | wx.ICON_ERROR
            )

            return False

    def prompt_for_api_key(self):
        dialog = APIKeyDialog(self.bootstrap_frame)

        try:
            result = dialog.ShowModal()
        finally:
            dialog.Destroy()

        if result == wx.ID_OK and config.client is not None:
            self.show_main_window()
            return

        self.bootstrap_frame.Destroy()
        self.ExitMainLoop()

    def show_main_window(self):
        from .main_window import MainFrame

        self.frame = MainFrame()
        self.frame.Show()

        bootstrap_frame = getattr(
            self,
            "bootstrap_frame",
            None
        )

        if bootstrap_frame is not None:
            bootstrap_frame.Destroy()
            self.bootstrap_frame = None
