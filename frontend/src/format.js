export const rs = (n) => "Rs " + Math.round(Number(n) || 0).toLocaleString("en-US");

// 150000 -> "1.5 lakh", 80000 -> "80k"
export const lakh = (n) =>
  n >= 100000 ? `${parseFloat((n / 100000).toFixed(2))} lakh` : `${Math.round(n / 1000)}k`;
