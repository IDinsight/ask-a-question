/**
 * Categorical colours for content-performance charts, in fixed order.
 * Slot 1 is the brand chart blue (--chart-1); the rest follow the dataviz
 * reference order. Checked with the dataviz palette validator on a white
 * surface: passes lightness, chroma, colour-blind and normal-vision separation.
 * Slots 3–5 are below 3:1 contrast, so every chart using them also has a
 * legend and the table below acts as the table view.
 */
export const SERIES_COLORS = ["#264D96", "#EB6834", "#1BAF7A", "#EDA100", "#E87BA4"];
