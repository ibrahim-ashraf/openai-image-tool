from image_tool.ui.application import ImageApplication


if __name__ == "__main__":
    application = ImageApplication(clearSigInt=True)
    application.MainLoop()
