// UiPath Inject JS Script 규약: 단일 함수, 반환값(문자열)이 ScriptOutput으로 전달됨.
// 가상 스크롤 리뷰: 한 화면씩 아래로 점진 스크롤 + scroll/wheel 이벤트를 명시적으로 발생시켜
// 사이트의 lazy 데이터 로드(가상 리스트 다음 배치)를 유발한다.
// 현재 위치 y, 전체 높이 h, 뷰포트 ih 를 JSON으로 반환 → RPA가 바닥 도달 판단.
function scrollMore(element) {
    var el = document.scrollingElement || document.documentElement || document.body;
    var ih = window.innerHeight || 800;
    var step = Math.max(500, Math.floor(ih * 0.8));
    var target = el.scrollTop + step;
    el.scrollTop = target;
    try { document.documentElement.scrollTop = target; } catch (e) {}
    try { document.body.scrollTop = target; } catch (e) {}
    try { window.scrollTo(0, target); } catch (e) {}
    // 가상 리스트/Lazy 로더가 듣는 이벤트를 명시적으로 발생
    try { window.dispatchEvent(new Event('scroll', { bubbles: true })); } catch (e) {}
    try { document.dispatchEvent(new Event('scroll', { bubbles: true })); } catch (e) {}
    try { window.dispatchEvent(new WheelEvent('wheel', { deltaY: step, bubbles: true })); } catch (e) {}
    return JSON.stringify({ y: el.scrollTop, h: el.scrollHeight, ih: ih });
}
