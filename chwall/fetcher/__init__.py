import requests
from chwall import __version__


def requests_get(url, agent=None, **kwargs):
    if not agent:
        agent = "Chwall:v{version} (+https://git.umaneti.net/chwall)"
    headers = kwargs.pop("headers", {})
    headers["user-agent"] = agent.format(version=__version__)
    return requests.get(url, headers=headers, **kwargs)
