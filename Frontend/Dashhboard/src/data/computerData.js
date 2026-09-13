
/* =====================================================
   COMPUTER DATA
===================================================== */

const base = Array.from({ length: 24 }, (_, i) => {
  const n = i + 1;
  const off = [5, 7, 12, 16, 20, 24].includes(n);
  const w11 = n % 2 === 1;
  const total = w11 ? 512 : 256;

  return {
    id: n,
    name: `PC-${String(n).padStart(2, "0")}`,
    ip: `192.168.1.${100 + n}`,
    os:
      n === 7
        ? "Windows 7 Ultimate 64-bit"
        : `${w11 ? "Windows 11" : "Windows 10"} Pro 64-bit`,
    cpu: w11
      ? "Intel Core i5-10400 @ 2.90GHz"
      : "Intel Core i5-9400 @ 2.90GHz",
    ram: w11 ? "16 GB" : "8 GB",
    free: [
      256, 120, 300, 180, 80, 200, 40, 150, 280, 110, 350, 90, 220, 130,
      410, 70, 260, 140, 380, 60, 290, 125, 320, 55,
    ][i],
    total,
    last: n <= 16 ? "21 May 2025" : "20 May 2025",
    time: "10:15 AM",
    status: off ? "Offline" : "Online",
    lab: n <= 12 ? "Lab 1" : "Lab 2",
  };
});