# LTP2-party

**Lucky & Tigrou Party 2, 1998: the event pages.** LTP was a French demoparty series organised by
Orange Juice. This is the small ASP site that ran the registrations, the compo lists and the
votes of the second party (1998).

Archive of an old dynamic website (classic ASP over flat `.txt` files), published as a
**100 % static, read-only site** on bunny.net at the hostname of [`site.json`](site.json).
Kept online for history, no longer developed. Visitors can never write anything: the pages are
the static pages committed in `site/`, the CDN only serves files, and every method except
GET/HEAD/OPTIONS is refused at the edge. Other LTP archives: `LTP4`, `LTP4-postparty`.

## Layout

| Path | Content |
| --- | --- |
| `site/` | The static site, exactly as served |
| `private/` | Raw originals (git-ignored, never published): `party-raw/` is a copy of `Sites web/ltp/party/` (ASP sources, compo and vote files, **the registrations**) |
| `hosting/404.html` | Custom 404 page, deployed next to `site/` |
| `site.json` | The only site-specific settings: repository, storage zone, pull zone, hostname, 404 page |
| `infra/` | OpenTofu: storage zone, pull zone, hostname, hardening edge rules (state encrypted, committed) |
| `infra/secrets.env` | Proton Pass **references** to the secrets (vault `OldSites`), no secret values |
| `scripts/statify.py` | Raw originals (`private/`) → `site/` (run locally) |
| `scripts/verify_build.py` | Checks `site/`: no ASP, forms, e-mails, codes, personal value of the registrations, new broken links |
| `scripts/check_excludes.py` | Fails if `site/` holds a path of `scripts/exclude-globs.txt` |
| `scripts/preview.py` | Local preview with the charsets of the edge rules |
| `scripts/deploy.py` | Sync `site/` to the storage zone, purge the CDN |
| `scripts/smoke_test.py` | Check the public site: pages as in `site/`, POST refused, security headers, charset, 404 |
| `scripts/bootstrap.sh` | One-time setup (`new` for this site, `github` for the repository and secrets) |

DNS is not managed here: the hostname is a CNAME to `<pull zone>.b-cdn.net` at Infomaniak.

## What was changed from the original

Source: `Sites web/ltp/party/` on the NAS, copied into `private/party-raw/`. The original is four
ASP pages (`inscription.asp`, `inscription_liste.asp`, `votes.asp`, `votes_resultats.asp`) over
flat files: `inscriptions/` (one file per registration), `compos/` (entries per compo) and
`votes/` (scores). Nothing of it can run any more, so each page is rebuilt once by
`scripts/statify.py`; `build-meta/redirects.tsv` lists the old → new names.

- **Registration form** (`inscription.html`) → an "archived, read-only" notice over the original
  background image (`back_p.jpg`), shown once. The form fields and their ASP code are gone.
- **List of attendees** (`inscription_liste.html`): the original table of code, handle, group,
  sex and price is reduced to **handle and group only** (217 registrations, sorted by handle as
  the ASP did, plus the count). Nothing else of a registration is published.
- **Vote form** (`votes.html`) → an "archived, read-only" notice.
- **Vote results** (`votes_resultats.html`) and **compo lists** (`compos.html`, added) are
  rendered from `compos/` and `votes/`. Only 4 of the 12 compos kept entries, and the vote files
  hold a few test votes (the entries of one compo are keyboard mashing): they are shown as
  found, with a note saying they are not the party's results.
- **Framed**: every public page (`index.html`, `inscription.html`, ...) is a small shell with an
  iframe of 1021x650, the size of the background image, loading the content page `f/<same name>`;
  links inside the frames stay inside the frame. The frame scrolls when a page is longer.
- **Added**: `index.html` (the original has no entry page; marked "page added in 2026"), a
  navigation line on the rebuilt pages, `compos.html`. `face="Verdana"` gets sans-serif fallbacks.
- **Not published, never**: the registration files (`inscriptions/`, `#save/`:
  names, birth dates, addresses, e-mails), `inscriptions.zip` (the same data), the registration
  codes (they were the voting passwords), the raw `votes/` and `compos/` files, every `.asp`
  source, `#html_bak/` (older ASP copies) and `#images/` (Photoshop sources of the form, 38 MB).
  The build is checked against the raw registrations: `scripts/verify_build.py` fails if any
  name, address or e-mail value appears in `site/`, or any 8-digit hex code.
