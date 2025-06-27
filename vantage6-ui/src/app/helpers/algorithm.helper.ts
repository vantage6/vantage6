import { ArgumentType } from '../models/api/algorithm.model';

export const isListTypeArgument = (type: string) => {
  return (
    type === ArgumentType.ColumnList ||
    type === ArgumentType.FloatList ||
    type === ArgumentType.IntegerList ||
    type === ArgumentType.StringList ||
    type === ArgumentType.OrganizationList
  );
};

export const isArgumentWithAllowedValues = (type: string) => {
  return (
    type === ArgumentType.String ||
    type === ArgumentType.Integer ||
    type === ArgumentType.Float
  );
};
