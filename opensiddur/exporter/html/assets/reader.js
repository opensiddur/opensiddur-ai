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

  function sameValue(a, b) {
    return JSON.stringify(a) === JSON.stringify(b);
  }

  // ── The reader's settings ──────────────────────────────────────────────

  var features = {};
  book.features.forEach(function (feature) {
    features[feature.fs + "\u0000" + feature.name] = feature;
  });

  function has(fs, name) {
    return !!reader[fs] && Object.prototype.hasOwnProperty.call(reader[fs], name);
  }

  // undefined clears the reader's setting, so the book's default applies again; null is the
  // reader's own "show every option".
  function setValue(fs, name, value) {
    if (value === undefined) {
      if (reader[fs]) {
        delete reader[fs][name];
        if (!Object.keys(reader[fs]).length) delete reader[fs];
      }
    } else {
      (reader[fs] = reader[fs] || {})[name] = value;
    }
  }

  var refreshers = [];

  // A change previews at once; it is kept (saved) only when the reader says Done.
  function changed() {
    apply();
    refreshers.forEach(function (refresh) { refresh(); });
  }

  function featureLabel(feature) {
    return feature.label || words(feature.name);
  }

  function valueLabel(feature, value) {
    var labels = feature.valueLabels || {};
    var key = String(settable(value));
    return Object.prototype.hasOwnProperty.call(labels, key) ? labels[key] : describe(value);
  }

  // ── Controls ───────────────────────────────────────────────────────────

  var controlCount = 0;

  function row(label, control, note) {
    var id = "os-setting-" + (controlCount++);
    control.id = id;
    var children = [el("label", { for: id, text: label }), control];
    if (note) {
      control.setAttribute("aria-describedby", id + "-note");
      children.push(el("span", { id: id + "-note", class: "os-setting-count", text: note }));
    }
    return el("div", { class: "os-setting" }, children);
  }

  function passages(count) {
    return count === 1 ? "1 passage" : count + " passages";
  }

  // A composite control (basic_settings.yaml): each option sets several features at once.
  function compositeControl(entry) {
    var keys = [];
    entry.options.forEach(function (option) {
      Object.keys(option.set).forEach(function (fs) {
        Object.keys(option.set[fs]).forEach(function (name) {
          if (!keys.some(function (k) { return k[0] === fs && k[1] === name; })) keys.push([fs, name]);
        });
      });
    });
    var defaults = keys.filter(function (k) {
      var set = book.defaults[k[0]];
      return set && set[k[1]] !== undefined && set[k[1]] !== null;
    });
    var select = el("select");
    if (defaults.length) {
      // The book's own choice, by the option it amounts to if there is one.
      var bookChoice = entry.options.find(function (option) {
        return Object.keys(option.set).every(function (fs) {
          return Object.keys(option.set[fs]).every(function (name) {
            var set = book.defaults[fs];
            return set && sameValue(set[name], option.set[fs][name]);
          });
        });
      });
      select.appendChild(el("option", { value: "", text: "The book's default" +
        (bookChoice ? " — " + bookChoice.label : "") }));
      select.appendChild(el("option", { value: "null", text: "Show every option" }));
    } else {
      select.appendChild(el("option", { value: "", text: "Not set — show every option" }));
    }
    entry.options.forEach(function (option, index) {
      select.appendChild(el("option", { value: String(index), text: option.label }));
    });
    var custom = el("option", { value: "custom", text: "Custom (set in Advanced)", disabled: "" });
    select.appendChild(custom);

    function matches(option) {
      return Object.keys(option.set).every(function (fs) {
        return Object.keys(option.set[fs]).every(function (name) {
          return has(fs, name) && sameValue(reader[fs][name], option.set[fs][name]);
        });
      });
    }

    function everyOption() {
      return keys.every(function (k) { return has(k[0], k[1]) && reader[k[0]][k[1]] === null; });
    }

    function refresh() {
      var found = entry.options.findIndex(matches);
      var any = keys.some(function (k) { return has(k[0], k[1]); });
      var every = defaults.length && everyOption();
      custom.hidden = found >= 0 || every || !any;
      select.value = found >= 0 ? String(found) : every ? "null" : (any ? "custom" : "");
    }

    select.addEventListener("change", function () {
      keys.forEach(function (k) { setValue(k[0], k[1], undefined); });
      if (select.value === "null") {
        // The reader's own "show every option", over the book's default.
        keys.forEach(function (k) { setValue(k[0], k[1], null); });
      } else if (select.value !== "") {
        var option = entry.options[Number(select.value)];
        Object.keys(option.set).forEach(function (fs) {
          Object.keys(option.set[fs]).forEach(function (name) {
            setValue(fs, name, option.set[fs][name]);
          });
        });
      }
      changed();
    });
    refreshers.push(refresh);
    refresh();
    return row(entry.label, select, entry.note);
  }

  // One feature: a select of its values, or for a number without names, a number field.
  function featureControl(feature, label) {
    var fallback = book.defaults[feature.fs] && book.defaults[feature.fs][feature.name];
    var hasDefault = fallback !== undefined && fallback !== null;
    var values = feature.values.map(settable).filter(function (value, i, all) {
      return all.findIndex(function (other) { return sameValue(other, value); }) === i;
    });
    var named = feature.valueLabels && Object.keys(feature.valueLabels).length;
    if (feature.kind === "binary") values = [true, false];
    if (named) {
      values = Object.keys(feature.valueLabels).map(function (key) {
        return feature.kind === "numeric" ? Number(key) : key;
      });
    }
    var note = passages(feature.scopes);

    if (feature.kind === "numeric" && !named) {
      var input = el("input", { type: "number", inputmode: "numeric", step: "1", min: "0",
                                placeholder: hasDefault ? "Default: " + describe(fallback) : "Not set" });
      input.addEventListener("change", function () {
        // A number field reports what it cannot read as empty: that is not "unset".
        if (input.validity.badInput) {
          input.setCustomValidity("Enter a whole number, or clear the field.");
          input.reportValidity();
          return;
        }
        var text = input.value.trim();
        var number = Number(text);
        if (text !== "" && !(Number.isInteger(number) && number >= 0)) {
          input.setCustomValidity("Enter a whole number, or clear the field.");
          input.reportValidity();
          return;
        }
        input.setCustomValidity("");
        setValue(feature.fs, feature.name, text === "" ? undefined : number);
        changed();
      });
      refreshers.push(function () {
        var value = has(feature.fs, feature.name) ? reader[feature.fs][feature.name] : null;
        input.value = typeof value === "number" ? String(value) : "";
      });
      refreshers[refreshers.length - 1]();
      return row(label, input, note);
    }

    var select = el("select");
    if (hasDefault) {
      select.appendChild(el("option", { value: "", text: "The book's default — " + valueLabel(feature, fallback) }));
      select.appendChild(el("option", { value: "null", text: "Show every option" }));
    } else {
      select.appendChild(el("option", { value: "", text: "Not set — show every option" }));
    }
    values.forEach(function (value) {
      select.appendChild(el("option", { value: JSON.stringify(value), text: valueLabel(feature, value) }));
    });
    select.addEventListener("change", function () {
      setValue(feature.fs, feature.name, select.value === "" ? undefined : JSON.parse(select.value));
      changed();
    });
    refreshers.push(function () {
      select.value = has(feature.fs, feature.name)
        ? JSON.stringify(reader[feature.fs][feature.name]) : "";
      if (select.selectedIndex < 0) select.value = "";
    });
    refreshers[refreshers.length - 1]();
    return row(label, select, note);
  }

  // ── Dialogs ────────────────────────────────────────────────────────────

  // A header with the title and ×, a body that scrolls, and a footer that does not, so its
  // buttons are always in reach however long the body.
  function dialogFrame(id, title, closeLabel) {
    var dialog = el("dialog", { id: id, class: "os-dialog", "aria-labelledby": id + "-title" });
    var close = el("button", { type: "button", class: "os-x", "aria-label": closeLabel, text: "×" });
    close.addEventListener("click", function () { dialog.close(); });
    var body = el("div", { class: "os-dialog-body" });
    var footer = el("div", { class: "os-dialog-footer" });
    dialog.appendChild(el("div", { class: "os-dialog-header" }, [
      el("h2", { id: id + "-title", text: title }), close]));
    dialog.appendChild(body);
    dialog.appendChild(footer);
    // A click on the backdrop lands on the dialog element itself -- but so does the end of a
    // drag that began inside it, and a press that began inside it is not a click outside.
    var pressedOutside = false;
    dialog.addEventListener("pointerdown", function (event) {
      pressedOutside = event.target === dialog && outside(dialog, event);
    });
    dialog.addEventListener("click", function (event) {
      if (pressedOutside && event.target === dialog && outside(dialog, event)) dialog.close();
      pressedOutside = false;
    });
    // Escape closes the dialog by itself; what closing means is the close event's to say.
    return { dialog: dialog, body: body, footer: footer };
  }

  function outside(dialog, event) {
    var box = dialog.getBoundingClientRect();
    return event.clientX < box.left || event.clientX > box.right ||
           event.clientY < box.top || event.clientY > box.bottom;
  }

  function button(text, className, onClick) {
    var b = el("button", { type: "button", class: className || "", text: text });
    b.addEventListener("click", onClick);
    return b;
  }

  function settingsDialog() {
    var snapshot = "{}";
    var done = false;
    var frame = dialogFrame("os-settings", "Settings", "Cancel");

    // However the dialog closes -- ×, Cancel, Escape, a click outside -- the settings go back
    // to what they were when it opened, unless the reader said Done.
    frame.dialog.addEventListener("close", function () {
      if (done) {
        saveSettings(reader);
      } else {
        reader = JSON.parse(snapshot);
        changed();
      }
    });

    var body = frame.body;
    body.appendChild(el("p", { class: "os-note", text:
      "Choose what applies, and the book shows what you say. A passage that depends on " +
      "something not set is shown with the instruction for when to say it, as in the " +
      "printed book." }));

    if (book.basic && book.basic.length) {
      var basic = el("div", { class: "os-basic" });
      book.basic.forEach(function (entry) {
        if (entry.type === "control") {
          basic.appendChild(compositeControl(entry));
        } else {
          var feature = features[entry.fs + "\u0000" + entry.name];
          if (feature) basic.appendChild(featureControl(feature, featureLabel(feature)));
        }
      });
      body.appendChild(basic);
    }

    var advanced = el("details", { class: "os-advanced" }, [
      el("summary", { text: "Advanced: set each feature" })]);
    var groups = {};
    book.features.forEach(function (feature) {
      (groups[feature.fs] = groups[feature.fs] || []).push(feature);
    });
    Object.keys(groups).sort().forEach(function (fs) {
      var fieldset = el("fieldset", {}, [el("legend", { text: words(fs) })]);
      groups[fs].forEach(function (feature) {
        fieldset.appendChild(featureControl(feature, featureLabel(feature)));
      });
      advanced.appendChild(fieldset);
    });
    body.appendChild(advanced);

    if (book.calendarScopes) {
      body.appendChild(el("p", { class: "os-note", text:
        book.calendarScopes + " passages depend on the day, the time or the place. Set them " +
        "here, by hand: this edition cannot yet read them from your device, nor work out one " +
        "from another. A Hebrew date does not say what kind of day it is: set that too." }));
    }

    frame.footer.appendChild(button("Clear all", "os-clear", function () {
      reader = {};
      changed();
    }));
    frame.footer.appendChild(el("span", { class: "os-spacer" }));
    frame.footer.appendChild(button("Cancel", "", function () { frame.dialog.close(); }));
    frame.footer.appendChild(button("Done", "os-primary", function () {
      done = true;
      frame.dialog.close();
    }));

    frame.open = function () {
      snapshot = JSON.stringify(reader);
      done = false;
      refreshers.forEach(function (refresh) { refresh(); });
      frame.dialog.showModal();
    };
    return frame;
  }

  function contentsDialog() {
    var frame = dialogFrame("os-contents", "Contents", "Close");
    var list = el("ol", { class: "os-contents" });
    var headings = document.querySelectorAll(".os-book h1, .os-book h2, .os-book h3");
    var shown = OSCond.sectionsShown(book, OSCond.scopeCss(book, reader, book.defaults).states);
    Array.prototype.forEach.call(headings, function (heading, index) {
      if (heading.closest(".col-parallel")) return;  // a translated heading repeats its row's
      if (!heading.getClientRects().length) return;  // in a passage the settings hide
      // A section none of whose text will show, though its heading does.
      if (heading.dataset.section !== undefined && !shown[Number(heading.dataset.section)]) return;
      if (!heading.id) heading.id = "os-heading-" + index;
      var link = el("a", { href: "#" + heading.id, text: heading.textContent.trim() });
      link.addEventListener("click", function () { frame.dialog.close(); });
      list.appendChild(el("li", { class: "os-contents-" + heading.tagName.toLowerCase() }, [link]));
    });
    frame.body.appendChild(list);
    frame.footer.appendChild(el("span", { class: "os-spacer" }));
    frame.footer.appendChild(button("Close", "os-primary", function () { frame.dialog.close(); }));
    return frame;
  }

  // ── Start ──────────────────────────────────────────────────────────────

  apply();

  var settings = settingsDialog();
  document.body.appendChild(settings.dialog);
  var toolbar = document.querySelector(".os-toolbar");
  toolbar.hidden = false;
  document.getElementById("os-open-settings").addEventListener("click", settings.open);
  // Built afresh each time: which headings are shown depends on the settings.
  document.getElementById("os-open-contents").addEventListener("click", function () {
    var old = document.getElementById("os-contents");
    if (old) old.remove();
    var contents = contentsDialog();
    document.body.appendChild(contents.dialog);
    contents.dialog.showModal();
  });

  // Passages shown or hidden above may have moved a linked one: go to it again.
  if (location.hash) {
    var id = location.hash.slice(1);
    try { id = decodeURIComponent(id); } catch (e) { /* use it as it is */ }
    var target = document.getElementById(id);
    if (target) target.scrollIntoView();
  }
})();
