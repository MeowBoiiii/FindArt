
import json
import time
from datetime import datetime
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://bwa.wroc.pl"
LIST_URL = f"{BASE_URL}/wydarzenie/"
OUTPUT_FILE = "wydarzenia_bwa.json"

HEADERS = {
    "User-Agent": (
        "FindArt/1.0 "
        "(educational cultural-events research scraper)"
    )
}

session = requests.Session()
session.headers.update(HEADERS)


def get_soup(url):
    """Pobiera stronę i zwraca obiekt BeautifulSoup."""
    response = session.get(url, timeout=25)
    response.raise_for_status()

    # requests zwykle poprawnie rozpoznaje kodowanie strony.
    response.encoding = response.apparent_encoding
    return BeautifulSoup(response.text, "html.parser")


def clean_text(element):
    if not element:
        return None
    return element.get_text(" ", strip=True) or None


def parse_date(soup, itemprop):
    element = soup.select_one(f'time[itemprop="{itemprop}"]')

    if not element:
        return None

    value = element.get("datetime") or element.get("content")

    if not value:
        return None

    try:
        return datetime.fromisoformat(value).isoformat()
    except ValueError:
        return None


def extract_event(html, source_url):
    """Parsuje stronę pojedynczego wydarzenia."""
    soup = BeautifulSoup(html, "html.parser")

    event = soup.select_one(
        'div.event__details[itemtype="https://schema.org/Event"]'
    )

    if not event:
        print(f"  Pominięto — brak event__details: {source_url}")
        return None

    # Tytuł znajduje się w ukrytej etykiecie początku wydarzenia.
    title_element = event.select_one(
        '.dl.dt [itemprop="name"]'
    )
    title = clean_text(title_element)

    # Opis ze znacznika schema.org.
    description = clean_text(
        event.select_one('[itemprop="description"]')
    )

    # Dodatkowe informacje, np. wernisaż i wydarzenia towarzyszące.
    extra_element = soup.select_one(".sidebar__content")
    extra_info = clean_text(extra_element)

    # Daty zachowują informację o strefie czasowej.
    start_date = parse_date(event, "startDate")
    end_date = parse_date(event, "endDate")

    # Plakat: najpierw Open Graph, potem obrazek wydarzenia.
    image_element = soup.select_one('meta[property="og:image"]')
    image_url = (
        image_element.get("content") if image_element else None
    )

    if not image_url:
        image_element = event.select_one('img[itemprop="image"]')
        image_url = (
            image_element.get("src") if image_element else None
        )

    # Typ wydarzenia z okruszków nawigacyjnych.
    event_type = None
    for item in soup.select(
        'script.rank-math-schema[type="application/ld+json"]'
    ):
        try:
            data = json.loads(item.string or item.get_text())
            graph = data.get("@graph", [])

            for node in graph:
                if node.get("@type") == "BreadcrumbList":
                    crumbs = node.get("itemListElement", [])
                    if len(crumbs) >= 3:
                        event_type = crumbs[-2]["item"].get("name")
                    break
        except (ValueError, TypeError, KeyError, AttributeError):
            continue

    # Wszystkie lokalizacje wydarzenia.
    galleries = []
    location = event.select_one('[itemprop="location"]')

    if location:
        for name_element in location.select(
            ':scope > [itemprop="name"]'
        ):
            name = clean_text(name_element)

            address_element = name_element.find_next_sibling(
                "div", attrs={"itemprop": "address"}
            )

            def address_value(prop):
                if not address_element:
                    return None
                return clean_text(
                    address_element.select_one(
                        f'[itemprop="{prop}"]'
                    )
                )

            street = address_value("streetAddress")
            postal_code = address_value("postalCode")
            city = address_value("addressLocality")

            address_parts = [
                street,
                " ".join(
                    part for part in [postal_code, city] if part
                ),
            ]
            address = ", ".join(
                part for part in address_parts if part
            ) or None

            if name:
                galleries.append({
                    "name": name,
                    "address": address,
                    "city": city,
                    "website_url": BASE_URL,
                })

    return {
        "title": title,
        "event_type": event_type,
        "start_date": start_date,
        "end_date": end_date,
        "description": description,
        "extra_info": extra_info,
        "image_url": image_url,
        "source_url": source_url,
        "galleries": galleries,
    }


def get_event_links(list_url):
    """Zbiera linki do wydarzeń z jednej strony listy."""
    soup = get_soup(list_url)
    links = set()

    for anchor in soup.select("a[href]"):
        href = urljoin(list_url, anchor["href"])
        parsed = urlparse(href)

        # Tylko wydarzenia z domeny BWA.
        if parsed.netloc not in ("bwa.wroc.pl", "www.bwa.wroc.pl"):
            continue

        path = parsed.path.rstrip("/")

        if (
            path.startswith("/wydarzenie/")
            and path != "/wydarzenie"
            and "/page/" not in path
        ):
            links.add(f"{parsed.scheme}://{parsed.netloc}{path}/")

    # Usuń duplikaty i zachowaj kolejność.
    return sorted(links)


def get_listing_pages(max_pages=20):
    """Przechodzi po paginacji listy wydarzeń."""
    current_url = LIST_URL
    visited = set()

    for _ in range(max_pages):
        if current_url in visited:
            break

        visited.add(current_url)
        print(f"Pobieram listę: {current_url}")
        soup = get_soup(current_url)

        yield current_url, soup

        next_link = soup.select_one(
            'a.next.page-numbers, '
            'a[rel="next"], '
            '.pagination a.next'
        )

        if not next_link or not next_link.get("href"):
            break

        current_url = urljoin(current_url, next_link["href"])


def scrape_bwa(max_pages=20):
    """Pobiera wydarzenia z listy i parsuje strony szczegółowe."""
    event_urls = []
    seen_urls = set()

    for page_url, soup in get_listing_pages(max_pages):
        for anchor in soup.select("a[href]"):
            href = urljoin(page_url, anchor["href"])
            parsed = urlparse(href)
            path = parsed.path.rstrip("/")

            if parsed.netloc not in (
                "bwa.wroc.pl", "www.bwa.wroc.pl"
            ):
                continue

            if (
                path.startswith("/wydarzenie/")
                and path != "/wydarzenie"
                and "/page/" not in path
            ):
                normalized_url = (
                    f"https://bwa.wroc.pl{path}/"
                )

                if normalized_url not in seen_urls:
                    seen_urls.add(normalized_url)
                    event_urls.append(normalized_url)

        time.sleep(0.5)

    print(f"\nZnaleziono linków: {len(event_urls)}")
    events = []

    for index, url in enumerate(event_urls, start=1):
        print(f"[{index}/{len(event_urls)}] {url}")

        try:
            detail_soup = get_soup(url)
            event = extract_event(str(detail_soup), url)

            if event and event["title"]:
                events.append(event)
                print(f"  OK: {event['title']}")

        except requests.RequestException as error:
            print(f"  Błąd pobierania: {error}")

        except Exception as error:
            print(f"  Błąd parsowania: {error}")

        # Nie wysyłamy żądań zbyt szybko.
        time.sleep(1)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(
            events,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print(f"\nGotowe! Zapisano {len(events)} wydarzeń.")
    print(f"Plik wynikowy: {OUTPUT_FILE}")


if __name__ == "__main__":
    scrape_bwa(max_pages=20)
