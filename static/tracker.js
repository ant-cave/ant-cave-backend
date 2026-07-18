/**
 * Ant Cave Analytics — Embeddable tracker script.
 *
 * Include in any HTML page:
 *   <script src="https://your-server.com/tracker.js" async></script>
 *
 * To override the API endpoint:
 *   <script>window._antTrackEndpoint = "https://custom-api.com/api/track";</script>
 *
 * To fire a manual page view (SPA navigation):
 *   window._antTrackPageView();
 */
(function () {
  "use strict";

  // Respect Do Not Track
  if (navigator.doNotTrack === "1") return;

  var endpoint =
    window._antTrackEndpoint ||
    (function () {
      var scripts = document.getElementsByTagName("script");
      var src = scripts[scripts.length - 1]?.src || "";
      if (!src) return "/api/track";
      var base = src.substring(0, src.lastIndexOf("/"));
      return base.replace(/\/+$/, "") + "/api/track";
    })();

  function collect() {
    return {
      page_url: window.location.href,
      referrer: document.referrer || "",
      screen_resolution: screen.width + "x" + screen.height,
      language: (navigator.language || navigator.userLanguage || "").substring(
        0,
        10
      ),
      title: document.title,
      user_agent: navigator.userAgent,
    };
  }

  function send(data) {
    try {
      var blob = new Blob([JSON.stringify(data)], {
        type: "application/json",
      });
      if (navigator.sendBeacon) {
        navigator.sendBeacon(endpoint, blob);
      } else {
        fetch(endpoint, {
          method: "POST",
          body: blob,
          keepalive: true,
          credentials: "omit",
          mode: "cors",
        }).catch(function () {});
      }
    } catch (e) {
      /* silent fail — tracking must never break the page */
    }
  }

  // Expose manual page view trigger for SPAs
  window._antTrackPageView = function () {
    send(collect());
  };

  // Send on initial page load
  if (document.readyState === "complete") {
    send(collect());
  } else {
    window.addEventListener("load", function () {
      send(collect());
    });
  }
})();
