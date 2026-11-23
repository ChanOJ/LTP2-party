#!/usr/bin/env python3
"""Statify the LTP 2 (Lucky & Tigrou Party, 1998) event site into plain static HTML.

    python3 scripts/statify.py [--raw PATH] [--out site]

The original is a handful of classic-ASP pages over flat files (registrations, compo
lists, votes). Nothing of it can run any more, so every page is rebuilt once:

  inscription.asp         -> inscription.html          registration form -> "archived" notice, 
  inscription_liste.asp   -> inscription_liste.html    list of attendees: HANDLE and GROUP only
  votes.asp               -> votes.html                vote form -> "archived" notice
  votes_resultats.asp     -> votes_resultats.html      compo entries and their scores
  (added)                 -> index.html, compos.html   entry page, compo lists

Every public page is a shell with an iframe of 1021x650 (the size of back_p.jpg) that loads the
content page `f/<name>`; the links of the framed pages stay inside the frame (they point to their siblings in `f/`).

Personal data is never read into the output: of each registration file only the first two
lines (handle, group) are used. Names, birth dates, addresses, e-mails, prices, sex and the
registration codes (which were the voting passwords) are ignored, and the raw files
(`inscriptions/`, `#save/`, `inscriptions.zip`) are never copied.

Reads ONLY from the raw tree (never writes to it). Python 3.9+, standard library only.
Files are written as iso-8859-1, like the 1998 pages (characters outside it become
numeric references).
"""
import argparse
import re
import os
import shutil
import sys
from pathlib import Path

ENC = "iso-8859-1"

# ---- removal-request footer: added to every page that lists or describes people
REMOVAL_MARK = 'id="removal-note"'
REMOVAL_NOTE = (
    '<div id="removal-note" style="clear:both;margin:28px auto 8px;padding:6px 8px 0;width:60%;'
    'border-top:1px solid #808080;text-align:center;font:10px/14px Verdana,Arial,Helvetica,sans-serif;'
    'color:#808080;background:transparent">To be removed from this page, '
    '<a href="mailto:chandra_oj@pm.me" style="color:#808080;text-decoration:underline">contact me</a>.</div>'
)
_BODY_END = re.compile(r"(?is)</body\s*>(?!.*</body\s*>)")


def add_removal_note(text):
    if REMOVAL_MARK in text:
        return text
    m = _BODY_END.search(text)
    if m:
        return text[: m.start()] + REMOVAL_NOTE + "\n" + text[m.start():]
    return text + "\n" + REMOVAL_NOTE + "\n"

# Pages that list or describe people (attendee list).
PEOPLE_PAGES = {"inscription_liste.html"}


def is_people_page(rel):
    return rel in PEOPLE_PAGES

SRC_ENC = "cp1252"          # the 1998 flat files (Windows)
REPO = Path(__file__).resolve().parent.parent
RAW_DEFAULT = Path(os.environ.get("LTP2_RAW") or (REPO / "private" / "party-raw"))
IMAGES = ("back_f.jpg", "back_p.jpg")   # the only assets the pages use
FONT = 'face="Verdana, Arial, Helvetica, sans-serif, DejaVu Sans, Geneva"'
META = '<meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1">'


def esc(s):
    """Server.HTMLEncode."""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def read_lines(path):
    """Lines of a flat file, ASP ReadLine style (CRLF), nothing trimmed but the line end."""
    text = Path(path).read_bytes().decode(SRC_ENC)
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def page(title, body, body_attrs='text="#C0C0C0" bgcolor="#000000" link="#C0C0C0" alink="#C0C0C0" vlink="#C0C0C0"'):
    return ('<HTML>\n<HEAD>\n%s\n<TITLE>%s</TITLE>\n</HEAD>\n<BODY %s>\n<FONT size="2" %s><B>\n%s\n'
            '</B></FONT>\n</BODY>\n</HTML>\n' % (META, esc(title), body_attrs, FONT, body))


def nav(current):
    items = [("index.html", "HOME"), ("inscription_liste.html", "ATTENDEES"), ("compos.html", "COMPOS"),
             ("votes_resultats.html", "VOTE RESULTS")]
    return "<P>" + " | ".join(label if href == current else '<A HREF="%s">%s</A>' % (href, label)
                              for href, label in items) + "</P>"


def notice(what):
    return ('<P><FONT size="1" color="#808080">[ archived: %s is no longer available &#8211; this site is a '
            'read-only snapshot of 1998 ]</FONT></P>' % what)


# --------------------------------------------------------------------- data
def load_attendees(raw):
    """(handle, group) of every registration file: lines 1 and 2 only, nothing else is read."""
    out = []
    for p in sorted((raw / "inscriptions").glob("*.txt")):
        lines = read_lines(p)
        if len(lines) >= 2:
            out.append((lines[0].strip(), lines[1].strip()))
    return sorted(out, key=lambda t: t[0])      # the ASP sorted by handle (stable for ties)


