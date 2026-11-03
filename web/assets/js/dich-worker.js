/* dich-worker.js — chạy bộ máy dịch (Python dich_pdf.py + PyMuPDF qua Pyodide) trong Web Worker,
   để giao diện không bị đứng khi dựng PDF. Tài liệu chỉ nằm trong bộ nhớ của trình duyệt.

   Nguồn tải bộ máy (khoảng 30 MB):
   - "cdn" (mặc định): Pyodide từ jsDelivr, PyMuPDF từ PyPI. Website chỉ phát phông chữ và mã dịch (~2-3 MB),
     nên băng thông Vercel gần như không tăng theo số người dùng. Mọi file tải từ CDN đều được kiểm mã SHA-256
     trước khi chạy, và chạy đúng các byte đã kiểm; sai mã, lỗi hoặc treo thì tự chuyển sang bản trên website.
   - "self": mọi thứ lấy từ thư mục engine/ của website. */
"use strict";

var ENGINE = new URL("../../engine/", self.location.href).href;
var PYODIDE_VER = "0.29.5";
var WHEEL = "pymupdf-1.28.2-cp313-abi3-pyemscripten_2025_0_wasm32.whl";
var WHEEL_SHA256 = "2e1b574c0fd2cb238021033fd3c0f9c4388816638df064e4bfb56d9d81736dc8";
var CDN_CORE = [
  { name: "jsDelivr", url: "https://cdn.jsdelivr.net/npm/pyodide@" + PYODIDE_VER + "/" },
  { name: "jsDelivr (Fastly)", url: "https://fastly.jsdelivr.net/npm/pyodide@" + PYODIDE_VER + "/" }
];
var CDN_WHEEL = [
  { name: "PyPI", url: "https://files.pythonhosted.org/packages/58/8c/d897dcd32a25b58186c968b15ce4324ca029e9d96460de12325314e390be/" + WHEEL }
];
// mã SHA-256 của gói npm pyodide@0.29.5 (đúng các file trong engine/pyodide/)
var CORE_SHA256 = {
  "pyodide.js": "7f832a350240263d9946a9c3c877f7bcdab6c37d6dc65f72cd3be5905dca62dd",
  "pyodide.asm.js": "356c42f69e1695397e9d8670bd3c2e678248cde76e18bdae1731e848537b47d7",
  "pyodide.asm.wasm": "54309a5a2cfd757b1f0fdbc9093c92503f7b341500110329d932487183912718",
  "python_stdlib.zip": "831fd1e535084b972f87c6a35275de3d236efd5166f5e77ce89497710635e73c",
  "pyodide-lock.json": "14d2c2dba101277999e17135e653d8f15389ad1437f53eae213bf0c3cdff723d"
};
var CORE_BYTES = 12286633;
var MIME = { js: "text/javascript", wasm: "application/wasm", json: "application/json", zip: "application/zip" };
var SELF_CORE = { name: "website", url: ENGINE + "pyodide/", self: true };
var SELF_WHEEL = { name: "website", url: ENGINE + WHEEL };
var FONT_BASE = { serif: "LiberationSerif", sans: "LiberationSans", mono: "LiberationMono", calibri: "Carlito" };
var STYLES = ["Regular", "Bold", "Italic", "BoldItalic"];
var OPTS = { source: "cdn", ver: "" };
var py = null, api = null, initPromise = null, loadedFamilies = {}, used = {};

function status(text, frac) { self.postMessage({ type: "status", text: text, frac: frac }); }

// File CDN đã kiểm mã: Pyodide xin URL nào thì trả đúng các byte đã kiểm, không tải lại từ mạng
var verified = {};
var realFetch = self.fetch.bind(self), realImport = self.importScripts.bind(self);
self.fetch = function (input, init) {
  var u = typeof input === "string" ? input : (input && input.url) || String(input);
  var v = verified[u];
  if (v) return Promise.resolve(new Response(v.bytes, { status: 200, headers: { "Content-Type": v.type } }));
  return realFetch(input, init);
};
self.importScripts = function () {
  return realImport.apply(self, Array.prototype.map.call(arguments, function (u) { return verified[u] && verified[u].blob || u; }));
};

// tải một file; không có byte đầu trong firstMs, hoặc ngừng giữa chừng 20 giây, thì bỏ để chuyển nguồn khác
async function fetchBytes(url, firstMs, onProgress, stop) {
  var ctrl = new AbortController(), timer = null;
  if (stop) { if (stop.aborted) ctrl.abort(); else stop.addEventListener("abort", function () { ctrl.abort(); }); }
  function arm(ms) { clearTimeout(timer); timer = setTimeout(function () { ctrl.abort(); }, ms); }
  arm(firstMs);
  try {
    var res = await realFetch(url, { signal: ctrl.signal });
    if (!res.ok) throw new Error("HTTP " + res.status);
    var total = Number(res.headers.get("Content-Length")) || 0;
    if (!res.body) { arm(120000); var b = new Uint8Array(await res.arrayBuffer()); if (onProgress) onProgress(b.length, b.length); return b; }
    var reader = res.body.getReader(), chunks = [], got = 0;
    for (;;) {
      arm(20000);
      var r = await reader.read();
      if (r.done) break;
      chunks.push(r.value); got += r.value.length;
      if (onProgress) onProgress(got, total);
    }
    var out = new Uint8Array(got), pos = 0;
    chunks.forEach(function (c) { out.set(c, pos); pos += c.length; });
    return out;
  } finally { clearTimeout(timer); }
}

