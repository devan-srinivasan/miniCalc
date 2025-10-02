#!/usr/bin/env python
from pathlib import Path

import trio # type: ignore

from lean_client.trio_server import TrioLeanServer

async def main():
    filename = '/Users/mrmackamoo/Projects/calc4lean/lean/LeanCalc/main.lean'
    lines = Path(filename).read_text().split('\n')

    async with trio.open_nursery() as nursery:
        server = TrioLeanServer(nursery, debug=False)
        await server.start()
        await server.full_sync(filename)

        for i, line in enumerate(lines):
            before = await server.state(filename, i+1, 0)
            after = await server.state(filename, i+1, len(line))
            if before or after:
                print(f'Line {i+1}: {line}')
                print(f'State before:\n{before}\n')
                print(f'State after:\n{after}\n')

        server.kill()
        nursery.cancel_scope.cancel()

if __name__ == '__main__':
    trio.run(main)