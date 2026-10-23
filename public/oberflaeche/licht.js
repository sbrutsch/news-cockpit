/* Oberflächen-Standard · licht.js
   Optionales Verhalten, keine Abhängigkeiten, als eigene Datei oder inline nutzbar.
   - Zeigerlicht: Glanzfleck folgt der Maus auf .glass und .spotlight (setzt --gx/--gy)
   - Kippen: Elemente mit [data-tilt] neigen sich bis ca. 5° zur Maus (setzt --rx/--ry)
   - Design: [data-theme-set="system|light|dark"] und [data-theme-toggle], gemerkt in localStorage
   Zeigerlicht und Kippen laufen nur mit Maus/Trackpad, Kippen nie bei "Bewegung reduzieren".
   Quelle der Wahrheit: skills-bibliothek/claude-code-global/oberflaechen-standard/assets/ */
(() => {
  const root = document.documentElement;
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch {} }
  };
  // Wechsel mit View Transition, wo verfügbar
  const swap = fn => (document.startViewTransition ? document.startViewTransition(fn) : fn());

  // ---- Design: System / Hell / Dunkel ----
  const applyTheme = t => {
    t === "system" ? root.removeAttribute("data-theme") : root.setAttribute("data-theme", t);
    store.set("theme", t);
  };
  applyTheme(store.get("theme") || "system");
  addEventListener("click", e => {
    const set = e.target.closest?.("[data-theme-set]");
    if (set) swap(() => applyTheme(set.dataset.themeSet));
    if (e.target.closest?.("[data-theme-toggle]")) {
      const now = root.dataset.theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
      swap(() => applyTheme(now === "dark" ? "light" : "dark"));
    }
  });

  // ---- Zeigerlicht + Kippen: ein Frame pro Bildschirmaktualisierung ----
  const fine = matchMedia("(hover: hover) and (pointer: fine)");
  const still = matchMedia("(prefers-reduced-motion: reduce)");
  if (!fine.matches) return;
  let lit = null, tilt = null, ev = null, queued = false;
  const unlight = () => { lit?.style.removeProperty("--gx"); lit?.style.removeProperty("--gy"); lit = null; };
  const untilt = () => {
    if (!tilt) return;
    tilt.classList.remove("is-tilting");
    tilt.style.removeProperty("--rx"); tilt.style.removeProperty("--ry");
    tilt = null;
  };
  const frame = () => {
    queued = false;
    if (!ev) return;
    const host = ev.target.closest?.(".glass, .spotlight") ?? null;
    if (host !== lit) { unlight(); lit = host; }
    if (lit) {
      const r = lit.getBoundingClientRect();
      lit.style.setProperty("--gx", `${(ev.clientX - r.left) | 0}px`);
      lit.style.setProperty("--gy", `${(ev.clientY - r.top) | 0}px`);
    }
    const t = still.matches ? null : ev.target.closest?.("[data-tilt]") ?? null;
    if (t !== tilt) { untilt(); tilt = t; }
    if (tilt) {
      const r = tilt.getBoundingClientRect();
      const x = (ev.clientX - r.left) / r.width - .5, y = (ev.clientY - r.top) / r.height - .5;
      tilt.classList.add("is-tilting");
      tilt.style.setProperty("--rx", `${(-y * 8).toFixed(2)}deg`);
      tilt.style.setProperty("--ry", `${(x * 10).toFixed(2)}deg`);
    }
  };
  addEventListener("pointermove", e => { ev = e; if (!queued) { queued = true; requestAnimationFrame(frame); } }, { passive: true });
  document.addEventListener("pointerleave", () => { ev = null; unlight(); untilt(); });
})();
