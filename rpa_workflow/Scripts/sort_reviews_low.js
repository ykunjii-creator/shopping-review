// UiPath Inject JS Script 규약: 단일 함수, 반환값(JSON 문자열)이 ScriptOutput으로 전달됨.
// 올리브영 리뷰 정렬을 "평점 낮은순"으로 변경한다.
// 정렬 컨트롤은 OY-REVIEW-* 웹컴포넌트의 (open) Shadow DOM 안 → deepQueryAll 재귀 탐색.
// 드롭다운 열기→옵션선택이 2단계일 수 있어 RPA가 Delay를 두고 이 스크립트를 2회 호출한다.
//   1회차: 토글 열기(또는 select/직접클릭으로 즉시 적용)  2회차: 떠 있는 "낮은순" 옵션 클릭.
// 멱등 가드: 이미 "낮은순"이면 아무 것도 하지 않고 종료. 셀렉터는 best-effort(라이브 검증 필요).
function sortReviewsLow(element) {
    function deepQueryAll(root, sel, acc) {
        acc = acc || [];
        if (!root) return acc;
        try { var d = root.querySelectorAll(sel); for (var i = 0; i < d.length; i++) acc.push(d[i]); } catch (e) {}
        var all; try { all = root.querySelectorAll('*'); } catch (e) { all = []; }
        for (var j = 0; j < all.length; j++) { if (all[j].shadowRoot) deepQueryAll(all[j].shadowRoot, sel, acc); }
        return acc;
    }
    function txt(el) { return el ? (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim() : ''; }
    function visible(el) {
        return el && el.offsetParent !== null && !el.disabled
            && el.getAttribute('aria-disabled') !== 'true';
    }
    var LOW = /낮은\s*순/;

    // 0) 멱등 가드 — 현재 활성 정렬 라벨이 이미 "낮은순"이면 종료.
    //    (선택된 옵션/현재 정렬 표시는 보통 aria-selected / .on / .active / [aria-current] 로 표기)
    var actives = deepQueryAll(document,
        '[aria-current="true"], [aria-current="page"], [aria-selected="true"], [class*="sort"] .on, [class*="sort"] .active, [class*="order"] .on', []);
    for (var a = 0; a < actives.length; a++) {
        if (LOW.test(txt(actives[a]))) return JSON.stringify({ applied: true, already: true });
    }

    // 1) 주 경로 — 이미 떠 있는 "낮은순" 옵션을 직접 클릭 (드롭다운이 열린 2회차 포함)
    var options = deepQueryAll(document,
        'li, [role="option"], [role="menuitem"], button, a, label, span', []);
    for (var o = 0; o < options.length; o++) {
        var ot = txt(options[o]);
        if (ot && ot.length <= 12 && LOW.test(ot) && visible(options[o])) {
            options[o].click();
            return JSON.stringify({ applied: true, method: 'click', text: ot });
        }
    }

    // 2) 부 경로 — 네이티브 <select> 의 "낮은순" 옵션 선택 + change 디스패치
    var selects = deepQueryAll(document, 'select', []);
    for (var s = 0; s < selects.length; s++) {
        var opts = selects[s].options || [];
        for (var p = 0; p < opts.length; p++) {
            if (LOW.test(txt(opts[p])) || LOW.test(opts[p].value || '')) {
                selects[s].selectedIndex = p;
                selects[s].value = opts[p].value;
                try { selects[s].dispatchEvent(new Event('change', { bubbles: true })); } catch (e) {}
                return JSON.stringify({ applied: true, method: 'select', text: txt(opts[p]) });
            }
        }
    }

    // 3) 정렬 드롭다운 토글을 연다 (현재 정렬 라벨/정렬 컨트롤 추정) → 다음 호출에서 1)이 옵션 클릭
    var toggles = deepQueryAll(document,
        '[class*="sort"] button, [class*="sort"] a, button[class*="sort"], [class*="order"] button, [aria-haspopup]', []);
    for (var g = 0; g < toggles.length; g++) {
        if (visible(toggles[g])) { toggles[g].click(); return JSON.stringify({ opened: true, via: 'toggle' }); }
    }
    var labels = deepQueryAll(document, 'button, a, span, div', []);
    for (var l = 0; l < labels.length; l++) {
        var lt = txt(labels[l]);
        if (lt && lt.length <= 8 && /(베스트순|최신순|추천순|정렬|높은\s*순)/.test(lt) && visible(labels[l])) {
            labels[l].click();
            return JSON.stringify({ opened: true, via: 'label', text: lt });
        }
    }

    return JSON.stringify({ applied: false, opened: false, via: 'none' });
}
