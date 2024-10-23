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
