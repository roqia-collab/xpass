export const ACTIVITIES = [
  { slug: "sport", name: "Sport" },
  { slug: "culture", name: "Culture" },
  { slug: "beaute", name: "Beauté" },
  { slug: "sorties", name: "Sorties" },
] as const;

export type ActivitySlug = (typeof ACTIVITIES)[number]["slug"];

export function activityName(slug: string | undefined | null): string {
  return ACTIVITIES.find((item) => item.slug === slug)?.name ?? "";
}
