"use client";

import { Bell } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

export interface AdminAlert {
  href: string;
  title: string;
  detail: string;
}

/** Cloche de l'admin : demandes, litiges, dossiers et messages encore ouverts. */
export function AdminAlerts({ items }: { items: AdminAlert[] }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="alerts">
      <button
        type="button"
        className="btn ghost alerts-btn"
        aria-label={items.length ? `${items.length} notifications` : "Notifications"}
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        <Bell size={18} aria-hidden />
        {items.length > 0 && <span className="alerts-count">{items.length > 9 ? "9+" : items.length}</span>}
      </button>
      {open && (
        <div className="alerts-menu" role="menu">
          <p className="muted" style={{ margin: "6px 12px 4px", fontSize: 12, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase" }}>
            Notifications
          </p>
          {items.length === 0 && <p className="muted" style={{ padding: "8px 12px" }}>Rien en attente.</p>}
          {items.map((item) => (
            <Link key={`${item.href}-${item.title}`} href={item.href} onClick={() => setOpen(false)}>
              <strong>{item.title}</strong>
              <span>{item.detail}</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