async function sha256Hex(bytes) {
  var h = await crypto.subtle.digest("SHA-256", bytes);
  return Array.prototype.map.call(new Uint8Array(h), function (b) { return ("0" + b.toString(16)).slice(-2); }).join("");
}

// tải đủ 5 file lõi Pyodide từ một CDN, kiểm từng mã SHA-256; lệch một file là bỏ cả nguồn
async function fetchCoreVerified(c) {
  var names = Object.keys(CORE_SHA256), got = {}, stop = new AbortController();
  var label = "Đang tải bộ máy Python (" + c.name + ")";
  function prog() {
    if (stop.signal.aborted) return;
    var sum = 0; names.forEach(function (n) { sum += got[n] || 0; });
    status(label + " " + Math.round(sum / 1e6) + "/" + Math.round(CORE_BYTES / 1e6) + " MB", 0.03 + 0.32 * Math.min(1, sum / CORE_BYTES));
  }
  status(label, 0.03);
  var files = await Promise.all(names.map(function (n) {
    return fetchBytes(c.url + n, n === "pyodide.js" ? 6000 : 12000, function (g) { got[n] = g; prog(); }, stop.signal)
      .then(async function (b) {
        if (await sha256Hex(b) !== CORE_SHA256[n]) throw new Error(n + ": mã kiểm tra SHA-256 không khớp");
        return b;
      });
  })).catch(function (e) { stop.abort(); throw e; });   // một file hỏng: dừng các file còn lại của nguồn này
  var map = {};
  names.forEach(function (n, i) {
    var ext = n.split(".").pop(), type = MIME[ext] || "application/octet-stream";
    map[c.url + n] = { bytes: files[i], type: type, blob: ext === "js" ? URL.createObjectURL(new Blob([files[i]], { type: type })) : null };
  });
  return map;
}

function forget(map) {
  Object.keys(map).forEach(function (u) { if (map[u].blob) URL.revokeObjectURL(map[u].blob); delete verified[u]; });
}

async function loadCore(cands) {
  var last;
  for (var i = 0; i < cands.length; i++) {
    var c = cands[i], map = {};
    try {
      if (c.self) status("Đang tải bộ máy Python (" + c.name + ")", 0.03);
      else { map = await fetchCoreVerified(c); Object.assign(verified, map); }
      importScripts(c.url + "pyodide.js");
      status("Đang khởi động Python", 0.37);
      var p = await loadPyodide({ indexURL: c.url });
      used.core = c.name;
      forget(map);          // đã nạp xong, trả lại bộ nhớ
      return p;
    } catch (e) { forget(map); last = e; console.warn("Pyodide từ " + c.name + " lỗi:", e && e.message); }
  }
  throw new Error("Không tải được bộ máy Python: " + (last && last.message || last));
}

async function loadWheel(cands) {
  var last;
  for (var i = 0; i < cands.length; i++) {
    try {
      var label = "Đang tải thư viện PDF (" + cands[i].name + ")";
      status(label, 0.4);
      var bytes = await fetchBytes(cands[i].url, 12000, function (g, t) {
        if (t) status(label + " " + Math.round(g / 1e6) + "/" + Math.round(t / 1e6) + " MB", 0.4 + 0.42 * Math.min(1, g / t));
      });
      var h = await sha256Hex(bytes);
      if (h !== WHEEL_SHA256) throw new Error("mã kiểm tra SHA-256 không khớp");
      status("Đang khởi động thư viện PDF", 0.84);
      // cài thẳng từ đúng các byte vừa kiểm tra mã SHA-256 (không tải lại lần hai)
      var site = py.runPython("import site; site.getsitepackages()[0]");
      py.unpackArchive(bytes.buffer, "wheel", { extractDir: site });
      py.pyimport("pymupdf");
      used.wheel = cands[i].name;
      return;
    } catch (e) { last = e; console.warn("PyMuPDF từ " + cands[i].name + " lỗi:", e && e.message); }
  }
  throw new Error("Không tải được thư viện PDF: " + (last && last.message || last));
}

