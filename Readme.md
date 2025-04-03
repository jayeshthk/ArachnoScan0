# ArachnoScan0 - The Agile Web Pathfinder

A high-performance async web crawler that meticulously maps website structures with surgical precision.
crawler built with Python and aiohttp for discovering URLs on websites.
Like a spider sensing vibrations across its web, ArachnoScan detects every meaningful connection within your target sites.

![spider](./spider.jpg)

## Features

- Async I/O for high performance
- Multiple discovery sources (links, scripts, forms)
- Configurable depth and concurrency
- JSON output support
- URL filtering and scope control

## Installation

```bash
git clone https://github.com/jayeshthk/ArachnoScan0.git
cd ArachnoScan0
pip install -r requirements.txt
```

## Usage

Basic usage:

```bash
cat urls.txt | python crawler.py [options]
```

Example:

```bash
echo "https://example.com" | python crawler.py -d 2 -t 10 --json
```

## Docker Usage

Build the image:

```bash
docker build -t web-crawler .
```

Run with Docker:

```bash
cat urls.txt | docker run -i web-crawler [options]
```

Callable Async method :

```python
from hakrawler import run_crawler

await run_crawler(
        urls=["https://example.com"],
        depth=2,
        threads=10,
        show_source=True,
        insecure=True
    )

```

## Options

```
  -i, --inside           Only crawl inside path
  -t, --threads          Number of threads to utilise (default: 8)
  -d, --depth            Depth to crawl (default: 2)
  --max-size             Page size limit in KB
  --insecure             Disable TLS verification
  --subs                 Include subdomains
  --json                 Output as JSON
  -s, --show-source      Show source of URL
  -w, --show-where       Show where URL was found
  -H, --headers          Custom headers (format: "Header: Value;;Header2: Value2")
  -u, --unique           Show only unique URLs
  --proxy                Proxy URL
  --timeout              Max time per URL in seconds
  --disable-redirects    Disable following redirects
```

## Examples

1. Basic crawl with JSON output:

```bash
cat urls.txt | python crawler.py -d 3 --json
```

2. Crawl with custom headers and proxy:

```bash
cat urls.txt | python crawler.py -H "Cookie: session=123;;Referer: https://example.com" --proxy http://localhost:8080
```

3. Get unique results from subdomains:

```bash
cat urls.txt | python crawler.py --subs -u
```

5. Print the unique urls with source:

```bash
echo "https://google.com" | python crawler.py -u -w
```

# Citation =>

- @hakluke - ![hakrawler](https://github.com/hakluke/hakrawler.git) a Golang implementation for web crawler.
