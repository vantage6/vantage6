import { deepcopy } from 'src/app/shared/utils';

export interface Node {
  id: number;
  name: string;
  collaboration_id: number;
  organization_id: number;
  ip: string;
  is_online: boolean;
  api_key?: string;
}

export const EMPTY_NODE: Node = {
  id: -1,
  name: '',
  collaboration_id: -1,
  organization_id: -1,
  ip: '',
  is_online: false,
};

export function getEmptyNode(): Node {
  return deepcopy(EMPTY_NODE);
}
