import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Resource } from 'src/app/shared/types';
import { ApiNodeService } from 'src/app/services/api/api-node.service';
import { ConvertJsonService } from 'src/app/services/common/convert-json.service';
import { BaseDataService } from 'src/app/services/data/base-data.service';
import { Node } from 'src/app/interfaces/node';

@Injectable({
  providedIn: 'root',
})
export class NodeDataService extends BaseDataService {
  constructor(
    protected apiService: ApiNodeService,
    protected convertJsonService: ConvertJsonService
  ) {
    super(apiService, convertJsonService);
  }

  async get(
    id: number,
    force_refresh: boolean = false
  ): Promise<Observable<Node>> {
    return (await super.get_base(
      id,
      this.convertJsonService.getNode,
      [],
      force_refresh
    )) as Observable<Node>;
  }

  async list(force_refresh: boolean = false): Promise<Observable<Node[]>> {
    return (await super.list_base(
      this.convertJsonService.getNode,
      [],
      force_refresh
    )) as Observable<Node[]>;
  }
}
