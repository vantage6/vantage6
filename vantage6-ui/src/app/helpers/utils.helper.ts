export function isNested(data: object): boolean {
  return Object.values(data).some((value) => typeof value === 'object');
}

export function isTruthy(value: string | boolean | unknown): boolean {
  if (typeof value === 'string') {
    return value.toLowerCase() === 'true';
  }
  return !!value;
}
