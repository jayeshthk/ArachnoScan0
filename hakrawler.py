import asyncio
import json
import re
import sys
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import aiohttp
from aiohttp import ClientSession, ClientTimeout
from types import SimpleNamespace

def parse_headers(raw_headers):
    headers = {}
    if not raw_headers:
        return headers
    for header in raw_headers.split(';;'):
        if ': ' in header:
            key, val = header.split(': ', 1)
        elif ':' in header:
            key, val = header.split(':', 1)
        else:
            continue
        headers[key.strip()] = val.strip()
    return headers

async def crawl(start_url, results_queue, semaphore, session, args):
    try:
        parsed_start_url = urlparse(start_url)
        hostname = parsed_start_url.hostname
        if not hostname:
            return

        allowed_domains = [hostname] if not args.subs else None
        regex = None
        if args.subs:
            escaped_hostname = re.escape(hostname)
            pattern = re.compile(rf'.*([.]|//){escaped_hostname}(/|#|\?|$|:)')
            regex = pattern

        visited = set()
        queue = asyncio.Queue()
        await queue.put((start_url, 0))

        while not queue.empty():
            current_url, depth = await queue.get()
            if depth > args.depth or current_url in visited:
                queue.task_done()
                continue
            visited.add(current_url)

            try:
                async with semaphore:
                    timeout = ClientTimeout(total=args.timeout if args.timeout > 0 else None)
                    async with session.get(
                        current_url,
                        proxy=args.proxy,
                        allow_redirects=not args.disable_redirects,
                        timeout=timeout
                    ) as response:
                        if args.max_size > 0:
                            content_length = response.headers.get('Content-Length')
                            if content_length and int(content_length) > args.max_size * 1024:
                                continue

                        content = await response.text()
                        soup = BeautifulSoup(content, 'html.parser')

                        for tag, attr, source in [
                            ('a', 'href', 'href'),
                            ('script', 'src', 'script'),
                            ('form', 'action', 'form')
                        ]:
                            elements = soup.find_all(tag, {attr: True})
                            for el in elements:
                                link = el.get(attr)
                                abs_link = urljoin(current_url, link)
                                parsed_link = urlparse(abs_link)

                                allowed = False
                                if allowed_domains:
                                    if parsed_link.hostname in allowed_domains:
                                        allowed = True
                                elif regex:
                                    allowed = bool(regex.match(abs_link))
                                else:
                                    allowed = True

                                if not allowed:
                                    continue

                                if args.inside:
                                    start_path = parsed_start_url.path
                                    link_path = parsed_link.path
                                    if not link_path.startswith(start_path):
                                        continue

                                await results_queue.put((abs_link, source, current_url))
                                if depth < args.depth:
                                    await queue.put((abs_link, depth + 1))

            except Exception as e:
                print(f"Error fetching {current_url}: {e}", file=sys.stderr)
            finally:
                queue.task_done()

    except asyncio.CancelledError:
        print(f"Timeout for {start_url}", file=sys.stderr)
        raise

async def print_results(results_queue, args, urls_found):
    seen = set()
    while True:
        try:
            url, source, where = await results_queue.get()
            if args.unique:
                if url in seen:
                    results_queue.task_done()
                    continue
                seen.add(url)

            output = ""
            if args.json:
                result = {
                    "Source": source,
                    "URL": url,
                    "Where": where if args.show_where else ""
                }
                output = json.dumps(result)
            else:
                parts = []
                if args.show_source:
                    parts.append(f"[{source}]")
                if args.show_where:
                    parts.append(f"[{where}]")
                parts.append(url)
                output = ' '.join(parts)
            
            print(output)
            urls_found[0] = True
            results_queue.task_done()
        except asyncio.CancelledError:
            break

async def run_crawler(
    urls,
    inside=False,
    threads=8,
    depth=2,
    max_size=-1,
    insecure=False,
    subs=False,
    json=False,
    show_source=False,
    show_where=False,
    headers_str='',
    unique=False,
    proxy='',
    timeout=-1,
    disable_redirects=False
):
    args = SimpleNamespace(
        inside=inside,
        threads=threads,
        depth=depth,
        max_size=max_size,
        insecure=insecure,
        subs=subs,
        json=json,
        show_source=show_source,
        show_where=show_where,
        headers=headers_str,
        unique=unique,
        proxy=proxy,
        timeout=timeout,
        disable_redirects=disable_redirects
    )

    headers = parse_headers(args.headers)
    clean_urls = [url.strip() for url in urls if url.strip()]

    if not clean_urls:
        print("No valid URLs provided", file=sys.stderr)
        return

    connector = aiohttp.TCPConnector(ssl=not args.insecure)
    async with ClientSession(headers=headers, connector=connector) as session:
        results_queue = asyncio.Queue()
        urls_found = [False]
        consumer = asyncio.create_task(print_results(results_queue, args, urls_found))

        semaphore = asyncio.Semaphore(args.threads)
        crawlers = []

        for url in clean_urls:
            task = asyncio.create_task(
                asyncio.wait_for(
                    crawl(url, results_queue, semaphore, session, args),
                    timeout=args.timeout if args.timeout > 0 else None
                )
            )
            crawlers.append(task)

        try:
            await asyncio.gather(*crawlers)
        except:
            pass
        finally:
            await results_queue.join()
            consumer.cancel()
            try:
                await consumer
            except asyncio.CancelledError:
                pass

        if not urls_found[0]:
            print("No URLs found during crawling", file=sys.stderr)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--inside', action='store_true')
    parser.add_argument('-t', '--threads', type=int, default=8)
    parser.add_argument('-d', '--depth', type=int, default=2)
    parser.add_argument('--max-size', type=int, default=-1)
    parser.add_argument('--insecure', action='store_true')
    parser.add_argument('--subs', action='store_true')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('-s', '--show-source', action='store_true')
    parser.add_argument('-w', '--show-where', action='store_true')
    parser.add_argument('-H', '--headers', type=str, default='')
    parser.add_argument('-u', '--unique', action='store_true')
    parser.add_argument('--proxy', type=str, default='')
    parser.add_argument('--timeout', type=int, default=-1)
    parser.add_argument('--disable-redirects', action='store_true')
    cli_args = parser.parse_args()

    # Read URLs from stdin
    input_urls = [line.strip() for line in sys.stdin if line.strip()]
    
    asyncio.run(run_crawler(
        urls=input_urls,
        inside=cli_args.inside,
        threads=cli_args.threads,
        depth=cli_args.depth,
        max_size=cli_args.max_size,
        insecure=cli_args.insecure,
        subs=cli_args.subs,
        json=cli_args.json,
        show_source=cli_args.show_source,
        show_where=cli_args.show_where,
        headers_str=cli_args.headers,
        unique=cli_args.unique,
        proxy=cli_args.proxy,
        timeout=cli_args.timeout,
        disable_redirects=cli_args.disable_redirects
    ))