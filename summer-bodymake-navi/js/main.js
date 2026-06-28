/**
 * メンズ男磨きナビ
 * 最小限のJavaScript（Lighthouseパフォーマンス重視）
 * ナビゲーションはCSSで制御。ここではお問い合わせフォームの静的フィードバックのみ。
 */
(function () {
  "use strict";

  var form = document.getElementById("contact-form");
  if (!form) return;

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var msg = document.getElementById("form-message");
    if (msg) {
      msg.hidden = false;
      msg.textContent = "送信機能はデモのため無効です。実際のお問い合わせはメールにてご連絡ください。";
    }
  });
})();
