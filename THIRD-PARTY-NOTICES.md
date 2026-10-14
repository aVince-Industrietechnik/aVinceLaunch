# Third-party notices

aVinceLaunch is a fork. This file records where the inherited code comes
from and under which terms it was received. Nothing in this file may be
removed when the code is redistributed.

## TheLauncher

| | |
|---|---|
| Name | TheLauncher |
| UUID | `thelauncher@sin-apps.com` |
| Version taken as baseline | 1.0.3 |
| Author | MHK924 |
| Homepage | https://sin-apps.com/launchdesklet |
| Source | `linuxmint/cinnamon-spices-desklets`, commit `2b84136` (2026-09-07, repository state) |
| Last upstream commit of the xlet directory | `8e2943e` (local Spices index, 2026-10-07) |
| Declared license | **MIT**, stated in the upstream `info.json` (`"license": "MIT"`) and in the upstream `README.md` |

The upstream `info.json` and `README.md` are kept verbatim in
[`docs/upstream/`](docs/upstream/) as the record of that declaration.

The first commit of this repository contains the upstream code exactly as
published, so the boundary between inherited code and aVinceLaunch's own
work stays verifiable at any time:

```
git diff <first-commit> HEAD -- Desklet/
```

### License record

The upstream README points to a "repository LICENSE file" for the MIT text.
No such file exists in the upstream xlet directory, and the repository root
carries `COPYING` (GPL-2.0) for the collection as a whole. The license
declaration for TheLauncher itself is the `"license": "MIT"` field in
`info.json`, the README statement, and the author's own pull request that
added TheLauncher to Cinnamon Spices (linuxmint/cinnamon-spices-desklets
#1867, 2026-07-09: "License: MIT").

On 2026-10-13 the author was asked in that pull request to confirm the MIT
declaration and to name the copyright holder for the notice below:
https://github.com/linuxmint/cinnamon-spices-desklets/pull/1867#issuecomment-6147520770

The author answered the same day:
https://github.com/linuxmint/cinnamon-spices-desklets/pull/1867#issuecomment-6147812746

- TheLauncher is licensed under the MIT License (confirmed).
- No particular copyright line is required; the author asked only to be
  mentioned. The notice below keeps the usual MIT form with the author's name,
  so the licence text stays complete.
- The missing LICENSE file in the upstream folder is for the author to look
  into; it does not change the terms.
- The author explicitly welcomes further development ("Feel free to enhance
  as you see fit").

Many thanks to MHK924 for TheLauncher and for kindly allowing it to be built
upon.

### MIT notice for the inherited parts

```
MIT License

Copyright (c) 2026 MHK924
(TheLauncher, https://sin-apps.com/launchdesklet)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Cinnamon's about dialog

`Desklet/about-dialog.py` (inherited from TheLauncher) follows the structure
of Cinnamon's `/usr/bin/xlet-about-dialog` (Linux Mint, GPL-2.0-or-later,
see `/usr/share/doc/cinnamon/copyright`). The MIT notice above therefore
does not describe that file's origin completely; GPL-2.0-or-later is
compatible with this project's GPL-3.0-only.

## Copy inside the desklet package

Only the `Desklet/` folder is distributed through Cinnamon Spices. It
carries its own [`Desklet/THIRD-PARTY-NOTICES.md`](Desklet/THIRD-PARTY-NOTICES.md)
(GPL-3.0-only notice, full MIT notice, acknowledgments) and
[`Desklet/LICENSE`](Desklet/LICENSE) (GPL-3.0 text, identical to the root
`LICENSE`). Both must stay in step with this file.

## Acknowledgment carried over from upstream

TheLauncher itself credits *Quick Links - Launcher* by **NotSirius-A** as its
starting point. That acknowledgment is kept in the desklet metadata and is
repeated here.

## aVinceLaunch's own work

Everything added after the baseline commit is

```
Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik
SPDX-License-Identifier: GPL-3.0-only
```

MIT-licensed code may be combined into a GPL-3.0 work; the MIT notice above
stays in force for the inherited parts.
