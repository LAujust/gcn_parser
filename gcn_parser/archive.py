import requests
from bs4 import BeautifulSoup

BASE_URL = "https://gcn.nasa.gov/circulars/events/"


def fetch_event_circulars(event: str) -> list[dict]:
    """Fetch all GCN circulars for a given event from the NASA archive.

    Args:
        event: Event identifier, e.g. ``"GRB250101A"``.

    Returns:
        List of dicts with keys ``gcn`` and ``text``.

    Raises:
        requests.HTTPError: If the HTTP request fails.
    """
    url = BASE_URL + event.lower()
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    results = []

    for h2 in soup.find_all("h2"):
        gcn_number = h2.get_text(strip=True)
        block = h2.parent
        pre = block.find("pre")
        if pre:
            text = pre.get_text("\n", strip=True)
            results.append({"gcn": gcn_number, "text": text})

    return results
