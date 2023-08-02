import io
import tkinter
from tkinter import *
from tkinter import ttk
from PIL import Image, ImageTk
import base64


class CaptchaVerificationRequestDialog:
    def __init__(self, cmd_text, image_base64):
        self.cmd_text = cmd_text
        self.image_base64 = image_base64.replace("data:image/jpeg;base64,", "")
        self.wnd = Tk()
        self.answer_var = StringVar()

    def __submit(self):
        self.wnd.destroy()
        pass

    def show(self) -> str:
        self.wnd.title("Captcha")
        self.wnd.geometry('400x250')

        self.wnd.columnconfigure(0, weight=1)
        self.wnd.rowconfigure(4, weight=1)

        cmd_label = ttk.Label(self.wnd, text=self.cmd_text)
        cmd_label.grid(column=0, row=0)

        img = Image.open(io.BytesIO(base64.b64decode(self.image_base64)))
        captcha_code = ImageTk.PhotoImage(img)
        captcha_image_component = Label(self.wnd, image=captcha_code)
        captcha_image_component.grid(column=0, row=1)

        answer_label = ttk.Label(self.wnd, text='Your answer:')
        answer_label.grid(column=0, row=3)

        answer_entry = Entry(self.wnd, textvariable=self.answer_var)
        answer_entry.grid(column=0, row=4)

        ok_button = ttk.Button(self.wnd, text="OK", command=self.__submit)
        ok_button.grid(column=0, row=5)

        self.wnd.mainloop()

        return self.answer_var.get()
