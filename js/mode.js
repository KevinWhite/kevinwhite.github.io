/* Runs in <head> (blocking, tiny) so the saved mode applies before first paint.
   "js" lets CSS show the Outie/Innie switch; without JavaScript the page is outie only. */
(function () {
  var KEY = "clubpit.mode";
  var root = document.documentElement;
  var mode = "outie";
  try { if (localStorage.getItem(KEY) === "innie") mode = "innie"; } catch (e) { /* storage blocked: default */ }
  root.classList.add("js", "mode-" + mode);
})();
