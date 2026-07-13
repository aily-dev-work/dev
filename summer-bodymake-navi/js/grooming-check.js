/**
 * 3分男磨き診断 — スコア集計と結果表示
 */
(function () {
  "use strict";

  var form = document.getElementById("grooming-quiz");
  var results = document.getElementById("quiz-results");
  if (!form || !results) {
    return;
  }

  var priority = ["A", "C", "B"];

  form.addEventListener("submit", function (e) {
    e.preventDefault();

    if (!form.checkValidity()) {
      form.reportValidity();
      return;
    }

    var scores = { A: 0, B: 0, C: 0 };
    var data = new FormData(form);

    ["q1", "q2", "q3"].forEach(function (name) {
      var value = data.get(name);
      if (value && scores[value] !== undefined) {
        scores[value] += 1;
      }
    });

    var winner = pickWinner(scores);
    showResult(winner);
  });

  function pickWinner(scores) {
    var max = Math.max(scores.A, scores.B, scores.C);
    var tied = priority.filter(function (key) {
      return scores[key] === max;
    });
    return tied[0];
  }

  function showResult(winner) {
    results.hidden = false;

    var cards = results.querySelectorAll(".check-result-card");
    cards.forEach(function (card) {
      var match = card.getAttribute("data-result") === winner;
      card.classList.toggle("check-result-card--winner", match);
      card.setAttribute("aria-hidden", match ? "false" : "true");
    });

    var summary = document.getElementById("quiz-result-summary");
    if (summary) {
      var labels = { A: "脱毛", B: "ジム", C: "スキンケア" };
      summary.textContent =
        "診断結果：いちばん優先度が高いのは「" + labels[winner] + "」です。";
      summary.hidden = false;
    }

    results.scrollIntoView({ behavior: "smooth", block: "start" });
  }
})();
