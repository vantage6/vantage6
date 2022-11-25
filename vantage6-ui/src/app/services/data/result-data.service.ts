import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { Result } from 'src/app/interfaces/result';
import { TaskStatus } from 'src/app/shared/enum';
import { filterArrayByProperty } from 'src/app/shared/utils';
import { ResultApiService } from '../api/result-api.service';
import { ConvertJsonService } from '../common/convert-json.service';
import { SocketioConnectService } from '../common/socketio-connect.service';
import { BaseDataService } from './base-data.service';

@Injectable({
  providedIn: 'root',
})
export class ResultDataService extends BaseDataService {
  queried_task_ids: number[] = [];
  resources_per_task: { [task_id: number]: BehaviorSubject<Result[]> } = {};

  // TODO update on result updates
  constructor(
    protected apiService: ResultApiService,
    protected convertJsonService: ConvertJsonService,
    private socketConnectService: SocketioConnectService
  ) {
    super(apiService, convertJsonService);
    // subscribe to changes communicated via socket
    this.socketConnectService
      .getAlgorithmStatusUpdates()
      .subscribe((update) => {
        this.updateResultOnSocketEvent(update);
      });
    this.resource_list.subscribe((resources) => {
      // When the list of all resources is updated, ensure that observables
      // by task id
      this.updateObsPerTask(resources as Result[]);
    });
  }

  updateObsPerTask(resources: Result[]): void {
    if (this.queried_task_ids.length === 0) return;
    for (let task_id of this.queried_task_ids) {
      if (task_id in this.resources_per_task) {
        this.resources_per_task[task_id].next(
          filterArrayByProperty(resources, 'task_id', task_id)
        );
      } else {
        this.resources_per_task[task_id] = new BehaviorSubject<Result[]>(
          filterArrayByProperty(resources, 'task_id', task_id)
        );
      }
    }
  }

  async get_by_task_id(
    task_id: number,
    force_refresh: boolean = false
  ): Promise<Observable<Result[]>> {
    // get resources by task ID
    if (force_refresh || !this.queried_task_ids.includes(task_id)) {
      if (!(task_id in this.resources_per_task)) {
        // create empty observable as task id had not yet been queried
        this.resources_per_task[task_id] = new BehaviorSubject<Result[]>([]);
      }
      if (!this.queried_task_ids.includes(task_id)) {
        this.queried_task_ids.push(task_id);
      }
      let results = await this.apiService.getResourcesByTaskId(task_id);
      this.saveMultiple(results);
    }
    return this.resources_per_task[task_id].asObservable();
  }

  save(result: Result) {
    // don't save organization along with result as this can lead to loop
    // of saves when then the organization is updated, then result again, etc
    if (result.organization) result.organization = undefined;
    super.save(result);
  }

  updateResultOnSocketEvent(data: any): void {
    if (data.status === TaskStatus.COMPLETED) {
      // TODO improve this code: now we wait for 5 seconds to retrieve results
      // when we get a socket update says result is finished, so that we are
      // 'sure' the results are updated in the database
      setTimeout(() => {
        this.get_base(data.result_id, this.convertJsonService.getResult, true);
      }, 5000);
    }
    let results = this.resource_list.value;
    for (let result of results as Result[]) {
      if (result.id === data.result_id) {
        result.status = data.status;
        break;
      }
    }
    this.resource_list.next(results);
  }
}
