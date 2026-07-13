/**
 * メンズ男磨きナビ — 共通スクリプト
 * モバイルナビ（a11y）、お問い合わせフォーム、解析の初期化
 */
(function () {
  "use strict";

  initMobileNav();
  initContactForm();

  function initMobileNav() {
    var toggle = document.getElementById("nav-toggle");
    var label = document.querySelector(".nav-toggle-label");
    var nav = document.getElementById("site-nav") || document.querySelector(".site-nav");

    if (!toggle || !label) {
      return;
    }

    if (nav && !nav.id) {
      nav.id = "site-nav";
    }

    label.setAttribute("aria-controls", nav ? nav.id : "site-nav");

    function updateNavState() {
      var open = toggle.checked;
      label.setAttribute("aria-expanded", open ? "true" : "false");
      label.setAttribute("aria-label", open ? "メニューを閉じる" : "メニューを開く");
    }

    toggle.addEventListener("change", updateNavState);
    updateNavState();
  }

  function initContactForm() {
    var form = document.getElementById("contact-form");
    if (!form) {
      return;
    }

    var config = window.SITE_CONFIG || {};
    if (config.formsubmitEmail) {
      form.setAttribute("action", "https://formsubmit.co/" + config.formsubmitEmail);
    }

    var submitBtn = document.getElementById("contact-submit");
    var feedback = document.getElementById("form-message");
    var action = form.getAttribute("action") || "";
    var endpoint = action.replace("https://formsubmit.co/", "https://formsubmit.co/ajax/");

    function showFeedback(text, isError) {
      if (!feedback) {
        return;
      }
      feedback.hidden = false;
      feedback.textContent = text;
      feedback.className =
        "form-feedback" + (isError ? " form-feedback--error" : " form-feedback--success");
    }

    function setSubmitting(isSubmitting) {
      if (!submitBtn) {
        return;
      }
      submitBtn.disabled = isSubmitting;
      submitBtn.textContent = isSubmitting ? "送信中…" : "送信する";
    }

    form.addEventListener("submit", function (e) {
      var honeypot = form.querySelector("[name='_honey']");
      if (honeypot && honeypot.value) {
        e.preventDefault();
        return;
      }

      if (!form.checkValidity()) {
        e.preventDefault();
        form.reportValidity();
        return;
      }

      if (!window.fetch || !endpoint) {
        return;
      }

      e.preventDefault();
      setSubmitting(true);
      if (feedback) {
        feedback.hidden = true;
      }

      fetch(endpoint, {
        method: "POST",
        body: new FormData(form),
        headers: { Accept: "application/json" },
      })
        .then(function (res) {
          if (!res.ok) {
            throw new Error("send failed");
          }
          window.location.href = "contact-thanks.html";
        })
        .catch(function () {
          setSubmitting(false);
          showFeedback("送信に失敗しました。時間をおいて再度お試しください。", true);
        });
    });
  }
})();
