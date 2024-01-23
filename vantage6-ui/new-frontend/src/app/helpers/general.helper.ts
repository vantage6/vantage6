export const isEqualString = (s1: string, s2: string): boolean => {
  return s1?.toLowerCase() === s2?.toLowerCase();
};

/* Remove percentage characters in string */
export const unlikeApiParameter = (parameter?: string): string | undefined => {
  return parameter ? parameter.replace(/%/g, '') : parameter;
};
