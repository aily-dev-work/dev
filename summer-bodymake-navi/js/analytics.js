/**
 * Google Analytics 4（site-config.js の測定IDが設定されている場合のみ読み込み）
 */
(function () {
  "use strict";

  if (typeof window.gtag === "function") {
    return;
  }

  if (document.querySelector('script[src*="googletagmanager.com/gtag/js"]')) {
    return;
  }

  var config = window.SITE_CONFIG || {};
  var measurementId = config.ga4MeasurementId;

  if (!measurementId || measurementId.indexOf("G-") !== 0) {
    return;
  }

  var script = document.createElement("script");
  script.async = true;
  script.src = "https://www.googletagmanager.com/gtag/js?id=" + measurementId;
  document.head.appendChild(script);

  window.dataLayer = window.dataLayer || [];
  function gtag() {
    window.dataLayer.push(arguments);
  }
  window.gtag = gtag;
  gtag("js", new Date());
  gtag("config", measurementId, { anonymize_ip: true });
})();
