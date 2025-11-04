const formatCurrency = (value) =>
  new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    maximumFractionDigits: 0,
  }).format(value);

const formatHours = (hours) => {
  if (hours <= 6) return 'до 6 часов';
  if (hours <= 12) return 'до 12 часов';
  if (hours <= 24) return 'до 24 часов';
  return `${Math.ceil(hours / 24)} дн.`;
};

document.addEventListener('DOMContentLoaded', () => {
  const activePopups = new Set();
  const pageHeight = Math.max(
    document.documentElement.scrollHeight - window.innerHeight,
    1
  );
  const popupTimers = {
    offer: null,
    exit: false,
    calculator: false,
  };

  const getPopup = (id) => document.getElementById(id);

  const toggleBodyScroll = (disable) => {
    document.body.style.overflow = disable ? 'hidden' : '';
  };

  const openPopup = (id) => {
    const popup = getPopup(id);
    if (!popup) return;
    popup.classList.add('popup--active');
    activePopups.add(popup);
    toggleBodyScroll(true);
  };

  const closePopup = (popup) => {
    popup.classList.remove('popup--active');
    activePopups.delete(popup);
    if (!activePopups.size) {
      toggleBodyScroll(false);
    }
  };

  window.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && activePopups.size) {
      activePopups.forEach((popup) => closePopup(popup));
    }
  });

  document.querySelectorAll('[data-popup-close]').forEach((button) => {
    button.addEventListener('click', () => {
      const popup = button.closest('.popup');
      if (popup) closePopup(popup);
    });
  });

  document.querySelectorAll('.popup').forEach((popup) => {
    popup.addEventListener('click', (event) => {
      if (event.target === popup) closePopup(popup);
    });
  });

  popupTimers.offer = window.setTimeout(() => {
    openPopup('popup-offer');
  }, 15000);

  document.addEventListener('mouseleave', (event) => {
    if (popupTimers.exit) return;
    if (event.clientY <= 0) {
      popupTimers.exit = true;
      openPopup('popup-exit');
    }
  });

  const onScroll = () => {
    const scrolled = window.scrollY;
    if (!popupTimers.calculator && scrolled / pageHeight >= 0.5) {
      popupTimers.calculator = true;
      openPopup('popup-calculator');
      window.removeEventListener('scroll', onScroll);
    }
  };

  window.addEventListener('scroll', onScroll, { passive: true });

  const calculator = document.querySelector('.calculator__form');
  if (calculator) {
    const priceEl = document.getElementById('calc-price');
    const deadlineEl = document.getElementById('calc-deadline');
    const pagesRange = calculator.querySelector('input[name="pages"]');
    const pagesOutput = document.getElementById('pages-output');

    const calculate = () => {
      const typeCost = Number(calculator.querySelector('select[name="type"]').value || 50);
      const pages = Number(pagesRange.value || 50);
      const current = Number(calculator.querySelector('input[name="current"]').value || 0);
      const target = Number(calculator.querySelector('input[name="target"]').value || 90);
      const speed = Number(calculator.querySelector('input[name="speed"]:checked')?.value || 1);

      const complexity = Math.max((target - current) / 50, 0.8);
      const basePrice = typeCost * pages;
      const resultPrice = Math.max(basePrice * complexity * speed, 1500);
      const baseHours = Math.max(pages / 8 * 6, 6);
      const resultHours = Math.max(baseHours / speed, 2);

      priceEl.textContent = `от ${formatCurrency(resultPrice)}`;
      deadlineEl.textContent = formatHours(resultHours);
      pagesOutput.textContent = pages.toString();
    };

    calculator.addEventListener('input', calculate);
    calculator.addEventListener('change', calculate);

    calculator.addEventListener('submit', (event) => {
      event.preventDefault();
      openPopup('popup-offer');
    });

    calculate();
  }

  document.querySelectorAll('form').forEach((form) => {
    if (form.classList.contains('calculator__form')) return;
    form.addEventListener('submit', (event) => {
      event.preventDefault();
      form.reset();
      const button = form.querySelector('button[type="submit"]');
      if (button) {
        const original = button.textContent;
        button.textContent = 'Заявка отправлена';
        button.disabled = true;
        window.setTimeout(() => {
          button.textContent = original;
          button.disabled = false;
        }, 4000);
      }
    });
  });

  const counters = document.querySelectorAll('[data-counter]');
  if (counters.length) {
    const animateCounter = (element) => {
      const target = Number(element.dataset.counter || 0);
      const duration = 1200;
      let start = null;
      const step = (timestamp) => {
        if (!start) start = timestamp;
        const progress = Math.min((timestamp - start) / duration, 1);
        const value = Math.floor(progress * target);
        element.textContent = value.toLocaleString('ru-RU');
        if (progress < 1) {
          window.requestAnimationFrame(step);
        } else {
          element.textContent = target.toLocaleString('ru-RU');
        }
      };
      window.requestAnimationFrame(step);
    };

    const observer = new IntersectionObserver(
      (entries, obs) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            animateCounter(entry.target);
            obs.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.6 }
    );

    counters.forEach((counter) => observer.observe(counter));
  }

  const ticker = document.querySelector('.metrics__ticker ul');
  if (ticker) {
    let index = 0;
    const rotate = () => {
      const items = ticker.querySelectorAll('li');
      if (!items.length) return;
      items.forEach((item, i) => {
        item.style.transform = `translateY(${(i - index) * 100}%)`;
        item.style.transition = 'transform 0.5s ease';
      });
      index = (index + 1) % items.length;
    };

    itemsToAbsolute(ticker);
    rotate();
    window.setInterval(rotate, 4000);
  }

  function itemsToAbsolute(list) {
    list.style.position = 'relative';
    list.querySelectorAll('li').forEach((item, i) => {
      item.style.position = 'absolute';
      item.style.left = '0';
      item.style.right = '0';
      item.style.transform = `translateY(${i * 100}%)`;
    });
  }

  const chatButton = document.querySelector('.chat-widget');
  if (chatButton) {
    chatButton.addEventListener('click', () => {
      openPopup('popup-offer');
    });
  }
});
