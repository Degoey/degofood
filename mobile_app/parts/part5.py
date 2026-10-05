
    # ---- Menu ----
    def menu_page(self):
        loading = ft.ProgressRing(visible=True, width=30, height=30)
        err = ft.Text('', color=ft.Colors.RED_400, size=14, text_align=ft.TextAlign.CENTER)
        col = ft.Column(spacing=12, expand=True, scroll=ft.ScrollMode.AUTO)

        def load(e=None):
            loading.visible = True
            self.page.update()
            try:
                r = self.api.get(f'/api/restaurants/{self.restaurant_id}/menu')
                r.raise_for_status()
                items = r.json()
                col.controls.clear()
                if not items:
                    col.controls.append(self.empty(ft.Icons.FASTFOOD, 'Menu kosong'))
                else:
                    for it in items:
                        col.controls.append(self.menu_card(it))
                err.value = ''
            except Exception:
                err.value = 'Gagal memuat menu. Pastikan backend berjalan.'
            finally:
                loading.visible = False
                self.page.update()

        self.page.views.clear()
        self.page.views.append(ft.View('/menu', padding=0, controls=[
            ft.Column(expand=True, spacing=0, controls=[
                self.header('Menu', subtitle=self.restaurant_name, back=lambda e: self.home()),
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

    def menu_card(self, item):
        def add(e):
            existing = next((i for i in self.cart if i['menu_id'] == item['id']), None)
            if existing:
                existing['quantity'] += 1
            else:
                self.cart.append({
                    'menu_id': item['id'],
                    'name': item['name'],
                    'price': item['price'],
                    'quantity': 1,
                })
            self.snack(f"{item['name']} ditambahkan", ft.Colors.GREEN_700)
            self.update_badge()

        return ft.Card(
            elevation=3,
            color=ft.Colors.WHITE,
            shape=ft.RoundedRectangleBorder(radius=16),
            content=ft.Container(
                padding=16,
                content=ft.Column(
                    spacing=8,
                    controls=[
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text(item.get('name', 'Menu'), weight=ft.FontWeight.BOLD, size=16, expand=True),
                                ft.Text(fmt_price(item.get('price', 0)), color=ACCENT, weight=ft.FontWeight.BOLD, size=14),
                            ],
                        ),
                        ft.Text(item.get('description', ''), color=ft.Colors.GREY_600, size=13),
                        ft.ElevatedButton(
                            'Tambah',
                            icon=ft.Icons.ADD_SHOPPING_CART,
                            color=ft.Colors.WHITE,
                            bgcolor=PRIMARY,
                            on_click=add,
                        ),
                    ],
                ),
            ),
        )

    def update_badge(self):
        total = sum(i['quantity'] for i in self.cart)
        self.nav.destinations[1].label = f'Cart ({total})' if total else 'Cart'
        self.page.update()
