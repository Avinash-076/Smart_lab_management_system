/**
 * Returns a high-fidelity SVG icon for well-known software packages.
 * Fallbacks to a vibrant monogram badge or cube icon.
 */
export function SoftwareIcon({ name, publisher, size = 28 }) {
  const n = (name || "").toLowerCase();
  const p = (publisher || "").toLowerCase();

  // 1. Google Chrome
  if (n.includes("chrome") || p.includes("google")) {
    return (
      <svg width={size} height={size} viewBox="0 0 48 48" fill="none">
        <circle cx="24" cy="24" r="20" fill="#EA4335" />
        <path
          d="M24 8h17.3A20 20 0 0 1 36.3 38.6L27.6 23.6A8 8 0 0 0 24 8Z"
          fill="#FBBC05"
        />
        <path
          d="M24 8v16l-7-4a8 8 0 0 0 0 8l-8.7 15A20 20 0 0 1 4 24C4 13 13 4 24 4v4Z"
          fill="#34A853"
        />
        <circle cx="24" cy="24" r="10" fill="#FFFFFF" />
        <circle cx="24" cy="24" r="7" fill="#1A73E8" />
      </svg>
    );
  }

  // 2. Microsoft Edge
  if (n.includes("edge")) {
    return (
      <svg width={size} height={size} viewBox="0 0 48 48" fill="none">
        <circle cx="24" cy="24" r="20" fill="#0078D7" />
        <path
          d="M24 8c8.8 0 16 7.2 16 16 0 7-4.5 13-11 15.1-1.5.5-3.1.9-4.8.9C15.2 40 8 32.8 8 24S15.2 8 24 8Z"
          fill="#00B294"
          opacity="0.85"
        />
        <path
          d="M32 24c0 4.4-3.6 8-8 8s-8-3.6-8-8c0-3 1.7-5.6 4.2-7 1.2-.7 2.5-1 3.8-1 4.4 0 8 3.6 8 8Z"
          fill="#FFFFFF"
        />
      </svg>
    );
  }

  // 3. Visual C++ / Visual Studio
  if (n.includes("visual c++") || n.includes("redistributable") || n.includes("visual studio")) {
    return (
      <svg width={size} height={size} viewBox="0 0 48 48" fill="none">
        <rect width="48" height="48" rx="10" fill="#68217A" />
        <path
          d="M13 25.5l9.5-8.5L34 32l-11.5 5.5L13 25.5Z"
          fill="#9B4F96"
        />
        <path
          d="M34 16l-11.5-5.5L13 22.5l9.5 8.5L34 16Z"
          fill="#C179B7"
        />
        <path
          d="M34 16v16l-6.5-4v-8L34 16Z"
          fill="#E5B2DE"
        />
      </svg>
    );
  }

  // 4. Python
  if (n.includes("python")) {
    return (
      <svg width={size} height={size} viewBox="0 0 48 48" fill="none">
        <rect width="48" height="48" rx="10" fill="#F8FAFC" />
        <path
          d="M23.6 10c-6.4 0-6 2.8-6 2.8l.1 2.9h6.1v.9h-8.5c-3.9 0-6.8 2.4-6.8 6.3 0 4 3 6.1 6.8 6.1h1.9v-2.7c0-3.1 2.7-5.8 5.8-5.8h6.1c2.5 0 4.6-2.1 4.6-4.6v-4.1c0-1.8-1.7-3.8-6.1-3.8h-4v2Zm-1.8 1.8a1 1 0 1 1 0 2 1 1 0 0 1 0-2Z"
          fill="#3776AB"
        />
        <path
          d="M24.4 38c6.4 0 6-2.8 6-2.8l-.1-2.9h-6.1v-.9h8.5c3.9 0 6.8-2.4 6.8-6.3 0-4-3-6.1-6.8-6.1h-1.9v2.7c0 3.1-2.7 5.8-5.8 5.8h-6.1c-2.5 0-4.6 2.1-4.6 4.6v4.1c0 1.8 1.7 3.8 6.1 3.8h4v-2Zm1.8-1.8a1 1 0 1 1 0-2 1 1 0 0 1 0 2Z"
          fill="#FFD43B"
        />
      </svg>
    );
  }

  // 5. Java
  if (n.includes("java") || p.includes("oracle")) {
    return (
      <svg width={size} height={size} viewBox="0 0 48 48" fill="none">
        <rect width="48" height="48" rx="10" fill="#FFF7ED" />
        <path
          d="M20 12c-2 4 1 6 3 8-3-2-5-4-3-8Z"
          fill="#EA580C"
        />
        <path
          d="M25 14c-1.5 3 .8 4.5 2.3 6-2.3-1.5-3.8-3-2.3-6Z"
          fill="#C2410C"
        />
        <path
          d="M15 28c4 1 13 1 17-1 2-1-2-2-5-2-4 0-9 1-12 3Z"
          fill="#0284C7"
        />
        <path
          d="M16 33c3 .8 11 .8 15 0 2-.4-1.5-1.5-4-1.5-4 0-8 .5-11 1.5Z"
          fill="#0369A1"
        />
      </svg>
    );
  }

  // 6. 7-Zip
  if (n.includes("7-zip") || n.includes("7z")) {
    return (
      <svg width={size} height={size} viewBox="0 0 48 48" fill="none">
        <rect width="48" height="48" rx="8" fill="#1E293B" />
        <text
          x="24"
          y="31"
          textAnchor="middle"
          fill="#FFFFFF"
          fontSize="20"
          fontWeight="900"
          fontFamily="system-ui, sans-serif"
        >
          7z
        </text>
      </svg>
    );
  }

  // 7. VLC Media Player
  if (n.includes("vlc") || n.includes("videolan")) {
    return (
      <svg width={size} height={size} viewBox="0 0 48 48" fill="none">
        <rect width="48" height="48" rx="10" fill="#FFFBEB" />
        <path
          d="M24 8l-8 24h16l-8-24Z"
          fill="#F97316"
        />
        <path
          d="M18.7 24h10.6l-2-6H20.7l-2 6Z"
          fill="#FFFFFF"
        />
        <path
          d="M16 32h16l-1.3-4H17.3l-1.3 4Z"
          fill="#FFFFFF"
        />
        <ellipse cx="24" cy="36" rx="14" ry="4" fill="#EA580C" />
      </svg>
    );
  }

  // 8. Microsoft (General / Office / Teams)
  if (p.includes("microsoft") || n.includes("office") || n.includes("teams")) {
    return (
      <svg width={size} height={size} viewBox="0 0 48 48" fill="none">
        <rect width="48" height="48" rx="10" fill="#F8FAFC" />
        <rect x="11" y="11" width="11" height="11" fill="#F25022" />
        <rect x="25" y="11" width="11" height="11" fill="#7FBA00" />
        <rect x="11" y="25" width="11" height="11" fill="#00A4EF" />
        <rect x="25" y="25" width="11" height="11" fill="#FFB900" />
      </svg>
    );
  }

  // 9. Git
  if (n.includes("git")) {
    return (
      <svg width={size} height={size} viewBox="0 0 48 48" fill="none">
        <rect width="48" height="48" rx="10" fill="#FFF1F2" />
        <path
          d="M24 10l14 14-14 14L10 24l14-14Z"
          fill="#F05032"
        />
        <circle cx="20" cy="24" r="3" fill="#FFFFFF" />
        <circle cx="28" cy="24" r="3" fill="#FFFFFF" />
        <line x1="20" y1="24" x2="28" y2="24" stroke="#FFFFFF" strokeWidth="2" />
      </svg>
    );
  }

  // Fallback: Vibrant Monogram Badge
  const letter = (name ? name.trim().charAt(0) : "S").toUpperCase();
  const hues = [
    { bg: "#EFF6FF", fg: "#2563EB", border: "#BFDBFE" },
    { bg: "#F0FDF4", fg: "#16A34A", border: "#BBF7D0" },
    { bg: "#FAF5FF", fg: "#9333EA", border: "#E9D5FF" },
    { bg: "#FFF7ED", fg: "#EA580C", border: "#FED7AA" },
    { bg: "#F0FDFA", fg: "#0D9488", border: "#99F6E4" },
  ];
  const charCode = letter.charCodeAt(0) || 0;
  const color = hues[charCode % hues.length];

  return (
    <div
      style={{
        width: `${size}px`,
        height: `${size}px`,
        borderRadius: "8px",
        background: color.bg,
        border: `1px solid ${color.border}`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontWeight: 700,
        fontSize: `${Math.round(size * 0.45)}px`,
        color: color.fg,
        flexShrink: 0,
      }}
    >
      {letter}
    </div>
  );
}

/**
 * Windows Operating System Icon
 */
export function WindowsLogoIcon({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="#0078D7">
      <path d="M0 3.449L9.75 2.1v9.451H0m10.949-9.602L24 0v11.4H10.949M0 12.6h9.75v9.451L0 20.699M10.949 12.6H24V24l-12.949-1.8" />
    </svg>
  );
}
