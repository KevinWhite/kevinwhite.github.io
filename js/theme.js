/* Runs in <head> (blocking, tiny) so the saved theme applies before first paint. */
(function () {
  var KEY = "clubpit.theme";
  var THEMES = ["terminal", "neon"];
  var saved = null;
  try { saved = localStorage.getItem(KEY); } catch (e) { /* storage blocked: use default */ }
  if (THEMES.indexOf(saved) !== -1) {
    document.documentElement.setAttribute("data-theme", saved);
  }
})();
