// Subscribe form for Canvass And Analyze. Any element with class "subscribe-form" becomes a form.
// The Worker URL and Turnstile site key come from data attributes added at build time
// (scripts/subscribe_box.py, from subscribe/site.json).
(function () {
  var boxes = document.querySelectorAll(".subscribe-form[data-endpoint]");
  if (!boxes.length) return;

  function loadTurnstile(cb) {
    if (window.turnstile) return cb();
    var s = document.createElement("script");
    s.src = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";
    s.async = true;
    s.onload = cb;
    document.head.appendChild(s);
  }

  boxes.forEach(function (box) {
    var endpoint = box.dataset.endpoint, sitekey = box.dataset.sitekey;
    box.innerHTML =
      '<form class="sub-form" novalidate>' +
      '  <label class="sub-label" for="sub-' + Math.random().toString(36).slice(2, 8) + '">Email address</label>' +
      '  <div class="sub-row">' +
      '    <input class="sub-email" type="email" name="email" placeholder="you@example.com" autocomplete="email" required>' +
      '    <button class="sub-button" type="submit">Subscribe</button>' +
      '  </div>' +
      '  <div class="sub-check"></div>' +
      '  <p class="sub-msg" role="status" aria-live="polite"></p>' +
      '  <p class="sub-note">One email when something new is published. Unsubscribe anytime.</p>' +
      '</form>';
    var form = box.querySelector("form"), input = box.querySelector(".sub-email"),
        button = box.querySelector(".sub-button"), msg = box.querySelector(".sub-msg"),
        check = box.querySelector(".sub-check"), label = box.querySelector(".sub-label");
    label.htmlFor = input.id = label.getAttribute("for");
    var widget = null, token = "";

    function ensureWidget() {
      if (widget !== null || !sitekey) return;
      widget = "loading";
      loadTurnstile(function () {
        widget = window.turnstile.render(check, {
          sitekey: sitekey, size: "flexible", appearance: "interaction-only",
          callback: function (t) { token = t; },
          "expired-callback": function () { token = ""; }
        });
      });
    }
    input.addEventListener("focus", ensureWidget);      // only load the check when someone starts subscribing

    function say(text, kind) { msg.textContent = text; msg.className = "sub-msg " + (kind || ""); }

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      ensureWidget();
      var email = input.value.trim();
      if (!/^\S+@\S+\.\S+$/.test(email)) return say("Please enter a valid email address.", "error");
      var tries = 0;
      (function waitForCheck() {                         // the invisible check usually finishes in a second
        if (!token && sitekey && tries++ < 20) return setTimeout(waitForCheck, 250);
        button.disabled = true; say("Subscribing…");
        fetch(endpoint + "/subscribe", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: email, turnstile: token })
        }).then(function (r) { return r.json(); }).then(function (d) {
          if (d.ok) { form.classList.add("done"); say(d.message, "ok"); }
          else { say(d.error || "Something went wrong. Please try again.", "error"); button.disabled = false; }
        }).catch(function () {
          say("Couldn't reach the server. Please try again in a moment.", "error"); button.disabled = false;
        }).finally(function () {
          token = ""; if (window.turnstile && widget && widget !== "loading") window.turnstile.reset(widget);
        });
      })();
    });
  });
})();
