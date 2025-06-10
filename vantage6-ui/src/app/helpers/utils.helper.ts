export function isNested(data: object): boolean {
  return Object.values(data).some((value) => typeof value === 'object');
}

export function isTruthy(value: string | boolean | unknown): boolean {
  if (typeof value === 'string') {
    return value.toLowerCase() === 'true';
  }
  return !!value;
}

export function getEnumKeyByValue<T extends { [key: string]: string | number }>(enum_class: T, value: string): string {
  return Object.entries(enum_class).find(([, val]) => val === value)?.[0] || '';
}
