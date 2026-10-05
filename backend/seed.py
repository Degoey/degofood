from app.database import SessionLocal, Base, engine
from app.models import Restaurant, Menu, Customer


def seed_data():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Restaurant).count() == 0:
            restaurants = [
                Restaurant(
                    name='Warung Nasi Padang',
                    address='Jl. Sudirman No. 1, Jakarta',
                    phone='+6281234567890',
                    is_open=True
                ),
                Restaurant(
                    name='Bakso Enak',
                    address='Jl. Thamrin No. 2, Jakarta',
                    phone='081987654321',
                    is_open=True
                )
            ]
            db.add_all(restaurants)
            db.commit()
            for r in restaurants:
                db.refresh(r)
            print(f'{len(restaurants)} restaurant berhasil dimasukkan.')
        else:
            restaurants = db.query(Restaurant).all()

        if db.query(Menu).count() == 0:
            menus = [
                Menu(
                    restaurant_id=restaurants[0].id,
                    name='Nasi Padang Komplit',
                    description='Nasi dengan rendang, ayam pop, sayur, dan sambal',
                    price=25000,
                    is_available=True
                ),
                Menu(
                    restaurant_id=restaurants[0].id,
                    name='Rendang Sapi',
                    description='Rendang sapi khas Padang',
                    price=35000,
                    is_available=True
                ),
                Menu(
                    restaurant_id=restaurants[0].id,
                    name='Ayam Pop',
                    description='Ayam pop khas Padang dengan sambal merah',
                    price=20000,
                    is_available=True
                ),
                Menu(
                    restaurant_id=restaurants[0].id,
                    name='Sayur Nangka',
                    description='Sayur nangka dengan kuah santan',
                    price=12000,
                    is_available=True
                ),
                Menu(
                    restaurant_id=restaurants[1].id,
                    name='Bakso Urat',
                    description='Bakso urat dengan kuah kaldu sapi',
                    price=18000,
                    is_available=True
                ),
                Menu(
                    restaurant_id=restaurants[1].id,
                    name='Bakso Campur',
                    description='Bakso urat, bakso halus, mie, dan tahu',
                    price=22000,
                    is_available=True
                ),
                Menu(
                    restaurant_id=restaurants[1].id,
                    name='Mie Ayam Bakso',
                    description='Mie ayam dengan bakso dan kuah',
                    price=20000,
                    is_available=True
                ),
                Menu(
                    restaurant_id=restaurants[1].id,
                    name='Es Jeruk',
                    description='Es jeruk segar',
                    price=8000,
                    is_available=True
                )
            ]
            db.add_all(menus)
            db.commit()
            print(f'{len(menus)} menu berhasil dimasukkan.')

        if db.query(Customer).count() == 0:
            budi = Customer(
                name='Budi Santoso',
                phone='+628123456789',
                address='Jl. Merdeka No. 1'
            )
            db.add(budi)
            db.commit()
            print('Data pelanggan Budi Santoso berhasil dimasukkan.')

        print('Seeding selesai.')
    finally:
        db.close()


if __name__ == '__main__':
    seed_data()
