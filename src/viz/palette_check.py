"""Validate chart palettes for colour-vision-deficiency (CVD) safety and contrast.

Computes, instead of eyeballing, whether the colours in a palette can be told
apart: by readers with normal vision, by readers with red-green colour blindness
(protanopia, deuteranopia), and against the chart background.

Checks for a categorical palette (series identity, e.g. energy sources):
  - Lightness band:      OKLCH L inside the band for the mode (dark: 0.48 to 0.67)
  - Chroma floor:        OKLCH C >= 0.10, otherwise a colour reads as gray
  - CVD separation:      OKLab distance x100 between neighbouring colours under
                         simulated protan/deutan vision (Machado et al. 2009).
                         >= 8 pass, 6 to 8 only with direct labels, < 6 fail
  - Normal-vision floor: OKLab distance x100 between neighbours >= 15
  - Contrast:            WCAG contrast vs the chart surface >= 3:1, otherwise
                         the chart needs visible labels or a table view

"Neighbours" are adjacent entries (stacked areas, lines, bars). Use
pairs="all" for scatter plots and maps, where any two colours can touch.

Checks for an ordinal/sequential ramp: monotone lightness, visible steps,
end step visible against the surface, single hue.

Python port of validate_palette.js from the data-viz guidance used for this
project; thresholds and the CVD model are unchanged.

Run from the repo root:
    python src/viz/palette_check.py "#3987e5,#d95926,#199e70" --mode dark
    python src/viz/palette_check.py --project     # validate the palettes in style.py
"""

import argparse
import itertools
import math
import sys

BAND = {"light": (0.43, 0.77), "dark": (0.48, 0.67)}
CHROMA_FLOOR = 0.10
CVD_TARGET, CVD_FLOOR = 8.0, 6.0
NORMAL_FLOOR = 15.0
CONTRAST_MIN = 3.0
DEFAULT_SURFACE = {"light": "#fcfcfb", "dark": "#1a1a19"}
ORDINAL_MIN_DL = 0.06
ORDINAL_END_FLOOR = 2.0

# Machado, Oliveira & Fernandes (2009), severity 1.0, applied in linear RGB
MACHADO = {
    "protan": [[0.152286, 1.052583, -0.204868],
               [0.114503, 0.786281, 0.099216],
               [-0.003882, -0.048116, 1.051998]],
    "deutan": [[0.367322, 0.860646, -0.227968],
               [0.280085, 0.672501, 0.047413],
               [-0.011820, 0.042940, 0.968881]],
    "tritan": [[1.255528, -0.076749, -0.178779],
               [-0.078411, 0.930809, 0.147602],
               [0.004733, 0.691367, 0.303900]],
}


# -- colour conversions --------------------------------------------------------

def hex_to_srgb(h):
    h = h.strip().lstrip("#")
    return [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]


def _s2lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _lin2s(c):
    c = min(1.0, max(0.0, c))
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def linear_rgb(h):
    return [_s2lin(c) for c in hex_to_srgb(h)]