def load_compos(raw):
    """[(slug, title, [entries], [scores])] for the compos that kept at least one entry."""
    out, empty = [], 0
    for p in sorted((raw / "compos").glob("*.txt")):
        lines = read_lines(p)
        title = lines[0].strip() if lines else ""
        entries = []
        for line in lines[1:]:
            if line.strip() == "":
                break            # votes.asp stops at the first empty line
            entries.append(line.strip())
        if not title and not entries:
            empty += 1
            continue
        vp = raw / "votes" / p.name
        scores = [l.strip() for l in read_lines(vp)] if vp.is_file() else []
        scores = [s for s in scores if s != ""]
        out.append((p.stem, title, entries, scores))
    return out, empty


# -------------------------------------------------------------------- pages
def build_index(n_att, compos):
    body = ('<H2>LTP 2 &#8211; Lucky &amp; Tigrou Party, 1998</H2>\n'
            '<P>The event pages of the second Lucky &amp; Tigrou Party, a French demoparty organised by '
            'Orange Juice: registration, list of attendees, compos and votes.</P>\n'
            '<P>This is an archive. The registration and vote forms were dynamic (classic ASP); they are '
            'closed and kept here as they looked, read-only.</P>\n'
            '<UL>\n'
            '<LI><A HREF="inscription.html">Registration</A> (closed)</LI>\n'
            '<LI><A HREF="inscription_liste.html">List of attendees</A> &#8211; %d registrations, handles and groups only</LI>\n'
            '<LI><A HREF="compos.html">Compos</A> &#8211; the entries that survived (%d of %d compos)</LI>\n'
            '<LI><A HREF="votes.html">Voting</A> (closed)</LI>\n'
            '<LI><A HREF="votes_resultats.html">Vote results</A></LI>\n'
            '</UL>\n'
            '<P><FONT size="1" color="#808080">Page added in 2026; the other pages follow the 1998 originals.</FONT></P>'
            % (n_att, sum(1 for c in compos if c[2]), len(compos)))
    return page("LTP 2 - Lucky & Tigrou Party 1998", body)


def build_inscription():
    body = ('<BR><BR><BR><BR><BR><BR><BR>\n<TABLE border="0" cellspacing="0" cellpadding="12" bgcolor="#000000">\n<TR><TD>\n'
            '<FONT size="3" color="#FFFFFF">LTP 2 &#8211; REGISTRATION</FONT><BR><BR>\n'
            'Registrations for the party were taken here in 1998 (handle, group, machine, entrance fee). '
            'The form is closed.<BR>\n%s\n'
            '<A HREF="inscription_liste.html">LIST OF ATTENDEES</A> | <A HREF="index.html">HOME</A>\n'
            '</TD></TR>\n</TABLE>' % notice("the registration form"))
    return page("LTP 2 - INSCRIPTIONS", body,
                'background="../back_p.jpg" text="#FFFFFF" bgcolor="#000000" link="#FFFFFF" vlink="#C0C0C0" '
                'style="background-repeat:no-repeat"')


FRAME_W, FRAME_H = 1021, 650      # size of back_p.jpg: every page lives in a frame of that size


def shell(inner_html, name):
    """Outer page (the public URL): the content page `f/<name>` in a frame the size of the background image."""
    title = re.search(r"<TITLE>(.*?)</TITLE>", inner_html, re.S).group(1)
    body = ('<CENTER>\n<IFRAME src="f/%s" width="%d" height="%d" frameborder="0" scrolling="auto" '
            'title="%s"></IFRAME>\n</CENTER>' % (name, FRAME_W, FRAME_H, title))
    return ('<HTML>\n<HEAD>\n%s\n<TITLE>%s</TITLE>\n</HEAD>\n<BODY text="#FFFFFF" bgcolor="#000000" '
            'topmargin="0" leftmargin="0" marginheight="0" marginwidth="0">\n%s\n</BODY>\n</HTML>\n' % (META, title, body))


def build_list(att):
    rows = "".join('  <TR>\n    <TD NOWRAP>%s</TD>\n    <TD NOWRAP>%s</TD>\n  </TR>\n' % (esc(h), esc(g)) for h, g in att)
    body = ('%s\n<TABLE width="500">\n  <TR>\n    <TD width="50%%" NOWRAP><FONT color="#0000FF">PSEUDO</FONT></TD>\n'
            '    <TD width="50%%" NOWRAP><FONT color="#0000FF">GROUPE</FONT></TD>\n  </TR>\n%s</TABLE>\n'
            '<P>NOMBRE D\'INSCRITS : %d<BR></P>\n'
            '<P><FONT size="1" color="#808080">Only the handle and the group of each registration are published; '
            'every other field of the 1998 registrations (names, addresses, e-mails, ...) was removed.</FONT></P>'
            % (nav("inscription_liste.html"), rows, len(att)))
    return page("LTP 2 - LISTE DES INSCRITS", body, 'text="#000000" bgcolor="#FFFFFF" link="#0000FF" vlink="#000080"')


