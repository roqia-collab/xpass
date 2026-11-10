"use client";

import jsQR from "jsqr";
import { CalendarDays, Camera, CameraOff, CheckCircle2, Clock, Coins, Keyboard, Scissors, Users } from "lucide-react";
import { useCallback, useEffect, useRef, useState, useTransition } from "react";

import { Notice } from "@/components/ui";
import { formatDuration } from "@/lib/roles";

import { confirmRedemption, previewScan, type Redemption, type ScanPreview } from "./actions";

type Source = { qr?: string; code?: string };
type Step = { kind: "scan" } | { kind: "preview"; source: Source; preview: ScanPreview; key: string } | { kind: "done"; result: Redemption };

const longDate = (iso: string) =>
  new Intl.DateTimeFormat("fr-FR", { weekday: "long", day: "numeric", month: "long", year: "numeric" }).format(new Date(`${iso}:00`));

export function ScannerClient({ mediaBase }: { mediaBase: string }) {
  const [step, setStep] = useState<Step>({ kind: "scan" });
  const [error, setError] = useState<string>();
  const [pending, start] = useTransition();

  const submit = useCallback((source: Source) => {
    setError(undefined);
    start(async () => {
      const res = await previewScan(source);
      if (res.ok) setStep({ kind: "preview", source, preview: res.data, key: crypto.randomUUID() });
      else setError(res.error);
    });
  }, []);

  const confirm = () => {
    if (step.kind !== "preview") return;
    setError(undefined);
    start(async () => {
      const res = await confirmRedemption(step.source, step.key);
      if (res.ok) setStep({ kind: "done", result: res.data });
      else setError(res.error); // la même clé est réutilisée en cas de nouvel essai
    });
  };

  if (step.kind === "done") {
    return (
      <div className="card" style={{ maxWidth: 640, display: "flex", flexDirection: "column", gap: 14 }}>
        <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
          <CheckCircle2 size={44} color="#2f7a45" aria-hidden />
          <div>
            <h2>Consommation enregistrée</h2>
            <p className="muted">
              {step.result.offer_title} · {step.result.customer_name} · {step.result.credits} crédits
            </p>
          </div>
        </div>
        <p>
          Référence du reçu : <strong>{step.result.receipt_reference}</strong>
        </p>
        <button className="btn primary" onClick={() => setStep({ kind: "scan" })}>
          Scanner un autre client
        </button>
      </div>
    );
  }

  if (step.kind === "preview") {
    const p = step.preview;
    const cover = p.cover_image_key ? `${mediaBase}/${p.cover_image_key}` : null;
    return (
      <div style={{ maxWidth: 640, display: "flex", flexDirection: "column", gap: 14 }}>
        <p className="eyebrow">Vérification</p>
        <h1>Vérifier la prestation</h1>
        <p className="muted" style={{ fontSize: 16 }}>Contrôlez les informations de la réservation et confirmez la consommation.</p>
        <div className="card" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
            {cover ? <img className="thumb" src={cover} alt="" style={{ width: 96, height: 80 }} /> : <span className="thumb" style={{ width: 96, height: 80 }} />}
            <div>
              <h3>{p.location_name}</h3>
              <p className="muted">{p.kind_label} · {p.district_label}</p>
            </div>
          </div>
          <div className="list-row">
            <Scissors aria-hidden />
            <div>
              <strong>{p.offer_title}</strong>
              <div className="muted">{p.resource_name ? `Avec ${p.resource_name} · ` : ""}Client : {p.customer_name}</div>
            </div>
          </div>
          <div className="list-row"><CalendarDays aria-hidden /> {longDate(p.local_start)}</div>
          <div className="list-row"><Clock aria-hidden /> {p.local_start.slice(11)} ({formatDuration(p.duration_min)})</div>
          <div className="list-row"><Users aria-hidden /> {p.party_size} personne{p.party_size > 1 ? "s" : ""}</div>
        </div>
        <div className="card" style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <Coins aria-hidden />
          <div>
            <strong>{p.total_credits} crédits</strong>
            <div className="muted">Coût de cette prestation</div>
          </div>
        </div>
        <div className="notice mint">
          <CheckCircle2 size={18} aria-hidden /> <span><strong>Réservation confirmée</strong> · code valide</span>
        </div>
        {error && <p className="error" role="alert">{error}</p>}
        <button className="btn primary" onClick={confirm} disabled={pending}>
          {pending ? "Enregistrement…" : "Confirmer la consommation"}
        </button>
        <button className="btn outline" onClick={() => { setError(undefined); setStep({ kind: "scan" }); }} disabled={pending}>
          Retour au scanner
        </button>
        <p className="muted" style={{ textAlign: "center", fontSize: 13 }}>La validation enregistre une seule consommation.</p>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 640, display: "flex", flexDirection: "column", gap: 16 }}>
      <h1 style={{ textAlign: "center" }}>Scanner le QR client</h1>
      <p className="muted" style={{ textAlign: "center", fontSize: 17 }}>Présentez le code dans le cadre</p>
      <CameraScanner onDetected={(qr) => submit({ qr })} paused={pending} />
      <Notice>Le scan affiche un aperçu avant validation : rien n’est consommé à ce stade.</Notice>
      {error && <p className="error" role="alert">{error}</p>}
      <ManualCode onSubmit={(code) => submit({ code })} pending={pending} />
    </div>
  );
}

