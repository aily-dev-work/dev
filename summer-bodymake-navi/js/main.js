/**
 * @deprecated site.js に統合済み。互換のため site.js を読み込みます。
 */
(function () {
  var s = document.createElement("script");
  s.src = "js/site.js";
  s.defer = true;
  document.head.appendChild(s);
})();
