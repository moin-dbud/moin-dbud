import urllib.request

url = 'https://opbento.vercel.app/api/bento/image?g=moin-dbud&z=5d512'
req = urllib.request.Request(url, headers={'User-Agent': 'python-urllib'})
with urllib.request.urlopen(req, timeout=30) as r:
    print('status', r.status)
    for k, v in r.getheaders():
        print(f'{k}: {v}')
