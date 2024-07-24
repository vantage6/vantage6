export const isEqualString = (s1: string, s2: string): boolean => {
  return s1?.toLowerCase() === s2?.toLowerCase();
};

/* Remove percentage characters in string */
export const unlikeApiParameter = (parameter?: string): string | undefined => {
  return parameter ? parameter.replace(/%/g, '') : parameter;
};

export const compareObjIDs = (obj1: any, obj2: any): boolean => {
  // Compare that with the ID of the objects are the same
  return obj1 && obj2 && obj1.id && obj2.id && obj1.id === obj2.id;
};

export const capitalize = (s: string): string => s && s[0].toUpperCase() + s.slice(1);

export const printDate = (date: string | undefined): string => {
  // note appending the 'Z' which indicates that the string is in UTC time
  return date ? new Date(date + 'Z').toLocaleString() : '-';
};
