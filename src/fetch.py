"""Stage fetch: download Contracts Finder OCDS award-stage release packages (UK, OGL v3).
Resumable: each (window, page) saved as gzip JSON under data/raw/."""
import gzip, json, os, sys, time, urllib.request, datetime as dt
from concurrent.futures import ThreadPoolExecutor
BASE = "https://www.contractsfinder.service.gov.uk/Published/Notices/OCDS/Search"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
HDR = dict(UA="x")


def get(url, tries=12):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=dict([("User-Agent", "ax11-lab/1.0 (research use of OGL data)")]))
            with urllib.request.urlopen(req, timeout=90) as r:
                return r.read()
        except Exception:
            time.sleep(min(120, 10 * (i + 1)))
    raise RuntimeError("fetch failed " + url)


def window(start, end, tag):
    url = f"{BASE}?publishedFrom={start}&publishedTo={end}&stages=award&size=100"
    page = 0
    n = 0
    while url:
        fn = os.path.join(RAW, f"{tag}_p{page:04d}.json.gz")
        if os.path.exists(fn):
            d = json.loads(gzip.open(fn).read())
        else:
            body = get(url)
            d = json.loads(body)
            tmp = fn + ".tmp"
            with gzip.open(tmp, "wb") as f:
                f.write(body)
            os.rename(tmp, fn)
            time.sleep(1.5)
        n += len(d["releases"])
        page += 1
        url = (d.get("links") or dict()).get("next")
    return tag, n


if __name__ == "__main__":
    start = dt.date.fromisoformat(sys.argv[1])
    weeks = int(sys.argv[2])
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 6
    os.makedirs(RAW, exist_ok=True)
    jobs = []
    for w in range(weeks):
        a = start + dt.timedelta(days=7 * w)
        b = a + dt.timedelta(days=7)
        jobs.append((a.isoformat(), b.isoformat(), f"w{a.isoformat()}"))
    tot = 0
    with ThreadPoolExecutor(workers) as ex:
        for tag, n in ex.map(lambda j: window(*j), jobs):
            tot += n
            print(tag, n, tot, flush=True)
    print("DONE", tot, flush=True)
