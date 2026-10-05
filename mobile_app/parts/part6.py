
    # ---- Cart ----
    def cart_page(self):
        if not self.customer:
            self.page.views.clear()
            self.page.views.append(ft.View('/cart', padding=0, controls=[
                ft.Column(expand=True, spacing=0, controls=[
                    self.header('Keranjang'),
                    self.empty(
                        ft.Icons.LOGIN,
                        'Silakan masuk untuk mengakses keranjang',
                        ft.ElevatedButton('Masuk / Daftar', on_click=lambda e: self.auth_dialog(), bgcolor=PRIMARY, color=ft.Colors.WHITE),
                    ),
                ])
            ]))
            self.page.navigation_bar = self.nav
            self.page.update()
            return

        addr = ft.TextField(label='Alamat Pengiriman', value=self.customer.get('address', ''), multiline=True, min_lines=2, max_lines=4)
        notes = ft.TextField(label='Catatan (opsional)', multiline=True, min_lines=2, max_lines=4)
        col = ft.Column(spacing=12, expand=True, scroll=ft.ScrollMode.AUTO)
        sub = ft.Text(fmt_price(0), weight=ft.FontWeight.BOLD, size=14)
        total = ft.Text(fmt_price(DELIVERY_FEE), weight=ft.FontWeight.BOLD, size=20, color=ACCENT)
        btn = ft.ElevatedButton(
            'PESAN SEKARANG',
            width=400,
            height=50,
            color=ft.Colors.WHITE,
            bgcolor=PRIMARY,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)),
        )
