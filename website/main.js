(function () {
  const header = document.querySelector(".site-header");
  const reveals = document.querySelectorAll(".reveal");
  const navLinks = document.querySelectorAll("[data-nav]");
  const sections = ["about", "platform", "packs", "roadmap", "start", "services", "contact"]
    .map((id) => document.getElementById(id))
    .filter(Boolean);

  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

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
      { threshold: 0.08, rootMargin: "0px 0px -32px 0px" }
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
      { rootMargin: "-40% 0px -50% 0px", threshold: [0, 0.2] }
    );

    sections.forEach((section) => navObserver.observe(section));
  }
})();