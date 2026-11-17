"use client";

import { Handshake, ListChecks, Pause, Play, TrendingUp, Volume2, VolumeX } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { DemoSheet, type DemoKind } from "@/components/concept-demos";

/** Section vidéo : aperçu muet en boucle, lecture avec le son au clic. */
export function AdVideo() {
  const ref = useRef<HTMLVideoElement>(null);
  const [playing, setPlaying] = useState(false);
  const [muted, setMuted] = useState(true);
  const [started, setStarted] = useState(false);
  const [progress, setProgress] = useState(0);

  // L'aperçu ne tourne que lorsque la section est à l'écran.
  useEffect(() => {
    const video = ref.current;
    if (!video) return;
    const io = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) video.play().catch(() => {});
      else video.pause();
    }, { threshold: 0.35 });
    io.observe(video);
    return () => io.disconnect();
  }, []);

  const start = () => {
    const video = ref.current;
    if (!video) return;
    if (!started) { video.currentTime = 0; setStarted(true); }
    video.muted = false;
    setMuted(false);
    video.play().catch(() => {});
  };
  const toggle = () => {
    const video = ref.current;
    if (!video) return;
    if (video.paused) video.play().catch(() => {}); else video.pause();
  };
  const toggleSound = () => {
    const video = ref.current;
    if (!video) return;
    video.muted = !video.muted;
    setMuted(video.muted);
  };

  return (
    <section className="ad-video" id="video" aria-labelledby="ad-video-title">
      <div className="ad-video-copy">
        <p className="eyebrow">En 30 secondes</p>
        <h2 id="ad-video-title">XPASS, en mouvement.</h2>
        <p>Sport, culture, beauté et sorties : le membre réserve en crédits, vous scannez au comptoir. La vidéo dit tout, son compris.</p>
      </div>
      <div className={`ad-video-frame${started ? " is-started" : ""}`}>
        <video
          ref={ref}
          src="/video/xpass-pub-30s.mp4"
          poster="/video/xpass-pub-poster.jpg"
          muted
          loop
          playsInline
          preload="metadata"
          onPlay={() => setPlaying(true)}
          onPause={() => setPlaying(false)}
          onTimeUpdate={(e) => setProgress(e.currentTarget.currentTime / (e.currentTarget.duration || 30))}
          onClick={started ? toggle : start}
        />
        {!started && (
          <button type="button" className="ad-video-play" onClick={start}>
            <span><Play size={34} fill="currentColor" aria-hidden /></span>
            Regarder avec le son
          </button>
        )}
        {started && (
          <div className="ad-video-bar">
            <button type="button" onClick={toggle} aria-label={playing ? "Pause" : "Lecture"}>
              {playing ? <Pause size={20} aria-hidden /> : <Play size={20} aria-hidden />}
            </button>
            <div className="ad-video-track" aria-hidden><i style={{ transform: `scaleX(${progress})` }} /></div>
            <button type="button" onClick={toggleSound} aria-label={muted ? "Activer le son" : "Couper le son"}>
              {muted ? <VolumeX size={20} aria-hidden /> : <Volume2 size={20} aria-hidden />}
            </button>
          </div>
        )}
      </div>
    </section>
  );
}

const STEPS = [
  {
    icon: ListChecks,
    image: "/visuels/factures.jpg",
    title: "Envoyez vos informations",
    text: "Le formulaire dit qui vous êtes, le nom de l’établissement et l’activité. C’est ce qui ouvre le compte.",
    link: { href: "#demarrer", label: "Remplir le formulaire" },
    tag: "2 minutes",
  },
  {
    icon: Handshake,
    image: "/visuels/reglements.jpg",
    title: "Commencez à utiliser XPASS",
    text: "Après validation, la fiche est prête : planning, prestations, photos et scanner. Vous n’ouvrez que les places à remplir.",
    tag: "Fiche prête",
    demo: { kind: "planning" as DemoKind, label: "Voir l’espace commerçant" },
  },
  {
    icon: TrendingUp,
    image: "/visuels/promo-partenaires.jpg",
    title: "Générez des revenus",
    text: "Les membres réservent ces places et paient en crédits. Vous scannez au comptoir. Chaque semaine, 0,90 € par crédit vous sont versés.",
    tag: "0,90 € / crédit",
    demo: { kind: "revenus" as DemoKind, label: "Voir mes revenus" },
  },
];

/** « Notre concept » : trois étapes reliées par une ligne qui se remplit au défilement. */
export function ConceptSteps() {
  const ref = useRef<HTMLElement>(null);
  const [demo, setDemo] = useState<DemoKind | null>(null);

  useEffect(() => {
    const section = ref.current;
    if (!section) return;
    let frame = 0;
    const update = () => {
      const box = section.getBoundingClientRect();
      const span = box.height + window.innerHeight * 0.2;
      const p = Math.min(Math.max((window.innerHeight * 0.75 - box.top) / span, 0), 1);
      section.style.setProperty("--concept-progress", p.toFixed(3));
      section.querySelectorAll<HTMLElement>(".concept-step").forEach((step, i) => {
        step.classList.toggle("is-reached", p >= 0.12 + i * 0.22);
      });
    };
    const onScroll = () => { cancelAnimationFrame(frame); frame = requestAnimationFrame(update); };
    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => { window.removeEventListener("scroll", onScroll); window.removeEventListener("resize", onScroll); cancelAnimationFrame(frame); };
  }, []);

  return (
    <section className="concept" id="concept" ref={ref}>
      <div className="concept-head">
        <p className="eyebrow">Notre concept</p>
        <h2>Trois étapes, et vos places se remplissent.</h2>
        <p>Pas d’installation, pas d’abonnement : vous décidez des créneaux, XPASS amène les membres.</p>
      </div>
      <div className="concept-track">
        <div className="concept-line" aria-hidden><i /></div>
        <ol>
          {STEPS.map((step, i) => (
            <li key={step.title} className="concept-step">
              <span className="concept-dot" aria-hidden>{String(i + 1).padStart(2, "0")}</span>
              <article className={step.demo ? "is-clickable" : undefined}>
                {step.demo && (
                  <button type="button" className="concept-open" onClick={() => setDemo(step.demo.kind)} aria-label={`${step.title} : ${step.demo.label}`} />
                )}
                <div className="concept-photo">
                  <img src={step.image} alt="" />
                  <em>{step.tag}</em>
                </div>
                <div className="concept-body">
                  <span className="concept-icon"><step.icon size={26} strokeWidth={1.8} aria-hidden /></span>
                  <strong>{step.title}</strong>
                  <p>{step.text}</p>
                  {step.link && <a href={step.link.href}>{step.link.label} <span aria-hidden>→</span></a>}
                  {step.demo && <span className="concept-cta" aria-hidden>{step.demo.label} <span>→</span></span>}
                </div>
              </article>
            </li>
          ))}
        </ol>
      </div>
      <DemoSheet kind={demo} onClose={() => setDemo(null)} />
    </section>
  );
}
