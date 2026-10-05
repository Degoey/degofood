
        def update_summary():
            s = sum(i['price'] * i['quantity'] for i in self.cart)
            sub.value = fmt_price(s)
            total.value = fmt_price(s + DELIVERY_FEE)

        def render():
            col.controls.clear()
            if not self.cart:
                col.controls.append(self.empty(ft.Icons.SHOPPING_CART_OUTLINED, 'Keranjang kosong'))
            else:
                for idx, it in enumerate(self.cart):
                    def make_change(i, delta):
                        def on_click(e):
                            if self.cart[i]['quantity'] + delta <= 0:
                                del self.cart[i]
                            else:
                                self.cart[i]['quantity'] += delta
                            render()
                            self.update_badge()
                        return on_click

                    col.controls.append(ft.Card(
                        elevation=2,
                        color=ft.Colors.WHITE,
                        shape=ft.RoundedRectangleBorder(radius=12),
                        content=ft.Container(
                            padding=12,
                            content=ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                controls=[
                                    ft.Column(
                                        expand=True,
                                        spacing=4,
                                        controls=[
                                            ft.Text(it['name'], weight=ft.FontWeight.BOLD, size=15),
                                            ft.Text(fmt_price(it['price']), color=ACCENT, weight=ft.FontWeight.BOLD, size=14),
                                        ],
                                    ),
                                    ft.Row(
                                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                        controls=[
                                            ft.IconButton(icon=ft.Icons.REMOVE, icon_color=ft.Colors.RED_400, on_click=make_change(idx, -1)),
                                            ft.Text(str(it['quantity']), size=16, weight=ft.FontWeight.BOLD),
                                            ft.IconButton(icon=ft.Icons.ADD, icon_color=ft.Colors.GREEN_700, on_click=make_change(idx, 1)),
                                        ],
                                    ),
                                ],
                            ),
                        ),
                    ))
            update_summary()
            self.page.update()

        def checkout(e):
            if not self.cart:
                return self.snack('Keranjang masih kosong', ft.Colors.RED_400)
            if not self.restaurant_id:
                return self.snack('Restoran tidak valid', ft.Colors.RED_400)
            if not addr.value.strip():
                return self.snack('Alamat pengiriman wajib diisi', ft.Colors.RED_400)
            payload = {
                'customer_id': self.customer['id'],
                'restaurant_id': self.restaurant_id,
                'delivery_address': addr.value.strip(),
                'notes': notes.value.strip(),
                'items': [{'menu_id': i['menu_id'], 'quantity': i['quantity']} for i in self.cart],
            }
            btn.disabled = True
            btn.text = 'Memproses...'
            self.page.update()
            try:
                r = self.api.post('/api/orders/', json_data=payload)
                r.raise_for_status()
                self.cart.clear()
                self.update_badge()
                self.snack('Pesanan berhasil dibuat!', ft.Colors.GREEN_700)
                self.orders_page()
            except Exception as ex:
                self.snack('Gagal membuat pesanan: ' + str(ex), ft.Colors.RED_400)
                btn.disabled = False
                btn.text = 'PESAN SEKARANG'
                self.page.update()

        btn.on_click = checkout

        summary = ft.Card(
            elevation=4,
            color=ft.Colors.WHITE,
            shape=ft.RoundedRectangleBorder(radius=16),
            content=ft.Container(
                padding=20,
                content=ft.Column(
                    spacing=12,
                    controls=[
                        ft.Text('Ringkasan Harga', weight=ft.FontWeight.BOLD, size=18),
                        ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Text('Subtotal'), sub]),
                        ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Text('Biaya Pengiriman'), ft.Text(fmt_price(DELIVERY_FEE), weight=ft.FontWeight.BOLD)]),
                        ft.Divider(),
                        ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[ft.Text('Total', weight=ft.FontWeight.BOLD), total]),
                    ],
                ),
            ),
        )

        self.page.views.clear()
        self.page.views.append(ft.View('/cart', padding=0, controls=[
            ft.Column(expand=True, spacing=0, controls=[
                self.header('Keranjang'),
                ft.Container(expand=True, padding=16, content=ft.Column(expand=True, spacing=16, controls=[
                    col,
                    addr,
                    notes,
                    summary,
                    btn,
                ])),
            ])
        ]))
        self.page.navigation_bar = self.nav
        self.page.update()
        render()
