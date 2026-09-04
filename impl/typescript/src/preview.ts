/**
 * `usedesign preview` — a rough, honest visualiser of form contracts.
 *
 * Generates ONE self-contained HTML file: no server, no dependencies, openable from disk. Three
 * rails — the contract tree, the contract's content, and a grey-box wireframe of the selected
 * form in a selected entity state. When a form inventory is present, every wireframe element
 * carries a verdict badge: rendered, missing (the contract is ahead of the code), or rendered
 * beyond the contract.
 *
 * Deliberately crude: grey boxes and real labels. A pretty preview would start competing with
 * the product's own design system and lose; the wireframe's job is to show WHAT the owner
 * decided, state by state, and where reality disagrees.
 */
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { Config, frontMatter, expandGlob } from "./core.js";

interface PreviewData {
  contracts: any[];
  inventory: Record<string, Record<string, { fields: string[]; controls: string[] }>> | null;
  producedBy: string;
}

function bodyOf(path: string): string {
  const text = readFileSync(path, "utf8").replace(/^﻿/, "").replace(/\r\n/g, "\n");
  const end = text.indexOf("\n---", 3);
  return end === -1 ? "" : text.slice(end + 4).trim();
}

export function collectPreviewData(config: Config, base: string): PreviewData {
  const contracts: any[] = [];
  for (const pattern of ((config as any).forms as string[] | undefined) ?? []) {
    for (const file of expandGlob(base, pattern)) {
      const fm = frontMatter(file);
      if (fm && fm["usedesign_form"] === 1) contracts.push({ ...fm, __body: bodyOf(file), __file: file.split(/[\\/]/).pop() });
    }
  }

  let inventory: PreviewData["inventory"] = null;
  let producedBy = "";
  const location = (config as any).form_inventory as string | undefined;
  if (location && existsSync(join(base, location))) {
    const data = JSON.parse(readFileSync(join(base, location), "utf8"));
    producedBy = data.produced_by ?? "";
    inventory = {};
    for (const form of data.forms ?? []) {
      const states: Record<string, { fields: string[]; controls: string[] }> = {};
      for (const s of form.states ?? []) states[s.state] = { fields: s.fields ?? [], controls: s.controls ?? [] };
      inventory[form.screen] = states;
    }
  }
  return { contracts, inventory, producedBy };
}

