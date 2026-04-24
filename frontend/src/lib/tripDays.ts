function parseDateParts(dateStr: string): [number, number, number] | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(dateStr);
  if (!match) return null;
  return [Number(match[1]), Number(match[2]), Number(match[3])];
}

export function normalizeIsoDate(dateStr?: string): string | undefined {
  if (!dateStr) return undefined;
  const candidate = dateStr.trim().slice(0, 10);
  return parseDateParts(candidate) ? candidate : undefined;
}

export function parseIsoDate(dateStr: string): Date {
  const parts = parseDateParts(dateStr);
  if (!parts) return new Date(NaN);
  const [year, month, day] = parts;
  return new Date(year, month - 1, day, 12, 0, 0, 0);
}

export function toIsoDateString(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function addDaysToIsoDate(startDate: string, dayOffset: number): string {
  const base = parseIsoDate(startDate);
  base.setDate(base.getDate() + dayOffset);
  return toIsoDateString(base);
}

export function computeExpectedTripDayCount(startDate: string, endDate: string): number {
  const start = parseIsoDate(startDate);
  const end = parseIsoDate(endDate);
  const millisPerDay = 1000 * 60 * 60 * 24;
  return Math.floor((end.getTime() - start.getTime()) / millisPerDay) + 1;
}

export function expectedDayNumbers(startDate: string, endDate: string): number[] {
  const count = computeExpectedTripDayCount(startDate, endDate);
  if (count <= 0) return [];
  return Array.from({ length: count }, (_, i) => i + 1);
}

export function missingDayNumbers(expected: number[], actual: number[]): number[] {
  const actualSet = new Set(actual);
  return expected.filter((dayNum) => !actualSet.has(dayNum));
}
