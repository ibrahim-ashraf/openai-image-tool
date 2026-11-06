import wx

from .. import config
from .api_key_dialog import APIKeyDialog

class ImageApplication(wx.App):

    def OnInit(self):

        try:
            config.initialize_client()

            if config.client is None:
                dialog = APIKeyDialog(None)
                result = dialog.ShowModal()
                dialog.Destroy()

                if result != wx.ID_OK or config.client is None:
                    return False

            from .main_window import MainFrame

            frame = MainFrame()
            frame.Show()

            return True

        except Exception as exc:

            wx.MessageBox(
                f"تعذر بدء التطبيق:\n\n{exc}",
                "خطأ في الإعداد",
                wx.OK | wx.ICON_ERROR
            )

            return False
