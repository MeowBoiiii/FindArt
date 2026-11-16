
from sqlalchemy import select
from database import SessionLocal, Exhibition

with SessionLocal() as db:
    events = db.scalars(
        select(Exhibition).order_by(Exhibition.start_date)
    ).all()

    for event in events:
        print("=" * 60)
        print("Tytuł:", event.title)
        print("Początek:", event.start_date)
        print("Koniec:", event.end_date)
        print("Galerie:", [g.name for g in event.galleries])
        print("Tagi:", [t.name for t in event.tags])
        print("URL:", event.source_url)

    print(f"\nŁącznie wydarzeń: {len(events)}")
