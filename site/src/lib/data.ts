import videosRaw from "../data/videos.json";
import placesRaw from "../data/places.json";
import statsRaw from "../data/stats.json";
import wishlistRaw from "../data/wishlist.json";

export type Quote = { text: string; t: number; speaker?: string | null };
export type Review = {
  is_review?: boolean;
  place_name?: string | null;
  address?: string | null;
  area?: string | null;
  city?: string | null;
  dish?: string | null;
  price_dkk?: number | null;
  rating?: { value?: number | null; scale?: number | null; raw_quote?: string | null; t?: number | null };
  sub_scores?: { label: string; value: number; scale: number }[];
  verdict_short?: string | null;
  summary?: string | null;
  pros?: string[];
  cons?: string[];
  quotes?: Quote[];
  people?: string[];
  mood?: string;
  confidence?: number;
  stub?: boolean;
};
export type Viewers = {
  positive_pct: number; negative_pct: number; neutral_pct: number;
  agrees_with_rating?: boolean | null; disagreement_note?: string | null;
  themes?: { label: string; count_estimate: number }[];
  requested_places?: string[];
  best_comment?: string | null; best_comment_author?: string | null;
} | null;
export type Video = {
  id: string; title: string; date: string | null; duration: number | null;
  views: number | null; likes: number | null; comments: number | null;
  thumb: string; review: Review; score: number | null; viewers: Viewers;
  geo: { lat: number; lng: number } | null; place?: string; ep: number;
};
export type Place = {
  slug: string; name: string; address: string | null; area: string | null; city: string | null;
  geo: { lat: number; lng: number } | null; videos: string[]; score: number | null;
  latest: string; prices: number[];
};

// Jeppe films and is never on screen; generic labels aren't people either.
const NOT_ON_SCREEN = /^(jeppe|godt jeppe|vært|værten|værter|kebab ?tv.*|kebabtv.*|vært fra kebabtv)$/i;
const GENERIC_SPEAKER = /^(vært|værten|kebab ?tv|kebabtv-vært|kebabtv-værter)$/i;
function clean(v: any) {
  const r = v.review ?? {};
  r.people = (r.people ?? []).filter((n: string) => !NOT_ON_SCREEN.test(n.trim()));
  r.quotes = (r.quotes ?? []).map((q: any) => ({
    ...q,
    speaker: !q.speaker || GENERIC_SPEAKER.test(q.speaker.trim()) ? null
      : /^jeppe$/i.test(q.speaker.trim()) ? "Jeppe, bag kameraet" : q.speaker,
  }));
  return v;
}

// Episode number = order of release, oldest first.
const byDateAsc = [...(videosRaw as any[])].sort((a, b) => (a.date ?? "").localeCompare(b.date ?? ""));
const epOf = new Map(byDateAsc.map((v, i) => [v.id, i + 1]));
export const videos: Video[] = (videosRaw as any[]).map((v) => clean({ ...v, ep: epOf.get(v.id)! }));
export const places = placesRaw as Place[];
export const stats = statsRaw as any;
export const wishlist = wishlistRaw as { name: string; area?: string | null; mentions: number; already_reviewed: boolean }[];
export const videoById = new Map(videos.map((v) => [v.id, v]));
export const placeBySlug = new Map(places.map((p) => [p.slug, p]));

const dateFmt = new Intl.DateTimeFormat("da-DK", { day: "numeric", month: "short", year: "numeric" });
export function fmtDate(d: string | null) {
  if (!d) return "";
  return dateFmt.format(new Date(`${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6, 8)}`));
}
export function fmtNum(n: number | null | undefined) {
  return n == null ? "–" : n.toLocaleString("da-DK");
}
export function fmtDur(s: number | null) {
  if (!s) return "";
  const m = Math.round(s / 60);
  return m >= 60 ? `${Math.floor(m / 60)} t ${m % 60} min` : `${Math.max(1, m)} min`;
}
export function fmtScore(s: number | null | undefined) {
  return s == null ? "?" : s.toLocaleString("da-DK", { maximumFractionDigits: 1 });
}
export function fmtTime(t: number) {
  return `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, "0")}`;
}
/** Where on the yellow→oxblood bar a score sits. High = yellow (good), low = oxblood. */
/** Their own badge: over 8 is "dum dürüm, approved af KebabTV". */
export const isDumDurum = (s: number | null | undefined) => s != null && s >= 8;

export function scoreColor(s: number | null | undefined) {
  if (s == null) return "#ffffff";
  if (s >= 8.5) return "#F3DC07";
  if (s >= 7.5) return "#EDB10C";
  if (s >= 6.5) return "#DE7414";
  if (s >= 5) return "#C93118";
  return "#730A03";
}
export function scoreInk(s: number | null | undefined) {
  return s != null && s < 6.5 ? "#FFFFFF" : "#000000";
}
export function placeName(v: Video) {
  return v.review.place_name || v.title;
}
export function placeSub(v: Video) {
  const r = v.review;
  return r.address || [r.area, r.city].filter(Boolean).join(", ") || fmtDate(v.date);
}
