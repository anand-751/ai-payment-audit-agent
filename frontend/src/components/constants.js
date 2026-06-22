// // ── THEME TOKENS ─────────────────────────────────────────────────────────────
// // Modern fintech: deep slate base, electric cyan primary, vivid violet accent
// export const T = {
//   // Backgrounds — deep blue-slate hierarchy
//   bg0: "#070B14",
//   bg1: "#0C1220",
//   bg2: "#111827",
//   bg3: "#192033",

//   // Borders
//   border:  "#1C2B42",
//   border2: "#243450",

//   // Primary accent — electric cyan
//   cyan:    "#00D4FF",
//   cyanDim: "#0090B8",
//   cyanBg:  "#00D4FF12",
//   cyanGlow: "0 0 20px #00D4FF40",

//   // Secondary accent — vivid violet
//   violet:    "#8B5CF6",
//   violetDim: "#6D3FD9",
//   violetBg:  "#8B5CF610",

//   // Status colors — more vivid
//   red:    "#FF4D6D",
//   redDim: "#991B30",
//   redBg:  "#FF4D6D0D",

//   amber:   "#FFB627",
//   amberBg: "#FFB6270D",

//   green:   "#00E5A0",
//   greenBg: "#00E5A00D",

//   blue:    "#4DA6FF",

//   // Text hierarchy
//   text0: "#EEF2FF",
//   text1: "#8FA3C0",
//   text2: "#4A5E7A",

//   // Typography
//   mono: "'IBM Plex Mono','Courier New',monospace",
//   sans: "'Inter','DM Sans',system-ui,sans-serif",
// };

// // ── FORMATTERS ────────────────────────────────────────────────────────────────
// export const fmt = n =>
//   new Intl.NumberFormat("en-US", {
//     style: "currency",
//     currency: "USD",
//     minimumFractionDigits: 0,
//   }).format(n);

// export const fmtFull = n =>
//   new Intl.NumberFormat("en-US", {
//     style: "currency",
//     currency: "USD",
//     minimumFractionDigits: 2,
//   }).format(n);




// ── Enterprise Light Theme — Contrast-verified ────────────────────────────────
//
// Every colour has been checked against WCAG AA (4.5:1 for normal text).
// Contrast ratios on their typical backgrounds:
//
//   text0  #1E1B4B  → 15.99:1 on white   ✓✓  (AAA)
//   text1  #374151  → 10.31:1 on white   ✓✓  (AAA)
//   text2  #5C6170  →  5.60:1 on bg0     ✓   (AA)
//   cyan   #3730A3  →  9.93:1 on white   ✓✓  (AAA)  ← primary accent / readable
//   violet #0F766E  →  5.47:1 on white   ✓   (AA)   ← secondary accent
//   green  #047857  →  5.48:1 on white   ✓   (AA)
//   amber  #B45309  →  5.02:1 on white   ✓   (AA)
//   red    #B91C1C  →  5.91:1 on white   ✓   (AA)
//   white  #FFFFFF  →  9.93:1 on cyan    ✓✓  (button labels on filled buttons)

export const T = {
  // ── Backgrounds ──────────────────────────────────────────────────────────────
  bg0:    "#F1F4F9",   // page — soft blue-grey wash
  bg1:    "#FFFFFF",   // card surface — pure white
  bg2:    "#EEF1F8",   // input fill
  bg3:    "#E4E8F3",   // hover / subtle fill

  // ── Borders ──────────────────────────────────────────────────────────────────
  border:  "#D8DCE8",
  border2: "#B8BDD0",

  // ── Text — dark, all WCAG AA+ ─────────────────────────────────────────────────
  text0:  "#1E1B4B",   // primary — deep indigo-black    15.99:1 on white ✓✓
  text1:  "#374151",   // secondary — charcoal           10.31:1 on white ✓✓
  text2:  "#5C6170",   // muted labels                    5.60:1 on bg0   ✓

  // ── Primary accent — Deep Indigo ─────────────────────────────────────────────
  // Used for: badges, active states, progress bars, focus rings, accent text
  cyan:    "#3730A3",   // deep indigo    9.93:1 on white ✓✓
  cyanDim: "#4F46E5",   // medium indigo  6.29:1 on white ✓
  cyanBg:  "#EEF2FF",   // indigo tint bg (used as label background)

  // ── Secondary accent — Deep Teal ─────────────────────────────────────────────
  violet:    "#0F766E",   // deep teal    5.47:1 on white ✓
  violetBg:  "#F0FDFA",   // teal tint bg

  // ── Semantic — Green ─────────────────────────────────────────────────────────
  green:   "#047857",   // emerald-700   5.48:1 on white ✓
  greenBg: "#ECFDF5",

  // ── Semantic — Amber ─────────────────────────────────────────────────────────
  amber:   "#B45309",   // amber-700     5.02:1 on white ✓ (NOT light #F59E0B)
  amberBg: "#FFFBEB",

  // ── Semantic — Red ────────────────────────────────────────────────────────────
  red:     "#B91C1C",   // red-700       5.91:1 on white ✓ (NOT light #EF4444)
  redBg:   "#FEF2F2",
  redDim:  "#DC2626",   // red-600 — for borders only (not text on light bg)

  // ── Decorative — Orange (borders / stripes / glows ONLY — never as text) ────
  orange:    "#F97316",
  orangeBg:  "#FFF7ED",

  // ── Utility ──────────────────────────────────────────────────────────────────
  blue:    "#1D4ED8",   // blue-700   7.13:1 on white ✓

  // ── Typography ───────────────────────────────────────────────────────────────
  mono: "'IBM Plex Mono', 'Courier New', monospace",
  sans: "'Inter', system-ui, -apple-system, sans-serif",
};

// ── Formatters ────────────────────────────────────────────────────────────────
export const fmt = (n) =>
  n == null
    ? "—"
    : "₹" +
      Number(n).toLocaleString("en-IN", {
        maximumFractionDigits: 0,
      });

export const fmtFull = (n) =>
  n == null
    ? "—"
    : "₹" +
      Number(n).toLocaleString("en-IN", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      });