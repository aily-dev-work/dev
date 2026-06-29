/**
 * メンズ男磨きナビ
 * お問い合わせフォーム（FormSubmit 連携）
 */
(function () {
  "use strict";

  var form = document.getElementById("contact-form");
  if (!form) return;

  var submitBtn = document.getElementById("contact-submit");
  var feedback = document.getElementById("form-message");
  var endpoint = form.getAttribute("action").replace(
    "https://formsubmit.co/",
    "https://formsubmit.co/ajax/"
  );

  function showFeedback(text, isError) {
    if (!feedback) return;
    feedback.hidden = false;
    feedback.textContent = text;
    feedback.className = "form-feedback" + (isError ? " form-feedback--error" : " form-feedback--success");
  }

  function setSubmitting(isSubmitting) {
    if (!submitBtn) return;
    submitBtn.disabled = isSubmitting;
    submitBtn.textContent = isSubmitting ? "送信中…" : "送信する";
  }

  function validateForm() {
    if (!form.checkValidity()) {
      form.reportValidity();
      return false;
    }
    return true;
  }

  form.addEventListener("submit", function (e) {
    if (!validateForm()) {
      e.preventDefault();
      return;
    }

    if (!window.fetch) {
      return;
    }

    e.preventDefault();
    setSubmitting(true);
    if (feedback) {
      feedback.hidden = true;
    }

    var data = new FormData(form);

    fetch(endpoint, {
      method: "POST",
      body: data,
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
        showFeedback(
          "送信に失敗しました。時間をおいて再度お試しください。",
          true
        );
      });
  });
})();
