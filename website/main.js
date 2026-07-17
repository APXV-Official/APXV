(function () {
  const header = document.querySelector(".site-header");
  const reveals = document.querySelectorAll(".reveal");
  const navLinks = document.querySelectorAll("[data-nav]");
  const spotlight = document.getElementById("spotlight");
  const nav = document.getElementById("site-nav");
  const navToggle = document.getElementById("nav-toggle");
  const navBackdrop = document.getElementById("nav-backdrop");
  const sections = ["product", "how", "packs", "download", "docs", "contact"]
    .map((id) => document.getElementById(id))
    .filter(Boolean);

  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const finePointer = window.matchMedia("(pointer: fine)").matches;
  const isNarrow = () => window.matchMedia("(max-width: 820px)").matches;

  const setMenuOpen = (open) => {
    if (!nav || !navToggle) return;
    document.body.classList.toggle("nav-open", open);
    navToggle.setAttribute("aria-expanded", open ? "true" : "false");
    navToggle.setAttribute("aria-label", open ? "Close menu" : "Open menu");
    if (navBackdrop) {
      if (open) navBackdrop.removeAttribute("hidden");
      else navBackdrop.setAttribute("hidden", "");
    }
  };

  if (navToggle && nav) {
    navToggle.addEventListener("click", () => {
      setMenuOpen(!document.body.classList.contains("nav-open"));
    });
    nav.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => setMenuOpen(false));
    });
    if (navBackdrop) {
      navBackdrop.addEventListener("click", () => setMenuOpen(false));
    }
    window.addEventListener(
      "keydown",
      (e) => {
        if (e.key === "Escape") setMenuOpen(false);
      },
      { passive: true },
    );
    window.addEventListener(
      "resize",
      () => {
        if (!isNarrow()) setMenuOpen(false);
      },
      { passive: true },
    );
  }

  if (header) {
    const onScroll = () => header.classList.toggle("is-scrolled", window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  if (reveals.length && !reducedMotion) {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.06, rootMargin: "0px 0px -24px 0px" },
    );
    reveals.forEach((el) => observer.observe(el));
  } else {
    reveals.forEach((el) => el.classList.add("is-visible"));
  }

  if (navLinks.length && sections.length) {
    const setActive = (id) => {
      navLinks.forEach((link) => {
        link.classList.toggle("is-active", link.getAttribute("href") === `#${id}`);
      });
    };

    const navObserver = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (visible) setActive(visible.target.id);
      },
      { rootMargin: "-35% 0px -50% 0px", threshold: [0, 0.2] },
    );

    sections.forEach((section) => navObserver.observe(section));
  }

  // Soft cursor spotlight (desktop fine pointer only — not mobile)
  if (spotlight && finePointer && !reducedMotion) {
    let targetX = window.innerWidth * 0.5;
    let targetY = window.innerHeight * 0.25;
    let currentX = targetX;
    let currentY = targetY;

    const tick = () => {
      currentX += (targetX - currentX) * 0.14;
      currentY += (targetY - currentY) * 0.14;
      spotlight.style.transform = `translate3d(${currentX}px, ${currentY}px, 0) translate(-50%, -50%)`;
      requestAnimationFrame(tick);
    };

    document.body.classList.add("has-spotlight");
    requestAnimationFrame(tick);

    window.addEventListener(
      "pointermove",
      (e) => {
        if (e.pointerType === "touch") return;
        targetX = e.clientX;
        targetY = e.clientY;
        document.body.classList.add("has-spotlight");
      },
      { passive: true },
    );

    document.documentElement.addEventListener(
      "mouseleave",
      () => document.body.classList.remove("has-spotlight"),
      { passive: true },
    );
  }
})();
