const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches || navigator.saveData;
const bg = document.getElementById('ambient-bg');
if (!bg || reduced) { if(bg) bg.style.opacity='0.3'; }
else {
  let tx = 0.5, ty = 0.5, cx = 0.5, cy = 0.5, raf = null;
  document.addEventListener('mousemove', e => { tx = e.clientX / window.innerWidth; ty = e.clientY / window.innerHeight; });
  function loop() {
    cx += (tx - cx) * 0.06; cy += (ty - cy) * 0.06;
    bg.style.setProperty('--mouse-x', `${(cx * 100).toFixed(2)}%`);
    bg.style.setProperty('--mouse-y', `${(cy * 100).toFixed(2)}%`);
    raf = requestAnimationFrame(loop);
  }
  loop();
  window.addEventListener('unload', () => cancelAnimationFrame(raf));
}
