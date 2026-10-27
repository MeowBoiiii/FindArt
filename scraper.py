
import logging
from datetime import datetime, timezone
from urllib.parse import urljoin, urldefrag

import requests
from bs4 import BeautifulSoup
from sqlalchemy import select

from urllib.parse import urljoin
from bs4 import BeautifulSoup

from database import (
    Base,
    engine,
    SessionLocal,
    Exhibition,
    Gallery,
    Tag,
)

BASE_URL = "https://bwa.wroc.pl/"
EVENTS_URL = urljoin(BASE_URL, "wydarzenia/")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; GalleryResearchBot/1.0)"
    )
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

session_http = requests.Session()
session_http.headers.update(HEADERS)


def clean_text(element):
    """Pobiera tekst z elementu HTML i usuwa zbędne spacje."""
    if not element:
        return None

    text = element.get_text(" ", strip=True)
    return text or None


def get_soup(url):
    """Pobiera stronę i zamienia HTML na obiekt BeautifulSoup."""
    response = session_http.get(url, timeout=30)
    response.raise_for_status()

    return BeautifulSoup(response.text, "html.parser")


def parse_date(soup, itemprop):
    """
    Szuka daty w Schema.org, np.:
    <time itemprop="startDate"
          datetime="2026-10-09T18:00:00+02:00">
    """
    element = soup.find(
        attrs={"itemprop": itemprop}
    )

    if not element:
        return None

    value = (
        element.get("content")
        or element.get("datetime")
    )

    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(value)

        # Odrzucamy daty bez informacji o strefie,
        # aby nie przypisywać im arbitralnie UTC.
        if parsed.tzinfo is None:
            logging.warning(
                "Data bez strefy czasowej: %s = %s",
                itemprop,
                value,
            )

        return parsed

    except ValueError:
        logging.warning(
            "Nie udało się sparsować daty %s: %s",
            itemprop,
            value,
        )
        return None


def extract_event_links():
    """Zbiera unikalne adresy podstron wydarzeń."""
    soup = get_soup(EVENTS_URL)
    links = set()

    for anchor in soup.select("a[href]"):
        href = anchor.get("href", "")
        absolute_url = urljoin(BASE_URL, href)
        absolute_url, _ = urldefrag(absolute_url)

        # Ograniczamy się do podstron wydarzeń w domenie BWA.
        if (
            absolute_url.startswith(BASE_URL)
            and "/wydarzenie/" in absolute_url
        ):
            links.add(absolute_url.rstrip("/") + "/")

    logging.info("Znaleziono %d linków", len(links))
    return sorted(links)


def extract_gallery(soup):
    """
    Pobiera lokalizację oznaczoną Schema.org.
    Nazwa i adres mogą być zapisane w elementach potomnych.
    """
    location = soup.find(
        attrs={"itemprop": "location"}
    )

    if not location:
        return None

    name_element = location.find(
        attrs={"itemprop": "name"}
    )
    address_element = location.find(
        attrs={"itemprop": "address"}
    )

    name = (
        clean_text(name_element)
        or location.get("content")
    )

    address = (
        clean_text(address_element)
        or location.get("content")
    )

    if not name:
        name = clean_text(location)

    if not name:
        return None

    return {
        "name": name,
        "address": address,
        "city": "Wrocław",
        "website_url": BASE_URL.rstrip("/"),
    }


def extract_tags(soup):
    """
    Przykładowy selektor tagów.
    Należy dopasować go do rzeczywistego HTML strony.
    """
    tags = set()

    for element in soup.select(
        '[rel="tag"], .event__tags a, .tags a'
    ):
        name = clean_text(element)

        if name:
            tags.add(name.lstrip("#").strip())

    return sorted(tag for tag in tags if tag)


def get_meta(soup, *, name=None, prop=None):
    """Pobiera zawartość wskazanego znacznika meta."""
    attrs = {}

    if name:
        attrs["name"] = name

    if prop:
        attrs["property"] = prop

    element = soup.find("meta", attrs=attrs)

    if element:
        return element.get("content", "").strip() or None

    return None


