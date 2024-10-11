import { DefaultValueType } from '../models/api/algorithm.model';

export const getDefaultValueType = (value: string | number | boolean | null | undefined): DefaultValueType => {
  if (value === null || value === undefined) return DefaultValueType.None;
  if (typeof value === 'string') return DefaultValueType.String;
  if (typeof value === 'boolean') return DefaultValueType.Boolean;
  // for number, check if integer
  if (typeof value === 'number') {
    if (Number.isInteger(value)) return DefaultValueType.Integer;
    return DefaultValueType.Float;
  }
  // If we can't determine the type, default to string
  return DefaultValueType.String;
};
