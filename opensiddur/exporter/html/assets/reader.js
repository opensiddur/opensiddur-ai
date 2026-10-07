/*
 * The page script of an Open Siddur electronic book.
 *
 * The page arrives showing what the printed book shows for the same settings: the rules in
 * <style id="os-cond-default">, computed when the book was built. This script takes over from
 * them. It resolves every undecided passage against the reader's own settings, kept in this
 * browser, writes the result into <style id="os-cond-live">, and redoes it whenever a setting
 * changes. Without it -- no scripting, as in most EPUB readers -- the page is the printed book.
 *
 * Nothing leaves the device: no network access, no tracking.
 */
(function () {
  "use strict";

  var book = JSON.parse(document.getElementById("os-book").textContent);
  var storageKey = "opensiddur:" + book.id + ":settings";
  var liveStyle = document.getElementById("os-cond-live");
  var defaultStyle = document.getElementById("os-cond-default");

  // Every file:// page shares one origin, so the key carries the book's id. Storage can be
  // refused (a private window, a locked-down reader); the book still works, unremembered.
  function loadSettings() {
    try {
      var stored = JSON.parse(window.localStorage.getItem(storageKey));
      return stored && typeof stored === "object" ? stored : {};
    } catch (e) {
      return {};
    }
  }

  function saveSettings(settings) {
    try {
      window.localStorage.setItem(storageKey, JSON.stringify(settings));
    } catch (e) {
      /* not remembered */
    }
  }

  var reader = loadSettings();

  function apply() {
    liveStyle.textContent = OSCond.scopeCss(book, reader, book.defaults).css;
    defaultStyle.disabled = true;
  }

  // ── Words for the settings panel ───────────────────────────────────────

  function words(name) {
    var text = String(name).replace(/^[a-z]+:/, "").replace(/[-_]/g, " ");
    return text.charAt(0).toUpperCase() + text.slice(1);
  }

  function describe(value) {
    if (value === true) return "Yes";
    if (value === false) return "No";
    if (value !== null && typeof value === "object" && "num" in value) {
      return "max" in value ? value.num + "–" + value.max : String(value.num);
    }
    return words(value);
  }

  // A value the reader can set: a condition's range becomes its first number.
  function settable(value) {
    if (value !== null && typeof value === "object" && "num" in value) return value.num;
    return value;
  }

  function el(tag, attributes, children) {
    var element = document.createElement(tag);
    Object.keys(attributes || {}).forEach(function (key) {
      if (key === "text") element.textContent = attributes[key];
      else element.setAttribute(key, attributes[key]);
    });
    (children || []).forEach(function (child) { element.appendChild(child); });
    return element;
  }

  // ── The settings panel ─────────────────────────────────────────────────

  // The select's value for the reader's setting: "" when untouched, else its JSON (a null
  // being the reader's own "show every option").
  function currentChoice(feature) {
    var set = reader[feature.fs];
    return set && Object.prototype.hasOwnProperty.call(set, feature.name)
      ? JSON.stringify(set[feature.name]) : "";
  }

  // undefined clears the reader's setting, so the book's default applies again.
  function setValue(feature, value) {
    if (value === undefined) {
      if (reader[feature.fs]) {
        delete reader[feature.fs][feature.name];
        if (!Object.keys(reader[feature.fs]).length) delete reader[feature.fs];
      }
    } else {
      (reader[feature.fs] = reader[feature.fs] || {})[feature.name] = value;
    }
    saveSettings(reader);
    apply();
  }

  function control(feature, index) {
    var id = "os-setting-" + index;
    var fallback = book.defaults[feature.fs] && book.defaults[feature.fs][feature.name];
    var select = el("select", { id: id, "aria-describedby": id + "-count" });
    if (fallback === undefined || fallback === null) {
      select.appendChild(el("option", { value: "", text: "Not set — show every option" }));
    } else {
      select.appendChild(el("option", { value: "", text: "The book's default — " + describe(fallback) }));
      select.appendChild(el("option", { value: "null", text: "Show every option" }));
    }
    var values = feature.values.map(settable).filter(function (value, i, all) {
      return all.findIndex(function (other) {
        return JSON.stringify(other) === JSON.stringify(value);
      }) === i;
    });
    if (values.every(function (v) { return typeof v === "boolean"; })) values = [true, false];
    values.forEach(function (value) {
      select.appendChild(el("option", { value: JSON.stringify(value), text: describe(value) }));
    });
    select.value = currentChoice(feature);
    if (select.selectedIndex < 0) select.value = "";
    select.addEventListener("change", function () {
      setValue(feature, select.value === "" ? undefined : JSON.parse(select.value));
    });
    var count = feature.scopes === 1 ? "1 passage" : feature.scopes + " passages";
    return el("div", { class: "os-setting" }, [
      el("label", { for: id, text: words(feature.name) }),
      select,
      el("span", { id: id + "-count", class: "os-setting-count", text: count })
    ]);
  }

  function settingsDialog() {
    var dialog = el("dialog", { id: "os-settings", class: "os-dialog", "aria-labelledby": "os-settings-title" });
    var groups = {};
    book.features.forEach(function (feature, index) {
      (groups[feature.fs] = groups[feature.fs] || []).push(control(feature, index));
    });
    var body = [el("h2", { id: "os-settings-title", text: "Settings" }),
                el("p", { class: "os-note", text:
                  "Choose what applies to you, and the book shows what you say. " +
                  "A passage that depends on something not set is shown with the " +
                  "instruction for when to say it, as in the printed book." })];
    Object.keys(groups).sort().forEach(function (fs) {
      body.push(el("fieldset", {}, [el("legend", { text: words(fs) })].concat(groups[fs])));
    });
    if (book.calendarScopes) {
      body.push(el("p", { class: "os-note", text:
        book.calendarScopes + " passages depend on the date, the time or the place. " +
        "This edition cannot yet tell them from your device, so it shows each of them " +
        "with its instruction." }));
    }
    var reset = el("button", { type: "button", text: "Clear all settings" });
    reset.addEventListener("click", function () {
      reader = {};
      saveSettings(reader);
      apply();
      dialog.replaceWith(settingsDialog());
      document.getElementById("os-settings").showModal();
    });
    var close = el("button", { type: "button", class: "os-close", text: "Close" });
    close.addEventListener("click", function () { dialog.close(); });
    body.push(el("div", { class: "os-dialog-buttons" }, [reset, close]));
    body.forEach(function (child) { dialog.appendChild(child); });
    return dialog;
  }

  // ── Contents ───────────────────────────────────────────────────────────

  function contentsDialog() {
    var dialog = el("dialog", { id: "os-contents", class: "os-dialog", "aria-labelledby": "os-contents-title" });
    var list = el("ol", { class: "os-contents" });
    var headings = document.querySelectorAll(".os-book h1, .os-book h2, .os-book h3");
    Array.prototype.forEach.call(headings, function (heading, index) {
      if (heading.closest(".col-parallel")) return;  // a translated heading repeats its row's
      if (!heading.getClientRects().length) return;  // in a passage the settings hide
      if (!heading.id) heading.id = "os-heading-" + index;
      var link = el("a", { href: "#" + heading.id, text: heading.textContent.trim() });
      link.addEventListener("click", function () { dialog.close(); });
      list.appendChild(el("li", { class: "os-contents-" + heading.tagName.toLowerCase() }, [link]));
    });
    var close = el("button", { type: "button", class: "os-close", text: "Close" });
    close.addEventListener("click", function () { dialog.close(); });
    [el("h2", { id: "os-contents-title", text: "Contents" }), list,
     el("div", { class: "os-dialog-buttons" }, [close])].forEach(function (child) {
      dialog.appendChild(child);
    });
    return dialog;
  }

  // ── Start ──────────────────────────────────────────────────────────────

  apply();

  document.body.appendChild(settingsDialog());
  var toolbar = document.querySelector(".os-toolbar");
  toolbar.hidden = false;
  document.getElementById("os-open-settings").addEventListener("click", function () {
    document.getElementById("os-settings").showModal();
  });
  // Built afresh each time: which headings are shown depends on the settings.
  document.getElementById("os-open-contents").addEventListener("click", function () {
    var old = document.getElementById("os-contents");
    if (old) old.remove();
    var contents = contentsDialog();
    document.body.appendChild(contents);
    contents.showModal();
  });

  // Passages shown or hidden above may have moved a linked one: go to it again.
  if (location.hash) {
    var id = location.hash.slice(1);
    try { id = decodeURIComponent(id); } catch (e) { /* use it as it is */ }
    var target = document.getElementById(id);
    if (target) target.scrollIntoView();
  }
})();
