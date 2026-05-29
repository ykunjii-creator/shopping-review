// UiPath Inject JS Script 규약: 단일 함수. 반환값(JSON 문자열)이 ScriptOutput으로 전달됨.
// 올리브영 리뷰는 OY-REVIEW-* 웹컴포넌트의 (open) Shadow DOM + 가상 스크롤 리스트.
// 현재 렌더된 OY-REVIEW-REVIEW-ITEM 들에서 text / rating(채워진 별 수) / review_date 수집.
// 가상 스크롤이라 한 번에 ~11개만 잡힘 → RPA가 스크롤하며 반복 호출, 텍스트로 중복 제거.
function extractReviews(element) {
    function deepQueryAll(root, sel, acc) {
        acc = acc || [];
        if (!root) return acc;
        try {
            var direct = root.querySelectorAll(sel);
            for (var i = 0; i < direct.length; i++) { acc.push(direct[i]); }
        } catch (e) {}
        var all;
        try { all = root.querySelectorAll('*'); } catch (e) { all = []; }
        for (var j = 0; j < all.length; j++) {
            if (all[j].shadowRoot) { deepQueryAll(all[j].shadowRoot, sel, acc); }
        }
        return acc;
    }
    function deepFindOne(root, selectors) {
        for (var s = 0; s < selectors.length; s++) {
            var found = deepQueryAll(root, selectors[s], []);
            if (found.length) return found[0];
        }
        return null;
    }
    function txt(el) {
        return el ? (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim() : '';
    }
    // 별점: .rating 안의 oy-review-star-icon 각각의 shadow SVG path fill 이
    // 'none' 이 아니면 채워진 별. 채워진 별 수 = rating.
    function ratingOf(scope) {
        var ratingBox = deepFindOne(scope, ['div.rating', '.rating']);
        var stars = deepQueryAll(ratingBox || scope, 'oy-review-star-icon', []);
        var filled = 0;
        for (var i = 0; i < stars.length; i++) {
            var sr = stars[i].shadowRoot;
            var p = sr ? sr.querySelector('path') : null;
            var f = p ? (p.getAttribute('fill') || '').toLowerCase() : '';
            if (f && f !== 'none') filled++;
        }
        return filled;
    }

    var items = deepQueryAll(document, 'OY-REVIEW-REVIEW-ITEM', []);
    var out = [];
    for (var k = 0; k < items.length; k++) {
        var it = items[k];
        var scope = it.shadowRoot || it;
        var contentEl = deepFindOne(scope, ['div.content', '.review_cont .txt', '.content', 'p']);
        var text = txt(contentEl);
        if (!text) continue;
        var rating = ratingOf(scope);
        var dateEl = deepFindOne(scope, ['span.date', '[class*="date"]', '.review_info .date', 'time']);
        var date = txt(dateEl);
        out.push({ text: text, rating: rating, review_date: date });
    }
    return JSON.stringify(out);
}
