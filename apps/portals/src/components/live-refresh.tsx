"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

/** Relit les données du serveur pour rester aligné avec l'application et les autres portails. */
export function LiveRefresh({ seconds = 8 }: { seconds?: number }) {
  const router = useRouter();
  useEffect(() => {
    const id = setInterval(() => router.refresh(), seconds * 1000);
    return () => clearInterval(id);
  }, [router, seconds]);
  return null;
}
