Bible verses straight to your terminal — instantly.

A verse appears each time you open a new terminal, and `verse` on the command line prints one on demand. Verses are served from a small local cache that refills itself in the background, so display is effectively instant.

## Install

Requires Python 3.8+ and `pip`. One line:

```sh
curl -fsSL https://raw.githubusercontent.com/cristihainic/verse/master/verse.py | python3 - --install
```

The installer:

- Installs the Python dependencies (`beautifulsoup4`, `requests`) to your user site
- Copies `verse` to `~/.local/bin/verse`
- Appends a line to your shell rc (`~/.zshrc`, `~/.bashrc`, or `~/.bash_profile`) so a verse prints on every new terminal
- Primes the verse cache in the background

Open a new terminal to see your first verse. Type `verse` any time to print another.

If `~/.local/bin` isn't on your `$PATH`, the installer will tell you the one line to add.

## How it works

On every invocation, `verse` pops a pre-fetched verse from `~/.cache/verse/pool.json` and prints it with no network call. It then forks a detached background process to top the pool back up to 30 verses. Normal terminal usage keeps the cache perpetually full.

If the pool is ever empty (first run, or prolonged offline use), `verse` falls back to a live fetch.

## Uninstall

One line:

```sh
verse --uninstall
```

This removes the `verse` binary, the cache at `~/.cache/verse`, and the startup line from your shell rc. The `beautifulsoup4` and `requests` packages are left in place — remove them with `pip uninstall beautifulsoup4 requests` if you want them gone too.

## Platforms

Works on Linux and macOS. Not supported on Windows.

## Credits

Thanks to [DailyVerses.net](https://dailyverses.net/) for being such a scrapable site and providing the data used by this program!
