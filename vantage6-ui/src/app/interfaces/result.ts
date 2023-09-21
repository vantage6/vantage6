import { ResType } from '../shared/enum';
import { deepcopy } from '../shared/utils';

export interface Result {
  id: number;
  type: string;
  result: string;
}

export const EMPTY_RESULT: Result = {
  id: -1,
  type: ResType.RESULT,
  result: '',
};

export function getEmptyResult(): Result {
  return deepcopy(EMPTY_RESULT);
}
