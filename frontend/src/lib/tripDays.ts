export function parseIsoDate(dateStr: string): Date {
  return new Date(`${dateStr}T00:00:00`);
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
