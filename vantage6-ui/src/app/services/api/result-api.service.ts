import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Result } from 'src/app/interfaces/result';
import { ResType } from 'src/app/shared/enum';
import { environment } from 'src/environments/environment';
import { ConvertJsonService } from '../common/convert-json.service';
import { ModalService } from '../common/modal.service';
import { BaseApiService } from './base-api.service';

@Injectable({
  providedIn: 'root',
})
export class ResultApiService extends BaseApiService {
  constructor(
    protected http: HttpClient,
    protected modalService: ModalService,
    private convertJsonService: ConvertJsonService
  ) {
    super(ResType.RESULT, http, modalService);
  }

  get_by_task_id(task_id: number) {
    return this.http.get(environment.api_url + '/task/' + task_id + '/result');
  }

  // TODO this function is only required when creating/updating resources, so
  // for a result it is never used I think (?)
  get_data(result: Result): any {
    let data: any = {
      input: result.input,
      result: result.result,
      log: result.log,
      task_id: result.task_id,
      organization_id: result.organization_id,
      ports: result.ports,
      started_at: result.started_at,
      assigned_at: result.assigned_at,
      finished_at: result.finished_at,
      port_ids: result.port_ids,
    };
    return data;
  }

  async getResourcesByTaskId(task_id: number): Promise<Result[]> {
    // get data of resources that logged-in user is allowed to view
    let json_data: any = await this.get_by_task_id(task_id).toPromise();

    let results: Result[] = [];
    for (let dic of json_data) {
      results.push(this.convertJsonService.getResult(dic));
    }
    return results;
  }
}
