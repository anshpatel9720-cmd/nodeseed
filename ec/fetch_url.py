import requests


def fetch_url(url, method="get", params=None):
    response = requests.request(method, url, params=params, timeout=10)
    response.raise_for_status()
    return response
