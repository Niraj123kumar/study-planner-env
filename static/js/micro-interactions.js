document.addEventListener('DOMContentLoaded', () => {
  // Haptic tap
  document.querySelectorAll('[data-haptic]').forEach(el => {
    el.classList.add('haptic-btn');
    el.addEventListener('click', () => {
      el.classList.add('tap-scale');
      if (navigator.vibrate) navigator.vibrate(10);
      setTimeout(() => el.classList.remove('tap-scale'), 100);
    });
  });

  // Staggered lists
  document.querySelectorAll('[data-stagger]').forEach(list => {
    Array.from(list.children).forEach((child, i) => {
      child.classList.add('stagger-item');
      child.style.animationDelay = `${i * 60}ms`;
    });
  });
});
