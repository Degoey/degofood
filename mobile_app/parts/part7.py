
    # ---- Orders ----
    def orders_page(self):
        if not self.customer:
            self.page.views.clear()
            self.page.views.append(ft.View('/orders', padding=0, controls=[
                ft.Column(expand=True, spacing=0, controls=[
                    self.header('Riwayat Pesanan'),
                    self.empty(
                        ft.Icons.RECEIPT_LONG,
                        'Silakan masuk untuk melihat riwayat pesanan',
                        ft.ElevatedButton('Masuk / Daftar', on_click=lambda e: self.auth_dialog(), bgcolor=PRIMARY, color=ft.Colors.WHITE),
                    ),
                ])
            ]))
            self.page.navigation_bar = self.nav
            self.page.update()
            return

        col = ft.Column(spacing=12, expand=True, scroll=ft.ScrollMode.AUTO)
        loading = ft.ProgressRing(visible=True, width=30, height=30)
        err = ft.Text('', color=ft.Colors.RED_400, size=14, text_align=ft.TextAlign.CENTER)

        def load(e=None):
            loading.visible = True
            self.page.update()
            try:
                r = self.api.get(f'/api/orders/customer/{self.customer["id"]}')
                r.raise_for_status()
                orders = r.json()
                col.controls.clear()
                if not orders:
                    col.controls.append(self.empty(ft.Icons.RECEIPT_LONG, 'Belum ada pesanan'))
                else:
                    for o in orders:
                        col.controls.append(self.order_card(o))
                err.value = ''
            except Exception:
                err.value = 'Gagal memuat pesanan. Pastikan backend berjalan.'
            finally:
                loading.visible = False
                self.page.update()

        self.page.views.clear()
        self.page.views.append(ft.View('/orders', padding=0, controls=[
            ft.Column(expand=True, spacing=0, controls=[
                self.header('Riwayat Pesanan', actions=[
                    ft.IconButton(icon=ft.Icons.REFRESH, icon_color=ft.Colors.WHITE, on_click=load),
                ]),
                ft.Container(expand=True, padding=16, content=ft.Column(expand=True, spacing=16, controls=[
                    loading,
                    err,
                    col,
                ])),
            ])
        ]))
        self.page.navigation_bar = self.nav
        self.page.update()
        load()

    def order_card(self, order):
        def on_click(e):
            self.order_detail(order)

        return ft.Card(
            elevation=3,
            color=ft.Colors.WHITE,
            shape=ft.RoundedRectangleBorder(radius=16),
            content=ft.Container(
                padding=16,
                content=ft.Column(
                    spacing=12,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text('Order #' + str(order['id']), weight=ft.FontWeight.BOLD, size=16),
                                ft.Text(fmt_date(order['created_at']), color=ft.Colors.GREY_600, size=13),
                            ],
                        ),
                        status_badge(order['status']),
                        ft.Text(order.get('delivery_address', ''), color=ft.Colors.GREY_600, size=13),
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Text('Total', weight=ft.FontWeight.BOLD, size=14),
                                ft.Text(fmt_price(order.get('total_price', 0)), weight=ft.FontWeight.BOLD, size=16, color=ACCENT),
                            ],
                        ),
                    ],
                ),
            ),
        )
