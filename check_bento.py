import urllib.request
import json
import hashlib

api_url = "https://opbento.vercel.app/api/bento?n=Moin&g=moin-dbud&x=Moin_Sheikh09&l=moin-build&i=https%3A%2F%2Fwww.moinsheikh.in%2Fimage1.webp&p=https%3A%2F%2Fwww.moinsheikh.in%2F&z=5d512"
with urllib.request.urlopen(api_url, timeout=30) as r:
    data = json.load(r)
print("response url:", data["url"])
for ts in ["1", "2", "3"]:
    url = data["url"] + ("&ghcache=" + ts if "?" in data["url"] else "?ghcache=" + ts)
    with urllib.request.urlopen(url, timeout=30) as img:
        body = img.read()
        print(ts, "url=", url)
        print("  size", len(body))
        print("  sha", hashlib.sha256(body).hexdigest())
