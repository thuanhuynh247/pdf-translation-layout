/* dich-app.js — trang "Dịch PDF trên web". Bộ máy chạy trong dich-worker.js (Pyodide + PyMuPDF).
   Ba cách dịch: Dán (người dùng tự chép qua AI của mình), Khóa API (OpenRouter), Nhanh (Translator API của Chrome). */
(function () {
  "use strict";
  var $ = function (s) { return document.querySelector(s); };
  var $$ = function (s) { return Array.prototype.slice.call(document.querySelectorAll(s)); };

  var PASTE_CHARS = 6000, API_CHARS = 8000, FAST_CHARS = 4000, MAX_MB = 80;
  var PREFERRED_MODELS = ["google/gemini-2.5-flash", "google/gemini-2.5-pro", "anthropic/claude-sonnet-4.5",
    "openai/gpt-4.1-mini", "openai/gpt-4o-mini", "deepseek/deepseek-chat-v3.1", "deepseek/deepseek-chat"];

  // Quy tắc dịch lấy từ bộ máy (dich_pdf.QUY_TAC) theo chiều của tài liệu, để mọi kênh dùng chung một bản
  var LANG = { "en-vi": { src: "en", tgt: "vi", srcName: "tiếng Anh", tgtName: "tiếng Việt", label: "Anh → Việt", out: "_VI.pdf" },
    "vi-en": { src: "vi", tgt: "en", srcName: "tiếng Việt", tgtName: "tiếng Anh", label: "Việt → Anh", out: "_EN.pdf" } };
  function dir() { return LANG[(S.info && S.info.huong) || "en-vi"]; }
  function rules() { return (S.info && S.info.rules) || ""; }
  function rulesEnd(n) { return ((S.info && S.info.rules_end) || "").replace("{n}", n).replace(/\{\{/g, "{").replace(/\}\}/g, "}"); }

  /* ---------------- Worker ---------------- */
  var worker = null, seq = 0, waiting = {};
  function startWorker() {
    if (worker) return;
    worker = new Worker("assets/js/dich-worker.js");
    worker.onmessage = function (e) {
      var d = e.data;
      if (d.type === "status") { engineStatus(d.text, d.frac); return; }
      var w = waiting[d.id]; if (!w) return;
      delete waiting[d.id];
      if (d.ok) w.resolve(d.result); else w.reject(new Error(d.error));
    };
    worker.onerror = function (e) {
      Object.keys(waiting).forEach(function (k) { waiting[k].reject(new Error(e.message || "Bộ máy gặp lỗi.")); delete waiting[k]; });
    };
    // Nguồn tải bộ máy: "cdn" (jsDelivr + PyPI, tự chuyển về website khi lỗi) hoặc "self" (chỉ website)
    var CFG = window.SITE_CONFIG || {};
    worker.postMessage({ id: 0, cmd: "configure", args: [{ source: CFG.ENGINE_SOURCE || "cdn", ver: CFG.VERSION || "" }] });
  }
  function call(cmd) {
    var args = Array.prototype.slice.call(arguments, 1), transfer = [];
    args.forEach(function (a) { if (a instanceof ArrayBuffer) transfer.push(a); });
    startWorker();
    return new Promise(function (resolve, reject) {
      var id = ++seq; waiting[id] = { resolve: resolve, reject: reject };
      worker.postMessage({ id: id, cmd: cmd, args: args }, transfer);
    });
  }

  /* ---------------- Trạng thái ---------------- */
  var S = { bytes: null, name: "", hash: "", info: null, ids: [], warnIds: [], stop: false, running: false, urls: [] };

  function show(id, on) { var el = $(id); if (el) el.hidden = !on; }
  function setText(id, t) { var el = $(id); if (el) el.textContent = t; }
  function engineStatus(text, frac) {
    show("#engine", true); setText("#engine-text", text);
    if (typeof frac === "number") {
      $("#engine-bar").style.width = Math.round(frac * 100) + "%";
      $("#engine .bar").setAttribute("aria-valuenow", String(Math.round(frac * 100)));
    }
  }
  function err(id, msg) { var el = $(id); el.textContent = msg; el.hidden = !msg; }
  function trStatus(msg, bad) { var el = $("#tr-status"); el.textContent = msg || ""; el.className = "form-status" + (bad ? " is-error" : msg ? " is-ok" : ""); }
  function fmtMB(n) { return n < 1e6 ? Math.max(1, Math.round(n / 1e3)) + " KB" : (n / 1e6).toFixed(n > 1e7 ? 0 : 1).replace(".", ",") + " MB"; }
  function plural(n) { return n.toLocaleString("vi-VN"); }

  function setProgress(p) {
    if (!p || !p.total) return;
    var pct = Math.round(100 * p.done / p.total);
    $("#tr-bar").style.width = pct + "%";
    setText("#tr-text", "Đã dịch " + plural(p.done) + "/" + plural(p.total) + " đoạn (" + pct + "%) · lô xong " + p.batches_done + "/" + p.batches_total);
  }

  /* ---------------- Lưu tạm bản dịch (phòng khi tải lại trang) ---------------- */
  function storeKey() { return "ptl:" + S.hash + ":" + ($("#pages").value.trim() || "all") + ((S.info && S.info.huong === "vi-en") ? ":vi-en" : ""); }
  function saveLocal() {
    return call("translations").then(function (tr) {
      var v = JSON.stringify({ t: Date.now(), name: S.name, tr: tr });
      try { localStorage.setItem(storeKey(), v); }
      catch (e) {
        try {   // đầy bộ nhớ: xóa bản lưu cũ của file khác rồi thử lại
          Object.keys(localStorage).forEach(function (k) { if (k.indexOf("ptl:") === 0 && k !== storeKey() && k !== "ptl:or-key") localStorage.removeItem(k); });
          localStorage.setItem(storeKey(), v);
        } catch (e2) { /* không lưu được: bỏ qua */ }
      }
    }).catch(function () {});
  }
  function readLocal() { try { var v = localStorage.getItem(storeKey()); return v ? JSON.parse(v) : null; } catch (e) { return null; } }
  function dropLocal() { try { localStorage.removeItem(storeKey()); } catch (e) { /* bỏ qua */ } }

  /* ---------------- Bước 1: chọn file ---------------- */
  function hashBytes(buf) {
    if (!(window.crypto && crypto.subtle)) return Promise.resolve(String(buf.byteLength));
    return crypto.subtle.digest("SHA-256", buf).then(function (h) {
      return Array.prototype.map.call(new Uint8Array(h).slice(0, 12), function (b) { return ("0" + b.toString(16)).slice(-2); }).join("");
    });
  }

  function pickFile(file) {
    err("#b1-err", "");
    if (!file) return;
    if (!window.WebAssembly || !window.Worker) { err("#b1-err", "Trình duyệt này quá cũ để chạy bộ máy dịch. Hãy dùng Chrome, Edge, Firefox hoặc Safari bản mới."); return; }
    if (file.size > MAX_MB * 1e6) { err("#b1-err", "File lớn hơn " + MAX_MB + " MB. Hãy tách nhỏ file, hoặc dùng bản cho Claude."); return; }
    file.arrayBuffer().then(function (buf) {
      var head = new Uint8Array(buf.slice(0, 1024));
      var str = String.fromCharCode.apply(null, head);
      if (str.indexOf("%PDF") < 0) throw new Error("File này không phải PDF.");
      S.bytes = buf; S.name = file.name;
      setText("#drop-title", file.name);
      setText("#drop-sub", fmtMB(file.size) + " · bấm để chọn file khác");
      return hashBytes(buf);
    }).then(function (h) { S.hash = h; S.huong = "tu-dong"; return prepare(); })
      .catch(function (e) { err("#b1-err", e.message || String(e)); });
  }

  function prepare() {
    show("#b2", false); show("#b3", false); show("#b4", false);
    engineStatus("Đang chuẩn bị bộ máy (lần đầu khoảng 30 MB)…", 0.01);
    var pages = $("#pages").value.trim();
    return call("prepare", S.bytes.slice(0), S.name, 15, pages, S.huong || "tu-dong").then(function (r) {
      if (!r.ok) throw new Error(r.error || "Không mở được file.");
      S.info = r;
      $$('input[name="huong"]').forEach(function (x) { x.checked = x.value === r.huong; });
      setText("#huong-note", S.huong === "tu-dong" ? "Tự nhận theo chữ trong tài liệu" : "");
      var src = r.sources || {};
      engineStatus("Đã đọc xong tài liệu" + (src.core ? " · bộ máy tải từ " + (src.core === src.wheel ? src.core : src.core + " và " + src.wheel) : ""), 1);
      renderSummary(r);
      var saved = readLocal();
      if (saved && saved.tr && Object.keys(saved.tr).length) {
        return call("load", JSON.stringify(saved.tr)).then(function (lr) {
          var el = $("#resume");
          el.textContent = "Đã khôi phục " + plural(lr.done) + "/" + plural(lr.total) + " đoạn dịch từ lần trước trên máy này.";
          el.hidden = false; S.info.done = lr.done;
          renderSummary(Object.assign({}, r, lr));
        });
      }
      show("#resume", false);
    }).then(function () {
      show("#b2", true);
      $("#b2").scrollIntoView({ behavior: "smooth", block: "start" });
    }).catch(function (e) { show("#engine", false); err("#b1-err", e.message || String(e)); });
  }

  function renderSummary(r) {
    var lots = Math.max(1, Math.ceil(r.chars / PASTE_CHARS));
    var html = "<dl class='kv'>" +
      "<div><dt>Tài liệu</dt><dd>" + esc(r.name) + "</dd></div>" +
      "<div><dt>Số trang</dt><dd>" + plural(r.pages) + "</dd></div>" +
      "<div><dt>Đoạn cần dịch</dt><dd>" + plural(r.total) + " đoạn · khoảng " + plural(r.words) + " từ</dd></div>" +
      "<div><dt>Nếu dán qua AI</dt><dd>khoảng " + lots + " lần dán</dd></div>" +
      (r.done ? "<div><dt>Đã dịch</dt><dd>" + plural(r.done) + "/" + plural(r.total) + " đoạn</dd></div>" : "") +
      "</dl>";
    if (r.scanned && r.scanned.length) html += "<p class='notice'>Có " + r.scanned.length + " trang có vẻ là ảnh scan, không có chữ để dịch; các trang đó giữ nguyên.</p>";
    var c = r.clean || {}, cm = c.chuyen_ma || {}, kinds = Object.keys(cm);
    if (kinds.length) html += "<p class='notice'>Tài liệu dùng phông tiếng Việt cũ (" + kinds.map(function (k) { return k.toUpperCase(); }).join(", ") + "). Trang đã chuyển chữ sang Unicode trước khi dịch.</p>";
    if (c.dau_roi) html += "<p class='notice'>Có " + c.dau_roi + " dòng bị tách dấu thanh khỏi chữ cái; trang đã gắn lại.</p>";
    if (c.trang_loi_chu && c.trang_loi_chu.length) html += "<p class='notice'>" + c.trang_loi_chu.length + " trang trích ra chữ bị hỏng mã, không đọc được. Các trang đó giữ nguyên, không đưa cho AI.</p>";
    if (r.huong === "vi-en") html += "<p class='notice'>Bản tiếng Anh là bản nháp để đọc và tự kiểm. Học bạ, bằng cấp, giấy tờ nộp đại sứ quán hay cơ quan nhà nước vẫn cần người dịch ký và được chứng thực.</p>";
    if (!r.total) html += "<p class='notice'>Không tìm thấy chữ nào để dịch: có thể đây là PDF scan.</p>";
    $("#summary").innerHTML = html;
    $("#start").disabled = !r.total;
  }

  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }

  /* ---------------- Bước 3: dịch ---------------- */
  function mode() { var m = $('input[name="mode"]:checked'); return m ? m.value : "paste"; }

  function start() {
    show("#b3", true);
    ["paste", "api", "fast"].forEach(function (m) { show("#pane-" + m, m === mode()); });
    show("#warn-box", false); trStatus("");
    call("progress").then(setProgress);
    if (mode() === "paste") nextPrompt();
    if (mode() === "api") initApi();
    if (mode() === "fast") initFast();
    $("#b3").scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function promptFor(items, extra) {
    return rules() + (extra ? "\n" + extra : "") + "\n" + rulesEnd(items.length) + "\n\n" +
      items.map(function (it) { return JSON.stringify(it); }).join("\n");
  }

  function nextPrompt() {
    return call("nextItems", PASTE_CHARS).then(function (r) {
      setProgress(r);
      if (!r.items.length) { $("#prompt").value = ""; setText("#pb-label", "Đã dịch xong"); goBuild(); return; }
      S.ids = r.items.map(function (i) { return i.id; });
      $("#prompt").value = promptFor(r.items);
      var m = /LÔ (\d+)\/(\d+)/.exec(r.header || "");
      setText("#pb-label", (m ? "Câu nhắn lô " + m[1] + "/" + m[2] : "Câu nhắn") + " · " + r.items.length + " đoạn · " + plural($("#prompt").value.length) + " ký tự");
    });
  }

  function loadText(text) {
    return call("load", text).then(function (r) {
      if (!r.ok) throw new Error(r.error || "Không đọc được bản dịch.");
      setProgress(r);
      return call("missingIds", S.ids).then(function (miss) { r.missing = miss; return r; });
    }).then(function (r) { saveLocal(); return r; });
  }

  function showWarnings(w) {
    var ids = Object.keys(w || {});
    S.warnIds = ids;
    if (!ids.length) { show("#warn-box", false); return; }
    setText("#warn-title", ids.length + " đoạn nên xem lại (đã nạp, phiếu kiểm định sẽ ghi lại):");
    $("#warn-list").innerHTML = ids.slice(0, 12).map(function (k) {
      return "<li><span class='mono'>" + esc(k) + "</span> · " + esc(w[k].warning) + ": “" + esc(w[k].source.slice(0, 90)) + "”</li>";
    }).join("") + (ids.length > 12 ? "<li>… và " + (ids.length - 12) + " đoạn khác</li>" : "");
    show("#redo-warn", mode() === "paste");
    show("#warn-box", true);
  }

  function onLoadAnswer() {
    var text = $("#answer").value.trim();
    if (!text) { trStatus("Hãy dán câu trả lời của AI vào ô trên.", true); return; }
    var btn = $("#load-answer"); btn.disabled = true;
    loadText(text).then(function (r) {
      var n = S.ids.length - r.missing.length;
      trStatus("Đã nạp " + n + "/" + S.ids.length + " đoạn của lô này." +
        (r.missing.length ? " AI bỏ sót " + r.missing.length + " đoạn; chúng có trong câu nhắn kế tiếp." : ""), false);
      showWarnings(r.warnings);
      $("#answer").value = "";
      return nextPrompt();
    }).catch(function (e) {
      trStatus(e.message + " Hãy chép toàn bộ câu trả lời, có cả dấu { và }.", true);
    }).then(function () { btn.disabled = false; });
  }

  function redoWarnings() {
    if (!S.warnIds.length) return;
    call("itemsFor", S.warnIds).then(function (items) {
      S.ids = items.map(function (i) { return i.id; });
      $("#prompt").value = promptFor(items, dir().tgt === "en"
        ? "- This is a retry: last time these segments still had Vietnamese words, or changed numbers, dates or document numbers. Fix them."
        : "- Đây là lượt dịch lại: các đoạn này lần trước còn tiếng Anh, thiếu dấu hoặc lệch số liệu. Hãy sửa.");
      setText("#pb-label", "Câu nhắn dịch lại · " + items.length + " đoạn");
      show("#warn-box", false);
      $("#prompt").scrollIntoView({ behavior: "smooth", block: "center" });
    });
  }

  function copyPrompt() {
    var ta = $("#prompt"), btn = $("#copy-prompt");
    function ok() { var t = btn.textContent; btn.textContent = "Đã chép"; setTimeout(function () { btn.textContent = t; }, 1500); }
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(ta.value).then(ok, function () { ta.select(); document.execCommand("copy"); ok(); });
    else { ta.select(); document.execCommand("copy"); ok(); }
  }

  /* ---------- Khóa API: OpenRouter ---------- */
  var modelsLoaded = false;
  function getKey() {
    try { return localStorage.getItem("ptl:or-key") || sessionStorage.getItem("ptl:or-key") || ""; } catch (e) { return ""; }
  }
  function putKey(k, remember) {
    try {
      sessionStorage.setItem("ptl:or-key", k);
      if (remember) localStorage.setItem("ptl:or-key", k); else localStorage.removeItem("ptl:or-key");
    } catch (e) { /* bỏ qua */ }
  }
  function initApi() {
    var k = getKey();
    if (k && !$("#api-key").value) { $("#api-key").value = k; try { $("#remember-key").checked = !!localStorage.getItem("ptl:or-key"); } catch (e) { /* */ } }
    loadModels();
  }
  function loadModels() {
    if (modelsLoaded) return;
    fetch("https://openrouter.ai/api/v1/models").then(function (r) { return r.json(); }).then(function (d) {
      var ids = (d.data || []).map(function (m) { return m.id; });
      if (!ids.length) return;
      modelsLoaded = true;
      $("#model-list").innerHTML = ids.map(function (i) { return "<option value='" + esc(i) + "'>"; }).join("");
      if (!$("#api-model").value) {
        var pick = PREFERRED_MODELS.filter(function (p) { return ids.indexOf(p) >= 0; })[0];
        if (pick) $("#api-model").value = pick;
      }
      setText("#model-hint", "Có " + ids.length + " mô hình. Gợi ý: Gemini Flash rẻ và nhanh; Claude, GPT bản lớn dịch hay hơn nhưng đắt hơn.");
    }).catch(function () { /* không lấy được danh sách: người dùng tự nhập mã mô hình */ });
  }

  function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }

  function askOpenRouter(key, model, items, tries) {
    tries = tries || 0;
    return fetch("https://openrouter.ai/api/v1/chat/completions", {
      method: "POST",
      headers: { "Authorization": "Bearer " + key, "Content-Type": "application/json",
        "HTTP-Referer": location.origin, "X-Title": "pdf-translation-layout" },
      body: JSON.stringify({ model: model, temperature: 0, messages: [
        { role: "system", content: rules().replace("trong cuộc trò chuyện này", "trong toàn bộ tài liệu") + "\n" + rulesEnd(items.length) },
        { role: "user", content: items.map(function (it) { return JSON.stringify(it); }).join("\n") }] })
    }).then(function (res) {
      if (res.status === 429 || res.status >= 500) {
        if (tries < 4) return sleep(2000 * Math.pow(2, tries)).then(function () { return askOpenRouter(key, model, items, tries + 1); });
      }
      return res.json().catch(function () { return {}; }).then(function (d) {
        if (!res.ok) {
          var m = (d.error && d.error.message) || ("HTTP " + res.status);
          if (res.status === 401) m = "Khóa OpenRouter không đúng hoặc đã bị thu hồi.";
          if (res.status === 402) m = "Tài khoản OpenRouter không đủ tiền cho lượt này.";
          if (res.status === 400 && /model/i.test(m)) m = "Mã mô hình không đúng: " + model + ".";
          throw new Error(m);
        }
        var c = d.choices && d.choices[0] && d.choices[0].message && d.choices[0].message.content;
        if (!c) throw new Error("Mô hình không trả về nội dung.");
        return { text: c, usage: d.usage || {} };
      });
    });
  }

  function runApi() {
    var key = $("#api-key").value.trim(), model = $("#api-model").value.trim();
    if (!key) { trStatus("Hãy nhập khóa OpenRouter.", true); $("#api-key").focus(); return; }
    if (!model) { trStatus("Hãy nhập mã mô hình.", true); $("#api-model").focus(); return; }
    putKey(key, $("#remember-key").checked);
    S.stop = false; S.running = true; show("#api-stop", true); $("#api-run").disabled = true;
    var tokens = 0, stuck = 0, lastDone = -1;
    function step() {
      if (S.stop) return finish("Đã dừng. Bấm Chạy tự động để làm tiếp.");
      return call("nextItems", API_CHARS).then(function (r) {
        setProgress(r);
        if (!r.items.length) return finish(null, true);
        if (r.done === lastDone) stuck++; else stuck = 0;
        lastDone = r.done;
        if (stuck >= 3) throw new Error("Mô hình nhiều lần không trả đủ bản dịch. Thử mô hình khác, hoặc dùng cách Dán.");
        S.ids = r.items.map(function (i) { return i.id; });
        trStatus("Đang dịch " + r.items.length + " đoạn…" + (tokens ? " Đã dùng " + plural(tokens) + " token." : ""));
        return askOpenRouter(key, model, r.items).then(function (ans) {
          tokens += (ans.usage.total_tokens || 0);
          return loadText(ans.text);
        }).then(function (lr) { showWarnings(lr.warnings); return step(); });
      });
    }
    function finish(msg, done) {
      S.running = false; show("#api-stop", false); $("#api-run").disabled = false;
      if (done) { trStatus("Đã dịch xong." + (tokens ? " Tổng " + plural(tokens) + " token." : ""), false); goBuild(); }
      else if (msg) trStatus(msg, false);
    }
    step().catch(function (e) { S.running = false; show("#api-stop", false); $("#api-run").disabled = false; trStatus(e.message, true); });
  }

  /* ---------- Dịch nhanh: Translator API của Chrome ---------- */
  function hasTranslator() { return typeof self.Translator !== "undefined" && self.Translator && typeof self.Translator.create === "function"; }
  function initFast() {
    if (!hasTranslator()) {
      setText("#fast-status", "Trình duyệt này chưa có bộ dịch tích hợp. Cần Chrome 138 trở lên trên máy tính (Windows, macOS, Linux). Hãy dùng cách Dán hoặc Khóa API.");
      $("#fast-run").disabled = true; return;
    }
    var L = dir();
    Translator.availability({ sourceLanguage: L.src, targetLanguage: L.tgt }).then(function (a) {
      var msg = { available: "Bộ dịch " + L.label + " đã có sẵn trên máy.", downloadable: "Lần đầu Chrome sẽ tải gói ngôn ngữ " + L.label + " (vài chục MB).",
        downloading: "Chrome đang tải gói ngôn ngữ.", unavailable: "Chrome trên máy này không hỗ trợ dịch " + L.label + ". Hãy dùng cách Dán." }[a] || a;
      setText("#fast-status", msg);
      $("#fast-run").disabled = a === "unavailable";
    }).catch(function (e) { setText("#fast-status", "Không kiểm tra được bộ dịch: " + e.message); });
  }
  function runFast() {
    S.stop = false; show("#fast-stop", true); $("#fast-run").disabled = true;
    Translator.create({ sourceLanguage: dir().src, targetLanguage: dir().tgt, monitor: function (m) {
      m.addEventListener("downloadprogress", function (e) { setText("#fast-status", "Đang tải gói ngôn ngữ " + Math.round(e.loaded * 100) + "%"); });
    } }).then(function (tr) {
      setText("#fast-status", "Đang dịch trên máy…");
      function step() {
        if (S.stop) { trStatus("Đã dừng.", false); return; }
        return call("nextItems", FAST_CHARS).then(function (r) {
          setProgress(r);
          if (!r.items.length) { trStatus("Đã dịch xong.", false); goBuild(); return; }
          S.ids = r.items.map(function (i) { return i.id; });
          var out = {};
          return r.items.reduce(function (p, it) {
            return p.then(function () { return tr.translate(it.text).then(function (v) { out[it.id] = v; }); });
          }, Promise.resolve()).then(function () { return loadText(JSON.stringify(out)); })
            .then(function (lr) { showWarnings(lr.warnings); return step(); });
        });
      }
      return step();
    }).catch(function (e) { trStatus("Dịch nhanh lỗi: " + e.message, true); })
      .then(function () { show("#fast-stop", false); $("#fast-run").disabled = false; });
  }

  /* ---------------- Bước 4: dựng, kiểm định, tải ---------------- */
  function goBuild() { show("#b4", true); $("#b4").scrollIntoView({ behavior: "smooth", block: "start" }); }

  function build() {
    var outs = $$('input[name="out"]:checked').map(function (c) { return c.value; });
    var footer = !$("#own-doc").checked;
    var btn = $("#build"); btn.disabled = true; show("#result", false);
    S.urls.forEach(function (u) { URL.revokeObjectURL(u); }); S.urls = [];
    var steps = ["don-ngu"].concat(outs), files = {}, t0 = Date.now();
    var L = dir();
    setText("#build-text", "Đang dựng bản " + L.tgtName + "… (tài liệu dài có thể mất vài phút)");
    steps.reduce(function (p, m, i) {
      return p.then(function () {
        setText("#build-text", "Đang dựng " + ({ "don-ngu": "bản " + L.tgtName, "doi-trang": "song ngữ đối trang", "hai-cot": "song ngữ hai cột", "xen-doan": "song ngữ xen đoạn" }[m]) + " (" + (i + 1) + "/" + steps.length + ")…");
        return call("build", m, footer).then(function (r) {
          if (!r.ok) throw new Error(r.error);
          r.files.forEach(function (f) { files[f.name] = f; });
        });
      });
    }, Promise.resolve()).then(function () {
      setText("#build-text", "Đang kiểm định…");
      return call("qa");
    }).then(function (qa) {
      renderQa(qa);
      var list = Object.keys(files).map(function (k) { return files[k]; })
        .filter(function (f) { return f.name.indexOf(L.out) > 0 || steps.some(function (m) { return m !== "don-ngu" && f.name.indexOf(m) > 0; }); });
      if (qa.report_path) list.push({ name: qa.report_name, path: qa.report_path, size: qa.report_md.length });
      return renderFiles(list).then(function () { return call("zipAll"); });
    }).then(function (z) {
      if (z && z.ok) return call("readFile", z.path).then(function (b) {
        var u = URL.createObjectURL(new Blob([b], { type: "application/zip" })); S.urls.push(u);
        var a = $("#zip-link"); a.href = u; a.download = z.name; a.hidden = false;
      });
    }).then(function () {
      setText("#build-text", "Xong sau " + Math.round((Date.now() - t0) / 1000) + " giây.");
      show("#result", true);
      $("#result").scrollIntoView({ behavior: "smooth", block: "start" });
    }).catch(function (e) { setText("#build-text", "Lỗi khi dựng: " + e.message); })
      .then(function () { btn.disabled = false; });
  }

  var DESC = { "_VI.pdf": "Bản tiếng Việt, đúng từng trang", "_EN.pdf": "Bản tiếng Anh, đúng từng trang", "song-ngu-doi-trang": "Trang gốc và trang dịch xen kẽ",
    "song-ngu-hai-cot": "Gốc bên trái, dịch bên phải", "song-ngu-xen-doan": "Mỗi đoạn gốc kèm bản dịch ngay dưới",
    "phieu-kiem-dinh": "Phiếu kiểm định (Markdown)" };
  function renderFiles(list) {
    var ul = $("#files"); ul.innerHTML = "";
    return list.reduce(function (p, f) {
      return p.then(function () { return call("readFile", f.path); }).then(function (b) {
        var type = /\.md$/.test(f.name) ? "text/markdown" : "application/pdf";
        var u = URL.createObjectURL(new Blob([b], { type: type })); S.urls.push(u);
        var key = Object.keys(DESC).filter(function (k) { return f.name.indexOf(k) >= 0; })[0];
        var li = document.createElement("li");
        li.innerHTML = "<span class='ic'>" + (/\.md$/.test(f.name) ? "QA" : "PDF") + "</span><div><strong><a download></a></strong><span></span></div>";
        var a = li.querySelector("a"); a.href = u; a.download = f.name; a.textContent = f.name;
        li.querySelector("span:last-child").textContent = (key ? DESC[key] + " · " : "") + fmtMB(b.length);
        ul.appendChild(li);
      });
    }, Promise.resolve());
  }

  function renderQa(qa) {
    var v = $("#verdict");
    v.className = "verdict " + (qa.pass ? "ok" : "bad");
    v.innerHTML = "<strong>" + (qa.pass ? "Phiếu kiểm định: ĐẠT" : "Phiếu kiểm định: CHƯA ĐẠT") + "</strong><span>" +
      (qa.pass ? "Không có ký tự lỗi phông, đoạn tràn khung hay đoạn chưa dịch." : "Xem các mục cần sửa bên dưới. Đoạn chưa dịch vẫn giữ " + dir().srcName + ".") + "</span>";
    $("#qa-body").innerHTML = (qa.checks || []).map(function (c, i) {
      var warnOnly = c.canh_bao !== undefined ? c.canh_bao : i >= 6;
      var mark = c.dat ? "✔ Đạt" : (warnOnly ? "⚠ Xem lại" : "✘ Cần sửa");
      return "<tr><th scope='row'>" + esc(c.muc) + "</th><td class='" + (c.dat ? "yes" : warnOnly ? "" : "no-bad") + "'>" + mark + "</td><td>" + esc(c.chi_tiet) + "</td></tr>";
    }).join("");
  }

  function resetAll() {
    if (S.running) S.stop = true;
    dropLocal();
    S.bytes = null; S.hash = ""; S.info = null;
    $("#file").value = ""; $("#pages").value = "";
    setText("#drop-title", "Kéo thả file PDF vào đây, hoặc bấm để chọn");
    setText("#drop-sub", "PDF có chữ thật (bôi đen được), tối đa " + MAX_MB + " MB.");
    ["#b2", "#b3", "#b4", "#result", "#engine"].forEach(function (id) { show(id, false); });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  /* ---------------- Chấm bản dịch có sẵn ---------------- */
  function runScore() {
    var g = $("#cham-goc").files[0], d = $("#cham-dich").files[0];
    if (!g || !d) { setText("#cham-text", "Hãy chọn đủ hai file."); return; }
    var btn = $("#cham-run"); btn.disabled = true; show("#cham-result", false);
    setText("#cham-text", "Đang chấm… (lần đầu trang tải bộ máy khoảng 30 MB)");
    Promise.all([g.arrayBuffer(), d.arrayBuffer()]).then(function (bufs) {
      return call("score", bufs[0], bufs[1], g.name, d.name);
    }).then(function (r) {
      if (!r.ok) throw new Error(r.error || "Không chấm được.");
      var lk = String(r.lien_ket).split("/").map(Number), pg = String(r.so_trang).split("/").map(Number);
      var rows = [
        ["Số trang (dịch/gốc)", r.so_trang, pg[0] === pg[1] ? "ok" : "Số trang khác bản gốc (bình thường nếu là bản song ngữ)"],
        ["Ký tự lỗi phông, mất dấu", r.ky_tu_loi_phong, r.ky_tu_loi_phong === 0 ? "ok" : "Có ký tự hiện thành ô vuông hoặc dấu hỏi"],
      ].concat(r.huong === "vi-en" ? [
        ["Từ tiếng Việt còn sót", r.ty_le_tu_tieng_viet_con_lai, r.ty_le_tu_tieng_viet_con_lai <= 0.02 ? "ok" : "Còn chữ tiếng Việt chưa dịch"],
        ["Tiếng Việt không dấu còn sót", r.ty_le_tu_tieng_viet_khong_dau, r.ty_le_tu_tieng_viet_khong_dau <= 0.02 ? "ok" : "Còn câu tiếng Việt bị mất dấu"]
      ] : [
        ["Tỷ lệ từ có dấu", r.ty_le_tu_co_dau, r.ty_le_tu_co_dau >= 0.5 ? "ok" : "Thấp: dấu hiệu mất dấu tiếng Việt"],
        ["Từ tiếng Anh còn sót", r.ty_le_tu_tieng_anh_con_lai, r.ty_le_tu_tieng_anh_con_lai <= 0.05 ? "ok" : "Còn nhiều tiếng Anh chưa dịch"]
      ]).concat([
        ["Liên kết (còn/gốc)", r.lien_ket, lk[0] >= lk[1] ? "ok" : "Mất liên kết"],
        ["Trang mất lớp chữ", r.trang_mat_lop_chu, r.trang_mat_lop_chu === 0 ? "ok" : "Có trang bị biến thành ảnh: không bôi đen, không tìm kiếm được"],
        ["Cặp dòng đè nhau", r.cap_dong_chong_nhau, r.cap_dong_chong_nhau === 0 ? "ok" : "Có chữ đè lên nhau"],
        ["Độ trùng bố cục", r.do_trung_bo_cuc === "" ? "không áp dụng" : r.do_trung_bo_cuc, r.do_trung_bo_cuc === "" || r.do_trung_bo_cuc >= 0.7 ? "ok" : "Chữ dịch lệch nhiều so với vị trí gốc"]
      ]);
      $("#cham-body").innerHTML = rows.map(function (x) {
        var ok = x[2] === "ok";
        return "<tr><th scope='row'>" + esc(x[0]) + "</th><td class='mono'>" + esc(String(x[1]).replace(".", ",")) + "</td><td class='" + (ok ? "yes" : "no-bad") + "'>" + (ok ? "✔ Tốt" : esc(x[2])) + "</td></tr>";
      }).join("");
      $("#cham-result").classList.add("qa-table");
      show("#cham-result", true);
      setText("#cham-text", "Đã chấm " + d.name + " so với " + g.name + ". Bộ chấm không đánh giá văn dịch hay dở; phần đó cần người đọc.");
    }).catch(function (e) { setText("#cham-text", "Lỗi: " + e.message); })
      .then(function () { btn.disabled = false; });
  }

  /* ---------------- Gắn sự kiện ---------------- */
  document.addEventListener("DOMContentLoaded", function () {
    var drop = $("#drop"), file = $("#file");
    file.addEventListener("change", function () { pickFile(file.files[0]); });
    ["dragenter", "dragover"].forEach(function (ev) { drop.addEventListener(ev, function (e) { e.preventDefault(); drop.classList.add("over"); }); });
    ["dragleave", "drop"].forEach(function (ev) { drop.addEventListener(ev, function (e) { e.preventDefault(); drop.classList.remove("over"); }); });
    drop.addEventListener("drop", function (e) { if (e.dataTransfer.files[0]) pickFile(e.dataTransfer.files[0]); });
    $("#pages-apply").addEventListener("click", function () { if (S.bytes) prepare(); });
    $$('input[name="huong"]').forEach(function (x) {
      x.addEventListener("change", function () { if (S.bytes && x.checked) { S.huong = x.value; prepare(); } });
    });
    $("#start").addEventListener("click", start);
    $("#copy-prompt").addEventListener("click", copyPrompt);
    $("#load-answer").addEventListener("click", onLoadAnswer);
    $("#skip-build").addEventListener("click", goBuild);
    $("#redo-warn").addEventListener("click", redoWarnings);
    $("#api-run").addEventListener("click", runApi);
    $("#api-stop").addEventListener("click", function () { S.stop = true; });
    $("#api-key").addEventListener("change", loadModels);
    $("#fast-run").addEventListener("click", runFast);
    $("#fast-stop").addEventListener("click", function () { S.stop = true; });
    $("#build").addEventListener("click", build);
    $("#new-file").addEventListener("click", resetAll);
    $("#cham-run").addEventListener("click", runScore);
    $$('input[name="mode"]').forEach(function (r) { r.addEventListener("change", function () { if (!$("#b3").hidden) start(); }); });
    if (!hasTranslator()) setText("#fast-note", "Cần Chrome 138 trở lên trên máy tính; trình duyệt này chưa có bộ dịch tích hợp. Bộ dịch chạy trên máy, không gửi chữ đi đâu.");
    window.__ptlTest = { call: call, state: S };   // cho kiểm thử tự động
  });
})();
