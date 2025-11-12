import argparse, os, re, urllib.parse
from tqdm import tqdm
from playwright.sync_api import sync_playwright

def sanitize(name: str) -> str:
    return re.sub(r"[^\w\.-]+", "_", name).strip("_")[:180]

def read_urls(path: str):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            u = line.strip()
            if u and not u.startswith("#"):
                yield u

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--viewport", default="1366x768")
    p.add_argument("--delay", type=int, default=1500)
    p.add_argument("--timeout", type=int, default=40000)
    args = p.parse_args()
    w, h = (int(x) for x in args.viewport.lower().split("x"))
    os.makedirs(args.out, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context(viewport={"width": w, "height": h})
        page = context.new_page()
        for url in tqdm(list(read_urls(args.input)), desc="Webshot"):
            try:
                parsed = urllib.parse.urlparse(url)
                frag = urllib.parse.unquote(parsed.fragment)
                base = f"{parsed.netloc}_{parsed.path}".replace("/", "_")
                if frag:
                    base += "_" + sanitize(frag)[:60]
                fname = sanitize(base) or "page"
                out_path = os.path.join(args.out, f"{fname}.png")
                page.goto(url, timeout=args.timeout, wait_until="domcontentloaded")
                # try to accept cookies
                for sel in ["button:has-text('Accept')", "button:has-text('Accetta')", "button:has-text('I agree')", "[id*='onetrust-accept']"]:
                    try:
                        el = page.locator(sel)
                        if el.first.is_visible():
                            el.first.click(timeout=1000)
                            break
                    except Exception:
                        pass
                page.wait_for_load_state("networkidle", timeout=args.timeout)
                if args.delay > 0:
                    page.wait_for_timeout(args.delay)
                page.screenshot(path=out_path, full_page=True)
            except Exception as e:
                with open(os.path.join(args.out, f"ERROR_{sanitize(url)}.txt"), "w", encoding="utf-8") as ef:
                    ef.write(str(e))
        browser.close()

if __name__ == "__main__":
    main()
