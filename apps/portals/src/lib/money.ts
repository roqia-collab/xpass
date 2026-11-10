/** Montants en unités mineures, jamais confondus avec des crédits. */
export const money = (minor: number, currency: string | null) =>
  new Intl.NumberFormat("fr-FR", { style: "currency", currency: currency ?? "EUR" }).format(minor / 100);
