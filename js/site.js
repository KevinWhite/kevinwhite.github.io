(function () {
  "use strict";
  var KEY = "clubpit.theme";
  var root = document.documentElement;
  var meta = document.querySelector('meta[name="theme-color"]');
  var COLOURS = { terminal: "#000000", neon: "#12041f" };

  /* ---- Theme toggle ---- */
  var buttons = document.querySelectorAll("[data-theme-choice]");

  function apply(theme) {
    root.setAttribute("data-theme", theme);
    for (var i = 0; i < buttons.length; i++) {
      var b = buttons[i];
      b.setAttribute("aria-pressed", String(b.getAttribute("data-theme-choice") === theme));
    }
    if (meta && COLOURS[theme]) meta.setAttribute("content", COLOURS[theme]);
  }

  for (var i = 0; i < buttons.length; i++) {
    buttons[i].addEventListener("click", function (ev) {
      var theme = ev.currentTarget.getAttribute("data-theme-choice");
      apply(theme);
      try { localStorage.setItem(KEY, theme); } catch (e) { /* not remembered, still applied */ }
    });
  }
  apply(root.getAttribute("data-theme") || "terminal");

  /* ---- "KB-AI says": the build renders one line; swap in a random one per visit ---- */
  var rot = document.querySelectorAll("[data-rotate]");
  for (var r = 0; r < rot.length; r++) {
    try {
      var lines = JSON.parse(rot[r].getAttribute("data-rotate"));
      if (lines.length) rot[r].textContent = lines[Math.floor(Math.random() * lines.length)];
    } catch (e) { /* keep the build-time line */ }
  }

  /* ---- Banner: play once, pausable (WCAG 2.2.2), still image for reduced motion ---- */
  var video = document.querySelector(".banner-video");
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
  btn.addEventListener("click", function () {
    if (video.ended) { video.currentTime = 0; video.play(); }
    else if (video.paused) { video.play(); }
    else { video.pause(); }
  });
  ["play", "pause", "ended"].forEach(function (ev) { video.addEventListener(ev, label); });
  label();
})();
