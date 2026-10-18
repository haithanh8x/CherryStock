/** Frontend-wide design tokens: edit themes here to update every page and chart. */
export const THEMES = {
  cherry_dark: {
    "--bg": "#07111f",
    "--surface": "#0f1b2d",
    "--surface-alt": "#15263b",
    "--surface-raised": "#1a3049",
    "--border": "#2a4259",
    "--text": "#e5edf7",
    "--muted": "#839ab1",
    "--primary": "#5b9ccc",
    "--positive": "#22c55e",
    "--negative": "#ef5555",
    "--warning": "#f4b04b",
    "--chart-vni": "#44c2bd",
    "--chart-spx": "#8da0ff",
    "--chart-ndx": "#d29dff",
    "--chart-btc": "#ffad52",
    "--chart-gold": "#ffd166",
    "--chart-oil": "#ea6f8e",
    "--chart-dxy": "#81a8b8",
    "--chart-usdvnd": "#ee9d52",
    "--chart-ma20": "#45c7d4",
    "--chart-ma50": "#7fb0f6",
    "--chart-ma100": "#e5b35b",
    "--chart-ma200": "#ba9fe7",
  },
  cherry_light: {
    "--bg": "#f4f7fb",
    "--surface": "#ffffff",
    "--surface-alt": "#eff4f9",
    "--surface-raised": "#e7eef6",
    "--border": "#d5e0ea",
    "--text": "#16263a",
    "--muted": "#657b90",
    "--primary": "#177ca8",
    "--positive": "#15803d",
    "--negative": "#dc2626",
    "--warning": "#b7791f",
    "--chart-vni": "#008c8b",
    "--chart-spx": "#4c64d9",
    "--chart-ndx": "#965aca",
    "--chart-btc": "#cf781e",
    "--chart-gold": "#b68c16",
    "--chart-oil": "#d6456b",
    "--chart-dxy": "#657e8e",
    "--chart-usdvnd": "#c17b17",
    "--chart-ma20": "#008c9c",
    "--chart-ma50": "#4775c0",
    "--chart-ma100": "#b88125",
    "--chart-ma200": "#845cc1",
  },
} as const;

export type ThemeName = keyof typeof THEMES;
export const DEFAULT_THEME: ThemeName = "cherry_dark";
export function resolveTheme(stored: string | null): ThemeName {
  return stored === "cherry_light" || stored === "cherry_dark" ? stored : DEFAULT_THEME;
}
export function applyTheme(name: ThemeName): void {
  const root = document.documentElement;
  const tokens = THEMES[name];
  for (const [key, value] of Object.entries(tokens)) root.style.setProperty(key, value);
  root.dataset.theme = name;
  root.style.colorScheme = name === "cherry_dark" ? "dark" : "light";
}
