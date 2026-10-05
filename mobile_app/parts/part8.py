
    def order_detail(self, order):
        items_text = '\n'.join([f"- {i['menu_name']} x{i['quantity']} @ {fmt_price(i['price'])}" for i in order.get('items', [])])
        content = ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=16,
            controls=[
                ft.Text('Detail Pesanan', size=20, weight=ft.FontWeight.BOLD),
                ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Text('Order ID'), ft.Text('#' + str(order['id']), weight=ft.FontWeight.BOLD)]),
                ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Text('Tanggal'), ft.Text(fmt_date(order['created_at']))]),
                ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Text('Status'), status_badge(order['status'])]),
                ft.Divider(),
                ft.Text('Item', size=16, weight=ft.FontWeight.BOLD),
                ft.Text(items_text or '-'),
                ft.Divider(),
                ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Text('Subtotal'), ft.Text(fmt_price(order['total_price'] - order['delivery_fee']))]),
                ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Text('Ongkir'), ft.Text(fmt_price(order['delivery_fee']))]),
                ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Text('Total', weight=ft.FontWeight.BOLD), ft.Text(fmt_price(order['total_price']), weight=ft.FontWeight.BOLD, color=ACCENT, size=18)]),
                ft.Divider(),
                ft.Text('Alamat Pengiriman', size=16, weight=ft.FontWeight.BOLD),
                ft.Text(order.get('delivery_address', '-')),
                ft.Text('Catatan', size=16, weight=ft.FontWeight.BOLD),
                ft.Text(order.get('notes') or '-'),
            ],
        )
        self.page.views.clear()
        self.page.views.append(ft.View('/order-detail', padding=0, controls=[
            ft.Column(expand=True, spacing=0, controls=[
                self.header('Detail Pesanan', back=lambda e: self.orders_page()),
                ft.Container(expand=True, padding=16, content=content),
            ])
        ]))
        self.page.navigation_bar = self.nav
        self.page.update()

    # ---- Profile ----
    def profile_page(self):
        if not self.customer:
            self.page.views.clear()
            self.page.views.append(ft.View('/profile', padding=0, controls=[
                ft.Column(expand=True, spacing=0, controls=[
                    self.header('Profil'),
                    self.empty(
                        ft.Icons.PERSON_OUTLINE,
                        'Silakan masuk terlebih dahulu',
                        ft.ElevatedButton('Masuk / Daftar', on_click=lambda e: self.auth_dialog(), bgcolor=PRIMARY, color=ft.Colors.WHITE),
                    ),
                ])
            ]))
            self.page.navigation_bar = self.nav
            self.page.update()
            return

        name = ft.TextField(label='Nama Lengkap', value=self.customer.get('name', ''))
        phone = ft.TextField(label='Nomor Telepon', value=self.customer.get('phone', ''), read_only=True)
        addr = ft.TextField(label='Alamat', value=self.customer.get('address', ''), multiline=True, min_lines=2, max_lines=4)

        def save(e):
            if not name.value.strip() or not addr.value.strip():
                return self.snack('Nama dan alamat wajib diisi', ft.Colors.RED_400)
            try:
                r = self.api.put(f'/api/customers/{self.customer["id"]}', json_data={
                    'name': name.value.strip(),
                    'phone': self.customer['phone'],
                    'address': addr.value.strip(),
                })
                r.raise_for_status()
                self.customer = r.json()
                self.save_customer()
                self.snack('Profil berhasil diperbarui', ft.Colors.GREEN_700)
            except Exception as ex:
                self.snack('Gagal memperbarui profil: ' + str(ex), ft.Colors.RED_400)

        def logout(e):
            self.customer = None
            self.cart.clear()
            self.save_customer()
            self.snack('Berhasil keluar', ft.Colors.BLUE_600)
            self.home()

        self.page.views.clear()
        self.page.views.append(ft.View('/profile', padding=0, controls=[
            ft.Column(expand=True, spacing=0, controls=[
                self.header('Profil'),
                ft.Container(expand=True, padding=16, content=ft.Column(expand=True, spacing=16, controls=[
                    ft.Card(
                        elevation=3,
                        color=ft.Colors.WHITE,
                        shape=ft.RoundedRectangleBorder(radius=16),
                        content=ft.Container(
                            padding=20,
                            content=ft.Column(
                                spacing=12,
                                controls=[
                                    ft.Text('Informasi Akun', size=18, weight=ft.FontWeight.BOLD),
                                    name,
                                    phone,
                                    addr,
                                    ft.ElevatedButton('Simpan Perubahan', on_click=save, bgcolor=PRIMARY, color=ft.Colors.WHITE, width=400),
                                ],
                            ),
                        ),
                    ),
                    ft.ElevatedButton('Keluar', on_click=logout, bgcolor=ft.Colors.RED_400, color=ft.Colors.WHITE, width=400),
                ])),
            ])
        ]))
        self.page.navigation_bar = self.nav
        self.page.update()


def main(page: ft.Page):
    app = DEGOFOODApp(page)
    app.start()


if __name__ == '__main__':
    ft.app(target=main)
