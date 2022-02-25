import { ResType } from 'src/app/shared/enum';
import { deepcopy } from 'src/app/shared/utils';

export interface Node {
  id: number;
  type: string;
  name: string;
  collaboration_id: number;
  organization_id: number;
  ip: string;
  is_online: boolean;
  last_seen: Date | null;
  api_key?: string;
}

export const EMPTY_NODE: Node = {
  id: -1,
  type: ResType.NODE,
  name: '',
  collaboration_id: -1,
  organization_id: -1,
  ip: '',
  last_seen: null,
  is_online: false,
};

export function getEmptyNode(): Node {
  return deepcopy(EMPTY_NODE);
}
