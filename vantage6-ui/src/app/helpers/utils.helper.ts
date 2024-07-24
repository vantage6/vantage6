export function isNested(data: object): boolean {
  return Object.values(data).some((value) => typeof value === 'object');
}
