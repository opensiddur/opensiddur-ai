/*
 * Condition evaluation for an Open Siddur electronic book, on the reader's device.
 *
 * A port of the compiler's evaluator (opensiddur/exporter/condition_eval.py) and of the
 * client settings it is resolved against (opensiddur/exporter/client_settings.py). The two
 * must agree: the agreement tests run the same cases through both. Conditions and settings
 * arrive as JSON, in the shapes condition_eval.py documents.
 *
 * Three-valued throughout. A result is one of the strings "true", "false" and "undefined",
 * never a JavaScript boolean: undefined is not falsy here. A condition that cannot be decided
 * keeps its text, with the rubric that says when to read it -- exactly as a printed book does.
 *
 * No DOM access: the page script (reader.js) applies the results.
 */
(function (root) {
  "use strict";

  var TRUE = "true";
  var FALSE = "false";
  var UNDEFINED = "undefined";

  function isObject(value) {
    return value !== null && typeof value === "object";
  }

  // ── Combinators (condition_eval._combine_*) ──────────────────────────────

  function combineAll(results) {
    if (results.every(function (r) { return r === TRUE; })) return TRUE;
    // A false conjunct settles the conjunction, whatever else is unknown.
    if (results.indexOf(FALSE) >= 0) return FALSE;
    return UNDEFINED;
  }

  function combineAny(results) {
    if (results.length === 0) return FALSE;
    if (results.indexOf(TRUE) >= 0) return TRUE;
    if (results.indexOf(UNDEFINED) >= 0) return UNDEFINED;
    return FALSE;
  }

  function combineOne(results) {
    if (results.length === 0) return FALSE;
    var trues = results.filter(function (r) { return r === TRUE; }).length;
    if (trues > 1) return FALSE;
    if (results.indexOf(UNDEFINED) >= 0) return UNDEFINED;
    return trues === 1 ? TRUE : FALSE;
  }

  function combineNone(results) {
    if (results.indexOf(TRUE) >= 0) return FALSE;
    if (results.indexOf(UNDEFINED) >= 0) return UNDEFINED;
    return TRUE;
  }

  var COMBINATORS = { all: combineAll, any: combineAny, one: combineOne, none: combineNone };

  function combine(op, results) {
    var combinator = COMBINATORS[op];
    if (!combinator) throw new Error("Unknown combinator " + op);
    return combinator(results);
  }

  // ── Matching one value (condition_eval._single_value_match) ──────────────

  // Python equality between an active setting and a binary or string condition: True == 1,
  // and a tei:numeric setting equals neither.
  function pyEqual(active, wanted) {
    if (isObject(active)) return false;
    if (typeof wanted === "boolean") {
      if (typeof active === "boolean") return active === wanted;
      if (typeof active === "number") return active === (wanted ? 1 : 0);
      return false;
    }
    return active === wanted;
  }

  function match(active, wanted) {
    if (active === null || active === undefined) return UNDEFINED;
    if (isObject(wanted) && wanted.undefined === true) return UNDEFINED;
    if (isObject(wanted) && "not" in wanted) {
      var inner = match(active, wanted.not);
      if (inner === UNDEFINED) return UNDEFINED;
      return inner === TRUE ? FALSE : TRUE;
    }
    if (isObject(wanted) && "alt" in wanted) {
      return combineAny(wanted.alt.map(function (alt) { return match(active, alt); }));
    }
    if (isObject(wanted) && "num" in wanted) {
      var number = isObject(active) ? active.num : active;
      if (typeof number === "boolean") number = number ? 1 : 0;
      if (typeof number !== "number") return FALSE;
      if (wanted.max !== undefined && wanted.max !== null) {
        return wanted.num <= number && number <= wanted.max ? TRUE : FALSE;
      }
      return number === wanted.num ? TRUE : FALSE;
    }
    return pyEqual(active, wanted) ? TRUE : FALSE;
  }

  // ── Settings (client_settings.ClientSettings) ────────────────────────────

  function lookup(settings, fsType, feature) {
    var features = settings && settings[fsType];
    if (!features || !Object.prototype.hasOwnProperty.call(features, feature)) {
      return { present: false };
    }
    return { present: true, value: features[feature] };
  }

  // Python's truthiness, which SettingSnapshot.get_bool applies.
  function truthy(value) {
    return !(value === false || value === 0 || value === "");
  }

  // Derivations whose every input is the reader's, as client_settings.CLIENT_DERIVATIONS.
  // Each takes a getter returning an active value or null, and returns the features it
  // derives, or null when it cannot run.
  var DERIVATIONS = {
    // calendar/compute.compute_quorum: ten adults are also three.
    "opensiddur:quorum": function (get) {
      var minyan = get("opensiddur:quorum", "minyan");
      if (minyan === null || !truthy(minyan)) return null;
      return { zimmun: true };
    }
  };

  function Settings(pinned, reader, defaults) {
    this.pinned = pinned || {};
    this.reader = reader || {};
    this.defaults = defaults || {};
  }

  Settings.prototype.explicit = function (fsType, feature) {
    var found = lookup(this.pinned, fsType, feature);
    if (found.present) return found;
    found = lookup(this.reader, fsType, feature);
    if (found.present && found.value !== null) return found;
    return lookup(this.defaults, fsType, feature);
  };

  Settings.prototype.derived = function (fsType, feature) {
    var derive = DERIVATIONS[fsType];
    if (!derive) return { present: false };
    var self = this;
    var computed = derive(function (fs, name) {
      var found = self.explicit(fs, name);
      return found.present && found.value !== null ? found.value : null;
    }) || {};
    if (Object.prototype.hasOwnProperty.call(computed, feature)) {
      return { present: true, value: computed[feature] };
    }
    return { present: false };
  };

  // The active value of a feature, or null when it is undefined or unset.
  Settings.prototype.get = function (fsType, feature) {
    var found = this.explicit(fsType, feature);
    if (!found.present) found = this.derived(fsType, feature);
    return found.present ? found.value : null;
  };

  // ── Evaluation (condition_eval.evaluate_condition) ───────────────────────

  function evaluate(condition, settings) {
    if ("fs" in condition) {
      return combineAll(condition.f.map(function (f) {
        return match(settings.get(condition.fs, f.name), f.v);
      }));
    }
    return combine(condition.op, condition.args.map(function (child) {
      return evaluate(child, settings);
    }));
  }

  function resolve(condition, pinned, reader, defaults) {
    return evaluate(condition, new Settings(pinned, reader, defaults));
  }

  // ── The book's conditions as CSS ─────────────────────────────────────────
  //
  // book.expressions: [{cond, pinned}], book.scopes: the expression of each scope by its
  // number. A scope that does not hold hides what it governs (class c<n>) and its markers
  // (m<n>); one that holds keeps its rubric and drops its brackets and rules; an undecided
  // one shows everything. html.py writes the same rules, for a page read without scripts.

  function scopeCss(book, reader, defaults) {
    var states = book.expressions.map(function (e) {
      return resolve(e.cond, e.pinned, reader, defaults);
    });
    var hidden = [];
    var settled = [];
    book.scopes.forEach(function (expression, cid) {
      var state = states[expression];
      if (state === FALSE) {
        hidden.push(".c" + cid, ".m" + cid);
      } else if (state === TRUE) {
        settled.push(".m" + cid + ".cm-close", ".m" + cid + ".cm-norubric",
                     ".m" + cid + " .cm-br");
      }
    });
    var css = "";
    if (hidden.length) css += hidden.join(",") + "{display:none}\n";
    if (settled.length) css += settled.join(",") + "{display:none}\n";
    return { css: css, states: states };
  }

  root.OSCond = {
    TRUE: TRUE,
    FALSE: FALSE,
    UNDEFINED: UNDEFINED,
    combine: combine,
    match: match,
    evaluate: evaluate,
    resolve: resolve,
    Settings: Settings,
    DERIVATIONS: DERIVATIONS,
    scopeCss: scopeCss
  };
})(typeof globalThis !== "undefined" ? globalThis : this);
