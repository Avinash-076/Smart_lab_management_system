
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
  };

  return <svg {...p}>{i[type] || i.computer}</svg>;
};

export default Icon;