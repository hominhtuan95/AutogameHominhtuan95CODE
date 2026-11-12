import ctypes
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
import license_hominhtuan95 as license_api

user32 = ctypes.windll.user32
EnumWindows = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
WM_KEYDOWN, WM_KEYUP = 0x0100, 0x0101
VK_TAB, VK_SPACE = 0x09, 0x20
MAX_SECONDS = 3 * 60 * 60


def windows_list():
    found = []
    def callback(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        size = user32.GetWindowTextLengthW(hwnd)
        if size <= 0:
            return True
        buff = ctypes.create_unicode_buffer(size + 1)
        user32.GetWindowTextW(hwnd, buff, size + 1)
        title = buff.value.strip()
        if title and 'Hominhtuan95' not in title:
            found.append((f'{title[:45]}  [HWND {int(hwnd)}]', int(hwnd)))
        return True
    user32.EnumWindows(EnumWindows(callback), 0)
    return found


def send_key(hwnd, vk):
    if not user32.IsWindow(hwnd):
        return False
    user32.PostMessageW(hwnd, WM_KEYDOWN, vk, 0)
    user32.PostMessageW(hwnd, WM_KEYUP, vk, 0xC0000001)
    return True


class Slot:
    def __init__(self, parent, index, app):
        self.app = app
        self.index = index
        self.running = False
        self.stop_event = threading.Event()
        self.started = 0.0
        self.hwnd = None
        self.status = tk.StringVar(value='Đang dừng')
        self.selection = tk.StringVar()
        self.controls = []
        self.frame = ttk.LabelFrame(parent, text=f'CỬA SỔ {index}', padding=7)
        self.frame.grid(row=(index - 1) // 2, column=(index - 1) % 2, padx=5, pady=5, sticky='nsew')
        self.combo = ttk.Combobox(self.frame, textvariable=self.selection, state='readonly', width=31)
        self.combo.grid(row=0, column=0, columnspan=3, sticky='ew', pady=(0, 5))
        self.controls.append(self.combo)
        self.vars = {}
        self.delays = {}
        items = [('Tab', VK_TAB, 3.0), ('Space', VK_SPACE, 5.0)] + [(str(i), 0x30 + i, 2.0) for i in range(1, 10)]
        # Nút điều khiển nằm ngay dưới ô chọn game, luôn nhìn thấy.
        self.button = tk.Button(self.frame, text='▶ BẬT AUTO', command=self.toggle,
                                bg='#16803c', fg='white', activebackground='#11632e',
                                activeforeground='white', relief='flat', font=('Segoe UI', 9, 'bold'))
        self.button.grid(row=1, column=0, columnspan=3, sticky='ew', pady=(0, 3))
        ttk.Label(self.frame, textvariable=self.status, foreground='#2870a0').grid(
            row=2, column=0, columnspan=3, sticky='w', pady=(0, 3))
        for row, (label, vk, default) in enumerate(items, 3):
            enabled = tk.BooleanVar(value=(label in ('Tab', 'Space')))
            delay = tk.StringVar(value=f'{default:g}')
            self.vars[vk] = enabled
            self.delays[vk] = delay
            cb = ttk.Checkbutton(self.frame, text=('Skill ' + label if label.isdigit() else label), variable=enabled)
            cb.grid(row=row, column=0, sticky='w')
            ent = ttk.Entry(self.frame, textvariable=delay, width=6)
            ent.grid(row=row, column=1, sticky='e', pady=1)
            self.controls.extend([cb, ent])
            ttk.Label(self.frame, text='s').grid(row=row, column=2, sticky='w', padx=(3, 0))

    def refresh(self, entries):
        if not self.running:
            self.combo['values'] = [label for label, _ in entries]
            if self.selection.get() not in self.combo['values']:
                self.selection.set('')

    def toggle(self):
        if self.running:
            self.stop()
        else:
            self.start()

    def start(self):
        if not license_api.is_activated():
            messagebox.showerror('Kích hoạt', 'Mã kích hoạt không hợp lệ hoặc đã hết hạn. Hãy mở lại Auto để kích hoạt.')
            return
        mapping = dict(self.app.entries)
        hwnd = mapping.get(self.selection.get())
        if hwnd is None or not user32.IsWindow(hwnd):
            messagebox.showwarning('Chưa chọn cửa sổ', f'Hãy chọn cửa sổ game cho ô {self.index}.')
            return
        schedule = {}
        for vk, enabled in self.vars.items():
            if enabled.get():
                try:
                    seconds = float(self.delays[vk].get().replace(',', '.'))
                    if not 0.1 <= seconds <= MAX_SECONDS:
                        raise ValueError()
                except ValueError:
                    messagebox.showerror('Thời gian không hợp lệ', 'Nhập thời gian từ 0.1 đến 10800 giây (s).')
                    return
                schedule[vk] = seconds
        if not schedule:
            messagebox.showwarning('Chưa chọn phím', 'Hãy chọn ít nhất một Skill, Tab hoặc Space.')
            return
        if any(slot.running and slot.hwnd == hwnd for slot in self.app.slots if slot is not self):
            messagebox.showwarning('Trùng cửa sổ', 'Cửa sổ game này đang được điều khiển ở ô khác.')
            return
        self.hwnd = hwnd
        self.stop_event = threading.Event()
        self.running = True
        self.started = time.monotonic()
        self.button.config(text='■ TẮT AUTO', bg='#bd2929', activebackground='#942020')
        self.combo.config(state='disabled')
        self.status.set('Đang chạy · 00:00:00 / 03:00:00')
        thread = threading.Thread(target=self.worker, args=(hwnd, schedule, self.stop_event), daemon=True)
        thread.start()

    def worker(self, hwnd, schedule, stop_event):
        next_fire = {vk: time.monotonic() for vk in schedule}
        while not stop_event.is_set():
            now = time.monotonic()
            if now - self.started >= MAX_SECONDS or not user32.IsWindow(hwnd):
                break
            for vk, interval in schedule.items():
                if stop_event.is_set():
                    break
                if now >= next_fire[vk]:
                    if not send_key(hwnd, vk):
                        stop_event.set()
                        break
                    next_fire[vk] = now + interval
            stop_event.wait(0.05)
        self.app.root.after(0, lambda: self.finish(stop_event))

    def finish(self, event):
        if self.stop_event is event:
            self.stop()

    def stop(self):
        self.stop_event.set()
        self.running = False
        self.hwnd = None
        self.button.config(text='▶ BẬT AUTO', bg='#16803c', activebackground='#11632e')
        self.combo.config(state='readonly')
        self.status.set('Đang dừng')

    def update_clock(self):
        if self.running:
            elapsed = min(int(time.monotonic() - self.started), MAX_SECONDS)
            h, rem = divmod(elapsed, 3600)
            m, s = divmod(rem, 60)
            self.status.set(f'Đang chạy · {h:02}:{m:02}:{s:02} / 03:00:00')


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('Hominhtuan95 - Auto 4 cửa sổ')
        self.root.geometry('640x740')
        self.root.minsize(610, 700)
        self.root.configure(bg='white')
        style = ttk.Style()
        if 'clam' in style.theme_names():
            style.theme_use('clam')
        style.configure('TFrame', background='white')
        style.configure('TLabelframe', background='white')
        style.configure('TLabelframe.Label', background='white', foreground='#173b5b', font=('Segoe UI', 9, 'bold'))
        style.configure('TLabel', background='white', font=('Segoe UI', 9))
        style.configure('TCheckbutton', background='white', font=('Segoe UI', 9))
        tk.Label(self.root, text='HOMINHTUAN95  |  AUTO 4 CỬA SỔ', bg='white', fg='#173b5b', font=('Segoe UI', 14, 'bold')).pack(pady=(8, 2))
        tk.Label(self.root, text='9 Skill (1–9)  •  Tab  •  Space  •  Thời gian: giây (s)', bg='white', fg='#555').pack()
        top = ttk.Frame(self.root)
        top.pack(fill='x', padx=12, pady=5)
        ttk.Button(top, text='↻ Làm mới danh sách cửa sổ', command=self.refresh).pack(side='left')
        ttk.Label(top, text='Tự dừng sau tối đa 3 giờ / ô').pack(side='right')
        board = ttk.Frame(self.root)
        board.pack(fill='both', expand=True, padx=7)
        board.columnconfigure(0, weight=1)
        board.columnconfigure(1, weight=1)
        board.rowconfigure(0, weight=1)
        board.rowconfigure(1, weight=1)
        self.entries = []
        self.slots = [Slot(board, i, self) for i in range(1, 5)]
        tk.Label(self.root, text='Liên hệ Zalo: TuanHo  |  0398438721', bg='white', fg='#173b5b', font=('Segoe UI', 10, 'bold')).pack(pady=(3, 7))
        self.refresh()
        self.root.after(500, self.tick)
        self.root.protocol('WM_DELETE_WINDOW', self.close)

    def refresh(self):
        self.entries = windows_list()
        for slot in self.slots:
            slot.refresh(self.entries)

    def tick(self):
        for slot in self.slots:
            slot.update_clock()
        self.root.after(500, self.tick)

    def close(self):
        for slot in self.slots:
            slot.stop_event.set()
        self.root.destroy()

    def run(self):
        self.root.mainloop()




def activation_dialog():
    """Yêu cầu kích hoạt trước khi mở giao diện chính."""
    if license_api.is_activated():
        return True
    root = tk.Tk()
    root.title('Hominhtuan95 - Kích hoạt bản quyền')
    root.geometry('510x300')
    root.resizable(False, False)
    root.configure(bg='white')
    result = {'ok': False}
    tk.Label(root, text='KÍCH HOẠT HOMINHTUAN95', bg='white', fg='#173b5b',
             font=('Segoe UI', 15, 'bold')).pack(pady=(15, 7))
    tk.Label(root, text='Gửi mã máy qua Zalo: TuanHo - 0398438721', bg='white').pack()
    try:
        hwid = license_api.machine_id()
    except OSError as exc:
        messagebox.showerror('Lỗi mã máy', str(exc), parent=root)
        root.destroy()
        return False
    tk.Label(root, text='MÃ MÁY (HWID)', bg='white').pack(pady=(12, 2))
    hwid_var = tk.StringVar(value=hwid)
    ttk.Entry(root, textvariable=hwid_var, state='readonly', width=46,
              justify='center').pack()
    def copy_hwid():
        root.clipboard_clear()
        root.clipboard_append(hwid)
        root.update()
    ttk.Button(root, text='Sao chép mã máy', command=copy_hwid).pack(pady=4)
    tk.Label(root, text='Nhập mã kích hoạt do chủ phần mềm cung cấp:', bg='white').pack(pady=(6, 2))
    code_var = tk.StringVar()
    ttk.Entry(root, textvariable=code_var, width=62).pack(padx=12)
    def activate():
        try:
            ok, msg = license_api.save_license(code_var.get())
        except OSError as exc:
            ok, msg = False, str(exc)
        if ok:
            result['ok'] = True
            messagebox.showinfo('Thành công', 'Đã kích hoạt Auto Hominhtuan95!', parent=root)
            root.destroy()
        else:
            messagebox.showerror('Không thể kích hoạt', msg, parent=root)
    ttk.Button(root, text='KÍCH HOẠT', command=activate).pack(pady=10)
    root.mainloop()
    return result['ok']


if __name__ == '__main__':
    if activation_dialog():
        App().run()
