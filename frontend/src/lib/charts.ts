export function formatPercentage(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

export function createLinePath(values: number[], width: number, height: number): string {
  const count = values.length;
  if (!count) return "";
  const maxValue = Math.max(...values, 1);
  const minValue = Math.min(...values, 0);
  const scaleY = (v: number) => height - ((v - minValue) / (maxValue - minValue || 1)) * height;
  const step = width / Math.max(count - 1, 1);
  return values
    .map((value, index) => `${index === 0 ? "M" : "L"} ${index * step} ${scaleY(value)}`)
    .join(" ");
}

export function createStabilitySeries(values: number[]): number[] {
  if (values.length <= 1) {
    return values.map(() => 1);
  }
  const deltas = values.map((value, index) => (index === 0 ? 0 : Math.abs(value - values[index - 1])));
  const maxDelta = Math.max(...deltas.slice(1), 0.01);
  return deltas.map((delta) => 1 - Math.min(1, delta / maxDelta));
}