async function doInit() {
  var cdn = OPTS.source !== "self";
  py = await loadCore(cdn ? CDN_CORE.concat([SELF_CORE]) : [SELF_CORE]);
  await loadWheel(cdn ? CDN_WHEEL.concat([SELF_WHEEL]) : [SELF_WHEEL]);
  py.FS.mkdirTree("/app/scripts"); py.FS.mkdirTree("/app/assets/fonts"); py.FS.mkdirTree("/tmp/in");
  var q = OPTS.ver ? "?v=" + encodeURIComponent(OPTS.ver) : "";
  for (var f of ["dich_pdf.py", "web_api.py"]) {
    var res = await fetch(ENGINE + f + q);
    if (!res.ok) throw new Error("Không tải được " + f + " (HTTP " + res.status + ")");
    py.FS.writeFile("/app/scripts/" + f, await res.text());
  }
  py.runPython("import sys; sys.path.insert(0, '/app/scripts')");
  api = py.pyimport("web_api");
  var ver = py.runPython("import pymupdf, dich_pdf; f'{dich_pdf.PHIEN_BAN} · PyMuPDF {pymupdf.VersionBind}'");
  status("Bộ máy sẵn sàng", 1);
  return { ready: true, version: ver, sources: used };
}

function init() {
  if (!initPromise) initPromise = doInit().catch(function (e) { initPromise = null; throw e; });
  return initPromise;
}

async function loadFonts(families) {
  var need = [];
  families.forEach(function (fam) { if (FONT_BASE[fam] && !loadedFamilies[fam]) need.push(fam); });
  if (!loadedFamilies.sans && need.indexOf("sans") < 0) need.push("sans");
  var jobs = [];
  need.forEach(function (fam) {
    STYLES.forEach(function (st) {
      var name = FONT_BASE[fam] + "-" + st + ".ttf";
      jobs.push(fetch(ENGINE + "fonts/" + name).then(function (r) {
        if (!r.ok) throw new Error("Không tải được phông " + name);
        return r.arrayBuffer();
      }).then(function (b) { py.FS.writeFile("/app/assets/fonts/" + name, new Uint8Array(b)); }));
    });
  });
  if (jobs.length) status("Đang tải phông chữ tiếng Việt", 0.98);
  await Promise.all(jobs);
  need.forEach(function (fam) { loadedFamilies[fam] = true; });
  return Object.keys(loadedFamilies);
}

function J(s) { return JSON.parse(s); }

var handlers = {
  configure: async function (opts) { if (opts) { OPTS.source = opts.source || "cdn"; OPTS.ver = opts.ver || ""; } return OPTS; },
  init: init,
  sources: async function () { return used; },
  prepare: async function (bytes, name, lo, trang, huong) {
    await init();
    var safe = (name || "tai-lieu.pdf").replace(/[\\/:*?"<>|]+/g, "_");
    if (!/\.pdf$/i.test(safe)) safe += ".pdf";
    try { py.FS.readdir("/tmp/in").forEach(function (f) { if (f !== "." && f !== "..") py.FS.unlink("/tmp/in/" + f); }); } catch (e) { /* trống */ }
    py.FS.writeFile("/tmp/in/" + safe, new Uint8Array(bytes));
    var r = J(api.prepare("/tmp/in/" + safe, lo || 15, trang || "", huong || "tu-dong"));
    if (r.ok) r.loadedFamilies = await loadFonts(r.families);
    r.sources = used;
    return r;
  },
  nextItems: async function (maxChars) { return J(api.next_items(maxChars || 6000)); },
  load: async function (text) { return J(api.load(text)); },
  missingIds: async function (ids) { return J(api.missing_ids(JSON.stringify(ids))); },
  itemsFor: async function (ids) { return J(api.items_for(JSON.stringify(ids))); },
  translations: async function () { return J(api.translations()); },
  progress: async function () { return J(api.progress()); },
  build: async function (mode, footer) { return J(api.build(mode, footer !== false)); },
  qa: async function () { return J(api.qa()); },
  zipAll: async function () { return J(api.zip_all()); },
  readFile: async function (path) { return py.FS.readFile(path); },
  score: async function (goc, dich, nameGoc, nameDich) {
    await init();
    py.FS.mkdirTree("/tmp/cham");
    py.FS.writeFile("/tmp/cham/goc.pdf", new Uint8Array(goc));
    py.FS.writeFile("/tmp/cham/dich.pdf", new Uint8Array(dich));
    var r = J(api.score("/tmp/cham/goc.pdf", "/tmp/cham/dich.pdf", nameDich || ""));
    r.ten_goc = nameGoc; r.ten_dich = nameDich;
    return r;
  },
};

self.onmessage = async function (e) {
  var d = e.data;
  try {
    var result = await handlers[d.cmd].apply(null, d.args || []);
    var transfer = result instanceof Uint8Array ? [result.buffer] : [];
    self.postMessage({ id: d.id, ok: true, result: result }, transfer);
  } catch (err) {
    self.postMessage({ id: d.id, ok: false, error: String(err && err.message || err) });
  }
};
