"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { SPACE_HOME, SPACE_LABEL, SPACE_ORDER } from "@/lib/roles";
import type { Space } from "@/lib/types";

/** Admin, puis RH, puis commerçant, puis l'application client. */
export function SpaceSwitcher({
  spaces,
  appUrl,
  homes,
}: {
  spaces: Space[];
  appUrl: string;
  homes?: Partial<Record<Space, string>>;
}) {
  const path = usePathname();
  const items = SPACE_ORDER.filter((space) => spaces.includes(space));
  if (items.length === 0) return null;
  return (
    <nav className="space-switcher" aria-label="Espaces XPASS">
      {items.map((space) => {
        const href = homes?.[space] ?? SPACE_HOME[space];
        const active = path.startsWith(SPACE_HOME[space]);
        return href.startsWith("http") ? (
          <a key={space} href={href} className={active ? "active" : ""}>{SPACE_LABEL[space]}</a>
        ) : (
          <Link key={space} href={href} className={active ? "active" : ""}>{SPACE_LABEL[space]}</Link>
        );
      })}
      <a href={appUrl} target="_blank" rel="noreferrer">
        App client
      </a>
    </nav>
  );
}
