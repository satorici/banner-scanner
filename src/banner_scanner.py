import argparse
import asyncio
import itertools
import sys
import uuid

from httpx import AsyncClient, Limits, Request

AMOUNT = None  # None for all
CONCURRENCY = 1000

client = AsyncClient(limits=Limits(max_connections=CONCURRENCY))


async def probe_ip(ip: str, port: int, timeout=3):
    try:
        req = Request(
            "HEAD",
            f"http://{ip}:{port}/{uuid.uuid4().hex}",
            extensions={
                "timeout": {
                    "connect": timeout,
                    "pool": timeout,
                    "read": timeout,
                    "write": timeout,
                }
            },
        )
        res = await client.send(req)

        if res.headers.get("Server") is not None:
            print(ip, res.headers["Server"], res.status_code, sep=",")
        else:
            print(ip, "NoServerHeader", file=sys.stderr, sep=",")
    except Exception as e:
        print(ip, e.__class__.__name__, file=sys.stderr, sep=",")


async def worker(ips: list[str], port: int, timeout: int):
    for ip in ips:
        await probe_ip(ip, port, timeout)


def read_ips(ip_file: str):
    ips: list[str] = []

    with open(ip_file) as file:
        for line in itertools.islice(file, AMOUNT):
            ips.append(line.strip())

    return ips


def split(a, n):
    k, m = divmod(len(a), n)
    return (a[i * k + min(i, m) : (i + 1) * k + min(i + 1, m)] for i in range(n))


def cli():
    parser = argparse.ArgumentParser()

    parser.add_argument("file", help="File with a list of IP addresses")
    parser.add_argument("port")
    parser.add_argument("--timeout", type=int, default=3)

    args = parser.parse_args()

    ips = read_ips(args.file)

    async def main():
        await asyncio.gather(
            *[worker(part, args.port, args.timeout) for part in split(ips, CONCURRENCY)]
        )

    asyncio.run(main())


if __name__ == "__main__":
    cli()
