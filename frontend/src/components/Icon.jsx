// Simple 24px line icons (stroke follows currentColor).
const P = {
  leaf: "M5 19c0-8 5-14 14-14 0 9-6 14-14 14zM5 19l7-7",
  bug: "M9 8a3 3 0 016 0v7a3 3 0 01-6 0zM4 9l4 2M20 9l-4 2M4 16l5-1M20 16l-5-1M9 5L7 3M15 5l2-2",
  cloud: "M7 18a4 4 0 010-8 5 5 0 019.6-1A4.5 4.5 0 0117 18zM8 21l1-2M12 21l1-2M16 21l1-2",
  pin: "M12 21s7-6 7-11a7 7 0 10-14 0c0 5 7 11 7 11zM12 12a2 2 0 100-4 2 2 0 000 4z",
  shield: "M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6zM8.5 12l2.5 2.5 4.5-5",
  camera: "M4 8h3l2-3h6l2 3h3v11H4zM12 17a4 4 0 100-8 4 4 0 000 8z",
  upload: "M12 16V4M7 9l5-5 5 5M4 20h16",
  arrow: "M5 12h14M13 6l6 6-6 6",
  menu: "M4 7h16M4 12h16M4 17h16",
  close: "M6 6l12 12M18 6L6 18",
  copy: "M9 9h10v11H9zM5 15V4h10",
  check: "M5 12.5l4.5 4.5L19 7.5",
  alert: "M12 4l9 16H3zM12 10v4M12 17v.5",
  user: "M12 12a4 4 0 100-8 4 4 0 000 8zM4 21c0-4 4-6 8-6s8 2 8 6",
  search: "M11 18a7 7 0 100-14 7 7 0 000 14zM16 16l5 5",
  list: "M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01",
  users: "M9 11a3.5 3.5 0 100-7 3.5 3.5 0 000 7zM2 20c0-3.5 3-5.5 7-5.5s7 2 7 5.5M17 5a3 3 0 010 6M19 15c2 .6 3 2 3 4",
  book: "M5 4h10a3 3 0 013 3v13H8a3 3 0 01-3-3zM5 17a3 3 0 013-3h10",
};
export default function Icon({ name, size = 20 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7"
         strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false"><path d={P[name]} /></svg>
  );
}
