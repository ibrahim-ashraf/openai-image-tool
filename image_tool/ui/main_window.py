import wx

from .api_key_dialog import APIKeyDialog
from .pages.costs import CostPage
from .pages.create import CreatePage
from .pages.describe import DescribePage
from .pages.edit import EditPage

class MainFrame(wx.Frame):

    def __init__(self):

        super().__init__(
            None,
            title=(
                "أداة إنشاء وتعديل ووصف الصور"
            ),
            size=(900, 750)
        )

        panel = wx.Panel(self)

        root = wx.BoxSizer(
            wx.VERTICAL
        )

        title = wx.StaticText(
            panel,
            label=(
                "أداة إنشاء وتعديل ووصف الصور "
                "باستخدام OpenAI"
            )
        )

        title.SetFont(
            wx.Font(
                16,
                wx.FONTFAMILY_DEFAULT,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_BOLD
            )
        )

        root.Add(
            title,
            0,
            wx.ALIGN_CENTER_HORIZONTAL |
            wx.ALL,
            12
        )

        self.book = wx.Notebook(panel)

        self.create_page = CreatePage(
            self.book,
            self
        )

        self.edit_page = EditPage(
            self.book,
            self
        )

        self.describe_page = DescribePage(
            self.book,
            self
        )

        self.cost_page = CostPage(
            self.book,
            self
        )

        self.book.AddPage(
            self.create_page,
            "إنشاء صورة"
        )

        self.book.AddPage(
            self.edit_page,
            "تعديل صورة"
        )

        self.book.AddPage(
            self.describe_page,
            "وصف الصور"
        )

        self.book.AddPage(
            self.cost_page,
            "سجل التكلفة"
        )

        root.Add(
            self.book,
            1,
            wx.EXPAND | wx.ALL,
            8
        )

        panel.SetSizer(root)

        self.SetMinSize(
            (750, 600)
        )

        settings_menu = wx.Menu()
        manage_key = settings_menu.Append(
            wx.ID_ANY,
            "إعداد مفتاح OpenAI..."
        )
        menu_bar = wx.MenuBar()
        menu_bar.Append(
            settings_menu,
            "إعدادات"
        )
        self.SetMenuBar(menu_bar)

        self.Bind(
            wx.EVT_MENU,
            self.manage_api_key,
            manage_key
        )

        self.Centre()

    def manage_api_key(self, event):
        dialog = APIKeyDialog(self)
        dialog.ShowModal()
        dialog.Destroy()

    def error(self, message):

        wx.MessageBox(
            message,
            "خطأ",
            wx.OK | wx.ICON_ERROR,
            self
        )

    def info(self, message):

        wx.MessageBox(
            message,
            "تم",
            wx.OK | wx.ICON_INFORMATION,
            self
        )
