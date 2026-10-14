
/* =====================================================
   ICONS
===================================================== */

const Icon = ({ type, size = 20 }) => {
  const p = {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round",
    strokeLinejoin: "round",
  };

  const i = {
    menu: (
      <>
        <path d="M4 6h16" />
        <path d="M4 12h16" />
        <path d="M4 18h16" />
      </>
    ),

    home: (
      <>
        <path d="m3 11 9-7 9 7" />
        <path d="M5 10v10h14V10" />
        <path d="M9 20v-6h6v6" />
      </>
    ),

    computer: (
      <>
        <rect x="3" y="4" width="18" height="13" rx="2" />
        <path d="M8 21h8" />
        <path d="M12 17v4" />
      </>
    ),

    details: (
      <>
        <rect x="4" y="3" width="16" height="18" rx="2" />
        <path d="M8 7h8" />
        <path d="M8 11h8" />
        <path d="M8 15h5" />
      </>
    ),

    software: (
      <>
        <path d="m12 3 8 4.5v9L12 21l-8-4.5v-9L12 3Z" />
        <path d="m4.5 7.5 7.5 4 7.5-4" />
        <path d="M12 12v9" />
      </>
    ),

    issue: (
      <>
        <path d="M5 3h10l4 4v14H5z" />
        <path d="M15 3v5h4" />
        <path d="M9 12h6" />
        <path d="M9 16h4" />
      </>
    ),

    maintenance: (
      <path d="M14 6a5 5 0 0 0-6.5 6.5L4 16l4 4 3.5-3.5A5 5 0 0 0 18 10l-3 3-4-4 3-3Z" />
    ),

    reports: (
      <>
        <path d="M5 3h10l4 4v14H5z" />
        <path d="M15 3v5h4" />
        <path d="M8 16v-3" />
        <path d="M12 16v-5" />
        <path d="M16 16v-7" />
      </>
    ),

    settings: (
      <>
        <circle cx="12" cy="12" r="3" />
        <path d="M19 15l2 1-2 3-2-1a7 7 0 0 1-2 1l-.3 2h-3.4L11 19a7 7 0 0 1-2-1l-2 1-2-3 2-1a7 7 0 0 1 0-2l-2-1 2-3 2 1a7 7 0 0 1 2-1l.3-2h3.4L15 6a7 7 0 0 1 2 1l2-1 2 3-2 1a7 7 0 0 1 0 2Z" />
      </>
    ),

    users: (
      <>
        <circle cx="9" cy="8" r="3" />
        <path d="M3 20a6 6 0 0 1 12 0" />
        <circle cx="17" cy="9" r="2.5" />
        <path d="M16 14a5 5 0 0 1 5 5" />
      </>
    ),

    audit: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v5l3 3" />
      </>
    ),

    logout: (
      <>
        <path d="M10 5H5v14h5" />
        <path d="M14 8l4 4-4 4" />
        <path d="M18 12H9" />
      </>
    ),

    search: (
      <>
        <circle cx="11" cy="11" r="6.5" />
        <path d="m16 16 5 5" />
      </>
    ),

    bell: (
      <>
        <path d="M18 9a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" />
        <path d="M10 21h4" />
      </>
    ),

    upload: (
      <>
        <path d="M12 16V4" />
        <path d="M7 9l5-5 5 5" />
        <path d="M5 14v5h14v-5" />
      </>
    ),

    refresh: (
      <>
        <path d="M20 11a8 8 0 0 0-14-4L4 9" />
        <path d="M4 4v5h5" />
        <path d="M4 13a8 8 0 0 0 14 4l2-2" />
        <path d="M20 20v-5h-5" />
      </>
    ),

    filter: (
      <>
        <path d="M4 5h16" />
        <path d="M7 12h10" />
        <path d="M10 19h4" />
      </>
    ),

    eye: (
      <>
        <path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12Z" />
        <circle cx="12" cy="12" r="2.5" />
      </>
    ),

    edit: (
      <>
        <path d="M4 20h4L19 9l-4-4L4 16v4Z" />
        <path d="m13 6 4 4" />
      </>
    ),

    trash: (
      <>
        <path d="M4 7h16" />
        <path d="M10 11v6" />
        <path d="M14 11v6" />
        <path d="M6 7l1 14h10l1-14" />
        <path d="M9 7V4h6v3" />
      </>
    ),

    windows: (
      <>
        <path
          d="M3 5.5 10 4v7H3zM11 3.8 21 2v9H11zM3 12h7v8l-7-1.5zM11 12h10v10l-10-1.8z"
          fill="currentColor"
          stroke="none"
        />
      </>
    ),

    grid: (
      <>
        <rect x="3" y="3" width="7" height="7" rx="1.5" />
        <rect x="14" y="3" width="7" height="7" rx="1.5" />
        <rect x="14" y="14" width="7" height="7" rx="1.5" />
        <rect x="3" y="14" width="7" height="7" rx="1.5" />
      </>
    ),

    dashboard: (
      <>
        <rect x="3" y="3" width="7" height="7" rx="1.5" />
        <rect x="14" y="3" width="7" height="7" rx="1.5" />
        <rect x="14" y="14" width="7" height="7" rx="1.5" />
        <rect x="3" y="14" width="7" height="7" rx="1.5" />
      </>
    ),

    "chevron-down": (
      <path d="m6 9 6 6 6-6" />
    ),

    "chevron-left": (
      <path d="m15 18-6-6 6-6" />
    ),

    "chevron-right": (
      <path d="m9 18 6-6-6-6" />
    ),

    "chevrons-left": (
      <>
        <polyline points="11 17 6 12 11 7" />
        <polyline points="18 17 13 12 18 7" />
      </>
    ),

    "chevrons-right": (
      <>
        <polyline points="13 17 18 12 13 7" />
        <polyline points="6 17 11 12 6 7" />
      </>
    ),

    "arrow-left": (
      <>
        <line x1="19" y1="12" x2="5" y2="12" />
        <polyline points="12 19 5 12 12 5" />
      </>
    ),

    plus: (
      <>
        <path d="M12 5v14" />
        <path d="M5 12h14" />
      </>
    ),

    pulse: (
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
    ),

    box: (
      <>
        <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
        <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
        <line x1="12" y1="22.08" x2="12" y2="12" />
      </>
    ),

    apple: (
      <path
        d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.81-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M15.97 6.42c.6-1.06.99-2.22.86-3.42-1.08.05-2.38.72-3.12 1.62-.64.77-.99 2-.85 3.19 1.2.09 2.51-.33 3.11-1.39z"
        fill="currentColor"
        stroke="none"
      />
    ),

    linux: (
      <path
        d="M12 2C9.5 2 8 3.8 8 6.5v2.8C6.3 10.3 5 12.5 5 15c0 1.5.6 2.5 1.5 3.2-.3 1.2.3 2.3 1.5 2.8.9.4 2.2.3 3-.3.7.2 1.4.3 2 .3s1.3-.1 2-.3c.8.6 2.1.7 3 .3 1.2-.5 1.8-1.6 1.5-2.8.9-.7 1.5-1.7 1.5-3.2 0-2.5-1.3-4.7-3-5.7V6.5C17 3.8 15.5 2 12 2z"
        fill="currentColor"
        stroke="none"
      />
    ),

    "more-vertical": (
      <>
        <circle cx="12" cy="12" r="1.5" />
        <circle cx="12" cy="5" r="1.5" />
        <circle cx="12" cy="19" r="1.5" />
      </>
    ),

    sort: (
      <>
        <path d="m7 15 5 5 5-5" />
        <path d="m7 9 5-5 5 5" />
      </>
    ),

    "clear-filter": (
      <>
        <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
        <line x1="1" y1="1" x2="23" y2="23" />
      </>
    ),

    export: (
      <>
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
        <polyline points="17 8 12 3 7 8" />
        <line x1="12" y1="3" x2="12" y2="15" />
      </>
    ),

    chip: (
      <>
        <rect x="5" y="5" width="14" height="14" rx="2" />
        <rect x="9" y="9" width="6" height="6" />
        <path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3" />
      </>
    ),

    cpu: (
      <>
        <rect x="5" y="5" width="14" height="14" rx="2" />
        <rect x="9" y="9" width="6" height="6" />
        <path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3" />
      </>
    ),

    ram: (
      <>
        <rect x="3" y="7" width="18" height="10" rx="1.5" />
        <path d="M7 11h2v3H7zM11 11h2v3h-2zM15 11h2v3h-2z" />
        <path d="M6 17v2M10 17v2M14 17v2M18 17v2" />
      </>
    ),

    memory: (
      <>
        <rect x="3" y="7" width="18" height="10" rx="1.5" />
        <path d="M7 11h2v3H7zM11 11h2v3h-2zM15 11h2v3h-2z" />
        <path d="M6 17v2M10 17v2M14 17v2M18 17v2" />
      </>
    ),

    storage: (
      <>
        <rect x="3" y="5" width="18" height="14" rx="2" />
        <circle cx="7" cy="12" r="1.5" fill="currentColor" />
        <line x1="11" y1="12" x2="17" y2="12" />
      </>
    ),

    gpu: (
      <>
        <rect x="3" y="4" width="18" height="12" rx="2" />
        <line x1="8" y1="20" x2="16" y2="20" />
        <line x1="12" y1="16" x2="12" y2="20" />
      </>
    ),

    network: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M3.6 9h16.8M3.6 15h16.8" />
        <path d="M12 3a15 15 0 0 1 0 18M12 3a15 15 0 0 0 0 18" />
      </>
    ),

    motherboard: (
      <>
        <rect x="3" y="3" width="18" height="18" rx="2" />
        <rect x="6" y="6" width="5" height="5" />
        <path d="M15 6h3M15 9h3M15 12h3M6 15h3M6 18h3M13 16h5v2h-5z" />
      </>
    ),

    clock: (
      <>
        <circle cx="12" cy="12" r="9" />
        <polyline points="12 7 12 12 15 14" />
      </>
    ),

    uptime: (
      <>
        <circle cx="12" cy="12" r="9" />
        <polyline points="12 7 12 12 15 14" />
      </>
    ),

    command: (
      <>
        <polyline points="16 18 22 12 16 6" />
        <polyline points="8 6 2 12 8 18" />
      </>
    ),

    info: (
      <>
        <circle cx="12" cy="12" r="9" />
        <line x1="12" y1="8" x2="12" y2="8.01" strokeWidth="2.5" />
        <line x1="12" y1="11" x2="12" y2="16" />
      </>
    ),

    "arrow-down": (
      <>
        <line x1="12" y1="5" x2="12" y2="19" />
        <polyline points="19 12 12 19 5 12" />
      </>
    ),

    "arrow-up": (
      <>
        <line x1="12" y1="19" x2="12" y2="5" />
        <polyline points="5 12 12 5 19 12" />
      </>
    ),

    calendar: (
      <>
        <rect x="3" y="4" width="18" height="18" rx="2" />
        <line x1="16" y1="2" x2="16" y2="6" />
        <line x1="8" y1="2" x2="8" y2="6" />
        <line x1="3" y1="10" x2="21" y2="10" />
      </>
    ),

    nodes: (
      <>
        <circle cx="18" cy="5" r="3" />
        <circle cx="6" cy="12" r="3" />
        <circle cx="18" cy="19" r="3" />
        <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" />
        <line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
      </>
    ),

    disk: (
      <>
        <ellipse cx="12" cy="5" rx="9" ry="3" />
        <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
        <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
      </>
    ),
  };

  return <svg {...p}>{i[type] || i.computer}</svg>;
};

export default Icon;