/**
 * The form-inventory producer helper — the missing half of check 5's adoption story (issue #7:
 * checks 1–3 were adoptable in an hour because a tool turns an existing artefact into their
 * inventory; check 5 had nothing, so authored contracts sat verifying nothing).
 *
 * The division of labour follows the issue's own suggestion: the FRAMEWORK-SPECIFIC part —
 * rendering a component in each entity state — stays in the adopter's test, where it belongs;
 * the CONVENTION — which anchors count, how containers chain — lives here, where it belongs,
 * so that projects stop inventing divergent conventions in every copy of the same file.
 *
 * The convention, proven on two panels and a modal before it was written down:
 *   data-field       — a value the user sees            → fields
 *   data-section     — a container with an identity      → fields (containers are content too)
 *   data-panel-head  — the panel's chrome header         → the fixed name "panel-head"
 *   data-action      — an interactive control            → controls
 *   data-control     — a container-flavoured control     → a container in `within` chains
 * `within` records, per anchor, EVERY container ancestor (data-section / data-panel-head /
 * data-control) across all instances — the full chain, not the nearest parent, deliberately:
 * a flat contract may seat a member at any level, and intermediate undescribed containers must
 * not read as misplacement. Collect from document.body when menus or overlays render through a
 * portal — a component that renders outside its own container is honestly rendered all the same.
 *
 * No DOM library is imported: the structural types below match any standards-shaped DOM
 * (jsdom under vitest/jest, happy-dom, a real browser). No dependencies — this must run inside
 * somebody else's test file via `npx`-installed usedesign.
 */

interface ElementLike {
  getAttribute(name: string): string | null;
  hasAttribute(name: string): boolean;
  parentElement: ElementLike | null;
}

interface RootLike {
  querySelectorAll(selector: string): Iterable<ElementLike> & ArrayLike<ElementLike>;
  querySelector(selector: string): ElementLike | null;
}

export interface CollectedState {
  fields: Set<string>;
  controls: Set<string>;
  within: Map<string, Set<string>>;
}

/** Walk one rendered root and collect the anchors the convention defines. */
export function collectScreenState(root: RootLike): CollectedState {
  const fields = new Set<string>();
  const controls = new Set<string>();
  const within = new Map<string, Set<string>>();

  const note = (name: string, el: ElementLike) => {
    const chain = within.get(name) ?? new Set<string>();
    for (let p = el.parentElement; p; p = p.parentElement) {
      if (p.hasAttribute("data-section")) chain.add(p.getAttribute("data-section")!);
      if (p.hasAttribute("data-panel-head")) chain.add("panel-head");
      if (p.hasAttribute("data-control")) chain.add(p.getAttribute("data-control")!);
    }
    within.set(name, chain);
  };

  for (const el of Array.from(root.querySelectorAll("[data-field]"))) {
    const name = el.getAttribute("data-field")!;
    fields.add(name);
    note(name, el);
  }
  for (const el of Array.from(root.querySelectorAll("[data-section]"))) {
    const name = el.getAttribute("data-section")!;
    fields.add(name);
    note(name, el);
  }
  const head = root.querySelector("[data-panel-head]");
  if (head) {
    fields.add("panel-head");
    note("panel-head", head);
  }
  for (const el of Array.from(root.querySelectorAll("[data-action]"))) {
    const name = el.getAttribute("data-action")!;
    controls.add(name);
    note(name, el);
  }
  return { fields, controls, within };
}

/** Merge several renders of ONE state (a screen re-rendered with different data still carries one state). */
export function mergeStates(states: CollectedState[]): CollectedState {
  const merged: CollectedState = { fields: new Set(), controls: new Set(), within: new Map() };
  for (const state of states) {
    for (const f of state.fields) merged.fields.add(f);
    for (const c of state.controls) merged.controls.add(c);
    for (const [name, chain] of state.within) {
      const mine = merged.within.get(name) ?? new Set<string>();
      for (const c of chain) mine.add(c);
      merged.within.set(name, mine);
    }
  }
  return merged;
}

/** One state entry, JSON-ready, with a stable order — a regenerated inventory that did not change must be byte-identical. */
export function stateEntry(state: string, collected: CollectedState) {
  return {
    state,
    fields: [...collected.fields].sort(),
    controls: [...collected.controls].sort(),
    within: Object.fromEntries(
      [...collected.within.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([k, v]) => [k, [...v].sort()]),
    ),
  };
}

/** The whole document check 5 consumes. `producedBy` must say HOW it was made — and its limits. */
export function formInventoryDocument(
  producedBy: string,
  forms: { screen: string; states: ReturnType<typeof stateEntry>[] }[],
) {
  return { usedesign_form_inventory: 1, produced_by: producedBy, forms };
}
