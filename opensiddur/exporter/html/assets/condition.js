/*
 * Condition evaluation for an Open Siddur electronic book, on the reader's device.
 *
 * A port of the compiler's evaluator (opensiddur/exporter/condition_eval.py) and of the
 * client settings it is resolved against (opensiddur/exporter/client_settings.py). The two
 * must agree: the agreement tests run the same cases through both. Conditions and settings
 * arrive as JSON, in the shapes condition_eval.py documents. The settings are derived by
 * calendar.js (OSCal), which is loaded first.
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

  // Python equality for what match() leaves to it: a string condition, or a binary one
  // against a setting that is neither a boolean nor a number.
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
    if (typeof wanted === "boolean") {
      // condition_eval._single_value_match: a binary condition asks whether a value is
      // true — 0 and false are false, any other number true.
      var value = isObject(active) && "num" in active ? active.num : active;
      if (typeof value === "boolean" || typeof value === "number") {
        return (value !== 0 && value !== false) === wanted ? TRUE : FALSE;
      }
    }
    return pyEqual(active, wanted) ? TRUE : FALSE;
  }

  // ── Settings (client_settings.derive_settings) ──────────────────────────
  //
  // The layers, the earliest first, each {fs type: {feature: value}}: what the device knows
  // by itself (its clock), the book's defaults, the reader's settings, and what the compile
  // pinned where the condition stands. A later layer prevails. The calendar's derivations run
  // over them all, as a compile runs them over its declarations.

  function layerEntries(layer, source, out) {
    Object.keys(layer || {}).forEach(function (fsType) {
      Object.keys(layer[fsType]).forEach(function (feature) {
        out.push({ fs: fsType, feature: feature, value: layer[fsType][feature], source: source });
      });
    });
    return out;
  }

  function baseEntries(reader, defaults, device) {
    var entries = layerEntries(device, "init", []);
    layerEntries(defaults, "init", entries);
    return layerEntries(reader, "declared", entries);
  }

  // Whether pinned values can change what is derived: only a value a derivation reads can.
  // The rest are laid over what the other layers derive, which comes to the same thing.
  function readByDerivations(pinned) {
    return Object.keys(pinned).some(function (fsType) {
      var read = OSCal.READ_FEATURES[fsType];
      return read && Object.keys(pinned[fsType]).some(function (f) { return read.indexOf(f) >= 0; });
    });
  }

  // The settings in force for each pinned set, under one set of reader, default and device
  // settings: derived once for everything that pins nothing the derivations read.
  function Resolver(reader, defaults, device) {
    this.base = baseEntries(reader, defaults, device);
    this.baseSettings = null;
    this.cache = {};
  }

  Resolver.prototype.settings = function (pinned) {
    if (this.baseSettings === null) this.baseSettings = OSCal.derive(this.base);
    if (!pinned || !Object.keys(pinned).length) return this.baseSettings;
    var key = JSON.stringify(pinned);
    if (Object.prototype.hasOwnProperty.call(this.cache, key)) return this.cache[key];
    var settings;
    if (readByDerivations(pinned)) {
      settings = OSCal.derive(layerEntries(pinned, "declared", this.base.slice()));
    } else {
      settings = {};
      var base = this.baseSettings;
      Object.keys(base).forEach(function (fsType) { settings[fsType] = base[fsType]; });
      Object.keys(pinned).forEach(function (fsType) {
        var merged = {};
        Object.keys(base[fsType] || {}).forEach(function (f) { merged[f] = base[fsType][f]; });
        Object.keys(pinned[fsType]).forEach(function (f) { merged[f] = pinned[fsType][f]; });
        settings[fsType] = merged;
      });
    }
    this.cache[key] = settings;
    return settings;
  };

  // The active value of a feature, or null when it is undefined or unset.
  function active(settings, fsType, feature) {
    var features = settings[fsType];
    if (!features || !Object.prototype.hasOwnProperty.call(features, feature)) return null;
    return features[feature];
  }

  // ── Evaluation (condition_eval.evaluate_condition) ───────────────────────

  function isTwilight(value) {
    return isObject(value) && "twilight" in value;
  }

  function conditionFeatures(condition, out) {
    if ("fs" in condition) {
      condition.f.forEach(function (f) { out.push([condition.fs, f.name]); });
    } else {
      condition.args.forEach(function (child) { conditionFeatures(child, out); });
    }
    return out;
  }

  function evaluateOn(condition, get) {
    if ("fs" in condition) {
      return combineAll(condition.f.map(function (f) {
        return match(get(condition.fs, f.name), f.v);
      }));
    }
    return combine(condition.op, condition.args.map(function (child) {
      return evaluateOn(child, get);
    }));
  }

  // Between sunset and nightfall a setting may hold its value on each of two days. The
  // condition is then decided only if it comes out the same on both.
  function evaluate(condition, settings) {
    var get = function (fsType, feature) { return active(settings, fsType, feature); };
    var twilight = conditionFeatures(condition, []).some(function (ref) {
      return isTwilight(get(ref[0], ref[1]));
    });
    if (!twilight) return evaluateOn(condition, get);
    var onDay = function (day) {
      return function (fsType, feature) {
        var value = get(fsType, feature);
        return isTwilight(value) ? value.twilight[day] : value;
      };
    };
    var ending = evaluateOn(condition, onDay(0));
    var starting = evaluateOn(condition, onDay(1));
    return ending === starting ? ending : UNDEFINED;
  }

  // client_settings.resolve: a value pinned for bein hashmashot holds one value for each of
  // the two days, and the condition is decided only if it comes out the same on both.
  function pinnedOnDay(pinned, day) {
    var out = {};
    Object.keys(pinned || {}).forEach(function (fsType) {
      out[fsType] = {};
      Object.keys(pinned[fsType]).forEach(function (name) {
        var value = pinned[fsType][name];
        out[fsType][name] = isTwilight(value) ? value.twilight[day] : value;
      });
    });
    return out;
  }

  function hasTwilight(pinned) {
    return Object.keys(pinned || {}).some(function (fsType) {
      return Object.keys(pinned[fsType]).some(function (name) {
        return isTwilight(pinned[fsType][name]);
      });
    });
  }

  function resolveWith(resolver, condition, pinned) {
    if (hasTwilight(pinned)) {
      var ending = evaluate(condition, resolver.settings(pinnedOnDay(pinned, 0)));
      var starting = evaluate(condition, resolver.settings(pinnedOnDay(pinned, 1)));
      return ending === starting ? ending : UNDEFINED;
    }
    return evaluate(condition, resolver.settings(pinned));
  }

  function resolve(condition, pinned, reader, defaults, device) {
    return resolveWith(new Resolver(reader, defaults, device), condition, pinned);
  }

  // ── The book's conditions as CSS ─────────────────────────────────────────
  //
  // book.expressions: [{cond, pinned}], book.scopes: the expression of each scope by its
  // number. A scope that does not hold hides what it governs (class c<n>) and its markers
  // (m<n>); one that holds drops the rubric that said when to read it, its rules and its
  // brackets, keeping any commentary anchored there; an undecided one shows everything. html.py writes the same rules, for a page read without scripts.

  function scopeCss(book, reader, defaults, device) {
    var resolver = new Resolver(reader, defaults, device);
    var states = book.expressions.map(function (e) {
      return resolveWith(resolver, e.cond, e.pinned);
    });
    var hidden = [];
    var settled = [];
    book.scopes.forEach(function (expression, cid) {
      var state = states[expression];
      if (state === FALSE) {
        hidden.push(".c" + cid, ".m" + cid);
      } else if (state === TRUE) {
        settled.push(".m" + cid + ".cm-close", ".m" + cid + " > .rubric",
                     ".m" + cid + " .cm-br");
      }
    });
    // A row none of whose text shows goes whole, so that off screen it is no row's height.
    (book.rows || []).forEach(function (sets, number) {
      var shows = sets.some(function (set) {
        return set.every(function (cid) { return states[book.scopes[cid]] !== FALSE; });
      });
      if (!shows) hidden.push(".r" + number);
    });
    // An optional page reference goes when every occurrence of one of its destinations does.
    (book.optionalReferences || []).forEach(function (destinations, number) {
      var reachable = destinations.every(function (occurrences) {
        return occurrences.some(function (set) {
          return set.every(function (cid) { return states[book.scopes[cid]] !== FALSE; });
        });
      });
      if (!reachable) hidden.push(".oref" + number);
    });
    var css = "";
    if (hidden.length) css += hidden.join(",") + "{display:none}\n";
    if (settled.length) css += settled.join(",") + "{display:none}\n";
    return { css: css, states: states, resolver: resolver };
  }

  // Whether each section of the book has text that shows, given the expressions' states:
  // book.sections[i] is null when some of its text is governed by no scope, or else the sets
  // of scopes its runs of text turn on -- it shows if one set has no scope that is false.
  function sectionsShown(book, states) {
    return (book.sections || []).map(function (sets) {
      return sets === null || sets.some(function (set) {
        return set.every(function (cid) { return states[book.scopes[cid]] !== FALSE; });
      });
    });
  }

  root.OSCond = {
    TRUE: TRUE,
    FALSE: FALSE,
    UNDEFINED: UNDEFINED,
    combine: combine,
    match: match,
    evaluate: evaluate,
    resolve: resolve,
    Resolver: Resolver,
    scopeCss: scopeCss,
    sectionsShown: sectionsShown
  };
})(typeof globalThis !== "undefined" ? globalThis : this);
