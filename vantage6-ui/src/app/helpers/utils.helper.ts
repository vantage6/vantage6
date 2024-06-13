export function isNested(data: any): boolean {
  return Object.values(data).some((value) => typeof value === 'object');
}
