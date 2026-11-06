import wx

from .. import config
from .api_key_dialog import APIKeyDialog

class ImageApplication(wx.App):

    def OnInit(self):

        try:
            config.initialize_client()

            if config.client is None:
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
        dialog = APIKeyDialog(None)

        try:
            result = dialog.ShowModal()
        finally:
            dialog.Destroy()

        if result == wx.ID_OK and config.client is not None:
            self.show_main_window()
            return

        self.ExitMainLoop()

    def show_main_window(self):
        from .main_window import MainFrame

        self.frame = MainFrame()
        self.frame.Show()
