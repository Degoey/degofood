
class DEGOFOODApp:
    """Kelas utama yang mengelola UI, state, dan integrasi API."""

    def __init__(self, page: ft.Page):
        self.page = page
        self.api = APIClient(API_BASE_URL)
        self.customer = None
        self.cart = []
        self.restaurant_id = None
        self.restaurant_name = None
        self.restaurants = []

        page.title = 'DEGOFOOD'
        page.theme_mode = ft.ThemeMode.LIGHT
        page.bgcolor = BG_COLOR
        page.padding = 0
        page.horizontal_alignment = ft.CrossAxisAlignment.STRETCH

        self.nav = ft.NavigationBar(
            selected_index=0,
            on_change=self.nav_change,
            destinations=[
                ft.NavigationBarDestination(icon=ft.Icons.HOME, label='Home'),
                ft.NavigationBarDestination(icon=ft.Icons.SHOPPING_CART, label='Cart'),
                ft.NavigationBarDestination(icon=ft.Icons.RECEIPT, label='Orders'),
                ft.NavigationBarDestination(icon=ft.Icons.PERSON, label='Profile'),
            ],
            bgcolor=ft.Colors.WHITE,
            indicator_color=ft.Colors.ORANGE_100,
            indicator_shape=ft.RoundedRectangleBorder(radius=12),
        )
        self.load_customer()

    # ---- Helpers ----
    def snack(self, msg, color=PRIMARY):
        self.page.open(ft.SnackBar(
            content=ft.Text(str(msg), color=ft.Colors.WHITE),
            bgcolor=color,
            duration=2500,
        ))

    def load_customer(self):
        try:
            self.customer = json.loads(self.page.client_storage.get(CUSTOMER_KEY) or '{}') or None
        except Exception:
            self.customer = None

    def save_customer(self):
        if self.customer:
            self.page.client_storage.set(CUSTOMER_KEY, json.dumps(self.customer))
        else:
            self.page.client_storage.remove(CUSTOMER_KEY)

    def header(self, title, subtitle=None, back=None, actions=None):
        rows = [ft.IconButton(icon=ft.Icons.ARROW_BACK, icon_color=ft.Colors.WHITE, on_click=back)] if back else []
        rows.append(ft.Text(title, size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, expand=True))
        if actions:
            rows.extend(actions)
        controls = [ft.Row(controls=rows, alignment=ft.MainAxisAlignment.SPACE_BETWEEN)]
        if subtitle:
            controls.append(ft.Text(subtitle, size=14, color=ft.Colors.WHITE70))
        return ft.Container(
            height=160,
            padding=ft.padding.only(left=16 if back else 24, right=24, top=40, bottom=24),
            border_radius=ft.border_radius.only(bottom_left=24, bottom_right=24),
            gradient=ft.LinearGradient(
                begin=ft.alignment.top_left,
                end=ft.alignment.bottom_right,
                colors=[ft.Colors.ORANGE_400, ft.Colors.ORANGE_700],
            ),
            content=ft.Column(
                alignment=ft.MainAxisAlignment.END,
                cross_axis_alignment=ft.CrossAxisAlignment.START,
                spacing=4,
                controls=controls,
            ),
        )

    def empty(self, icon, text, btn=None):
        controls = [
            ft.Icon(icon, size=80, color=ft.Colors.GREY_400),
            ft.Text(text, text_align=ft.TextAlign.CENTER, size=16, color=ft.Colors.GREY_600),
        ]
        if btn:
            controls.extend([ft.Container(height=16), btn])
        return ft.Column(
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
            controls=controls,
        )
