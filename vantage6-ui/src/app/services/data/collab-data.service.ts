import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Collaboration } from 'src/app/interfaces/collaboration';
import { Organization } from 'src/app/interfaces/organization';
import { Resource } from 'src/app/shared/types';
import { ApiCollaborationService } from '../api/api-collaboration.service';
import { ConvertJsonService } from '../common/convert-json.service';
import { BaseDataService } from './base-data.service';

@Injectable({
  providedIn: 'root',
})
export class CollabDataService extends BaseDataService {
  constructor(
    protected apiCollabService: ApiCollaborationService,
    protected convertJsonService: ConvertJsonService
  ) {
    super(apiCollabService, convertJsonService);
  }

  async list(
    organizations: Organization[] = [],
    force_refresh: boolean = false
  ): Promise<Observable<Collaboration[]>> {
    return (await super.list_base(
      this.convertJsonService.getCollaboration,
      [organizations],
      force_refresh
    )) as Observable<Collaboration[]>;
  }
}
