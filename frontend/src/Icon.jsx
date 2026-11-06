import React from "react";

const PATHS = {
  tag: <><path d="M3 12V4h8l10 10-8 8z" /><circle cx="7.5" cy="8.5" r="1.2" /></>,
  laptop: <><rect x="3" y="4" width="18" height="12" rx="2" /><path d="M2 20h20" /></>,
  phone: <><rect x="7" y="2" width="10" height="20" rx="2.5" /><path d="M11 18h2" /></>,
  gamepad: <><path d="M6 11h4M8 9v4" /><circle cx="15" cy="12" r="1" /><circle cx="18" cy="10" r="1" /><path d="M17.3 5H6.7a4 4 0 0 0-3.9 3.3L2 14a3 3 0 0 0 5.2 2.2L9 14h6l1.8 2.2A3 3 0 0 0 22 14l-.8-5.7A4 4 0 0 0 17.3 5z" /></>,
  code: <path d="m8 8-4 4 4 4M16 8l4 4-4 4M14 5l-4 14" />,
  briefcase: <><rect x="3" y="7" width="18" height="13" rx="2" /><path d="M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2M3 13h18" /></>,
  cap: <><path d="M2 9l10-5 10 5-10 5z" /><path d="M6 11v5c0 1.5 2.7 3 6 3s6-1.5 6-3v-5" /></>,
  camera: <><path d="M4 8h3l2-3h6l2 3h3a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1z" /><circle cx="12" cy="13" r="3.5" /></>,
  battery: <><rect x="2" y="8" width="17" height="8" rx="2" /><path d="M22 11v2M6 11v2M10 11v2" /></>,
  sun: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></>,
  wallet: <><path d="M3 7a2 2 0 0 1 2-2h13v4" /><rect x="3" y="7" width="18" height="13" rx="2" /><path d="M16 14h2" /></>,
  shield: <><path d="M12 3l8 3v6c0 4.5-3.2 8-8 9-4.8-1-8-4.5-8-9V6z" /><path d="m9 12 2 2 4-4" /></>,
  external: <path d="M15 3h6v6M10 14 21 3M21 14v5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5" />,
  chevron: <path d="m6 9 6 6 6-6" />,
  alert: <><path d="M12 3l10 18H2z" /><path d="M12 10v5M12 18h.01" /></>,
  reset: <><path d="M3 12a9 9 0 1 0 3-6.7L3 8" /><path d="M3 3v5h5" /></>,
  send: <><path d="M22 2 11 13" /><path d="M22 2l-7 20-4-9-9-4z" /></>,
  search: <><circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" /></>,
  check: <path d="m5 12 5 5 9-10" />,
};

export default function Icon({ name, size = 20, strokeWidth = 1.8, className }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
         strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round"
         className={className} aria-hidden="true">
      {PATHS[name]}
    </svg>
  );
}
