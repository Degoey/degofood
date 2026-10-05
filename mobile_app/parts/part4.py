
    # ---- Navigation ----
    def nav_change(self, e):
        index = e.control.selected_index
        if index == 0:
            self.home()
        elif index == 1:
            self.cart_page()
        elif index == 2:
            self.orders_page()
        else:
            self.profile_page()

    def start(self):
        if self.customer:
            self.home()
        else:
            self.welcome_page()

    def welcome_page(self):
        self.page.views.clear()
        self.page.views.append(ft.View('/welcome', padding=0, controls=[
            ft.Column(
                expand=True,
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=24,
                controls=[
                    ft.Icon(ft.Icons.DELIVERY_DINING, size=120, color=PRIMARY),
                    ft.Text('DEGOFOOD', size=40, weight=ft.FontWeight.BOLD, color=ACCENT),
                    ft.Text('Pesan makanan favoritmu dengan mudah', size=16, color=ft.Colors.GREY_600),
                    ft.ElevatedButton(
                        'Mulai Sekarang',
                        on_click=lambda e: self.auth_dialog(),
                        bgcolor=PRIMARY,
                        color=ft.Colors.WHITE,
                        width=250,
                        height=50,
                    ),
                ],
            )
        ]))
        self.page.update()

    # ---- Home ----
    def home(self):
        self.nav.selected_index = 0
        col = ft.Column(spacing=12, expand=True, scroll=ft.ScrollMode.AUTO)
        loading = ft.ProgressRing(visible=True, width=30, height=30)
        err = ft.Text('', color=ft.Colors.RED_400, size=14, text_align=ft.TextAlign.CENTER)

        def search(e):
            query = e.control.value.lower()
            filtered = [r for r in self.restaurants
                        if query in r.get('name', '').lower() or query in r.get('address', '').lower()]
            self.render_restaurants(col, filtered)

        def load(e=None):
            loading.visible = True
            self.page.update()
            try:
                r = self.api.get('/api/restaurants/')
                r.raise_for_status()
                self.restaurants = r.json()
                self.render_restaurants(col, self.restaurants)
                err.value = ''
            except Exception:
                err.value = 'Gagal memuat restoran. Pastikan backend berjalan.'
            finally:
                loading.visible = False
                self.page.update()

        self.page.views.clear()
        self.page.views.append(ft.View('/', padding=0, controls=[
            ft.Column(expand=True, spacing=0, controls=[
                self.header(
                    'DEGOFOOD',
                    subtitle='Pesan makanan favoritmu',
                    actions=[ft.IconButton(icon=ft.Icons.REFRESH, icon_color=ft.Colors.WHITE, on_click=load)],
                ),
                ft.Container(expand=True, padding=16, content=ft.Column(expand=True, spacing=16, controls=[
                    ft.TextField(
                        hint_text='Cari restoran...',
                        prefix_icon=ft.Icons.SEARCH,
                        filled=True,
                        fill_color=ft.Colors.WHITE,
                        border_radius=ft.border_radius.all(12),
                        on_change=search,
                    ),
                    ft.Text('Restoran Terdekat', size=18, weight=ft.FontWeight.BOLD),
                    loading,
                    err,
                    col,
                ])),
            ])
        ]))
        self.page.navigation_bar = self.nav
        self.page.update()
        load()

    def render_restaurants(self, col, items):
        col.controls.clear()
        if not items:
            col.controls.append(self.empty(ft.Icons.RESTAURANT_MENU, 'Tidak ada restoran ditemukan'))
        else:
            for r in items:
                col.controls.append(self.restaurant_card(r))
        self.page.update()

    def restaurant_card(self, restaurant):
        def open_menu(e):
            self.restaurant_id = restaurant['id']
            self.restaurant_name = restaurant['name']
            self.menu_page()

        return ft.Card(
            elevation=3,
            color=ft.Colors.WHITE,
            shape=ft.RoundedRectangleBorder(radius=16),
            content=ft.ListTile(
                leading=ft.CircleAvatar(
                    content=ft.Icon(ft.Icons.RESTAURANT, color=PRIMARY),
                    bgcolor=ft.Colors.ORANGE_50,
                ),
                title=ft.Text(restaurant.get('name', 'Restoran'), weight=ft.FontWeight.BOLD, size=16),
                subtitle=ft.Text(restaurant.get('address', ''), color=ft.Colors.GREY_600, size=13),
                trailing=ft.Icon(ft.Icons.CHEVRON_RIGHT, color=ft.Colors.GREY_400),
                on_click=open_menu,
            ),
        )
