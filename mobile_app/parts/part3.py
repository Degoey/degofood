
    # ---- Authentication ----
    def auth_dialog(self):
        phone = ft.TextField(label='Nomor Telepon', prefix_text='+62 ', keyboard_type=ft.KeyboardType.PHONE)

        def login(e):
            p = norm_phone(phone.value)
            if len(p) < 10:
                return self.snack('Nomor telepon tidak valid', ft.Colors.RED_400)
            r = self.api.get(f'/api/customers/phone/{p}')
            if r.status_code == 404:
                return self.register_dialog(p)
            r.raise_for_status()
            self.customer = r.json()
            self.save_customer()
            self.page.close(dlg)
            self.snack(f"Selamat datang, {self.customer['name']}!")
            self.home()

        dlg = ft.AlertDialog(
            title=ft.Text('Masuk ke DEGOFOOD'),
            content=ft.Column([ft.Text('Masukkan nomor telepon.'), phone], tight=True, spacing=12),
            actions=[
                ft.TextButton('Daftar', on_click=lambda e: self.register_dialog()),
                ft.ElevatedButton('Masuk', on_click=login, bgcolor=PRIMARY, color=ft.Colors.WHITE),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.open(dlg)

    def register_dialog(self, phone=''):
        name = ft.TextField(label='Nama Lengkap', autofocus=True)
        phone_f = ft.TextField(label='Nomor Telepon', prefix_text='+62 ',
                                value=phone[3:] if phone.startswith('+62') else phone)
        address = ft.TextField(label='Alamat Pengiriman', multiline=True, min_lines=2, max_lines=4)

        def submit(e):
            p = norm_phone(phone_f.value)
            if not (name.value.strip() and p and len(p) >= 10 and address.value.strip()):
                return self.snack('Lengkapi semua data', ft.Colors.RED_400)
            r = self.api.post('/api/customers/', json_data={
                'name': name.value.strip(),
                'phone': p,
                'address': address.value.strip(),
            })
            r.raise_for_status()
            self.customer = r.json()
            self.save_customer()
            self.page.close(dlg)
            self.snack('Akun berhasil dibuat!', ft.Colors.GREEN_700)
            self.home()

        dlg = ft.AlertDialog(
            title=ft.Text('Daftar Akun'),
            content=ft.Column([name, phone_f, address], tight=True, spacing=12),
            actions=[ft.ElevatedButton('Daftar', on_click=submit, bgcolor=PRIMARY, color=ft.Colors.WHITE)],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.open(dlg)