export function renderPreviewHtml(data: PreviewData): string {
  const payload = JSON.stringify(data).replace(/</g, "\\u003c");
  return `<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>usedesign — контракты форм</title>
<style>
  :root{--bg:#1114;--line:#d8d8d2;--ink:#22251f;--dim:#7a7d74;--ok:#2c7a3f;--todo:#b3372b;--extra:#8a6d1a;--card:#fbfbf8;}
  *{box-sizing:border-box}
  body{margin:0;font:14px/1.45 ui-sans-serif,system-ui,'Segoe UI',sans-serif;color:var(--ink);background:#efefe9;height:100vh;display:flex;flex-direction:column}
  header{padding:10px 16px;border-bottom:1px solid var(--line);background:var(--card);display:flex;gap:12px;align-items:baseline}
  header h1{font-size:15px;margin:0}
  header .sub{color:var(--dim);font-size:12px}
  /* лента рейлов: горизонтальная, без переноса, каждый рейл — своя ширина и свой скролл */
  .strip{flex:1;display:flex;overflow-x:auto;overflow-y:hidden;align-items:stretch;gap:0;justify-content:flex-start}
  .rail{flex:0 0 auto;display:flex;flex-direction:column;min-width:0;background:var(--card);border-right:1px solid var(--line);position:relative}
  .rail>.body{flex:1;overflow-y:auto;padding:12px 14px}
  .rail h2{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--dim);margin:0;padding:10px 14px 6px}
  .grip{position:absolute;top:0;right:-3px;width:6px;height:100%;cursor:col-resize;z-index:5}
  .grip:hover{background:#0002}
  /* рейл 1: дерево */
  .tree a{display:block;padding:5px 8px;border-radius:6px;color:inherit;text-decoration:none}
  .tree a:hover{background:#0000000d}
  .tree a.sel{background:#22251f;color:#fff}
  .tree .page{color:var(--dim);font-size:11px;margin:10px 0 2px;text-transform:uppercase;letter-spacing:.06em}
  .tree .opens{margin-left:16px;border-left:1px dotted var(--line);padding-left:8px}
  /* рейл 2: содержание */
  .kv{margin:0 0 12px}
  .kv dt{font-size:11px;color:var(--dim);text-transform:uppercase;letter-spacing:.06em;margin-top:10px}
  .kv dd{margin:2px 0 0}
  .item{padding:7px 9px;border:1px solid var(--line);border-radius:8px;margin:6px 0;background:#fff}
  .item .name{font-family:ui-monospace,monospace;font-size:12px}
  .item .shows{color:var(--ink)}
  .item .meta{color:var(--dim);font-size:12px}
  .prose{white-space:pre-wrap;color:var(--dim);font-size:12.5px;border-top:1px dashed var(--line);padding-top:10px;margin-top:14px}
  /* рейл 3: каркас */
  .states{display:flex;gap:6px;flex-wrap:wrap;padding:0 14px 8px}
  .states button{border:1px solid var(--line);background:#fff;border-radius:999px;padding:3px 10px;cursor:pointer;font:inherit;font-size:12px}
  .states button.sel{background:#22251f;color:#fff;border-color:#22251f}
  .wire{border:1px solid var(--line);border-radius:12px;background:#fff;padding:10px;display:flex;flex-direction:column;gap:8px}
  .el{border:1px dashed #b9b9b0;border-radius:8px;padding:8px 10px;background:#f6f6f1}
  .el .name{font-family:ui-monospace,monospace;font-size:11px;color:var(--dim)}
  .el .shows{font-size:13px}
  .btnrow{display:flex;gap:8px;flex-wrap:wrap;margin-top:4px}
  /* группы по назначению: рамка + подпись роли; вид грубый намеренно */
  .grp{border:1px solid var(--line);border-radius:10px;padding:8px;display:flex;flex-direction:column;gap:6px;background:#fff}
  .grp .grphead{font-size:10.5px;color:var(--dim);text-transform:uppercase;letter-spacing:.06em;display:flex;justify-content:space-between;gap:8px}
  .grp-header{background:#f2f2ea}
  .grp-footer{background:#f2f2ea;border-top:3px solid var(--line)}
  /* таблица/список — как таблица: ряды впритык, линия между рядами, чёт/нечет полосой */
  .grp-table,.grp-list{gap:0;padding:0;overflow:hidden}
  .grp-table .grphead,.grp-list .grphead{padding:8px 10px;background:#eae8dc;border-bottom:1px solid var(--line)}
  .grp-table .el,.grp-list .el{border:0;border-top:1px solid #e4e4dc;border-radius:0;background:#fff;margin:0;padding:7px 10px}
  .grp-table .el:nth-child(odd),.grp-list .el:nth-child(odd){background:#f7f7f1}
  .grp-table .ctl,.grp-list .ctl{margin:6px 10px;align-self:flex-start}
  .grp-toolbar{flex-direction:row;flex-wrap:wrap;align-items:center}
  .grp-menu{border-style:dashed;align-self:flex-end;max-width:70%}
  .ungrouped{border-top:1px dashed var(--line);margin-top:8px;padding-top:8px}
  /* кнопка — как кнопка: выпуклость, тень, нажатие */
  .ctl{border:1px solid #55584f;border-radius:8px;padding:6px 14px;background:linear-gradient(#ffffff,#e8e8e0);box-shadow:0 1px 2px #00000038,inset 0 1px 0 #fff;font-size:13px;cursor:pointer;user-select:none}
  .ctl:active{transform:translateY(1px);box-shadow:0 0 1px #00000038}
  .ctl.rule{border-style:dashed;color:var(--dim)}
  .ctl.removedghost{border-style:dotted;color:var(--todo);text-decoration:line-through}
  .el.family{border-style:double;border-width:3px}
  .ctl.family{border-style:double}
  .badge{display:inline-block;font-size:10.5px;border-radius:999px;padding:1px 7px;margin-left:6px;vertical-align:1px}
  .b-ok{background:#e3f2e6;color:var(--ok)}
  .b-todo{background:#fbe4e0;color:var(--todo)}
  .b-extra{background:#f7eecb;color:var(--extra)}
  .legend{color:var(--dim);font-size:11.5px;padding:8px 14px;border-top:1px solid var(--line)}
  .extras{margin-top:12px}
  .extras .el{border-style:dotted;background:#fdf9ea}
  @media (max-width: 900px){ .strip{flex-direction:column;overflow:visible} .rail{width:auto !important;flex:0 0 auto;border-right:0;border-bottom:1px solid var(--line)} .grip{display:none} }
</style>
</head>
<body data-page="usedesign-preview">
<header data-panel="preview-header">
  <h1>usedesign · контракты форм</h1>
  <span class="sub" id="src"></span>
</header>
<div class="strip" id="strip" data-panel="rail-strip">
  <section class="rail" id="rail-tree" data-panel="contract-tree" style="width:260px">
    <h2>Контракты</h2>
    <div class="body tree" id="tree" data-list="contracts"></div>
    <div class="grip" data-control="resize-tree"></div>
  </section>
  <section class="rail" id="rail-doc" data-panel="contract-doc" style="width:420px">
    <h2>Содержание</h2>
    <div class="body" id="doc" data-group="contract-content"></div>
    <div class="grip" data-control="resize-doc"></div>
  </section>
  <section class="rail" id="rail-wire" data-panel="contract-wireframe" style="width:460px">
    <h2>Каркас-превью</h2>
    <div class="states" id="states" data-group="state-toggle"></div>
    <div class="body" id="wire" data-group="wireframe"></div>
    <div class="legend" data-group="legend">
      <span class="badge b-ok">есть</span> отрендерено ·
      <span class="badge b-todo">нет в коде</span> контракт впереди кода ·
      <span class="badge b-extra">вне контракта</span> отрендерено, но не решено
    </div>
    <div class="grip" data-control="resize-wire"></div>
  </section>
</div>
<script id="data" type="application/json">${payload}</script>
<script>
const DATA = JSON.parse(document.getElementById('data').textContent);
const $ = (id) => document.getElementById(id);
const params = () => new URLSearchParams(location.search);

// ── рейлы: ширины с ограничениями, перетаскивание, сохранение ────────────────────────────────
const RAILS = [
  { el: 'rail-tree', grip: 0, def: 260, min: 180, max: 420 },
  { el: 'rail-doc',  grip: 1, def: 420, min: 280, max: 680 },
  { el: 'rail-wire', grip: 2, def: 460, min: 320, max: 760 },
];
for (const r of RAILS) {
  const saved = Number(localStorage.getItem('ud.rail.' + r.el));
  const w = Number.isFinite(saved) && saved >= r.min && saved <= r.max ? saved : r.def;
  $(r.el).style.width = w + 'px';
  const grip = $(r.el).querySelector('.grip');
  grip.addEventListener('pointerdown', (e) => {
    e.preventDefault();
    const startX = e.clientX, startW = $(r.el).getBoundingClientRect().width;
    const move = (ev) => {
      const w2 = Math.min(r.max, Math.max(r.min, startW + ev.clientX - startX));
      $(r.el).style.width = w2 + 'px';
    };
    const up = () => {
      localStorage.setItem('ud.rail.' + r.el, String($(r.el).getBoundingClientRect().width | 0));
      window.removeEventListener('pointermove', move); window.removeEventListener('pointerup', up);
    };
    window.addEventListener('pointermove', move); window.addEventListener('pointerup', up);
  });
}
// колесо над «тихим» местом листает ленту; клик по подрезанному рейлу довозит его
$('strip').addEventListener('wheel', (e) => {
  let node = e.target;
  while (node && node !== document.body) {
    if (node.scrollHeight > node.clientHeight + 1 && getComputedStyle(node).overflowY !== 'hidden') return;
    node = node.parentElement;
  }
  if (Math.abs(e.deltaY) > Math.abs(e.deltaX)) { $('strip').scrollLeft += e.deltaY; e.preventDefault(); }
}, { passive: false });
for (const r of RAILS) $(r.el).addEventListener('click', (e) => {
  if (e.target.closest('.grip')) return;
  const el = $(r.el), s = $('strip');
  const left = el.offsetLeft - s.scrollLeft, right = left + el.offsetWidth;
  if (left < 0 || right > s.clientWidth) el.scrollIntoView({ behavior: 'smooth', inline: 'nearest', block: 'nearest' });
});

// ── выбор: источник истины — URL ─────────────────────────────────────────────────────────────
function select(id, state, push = true) {
  const q = params();
  q.set('form', id);
  if (state) q.set('state', state); else q.delete('state');
  if (push) history.pushState(null, '', '?' + q.toString());
  renderAll();
}
window.addEventListener('popstate', renderAll);

function current() {
  const q = params();
  const id = q.get('form') || (DATA.contracts[0] && DATA.contracts[0].id);
  const c = DATA.contracts.find((x) => x.id === id) || DATA.contracts[0];
  return { c, state: q.get('state') };
}

function statesOf(c) {
  const set = new Set();
  const inv = DATA.inventory && DATA.inventory[c.screen];
  if (inv) for (const s of Object.keys(inv)) set.add(s);
  for (const p of c.presents || []) for (const s of p.when || []) set.add(s);
  for (const k of c.controls || []) for (const s of k.shown_when || []) set.add(s);
  return set.size ? [...set] : ['—'];
}

function renderTree() {
  const bag = {};
  for (const c of DATA.contracts) (bag[c.page || '(без страницы)'] ||= []).push(c);
  const opened = new Set();
  for (const c of DATA.contracts) for (const k of c.controls || []) if (k.opens) opened.add(k.opens);
  const { c: sel } = current();
  let html = '';
  for (const [page, list] of Object.entries(bag)) {
    html += '<div class="page" data-group="page">' + page + '</div>';
    for (const c of list.filter((x) => !opened.has(x.id))) html += leaf(c, sel, list, 0);
  }
  $('tree').innerHTML = html;
  function leaf(c, sel, list, depth) {
    let h = '<a href="?form=' + encodeURIComponent(c.id) + '" data-item="contract" data-id="' + c.id +
      '" class="' + (sel && sel.id === c.id ? 'sel' : '') + '">' + c.screen + '<br><span style="font-size:11px;color:' +
      (sel && sel.id === c.id ? '#cfcfc6' : 'var(--dim)') + '">' + c.id + '</span></a>';
    const children = [];
    for (const k of c.controls || []) if (k.opens) { const t = DATA.contracts.find((x) => x.id === k.opens); if (t) children.push(t); }
    if (children.length) h += '<div class="opens">' + children.map((t) => leaf(t, sel, list, depth + 1)).join('') + '</div>';
    return h;
  }
}
$('tree').addEventListener('click', (e) => {
  const a = e.target.closest('a[data-id]');
  if (a) { e.preventDefault(); select(a.getAttribute('data-id'), null); }
});

function renderDoc() {
  const { c } = current();
  if (!c) { $('doc').innerHTML = '<p>Контрактов не найдено.</p>'; return; }
  let h = '<dl class="kv" data-group="identity">';
  for (const [k, v] of [['id', c.id], ['screen', c.screen], ['page', c.page], ['entity', c.entity],
                        ['maturity', c.maturity === 'designed' ? 'designed — написан раньше экрана' : c.maturity]])
    if (v) h += '<dt>' + k + '</dt><dd>' + v + '</dd>';
  h += '</dl>';
  if (c.states && typeof c.states === 'object') {
    h += '<dl class="kv"><dt>states — состояния экрана → состояния данных</dt></dl>';
    for (const [s, spec] of Object.entries(c.states))
      h += '<div class="item" data-item="state-map"><div class="name">' + s + ' <span class="meta">→ ' + ((spec && spec.data) || '?') + '</span></div>' +
        (spec && spec.note ? '<div class="meta">' + spec.note + '</div>' : '') + '</div>';
  }
  const familyMeta = (p) => p === undefined ? '' : ' <span class="meta">· семейство, не меньше ' + (p === null ? 1 : p) + '</span>';
  h += '<dl class="kv"><dt>presents — что человек обязан видеть</dt></dl>';
  for (const p of c.presents || [])
    h += '<div class="item" data-item="presents"><div class="name">' + (p.field || p.field_pattern) +
      (p.field_pattern ? familyMeta(p.at_least === undefined ? null : p.at_least) : '') +
      (p.when ? ' <span class="meta">· ' + p.when.join(', ') + '</span>' : '') +
      '</div><div class="shows">' + p.shows + '</div>' + (p.note ? '<div class="meta">' + p.note + '</div>' : '') + '</div>';
  if ((c.controls || []).length) {
    h += '<dl class="kv"><dt>controls</dt></dl>';
    for (const k of c.controls || [])
      h += '<div class="item" data-item="control"><div class="name">' + (k.control || k.control_pattern) +
        (k.control_pattern ? familyMeta(k.at_least === undefined ? null : k.at_least) : '') +
        (k.shown_when ? ' <span class="meta">· ' + k.shown_when.join(', ') + '</span>' : '') + '</div>' +
        (k.calls ? '<div class="meta">calls: ' + k.calls + '</div>' : '') +
        (k.opens ? '<div class="meta">opens: ' + k.opens + '</div>' : '') +
        (k.shown_when_rule ? '<div class="meta">когда: ' + k.shown_when_rule + '</div>' : '') +
        (k.behaviour ? '<div class="meta">' + k.behaviour + '</div>' : '') + '</div>';
  }
  if ((c.groups || []).length) {
    h += '<dl class="kv"><dt>groups — как владелец группирует экран</dt></dl>';
    for (const g of c.groups || [])
      h += '<div class="item" data-item="group"><div class="name">' + g.group + ' <span class="meta">· ' + g.role + '</span></div>' +
        '<div class="meta">' + (g.contains || []).join(' · ') + '</div>' +
        (g.note ? '<div class="meta">' + g.note + '</div>' : '') + '</div>';
  }
  if ((c.removed || []).length) {
    h += '<dl class="kv"><dt>removed — решено, что этого быть не должно</dt></dl>';
    for (const r of c.removed || []) h += '<div class="item" data-item="removed"><div class="name">' + r.control + '</div><div class="meta">' + (r.was || '') + '</div></div>';
  }
  if (c.__body) h += '<div class="prose" data-group="prose">' + c.__body.replace(/</g, '&lt;') + '</div>';
  $('doc').innerHTML = h;
}

function renderWire() {
  const { c, state: fromUrl } = current();
  if (!c) { $('wire').innerHTML = ''; $('states').innerHTML = ''; return; }
  const states = statesOf(c);
  const state = states.includes(fromUrl) ? fromUrl : states[0];
  $('states').innerHTML = states.map((s) =>
    '<button data-control="state" data-state="' + s + '" class="' + (s === state ? 'sel' : '') + '">' + s + '</button>').join('');
  const inv = DATA.inventory && DATA.inventory[c.screen];
  const now = inv && inv[state];
  const badge = (kind, label) => '<span class="badge b-' + kind + '">' + label + '</span>';
  // Каркас рисуется ПО ГРУППАМ контракта: порядок групп = порядок на панели, роль группы —
  // подпись и грубый вид (шапка/подвал/таблица/кнопки/меню). Всё, что владелец не сгруппировал,
  // честно падает в «вне групп» — не спрятано и не разложено за него.
  // Семейство (field_pattern / control_pattern): «*» — любая последовательность символов.
  // Без регулярных выражений нарочно: шаблон один и простой, а страница — строка в шаблоне TS.
  const globMatch = (pattern, name) => {
    const parts = pattern.split('*');
    if (parts.length === 1) return pattern === name;
    if (!name.startsWith(parts[0])) return false;
    let pos = parts[0].length;
    for (let i = 1; i < parts.length - 1; i++) {
      const at = name.indexOf(parts[i], pos);
      if (at < 0) return false;
      pos = at + parts[i].length;
    }
    const last = parts[parts.length - 1];
    return name.length - pos >= last.length && name.endsWith(last);
  };
  const keyOfField = (p) => p.field || p.field_pattern;
  const keyOfControl = (k) => k.control || k.control_pattern;
  const fieldByName = new Map((c.presents || []).map((p) => [keyOfField(p), p]));
  const controlByName = new Map((c.controls || []).map((k) => [keyOfControl(k), k]));
  const grouped = new Set();
  for (const g of c.groups || []) {
    for (const m of g.contains || []) grouped.add(m);
    // Контейнер, который САМ показывает содержимое: якорь группы совпал с элементом presents —
    // элемент рисуется первым внутри своей группы, а не вторым экземпляром «вне групп».
    if (fieldByName.has(g.group)) grouped.add(g.group);
  }
  // Якорь группы учтён самой строкой группы — как и у сверщика; иначе контейнер, который
  // владелец назвал, рисовался бы «вне контракта».
  const claimedF = new Set([...(c.presents || []).filter((p) => p.field).map((p) => p.field), ...(c.groups || []).map((g) => g.group)]);
  const claimedC = new Set((c.controls || []).filter((k) => k.control).map((k) => k.control));
  const familiesF = (c.presents || []).filter((p) => p.field_pattern).map((p) => p.field_pattern);
  const familiesC = (c.controls || []).filter((k) => k.control_pattern).map((k) => k.control_pattern);

  // Вердикт семейства — счётом: сколько якорей подошло под шаблон против порога at_least.
  const familyVerdict = (pattern, floor, names) => {
    const n = names.filter((x) => globMatch(pattern, x)).length;
    return n >= floor ? badge('ok', 'есть ×' + n) : badge('todo', 'нет в коде' + (n ? ' (×' + n + ' из ' + floor + ')' : ''));
  };
  const fieldBox = (p) => {
    if (p.when && !p.when.includes(state)) return '';
    const key = keyOfField(p);
    const v = !now ? '' : p.field_pattern
      ? familyVerdict(p.field_pattern, p.at_least === undefined ? 1 : p.at_least, now.fields)
      : now.fields.includes(p.field) ? badge('ok', 'есть') : badge('todo', 'нет в коде');
    return '<div class="el' + (p.field_pattern ? ' family' : '') + '" data-item="wire-field" data-anchor="' + key + '"><div class="name">' + key + v + '</div><div class="shows">' + p.shows + '</div></div>';
  };
  const controlChip = (k) => {
    if (k.shown_when && !k.shown_when.includes(state)) return '';
    const key = keyOfControl(k);
    const v = !now ? '' : k.control_pattern
      ? familyVerdict(k.control_pattern, k.at_least === undefined ? 1 : k.at_least, now.controls)
      : now.controls.includes(k.control) ? badge('ok', 'есть') : badge('todo', 'нет в коде');
    return '<span class="ctl' + (k.shown_when ? '' : ' rule') + (k.control_pattern ? ' family' : '') + '" data-item="wire-control" data-anchor="' + key + '">' + key + v + '</span>';
  };
  const member = (name) =>
    fieldByName.has(name) ? fieldBox(fieldByName.get(name)) :
    controlByName.has(name) ? controlChip(controlByName.get(name)) : '';

  const ROLE_LABEL = { header: 'шапка', footer: 'подвал', section: 'секция', table: 'таблица', list: 'список', toolbar: 'кнопки', menu: 'меню ⋯' };
  let h = '<div class="wire" data-group="wire-canvas">';
  for (const g of c.groups || []) {
    const names = fieldByName.has(g.group) ? [g.group, ...(g.contains || [])] : (g.contains || []);
    const inner = names.map(member).join('');
    if (!inner) continue; // в этом состоянии группе нечего показать
    h += '<div class="grp grp-' + g.role + '" data-item="wire-group" data-anchor="' + g.group + '" data-role="' + g.role + '">' +
      '<div class="grphead"><span>' + g.group + '</span><span>' + (ROLE_LABEL[g.role] || g.role) + '</span></div>' + inner + '</div>';
  }

  const looseFields = (c.presents || []).filter((p) => !grouped.has(keyOfField(p))).map(fieldBox).join('');
  let looseControls = (c.controls || []).filter((k) => !grouped.has(keyOfControl(k))).map(controlChip).join('');
  for (const r of c.removed || []) {
    claimedC.add(r.control);
    if (now && now.controls.includes(r.control))
      looseControls += '<span class="ctl removedghost" data-item="wire-removed" data-anchor="' + r.control + '">' + r.control + badge('todo', 'должно исчезнуть') + '</span>';
  }
  if (looseFields || looseControls) {
    h += '<div class="' + ((c.groups || []).length ? 'ungrouped' : '') + '" data-group="wire-ungrouped">' +
      ((c.groups || []).length ? '<div class="grphead"><span>вне групп</span></div>' : '') +
      looseFields + (looseControls ? '<div class="btnrow" data-group="wire-controls">' + looseControls + '</div>' : '') + '</div>';
  }
  h += '</div>';
  if (now) {
    const extraF = now.fields.filter((f) => !claimedF.has(f) && !familiesF.some((p) => globMatch(p, f)));
    const extraC = now.controls.filter((f) => !claimedC.has(f) && !familiesC.some((p) => globMatch(p, f)));
    if (extraF.length || extraC.length) {
      h += '<div class="extras" data-group="wire-extras"><dl class="kv"><dt>отрендерено, но владелец не решал</dt></dl>';
      for (const f of extraF) h += '<div class="el"><div class="name">' + f + badge('extra', 'вне контракта') + '</div></div>';
      if (extraC.length) h += '<div class="btnrow">' + extraC.map((x) => '<span class="ctl rule">' + x + badge('extra', 'вне контракта') + '</span>').join('') + '</div>';
      h += '</div>';
    }
  }
  $('wire').innerHTML = h;
}
$('states').addEventListener('click', (e) => {
  const b = e.target.closest('button[data-state]');
  if (b) select(current().c.id, b.getAttribute('data-state'));
});

function renderAll() {
  document.getElementById('src').textContent =
    DATA.contracts.length + ' контракт(ов)' + (DATA.producedBy ? ' · перечень: ' + DATA.producedBy : ' · перечня формы нет — каркас без вердиктов');
  renderTree(); renderDoc(); renderWire();
}
renderAll();
</script>
</body>
</html>
`;
}

export function commandPreview(configPath: string, outPath: string, loadConfig: (p: string) => { config: Config; base: string }): number {
  const { config, base } = loadConfig(configPath);
  const data = collectPreviewData(config, base);
  if (data.contracts.length === 0) {
    console.error("usedesign preview: the config's `forms` patterns matched no contract");
    return 1;
  }
  writeFileSync(outPath, renderPreviewHtml(data), "utf8");
  console.log(`preview:    ${data.contracts.length} contract(s) → ${outPath}${data.inventory ? " (с вердиктами по перечню формы)" : " (перечня формы нет — без вердиктов)"}`);
  return 0;
}
