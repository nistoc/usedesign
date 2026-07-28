# docs/

A single self-contained HTML presentation of the Operation Card format:
[`index.html`](index.html).

- No CDN, no external stylesheets, no web fonts, no remote images, no network calls.
  All CSS and JS are inline; every graphic is inline SVG or CSS.
- It opens correctly by double-clicking the file from disk, offline.
- Content is drawn from [`SPEC.md`](../SPEC.md), the [schema](../schema/operation-card.schema.json)
  and the [example cards](../examples/) — every YAML excerpt in the deck is real.

## Viewing it

Locally: open `docs/index.html` in any browser.

Navigation: `→` / `Space` / `PageDown` next, `←` / `PageUp` back, `Home` / `End` first and last,
`T` toggles the theme, `L` switches the language. Touch swipe works too. The current slide is
reflected in the URL hash, so `index.html#7` links straight to a slide.

The deck is bilingual — English and Russian. The first visit follows the browser language; after
that the choice is remembered. The language is a query parameter and the slide is the hash, so
they compose: `index.html?lang=ru#7`. Code samples stay in English in both languages, because
they are quoted verbatim from the cards in this repository.

## Publishing it with GitHub Pages

1. Repository → **Settings** → **Pages**.
2. **Source:** *Deploy from a branch*.
3. **Branch:** `main`, **folder:** `/docs`. Save.

After the first build the deck is served at
`https://<user>.github.io/<repo>/` — for this repository, `https://nistoc.github.io/usedesign/`.

Nothing else in the repository is affected: Pages serves this folder only.
