// Apply the saved theme before the first paint, so dark-theme users never see a white flash.
// This is a separate file (not an inline script) so the Content Security Policy can allow
// scripts from our own origin only, with no exceptions for inline code.
(function () {
  try {
    var stored = localStorage.getItem("quantova-theme");
    var system = window.matchMedia("(prefers-color-scheme: dark)").matches;
    if (stored === "dark" || ((stored === null || stored === "system") && system)) {
      document.documentElement.classList.add("dark");
    }
  } catch (e) {
    // Storage unavailable: the theme provider falls back to the system theme.
  }
})();