def build_votes():
    body = ('<H3>LTP 2 &#8211; VOTES</H3>\n<P>Attenders voted here during the party with the code they got at registration: '
            'three points for the first choice, two for the second, one for the third.</P>\n%s\n%s'
            % (notice("voting"), nav("votes.html")))
    return page("LTP 2 - VOTES", body)


def build_compos(compos, empty):
    parts = []
    for _slug, title, entries, _scores in compos:
        if not entries:
            parts.append("<P>%s<BR>\n<FONT color=\"#808080\">(no entry kept)</FONT></P>\n" % esc(title.upper()))
            continue
        items = "".join("<LI>%s</LI>\n" % esc(e) for e in entries)
        parts.append("<P>%s (%d prods)<BR>\n<OL>\n%s</OL></P>\n" % (esc(title.upper()), len(entries), items))
    extra = ('<P><FONT size="1" color="#808080">%d other compos of the vote form had no entry left in the flat files.</FONT></P>' % empty
             if empty else "")
    return page("LTP 2 - COMPOS", nav("compos.html") + "\n" + "".join(parts) + extra)


def build_results(compos):
    parts = []
    for _slug, title, entries, scores in compos:
        if not entries:
            continue        # results.asp: IF COMPTEUR > 0
        rows = "".join("  <TR>\n    <TD>%s</TD>\n    <TD>%s</TD>\n  </TR>\n"
                       % (esc(e), esc(scores[i]) if i < len(scores) else "&nbsp;") for i, e in enumerate(entries))
        parts.append("%s\n<TABLE>\n%s</TABLE>\n" % (esc(title.upper()), rows))
    note = ('<P><FONT size="1" color="#808080">The vote files that survived are almost empty: a few test votes '
            'made while the voting page was being written. They are shown as found, they are not the party\'s '
            'results.</FONT></P>')
    return page("LTP 2 - RESULTATS DES VOTES", nav("votes_resultats.html") + "\n" + "".join(parts) + note)


# --------------------------------------------------------------------- main
def write(out, name, text):
    (out / name).write_bytes(text.encode(ENC, errors="xmlcharrefreplace"))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", default=str(RAW_DEFAULT), help="raw original tree (default: $LTP2_RAW or private/party-raw)")
    ap.add_argument("--out", default=str(REPO / "site"), help="published tree (default: <repo>/site)")
    ap.add_argument("--meta-dir", default=str(REPO / "build-meta"))
    a = ap.parse_args(argv)
    raw, out = Path(a.raw).resolve(), Path(a.out).resolve()
    if not raw.is_dir():
        ap.error("raw folder not found: %s" % raw)
    if out == raw or raw in out.parents or out in raw.parents:
        ap.error("--out must be a separate folder, outside the source tree")
    if out == REPO or out in REPO.parents or (out / ".git").exists() or out in (Path.home(), Path("/")):
        ap.error("refusing to empty %s (not a dedicated output folder)" % out)
    for _ in range(3):
        shutil.rmtree(out, ignore_errors=True)
        if not out.exists():
            break
    out.mkdir(parents=True)

    att = load_attendees(raw)
    compos, empty = load_compos(raw)
    (out / "f").mkdir()
    pages = {
        "index.html": build_index(len(att), compos),
        "inscription.html": build_inscription(),
        "inscription_liste.html": build_list(att),
        "votes.html": build_votes(),
        "compos.html": build_compos(compos, empty),
        "votes_resultats.html": build_results(compos),
    }
    for name, html in pages.items():
        if is_people_page(name):
            html = add_removal_note(html)
        write(out, "f/" + name, html)
        write(out, name, shell(html, name))
    for img in IMAGES:
        shutil.copy2(raw / img, out / img)

    meta = Path(a.meta_dir)
    meta.mkdir(parents=True, exist_ok=True)
    (meta / "redirects.tsv").write_text("\n".join("/%s.asp\t/%s.html" % (n, n) for n in
                                                  ("inscription", "inscription_liste", "votes", "votes_resultats")) + "\n")
    print("%d attendees (handle + group only); %d compos, %d with entries; 7 pages, %d images"
          % (len(att), len(compos), sum(1 for c in compos if c[2]), len(IMAGES)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
