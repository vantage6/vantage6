import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Run } from 'src/app/interfaces/run';
import { ResType } from 'src/app/shared/enum';
import { environment } from 'src/environments/environment';
import { ConvertJsonService } from '../common/convert-json.service';
import { ModalService } from '../common/modal.service';
import { BaseApiService } from './base-api.service';

@Injectable({
  providedIn: 'root',
})
export class RunApiService extends BaseApiService {
  constructor(
    protected http: HttpClient,
    protected modalService: ModalService,
    private convertJsonService: ConvertJsonService
  ) {
    super(ResType.RUN, http, modalService);
  }

  get_by_task_id(task_id: number) {
    return this.http.get(environment.api_url + '/run', {
      params: { task_id: task_id },
    });
  }

  // TODO this function is only required when creating/updating resources, so
  // for a result it is never used I think (?)
  get_data(run: Run): any {
    let data: any = {
      input: run.input,
      result: run.result,
      log: run.log,
      task_id: run.task_id,
      organization_id: run.organization_id,
      ports: run.ports,
      started_at: run.started_at,
      assigned_at: run.assigned_at,
      finished_at: run.finished_at,
      port_ids: run.port_ids,
    };
    return data;
  }

  async getResourcesByTaskId(task_id: number): Promise<Run[]> {
    // get data of resources that logged-in user is allowed to view
    let response: any = await this.get_by_task_id(task_id).toPromise();
    let json_data = response.data;

    let runs: Run[] = [];
    for (let dic of json_data) {
      runs.push(this.convertJsonService.getAlgorithmRun(dic));
    }
    return runs;
  }
}