def extract_event(url):
    """Pobiera podstawowe dane wydarzenia BWA."""
    soup = get_soup(url)

    # Preferujemy metadane Open Graph.
    title = (
        get_meta(soup, prop="og:title")
        or clean_text(soup.find("h1"))
    )

    description = (
        get_meta(soup, name="description")
        or get_meta(soup, prop="og:description")
    )

    canonical = soup.find(
        "link",
        rel="canonical",
    )

    source_url = (
        urljoin(url, canonical["href"])
        if canonical and canonical.get("href")
        else url
    )

    image_url = (
        get_meta(soup, prop="og:image")
        or get_meta(soup, name="twitter:image")
    )

    if image_url:
        image_url = urljoin(url, image_url)

    # Data i lokalizacja wymagają elementów z body.
    start_date = parse_date(soup, "startDate")
    end_date = parse_date(soup, "endDate")

    sidebar = soup.select_one(".sidebar__content")
    extra_info = clean_text(sidebar)

    gallery = extract_gallery(soup)
    tags = extract_tags(soup)

    if not title:
        print(f"Brak tytułu: {url}")
        return None

    return {
        "title": title,
        "event_type": None,  # Uzupełnimy po sprawdzeniu HTML.
        "start_date": start_date,
        "end_date": end_date,
        "description": description,
        "extra_info": extra_info,
        "image_url": image_url,
        "source_url": source_url,
        "gallery": gallery,
        "tags": tags,
    }


def get_or_create_gallery(db, data):
    """Pobiera istniejącą galerię lub tworzy nową."""
    if not data:
        return None

    gallery = db.scalar(
        select(Gallery).where(
            Gallery.name == data["name"]
        )
    )

    if gallery is None:
        gallery = Gallery(**data)
        db.add(gallery)
        db.flush()
    else:
        # Uzupełniamy brakujące dane, nie nadpisując
        # istniejących wartości pustymi polami.
        for field in ("address", "city", "website_url"):
            if data.get(field) and not getattr(gallery, field):
                setattr(gallery, field, data[field])

    return gallery


def get_or_create_tag(db, name):
    """Pobiera istniejący tag lub tworzy nowy."""
    tag = db.scalar(
        select(Tag).where(Tag.name == name)
    )

    if tag is None:
        tag = Tag(name=name)
        db.add(tag)
        db.flush()

    return tag


def save_event(db, data):
    """Zapisuje wydarzenie albo aktualizuje istniejący rekord."""
    event = db.scalar(
        select(Exhibition).where(
            Exhibition.source_url == data["source_url"]
        )
    )

    if event is None:
        event = Exhibition(
            title=data["title"],
            source_url=data["source_url"],
            created_at=datetime.now(timezone.utc),
        )
        db.add(event)

    # Aktualizujemy pola pobrane ze strony.
    for field in (
        "title",
        "event_type",
        "start_date",
        "end_date",
        "description",
        "extra_info",
        "image_url",
    ):
        setattr(event, field, data[field])

    gallery = get_or_create_gallery(db, data["gallery"])

    if gallery and gallery not in event.galleries:
        event.galleries.append(gallery)

    # Dodajemy znalezione tagi, nie duplikując relacji.
    for tag_name in data["tags"]:
        tag = get_or_create_tag(db, tag_name)

        if tag not in event.tags:
            event.tags.append(tag)

    db.flush()


def main():
    Base.metadata.create_all(engine)

    links = extract_event_links()

    with SessionLocal() as db:
        for index, url in enumerate(links, start=1):
            try:
                logging.info(
                    "[%d/%d] Pobieram %s",
                    index,
                    len(links),
                    url,
                )

                data = extract_event(url)

                if data:
                    save_event(db, data)
                    db.commit()
                    logging.info(
                        "Zapisano: %s",
                        data["title"],
                    )

            except (requests.RequestException, ValueError) as exc:
                db.rollback()
                logging.exception(
                    "Błąd pobierania %s: %s",
                    url,
                    exc,
                )

            except Exception:
                db.rollback()
                logging.exception(
                    "Błąd zapisu wydarzenia %s",
                    url,
                )

    logging.info("Scraping zakończony.")


if __name__ == "__main__":
    main()