def contrast(a, b):
    """WCAG 2 contrast ratio between two hex colours."""
    def lum(h):
        r, g, b_ = linear_rgb(h)
        return 0.2126 * r + 0.7152 * g + 0.0722 * b_
    hi, lo = sorted([lum(a), lum(b)], reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _oklab_from_lin(rgb):
    r, g, b = rgb
    l = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return [
        0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
        1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
        0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s,
    ]


def oklab(h):
    return _oklab_from_lin(linear_rgb(h))


def oklch(h):
    L, a, b = oklab(h)
    return L, math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360


def oklab_to_hex(lab):
    """OKLab -> hex (clipped to the sRGB gamut). Used to interpolate ramps."""
    L, a, b = lab
    l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    rgb = [
        4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s,
    ]
    return "#" + "".join(f"{round(_lin2s(c) * 255):02x}" for c in rgb)


def _simulate(h, kind):
    r, g, b = linear_rgb(h)
    return [min(1.0, max(0.0, row[0] * r + row[1] * g + row[2] * b)) for row in MACHADO[kind]]


def delta_e(h1, h2, kind=None):
    """OKLab distance x100; kind = protan/deutan/tritan simulates CVD."""
    a = _oklab_from_lin(_simulate(h1, kind) if kind else linear_rgb(h1))
    b = _oklab_from_lin(_simulate(h2, kind) if kind else linear_rgb(h2))
    return 100 * math.dist(a, b)


# -- checks --------------------------------------------------------------------

def _pairlist(n, pairs):
    if pairs == "all":
        return list(itertools.combinations(range(n), 2))
    return [(i, i + 1) for i in range(n - 1)]


def worst_cvd(palette, pairs="adjacent"):
    """Smallest protan/deutan distance on the pairlist (used to rank orders)."""
    pl = _pairlist(len(palette), pairs)
    if not pl:
        return 99.0
    return min(delta_e(palette[i], palette[j], k) for i, j in pl for k in ("protan", "deutan"))


def worst_normal(palette, pairs="adjacent"):
    pl = _pairlist(len(palette), pairs)
    if not pl:
        return 99.0
    return min(delta_e(palette[i], palette[j]) for i, j in pl)


def validate(palette, mode="dark", surface=None, pairs="adjacent", neutral=()):
    """Return (report, ok). report rows: (check, PASS/WARN/FAIL, detail).

    neutral: colours that are gray on purpose (e.g. an "Other" layer). They are
    exempt from the lightness band and chroma floor, but still have to be
    distinguishable from their neighbours and visible against the surface.
    """
    surface = surface or DEFAULT_SURFACE[mode]
    lo, hi = BAND[mode]
    report, ok = [], True
    hued = [c for c in palette if c not in neutral]
    note = f" ({len(neutral)} neutral exempt)" if neutral else ""

    offband = [(c, round(oklch(c)[0], 3)) for c in hued if not lo <= oklch(c)[0] <= hi]
    ok &= not offband
    report.append(("Lightness band", "FAIL" if offband else "PASS",
                   f"outside band: {offband}" if offband else f"all {len(hued)} inside L {lo}-{hi}{note}"))

    lowc = [(c, round(oklch(c)[1], 3)) for c in hued if oklch(c)[1] < CHROMA_FLOOR]
    ok &= not lowc
    report.append(("Chroma floor", "FAIL" if lowc else "PASS",
                   f"below floor (reads gray): {lowc}" if lowc else f"all {len(hued)} >= {CHROMA_FLOOR}{note}"))

    pl = _pairlist(len(palette), pairs)
    label = "all-pairs" if pairs == "all" else "adjacent"
    worst = None
    for kind in ("protan", "deutan"):
        for i, j in pl:
            d = delta_e(palette[i], palette[j], kind)
            if worst is None or d < worst[0]:
                worst = (d, kind, palette[i], palette[j])
    tri = min((delta_e(palette[i], palette[j], "tritan") for i, j in pl), default=99)
    wd = worst[0] if worst else 99
    state = "PASS" if wd >= CVD_TARGET else "WARN" if wd >= CVD_FLOOR else "FAIL"
    ok &= state != "FAIL"
    report.append(("CVD separation", state,
                   f"worst {label} {worst[2]}<->{worst[3]} dE {wd:.1f} ({worst[1]}), tritan {tri:.1f}"
                   if worst else "n/a"))

    nworst = min(((delta_e(palette[i], palette[j]), palette[i], palette[j]) for i, j in pl), default=None)
    nd = nworst[0] if nworst else 99
    ok &= nd >= NORMAL_FLOOR
    report.append(("Normal-vision floor", "PASS" if nd >= NORMAL_FLOOR else "FAIL",
                   f"worst {label} {nworst[1]}<->{nworst[2]} dE {nd:.1f}" if nworst else "n/a"))

    low = [(c, round(contrast(c, surface), 2)) for c in palette if contrast(c, surface) < CONTRAST_MIN]
    report.append(("Contrast vs surface", "WARN" if low else "PASS",
                   f"below {CONTRAST_MIN}:1, needs labels or table view: {low}" if low
                   else f"all {len(palette)} >= {CONTRAST_MIN}:1"))
    return report, bool(ok)


def validate_ordinal(palette, mode="dark", surface=None):
    """Checks for a one-hue ramp ordered from the surface end to the strong end."""
    surface = surface or DEFAULT_SURFACE[mode]
    report, ok = [], True
    Ls = [oklch(c)[0] for c in palette]

    mono = Ls == sorted(Ls) or Ls == sorted(Ls, reverse=True)
    ok &= mono
    report.append(("Lightness monotone", "PASS" if mono else "FAIL", f"L = {[round(x, 3) for x in Ls]}"))

    thin = [(palette[i], palette[i + 1], round(abs(Ls[i + 1] - Ls[i]), 3))
            for i in range(len(Ls) - 1) if abs(Ls[i + 1] - Ls[i]) < ORDINAL_MIN_DL]
    ok &= not thin
    report.append(("Adjacent dL", "FAIL" if thin else "PASS",
                   f"steps too close: {thin}" if thin else f"all gaps >= {ORDINAL_MIN_DL}"))

    by_l = sorted(palette, key=lambda c: oklch(c)[0])
    end = by_l[-1] if mode == "light" else by_l[0]
    cr = contrast(end, surface)
    ok &= cr >= ORDINAL_END_FLOOR
    report.append(("Surface-end contrast", "PASS" if cr >= ORDINAL_END_FLOOR else "FAIL",
                   f"{end} at {cr:.2f}:1 vs surface"))

    hues = [oklch(c)[2] for c in palette]
    spread = max(hues) - min(hues)
    spread = 360 - spread if spread > 180 else spread
    ok &= spread <= 40
    report.append(("Single hue", "PASS" if spread <= 40 else "FAIL", f"hue spread {spread:.0f} deg"))
    return report, bool(ok)


def print_report(name, report, ok):
    print(f"\n{name}")
    for check, state, detail in report:
        print(f"  [{state:<4}] {check:<22} {detail}")
    print(f"  -> {'ALL CHECKS PASS' if ok else 'FAILED'}")


def check_project():
    """Validate every palette defined in src/viz/style.py. Exit 1 on any FAIL."""
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from src.viz import style

    s = style.SURFACE
    results = [
        ("Energy sources, stack order bottom to top (adjacent)",
         *validate([style.SOURCE_COLORS[k] for k in style.SOURCE_ORDER], "dark", s,
                   neutral=[style.SOURCE_COLORS["other"]])),
        ("Countries, legend order (adjacent)",
         *validate([style.COUNTRY_COLORS[k] for k in style.COUNTRY_ORDER], "dark", s)),
        ("Countries, first 3 slots (all pairs, for scatter)",
         *validate([style.COUNTRY_COLORS[k] for k in style.COUNTRY_ORDER[:3]], "dark", s, "all")),
        ("Seasons (all pairs; WARN means direct labels required)",
         *validate([style.SEASON_COLORS[k] for k in style.SEASON_ORDER], "dark", s, "all")),
        # Every second step: the continuous colormap is fine-grained on purpose,
        # the ordinal check is about whether distinct steps can be told apart
        ("Sequential ramp, every 2nd step", *validate_ordinal(style.SEQUENTIAL[::2], "dark", s)),
    ]
    all_ok = True
    for name, report, ok in results:
        print_report(name, report, ok)
        all_ok &= ok
    return all_ok


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("palette", nargs="?", help="comma-separated hex colours")
    p.add_argument("--mode", choices=["light", "dark"], default="dark")
    p.add_argument("--surface")
    p.add_argument("--pairs", choices=["adjacent", "all"], default="adjacent")
    p.add_argument("--ordinal", action="store_true")
    p.add_argument("--project", action="store_true", help="validate the palettes in style.py")
    args = p.parse_args()

    if args.project:
        sys.exit(0 if check_project() else 1)
    if not args.palette:
        p.error("give a palette or --project")
    palette = [c.strip() for c in args.palette.split(",") if c.strip()]
    if args.ordinal:
        report, ok = validate_ordinal(palette, args.mode, args.surface)
    else:
        report, ok = validate(palette, args.mode, args.surface, args.pairs)
    print_report(f"Palette ({args.mode}, {len(palette)} colours)", report, ok)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
