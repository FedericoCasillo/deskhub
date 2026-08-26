const base = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round",
  strokeLinejoin: "round",
};

export function IconUsers({ className }) {
  return (
    <svg className={className} {...base}>
      <circle cx="9" cy="8" r="3.5" />
      <path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6" />
      <path d="M16 8.5a3 3 0 1 1 3.2 3M21 20c0-2.8-2-5-4.6-5.6" />
    </svg>
  );
}

export function IconPlay({ className }) {
  return (
    <svg className={className} {...base}>
      <polygon points="7,4 20,12 7,20" />
    </svg>
  );
}

export function IconSquare({ className }) {
  return (
    <svg className={className} {...base}>
      <rect x="5" y="5" width="14" height="14" rx="2" />
    </svg>
  );
}

export function IconBox({ className }) {
  return (
    <svg className={className} {...base}>
      <path d="M4 8l8-4 8 4-8 4-8-4Z" />
      <path d="M4 8v8l8 4 8-4V8" />
      <path d="M12 12v8" />
    </svg>
  );
}

export function IconRefresh({ className }) {
  return (
    <svg className={className} {...base}>
      <path d="M20 11A8 8 0 0 0 5.6 6.6M4 4v5h5" />
      <path d="M4 13a8 8 0 0 0 14.4 4.4M20 20v-5h-5" />
    </svg>
  );
}

export function IconTrash({ className }) {
  return (
    <svg className={className} {...base}>
      <path d="M4 7h16" />
      <path d="M9 7V4h6v3" />
      <path d="M6 7l1 13h10l1-13" />
      <path d="M10 11v6M14 11v6" />
    </svg>
  );
}

export function IconInfo({ className }) {
  return (
    <svg className={className} {...base}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11v6" />
      <circle cx="12" cy="7.5" r="0.15" fill="currentColor" stroke="none" />
      <path d="M12 7.2v0.6" strokeWidth="2.6" />
    </svg>
  );
}

export function IconList({ className }) {
  return (
    <svg className={className} {...base}>
      <path d="M4 6h16M4 12h11M4 18h14" />
    </svg>
  );
}

export function IconGear({ className }) {
  return (
    <svg className={className} {...base}>
      <circle cx="12" cy="12" r="3" />
      <path d="M12 3v2.2M12 18.8V21M4.9 4.9l1.6 1.6M17.5 17.5l1.6 1.6M3 12h2.2M18.8 12H21M4.9 19.1l1.6-1.6M17.5 6.5l1.6-1.6" />
    </svg>
  );
}

export function IconPlus({ className }) {
  return (
    <svg className={className} {...base}>
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}
