function showScreen(name) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    const el = document.getElementById('screen-' + name);
    if (el) { el.classList.add('active'); window.scrollTo(0, 0); }
    document.querySelectorAll('.screen-nav button').forEach(b => b.classList.remove('active'));
    const navBtns = document.querySelectorAll('.screen-nav button');
    navBtns.forEach(b => { if (b.getAttribute('onclick') && b.getAttribute('onclick').includes("'"+name+"'")) b.classList.add('active'); });
  }

  // FAQ toggle
  function toggleFaq(el) {
    const item = el.parentElement;
    const isOpen = item.classList.contains('open');
    document.querySelectorAll('.faq-item').forEach(i => i.classList.remove('open'));
    if (!isOpen) item.classList.add('open');
  }

  // Navbar scroll effect
  window.addEventListener('scroll', () => {
    const nav = document.getElementById('lp-nav');
    if (nav) nav.classList.toggle('scrolled', window.scrollY > 50);
  });