function CameraScanner({ onDetected, paused }: { onDetected: (payload: string) => void; paused: boolean }) {
  const video = useRef<HTMLVideoElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const [state, setState] = useState<"idle" | "running" | "denied" | "unavailable">("idle");
  const lastPayload = useRef<string | null>(null);

  useEffect(() => {
    if (state !== "running") return;
    let stream: MediaStream | undefined;
    let timer: number | undefined;
    let cancelled = false;
    (async () => {
      try {
        stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
      } catch (e) {
        setState(e instanceof DOMException && e.name === "NotAllowedError" ? "denied" : "unavailable");
        return;
      }
      if (cancelled || !video.current) return;
      video.current.srcObject = stream;
      await video.current.play().catch(() => undefined);
      timer = window.setInterval(() => {
        const v = video.current;
        const c = canvas.current;
        if (!v || !c || v.readyState < 2 || paused) return;
        c.width = v.videoWidth;
        c.height = v.videoHeight;
        const ctx = c.getContext("2d", { willReadFrequently: true });
        if (!ctx) return;
        ctx.drawImage(v, 0, 0);
        const found = jsQR(ctx.getImageData(0, 0, c.width, c.height).data, c.width, c.height);
        if (found?.data.startsWith("XPASS1:") && found.data !== lastPayload.current) {
          lastPayload.current = found.data;
          onDetected(found.data);
        }
      }, 250);
    })();
    return () => {
      cancelled = true;
      if (timer) window.clearInterval(timer);
      stream?.getTracks().forEach((t) => t.stop());
    };
  }, [state, onDetected, paused]);

  const startCamera = () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      setState("unavailable");
      return;
    }
    setState("running");
  };

  return (
    <div className="card" style={{ padding: 0, overflow: "hidden", position: "relative", background: "var(--navy)", minHeight: 300 }}>
      {state === "running" ? (
        <>
          <video ref={video} muted playsInline style={{ width: "100%", display: "block" }} aria-label="Aperçu de la caméra" />
          <canvas ref={canvas} hidden />
          <div aria-hidden style={{ position: "absolute", inset: "18%", border: "4px solid var(--lavender-strong)", borderRadius: 24 }} />
        </>
      ) : (
        <div style={{ color: "#fff", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 14, minHeight: 300, padding: 24, textAlign: "center" }}>
          {state === "idle" && (
            <>
              <Camera size={40} aria-hidden />
              <button className="btn primary" onClick={startCamera}>Activer la caméra</button>
            </>
          )}
          {state === "denied" && (
            <>
              <CameraOff size={40} aria-hidden />
              <p>Accès à la caméra refusé. Autorisez-le dans le navigateur ou saisissez le code du client.</p>
              <button className="btn outline" onClick={startCamera}>Réessayer</button>
            </>
          )}
          {state === "unavailable" && (
            <>
              <CameraOff size={40} aria-hidden />
              <p>Caméra indisponible sur cet appareil (une connexion HTTPS est requise hors localhost). Saisissez le code du client.</p>
            </>
          )}
        </div>
      )}
    </div>
  );
}

function ManualCode({ onSubmit, pending }: { onSubmit: (code: string) => void; pending: boolean }) {
  const [code, setCode] = useState("");
  const valid = code.replace(/[^A-Za-z0-9]/g, "").length === 8;
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (valid) onSubmit(code);
      }}
      style={{ display: "flex", gap: 10 }}
    >
      <label className="field" style={{ flex: 1 }}>
        <span className="muted" style={{ fontSize: 13 }}>Code à usage unique</span>
        <input
          value={code}
          onChange={(e) => setCode(e.target.value.toUpperCase())}
          placeholder="XXXX-XXXX"
          autoComplete="off"
          inputMode="text"
          maxLength={12}
          aria-label="Code à usage unique du client"
        />
      </label>
      <button className="btn primary" type="submit" disabled={!valid || pending} style={{ alignSelf: "flex-end" }}>
        <Keyboard size={18} aria-hidden /> {pending ? "Vérification…" : "Vérifier"}
      </button>
    </form>
  );
}