- **Not found elsewhere**: the Wayback Machine (CDX API, 2026-11-23) has no capture of
  `ltp.ojuice.net`, `www.ojuice.net/ltp*` or `ojuice.net/ltp*` in 1998-1999 (the first capture of
  `ltp.ojuice.net` is 2000-08, the LTP4 site), so no other page of LTP2 could be restored. The
  original public site of the party (the pages before the registrations) is not on the NAS either.

## Regenerating `site/`

`site/` is generated: never edit it by hand, fix `scripts/statify.py` and regenerate. The raw
originals live in `private/` (git-ignored; `$LTP2_RAW` overrides the path); the build never reads
the NAS. Keep `private/`, it is the working copy.

```bash
python3 scripts/statify.py && python3 scripts/verify_build.py && python3 scripts/check_excludes.py
```

```bash
python3 scripts/preview.py 3571
```

## Hardening (`infra/main.tf`)

- Edge rule 1: any method other than GET, HEAD, OPTIONS is blocked at the edge, before the
  origin (bunny.net answers 403; edge rules cannot return 405). `block_post_requests` is also on.
- Edge rule 2: `Content-Security-Policy` (same-origin, inline script/style allowed, images from
  the site only, `form-action 'none'`), `X-Content-Type-Options: nosniff`,
  `X-Frame-Options: SAMEORIGIN`, `Referrer-Policy`, HSTS, `Permissions-Policy`.
- Edge rules 3-4: `Content-Type` with `charset=iso-8859-1` for `.htm/.html/.shtml/.SHTML` and
  `.txt/.c` (the pages are ISO-8859-1).
- Edge rule 5: browser cache 7 days for images and archives, 1 hour for pages; CDN cache 30
  days, purged on each deployment.
- COOP/CORP `same-origin`. Search engines are allowed (no `X-Robots-Tag`, no `robots.txt`).
- CI (deploy workflow), before upload: excluded-paths check, `scripts/verify_build.py --build site`
  and a ClamAV scan of `site/`.
- Cookies are stripped before the origin; TLS "Compatible"; forced HTTPS.
- Custom 404: `hosting/404.html` (`not_found_page` in `site.json`).

## Deploying

- **Website**: push a change under `site/` or `hosting/` to `main` → workflow *Website: deploy*
  runs the checks, uploads the changed files, deletes the removed ones, purges the CDN and
  runs the smoke test. A manual run allows a dry run.
- **Infra**: pull requests touching `infra/` show the plan; apply is a manual run of
  *Infra: bunny.net* (action `apply`, from `main`), which commits the encrypted state, deploys
  `site/` and runs the smoke test.

GitHub secrets: `BUNNY_API_KEY` (bunny.net account API key) and `TF_VAR_STATE_PASSPHRASE`
(state encryption), both from Proton Pass vault `OldSites`.

Locally (Proton Pass CLI logged in):

```bash
pass-cli run --env-file infra/secrets.env -- python3 scripts/deploy.py --dry-run
```

```bash
cd infra && pass-cli run --env-file secrets.env -- tofu plan
```

## First setup

1. Write `site.json` and validate offline (done on 2026-11-23; secrets are the shared ones of
   the other old sites: same Proton Pass references):

   ```bash
   scripts/bootstrap.sh new LTP2-party ltp2-party ltp2-party ltp2-party.sauthier.family
   ```

2. Create the GitHub repository and its secrets, push, open the PR:

   ```bash
   scripts/bootstrap.sh github
   ```

3. After merge, run the *Infra: bunny.net* workflow with action `apply`: it creates the zones,
   hostname and edge rules, deploys `site/` and runs the smoke test.
4. At Infomaniak (Manager > Domaines > sauthier.family > Zone DNS), add a CNAME
   `ltp2-party` → `ltp2-party.b-cdn.net`. The certificate is issued once DNS answers;
   re-run the smoke test (*Monitoring: weekly smoke test*, manual run) after a few minutes.

