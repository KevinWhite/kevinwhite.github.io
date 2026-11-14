(function () {
  "use strict";
  var KEY = "clubpit.mode";
  var root = document.documentElement;
  var meta = document.querySelector('meta[name="theme-color"]');
  var status = document.getElementById("mode-status");
  var COLOURS = { outie: "#000000", innie: "#0b0c0c" };
  var NAMES = { outie: "Outie mode: the personal page.", innie: "Innie mode: the work page." };
  var video = document.querySelector(".banner-video");

  /* ---- Innie "Experience: N years": build.py writes N at build time; recompute so it rolls over each anniversary ---- */
  var spans = document.querySelectorAll("[data-years-since]");
  for (var s = 0; s < spans.length; s++) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(spans[s].getAttribute("data-years-since"));
    if (!m) continue;
    var now = new Date(), y = now.getFullYear() - Number(m[1]);
    if (now.getMonth() + 1 < Number(m[2]) || (now.getMonth() + 1 === Number(m[2]) && now.getDate() < Number(m[3]))) y--;
    spans[s].textContent = String(y);
  }

  /* ---- Outie / Innie switch (two aria-pressed buttons; class on <html> picks the content and style) ---- */
  var buttons = document.querySelectorAll("[data-mode-choice]");

  function apply(mode, announce) {
    root.classList.remove("mode-outie", "mode-innie");
    root.classList.add("mode-" + mode);
    for (var i = 0; i < buttons.length; i++) {
      var b = buttons[i];
      b.setAttribute("aria-pressed", String(b.getAttribute("data-mode-choice") === mode));
    }
    if (meta && COLOURS[mode]) meta.setAttribute("content", COLOURS[mode]);
    if (announce && status) status.textContent = NAMES[mode];
    if (mode === "innie" && video && !video.paused) video.pause(); /* the banner is outie-only */
  }

  for (var i = 0; i < buttons.length; i++) {
    buttons[i].addEventListener("click", function (ev) {
      var mode = ev.currentTarget.getAttribute("data-mode-choice");
      apply(mode, true);
      try { localStorage.setItem(KEY, mode); } catch (e) { /* not remembered, still applied */ }
    });
  }
  apply(root.classList.contains("mode-innie") ? "innie" : "outie", false);

  /* ---- Banner: play once, pausable (WCAG 2.2.2), still image for reduced motion ---- */
  var btn = document.querySelector(".banner-btn");
  if (!video || !btn) return;

  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)");

  function stillOnly() {
    video.pause();
    video.removeAttribute("autoplay");
    root.classList.add("banner-static");
    btn.hidden = true;
  }
  if (reduce && reduce.matches) { stillOnly(); return; }
  if (reduce && reduce.addEventListener) {
    reduce.addEventListener("change", function (e) { if (e.matches) stillOnly(); });
  }

  function label() {
    btn.textContent = video.ended ? "Smash it again" : (video.paused ? "Play animation" : "Pause animation");
  }
  btn.hidden = false;
  /* Never play behind the innie page (it is hidden there); outie can play it from the button. */
  video.addEventListener("play", function () { if (root.classList.contains("mode-innie")) video.pause(); });
  btn.addEventListener("click", function () {
    if (video.ended) { video.currentTime = 0; video.play(); }
    else if (video.paused) { video.play(); }
    else { video.pause(); }
  });
  ["play", "pause", "ended"].forEach(function (ev) { video.addEventListener(ev, label); });
  label();
})();
