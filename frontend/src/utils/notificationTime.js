const rtf = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });

const UNITS = [
  ["year", 31536000000],
  ["month", 2592000000],
  ["week", 604800000],
  ["day", 86400000],
  ["hour", 3600000],
  ["minute", 60000],
  ["second", 1000],
];

export function formatRelativeTime(value) {
  if (!value) return "";

  const date = value instanceof Date ? value : new Date(value);
  const timestamp = date.getTime();

  if (Number.isNaN(timestamp)) return "";

  const diff = timestamp - Date.now();
  const absDiff = Math.abs(diff);
  const [unit, unitMs] =
    UNITS.find(([, ms]) => absDiff >= ms) || UNITS[UNITS.length - 1];

  return rtf.format(Math.round(diff / unitMs), unit);
}
