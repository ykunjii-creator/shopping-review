// UiPath Inject JS Script 규약: 단일 함수, 반환값(문자열)이 ScriptOutput으로 전달됨.
// 페이지가 tab=review로 리뷰 섹션 '끝'으로 자동 스크롤되어 있으므로,
// 수집 루프 시작 전에 리뷰 리스트의 '맨 위'로 이동시킨다.
function gotoReviewsTop(element) {
    function deepQueryAll(root, sel, acc) {
        acc = acc || [];
        if (!root) return acc;
        try { var d = root.querySelectorAll(sel); for (var i = 0; i < d.length; i++) acc.push(d[i]); } catch (e) {}
        var all; try { all = root.querySelectorAll('*'); } catch (e) { all = []; }
        for (var j = 0; j < all.length; j++) { if (all[j].shadowRoot) deepQueryAll(all[j].shadowRoot, sel, acc); }
        return acc;
    }
    var el = document.scrollingElement || document.documentElement || document.body;
    var anchor = deepQueryAll(document, 'OY-REVIEW-REVIEW-LIST', [])[0]
        || deepQueryAll(document, 'OY-REVIEW-REVIEW-IN-PRODUCT', [])[0]
        || deepQueryAll(document, 'OY-REVIEW-REVIEW-ITEM', [])[0];
    if (anchor) {
        var rect = anchor.getBoundingClientRect();
        var top = rect.top + el.scrollTop - 120;
        el.scrollTop = Math.max(0, top);
        try { window.scrollTo(0, el.scrollTop); } catch (e) {}
    }
    return JSON.stringify({ y: el.scrollTop, h: el.scrollHeight, ih: window.innerHeight || 0 });
}
