/* ============================================================
   quiz.js — 可复用测验组件（共享组件 #2）
   用法：任意 .quiz 容器内放若干 .q，每 .q 内：
     <p class="q-text">问题</p>
     <div class="opts">
       <button class="opt" data-correct="true"  data-explain="为什么正确">…</button>
       <button class="opt" data-correct="false" data-explain="为什么错误">…</button>
     </div>
   点击即判分，给出即时反馈，答题后不可改；全答完显示得分。
   样式来自 lesson.css 的 .quiz 部分。
   ============================================================ */
(function () {
  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".quiz").forEach(function (quiz) {
      var questions = quiz.querySelectorAll(".q");
      var answered = 0;
      var correctCount = 0;

      // 一个进度条式的分数脚注
      var score = document.createElement("div");
      score.className = "score";
      score.innerHTML = '已答 <b class="answered">0</b> / <b class="total">' + questions.length + "</b>　·　答对 <b class=\"right\">0</b>";
      quiz.appendChild(score);
      var answeredEl = score.querySelector(".answered");
      var rightEl = score.querySelector(".right");

      function tally() {
        answeredEl.textContent = answered;
        rightEl.textContent = correctCount;
        if (answered === questions.length) {
          score.innerHTML = "本课自测：" + correctCount + " / " + questions.length + " 全对 ✓ —— 若未全对，翻回上文再看一遍相关概念，别急着往下走。";
          score.style.color = correctCount === questions.length ? "var(--good)" : "var(--rust)";
        }
      }

      questions.forEach(function (q) {
        var opts = q.querySelectorAll(".opt");
        opts.forEach(function (opt) {
          opt.addEventListener("click", function () {
            if (q.classList.contains("done")) return;
            q.classList.add("done");
            answered++;
            var isCorrect = opt.getAttribute("data-correct") === "true";

            opts.forEach(function (o) {
              o.disabled = true;
              if (o.getAttribute("data-correct") === "true") o.classList.add("correct");
            });
            if (!isCorrect) opt.classList.add("wrong");
            else correctCount++;

            // 显示解析
            var explain = q.querySelector(".explain");
            if (!explain) {
              explain = document.createElement("div");
              explain.className = "explain";
              q.appendChild(explain);
            }
            var text = opt.getAttribute("data-explain") || "";
            explain.innerHTML = (isCorrect ? "✅ 答对。" : "❌ 答错。") + text;
            tally();
          });
        });
      });
    });
  });
})();
