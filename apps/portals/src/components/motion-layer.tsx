"use client";

import { usePathname } from "next/navigation";
import { useEffect } from "react";

/**
 * Animations communes à tous les écrans, sans dépendance :
 * - apparition des blocs au défilement, en cascade entre éléments frères ;
 * - dévoilement des photos (rideau) ;
 * - compteurs qui défilent jusqu'à leur valeur ;
 * - barre de progression de lecture et en-tête qui se resserre au défilement.
 * Tout est coupé quand le système demande moins d'animations.
 */

const BLOCKS = [
  "main section",
  ".partners > section",
  ".partners-footer",
  ".why li",
  ".concept li",
  ".flux li",
  ".rules li",
  ".billboard-card",
  ".hub-board > li",
  ".page-head",
  ".card",
  ".stat",
  ".kpi",
  ".partners-faq details",
  ".planning-note > div",
  ".partners-calc-copy",
].join(",");

const PHOTOS = [
  ".why li img",
  ".flux li img",
  ".planning-note > img",
  ".partners-calc-photo img",
  ".hub-tile img",
  ".page-head img",
  ".concept-photo img",
].join(",");

const COUNTERS = [".lead-facts strong", ".rules li strong", ".stat strong", ".kpi strong"].join(",");

const SEEN = "data-motion";

function stillAnimated(el: Element) {
  const name = getComputedStyle(el).animationName;
  return Boolean(name) && name !== "none";
}

/** Rang de l'élément parmi ses frères révélés, pour la cascade. */
function stagger(el: HTMLElement) {
  const parent = el.parentElement;
  if (!parent) return 0;
  const siblings = Array.from(parent.children).filter((c) => c.matches(BLOCKS));
  return Math.min(Math.max(siblings.indexOf(el), 0), 6);
}

function countUp(el: HTMLElement) {
  const text = el.textContent ?? "";
  const match = text.match(/\d+(?:[.,]\d+)?/);
  if (!match) return;
  const raw = match[0];
  const decimals = raw.includes(",") || raw.includes(".") ? raw.split(/[.,]/)[1].length : 0;
  const target = Number(raw.replace(",", "."));
  if (!Number.isFinite(target) || target === 0) return;
  const sep = raw.includes(",") ? "," : ".";
  const before = text.slice(0, match.index);
  const after = text.slice((match.index ?? 0) + raw.length);
  const duration = 1100;
  const start = performance.now();
  el.style.minWidth = `${el.offsetWidth}px`;
  const tick = (now: number) => {
    const t = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - t, 4);
    const value = (target * eased).toFixed(decimals).replace(".", sep);
    el.textContent = `${before}${value}${after}`;
    if (t < 1) requestAnimationFrame(tick);
    else el.textContent = text;
  };
  requestAnimationFrame(tick);
}

export function MotionLayer() {
  const pathname = usePathname();

  useEffect(() => {
    const root = document.documentElement;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    root.classList.add("motion-ready");
    const photosOf = new Map<Element, HTMLElement[]>();
    // Suivi propre à ce passage : après une navigation ou un rechargement à chaud,
    // les éléments déjà marqués mais pas encore révélés sont de nouveau surveillés.
    const tracked = new WeakSet<Element>();
    const fresh = (el: Element) => !tracked.has(el) && !el.classList.contains("is-in");

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue;
          const el = entry.target as HTMLElement;
          photosOf.get(el)?.forEach((photo) => photo.classList.add("is-in"));
          photosOf.delete(el);
          if (el.hasAttribute(SEEN)) el.classList.add("is-in");
          if (el.matches(COUNTERS)) countUp(el);
          observer.unobserve(el);
        }
      },
      { rootMargin: "0px 0px -8% 0px", threshold: 0.12 },
    );

    const scan = () => {
      document.querySelectorAll<HTMLElement>(BLOCKS).forEach((el) => {
        if (!fresh(el) || (!el.hasAttribute(SEEN) && stillAnimated(el))) return;
        tracked.add(el);
        // Un bloc déjà révélé par son parent n'a pas besoin d'un second effet.
        if (el.parentElement?.closest("[data-motion='block']") && !el.matches(".why li, .concept li, .flux li, .rules li, .billboard-card, .hub-board > li, .stat, .kpi, .card")) return;
        el.setAttribute(SEEN, "block");
        el.style.setProperty("--motion-delay", `${stagger(el) * 90}ms`);
        observer.observe(el);
      });
      document.querySelectorAll<HTMLElement>(PHOTOS).forEach((el) => {
        if (!fresh(el) || (!el.hasAttribute(SEEN) && stillAnimated(el))) return;
        tracked.add(el);
        el.setAttribute(SEEN, "photo");
        // Une photo entièrement masquée n'est jamais « visible » pour l'observateur :
        // on surveille son conteneur, qui la révèle en entrant à l'écran.
        const holder = el.parentElement ?? el;
        photosOf.set(holder, [...(photosOf.get(holder) ?? []), el]);
        observer.observe(holder);
      });
      document.querySelectorAll<HTMLElement>(COUNTERS).forEach((el) => {
        if (!fresh(el)) return;
        tracked.add(el);
        el.setAttribute(SEEN, "count");
        observer.observe(el);
      });
    };

    scan();
    let pending = 0;
    const mutations = new MutationObserver(() => {
      cancelAnimationFrame(pending);
      pending = requestAnimationFrame(scan);
    });
    mutations.observe(document.body, { childList: true, subtree: true });

    const bar = document.createElement("div");
    bar.className = "scroll-progress";
    bar.setAttribute("aria-hidden", "true");
    document.body.appendChild(bar);
    let ticking = false;
    const onScroll = () => {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(() => {
        const max = document.documentElement.scrollHeight - window.innerHeight;
        bar.style.transform = `scaleX(${max > 0 ? window.scrollY / max : 0})`;
        root.classList.toggle("is-scrolled", window.scrollY > 12);
        // Profondeur : certains calques glissent moins vite que la page.
        document.querySelectorAll<HTMLElement>("[data-parallax]").forEach((el) => {
          const speed = Number(el.dataset.parallax) || 0;
          // Plafonné : le calque ne déborde jamais sur la section suivante.
          const shift = Math.min(window.scrollY * speed, 36);
          el.style.transform = `translate3d(0, ${shift.toFixed(1)}px, 0)`;
        });
        // Le menu suit la section lue.
        const links = document.querySelectorAll<HTMLAnchorElement>("nav a[href^='#']");
        let current: string | null = null;
        links.forEach((link) => {
          const target = document.getElementById(link.hash.slice(1));
          if (target && target.getBoundingClientRect().top < window.innerHeight * 0.4) current = link.hash;
        });
        links.forEach((link) => link.classList.toggle("is-active", link.hash === current));
        ticking = false;
      });
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });

    return () => {
      observer.disconnect();
      mutations.disconnect();
      window.removeEventListener("scroll", onScroll);
      bar.remove();
    };
  }, [pathname]);

  return null;
}
