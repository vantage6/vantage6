import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';
import { Run } from 'src/app/interfaces/run';
import { TaskStatus } from 'src/app/shared/enum';
import { filterArrayByProperty } from 'src/app/shared/utils';
import { RunApiService } from '../api/run-api.service';
import { ConvertJsonService } from '../common/convert-json.service';
import { SocketioConnectService } from '../common/socketio-connect.service';
import { BaseDataService } from './base-data.service';

@Injectable({
  providedIn: 'root',
})
export class RunDataService extends BaseDataService {
  queried_task_ids: number[] = [];
  resources_per_task: { [task_id: number]: BehaviorSubject<Run[]> } = {};

  // TODO update on run updates
  constructor(
    protected apiService: RunApiService,
    protected convertJsonService: ConvertJsonService,
    private socketConnectService: SocketioConnectService
  ) {
    super(apiService, convertJsonService);
    // subscribe to changes communicated via socket
    this.socketConnectService
      .getAlgorithmStatusUpdates()
      .subscribe((update) => {
        this.updateRunOnSocketEvent(update);
      });
    this.resource_list.subscribe((resources) => {
      // When the list of all resources is updated, ensure that observables
      // by task id
      this.updateObsPerTask(resources as Run[]);
    });
  }

  updateObsPerTask(resources: Run[]): void {
    if (this.queried_task_ids.length === 0) return;
    for (let task_id of this.queried_task_ids) {
      if (task_id in this.resources_per_task) {
        this.resources_per_task[task_id].next(
          filterArrayByProperty(resources, 'task_id', task_id)
        );
      } else {
        this.resources_per_task[task_id] = new BehaviorSubject<Run[]>(
          filterArrayByProperty(resources, 'task_id', task_id)
        );
      }
    }
  }

  async get_by_task_id(
    task_id: number,
    force_refresh: boolean = false
  ): Promise<Observable<Run[]>> {
    // get resources by task ID
    if (force_refresh || !this.queried_task_ids.includes(task_id)) {
      if (!(task_id in this.resources_per_task)) {
        // create empty observable as task id had not yet been queried
        this.resources_per_task[task_id] = new BehaviorSubject<Run[]>([]);
      }
      if (!this.queried_task_ids.includes(task_id)) {
        this.queried_task_ids.push(task_id);
      }
      let runs = await this.apiService.getResourcesByTaskId(task_id);
      this.saveMultiple(runs);
    }
    return this.resources_per_task[task_id].asObservable();
  }

  save(run: Run) {
    // don't save organization along with run as this can lead to loop
    // of saves when then the organization is updated, then run again, etc
    if (run.organization) run.organization = undefined;
    super.save(run);
  }

  updateRunOnSocketEvent(data: any): void {
    if (data.status === TaskStatus.COMPLETED) {
      // TODO improve this code: now we wait for 5 seconds to retrieve results
      // when we get a socket update says result is finished, so that we are
      // 'sure' the results are updated in the
      // TODO add collection of the result here -> that is not properly done for v4
      setTimeout(() => {
        this.get_base(
          data.run_id,
          this.convertJsonService.getAlgorithmRun,
          true
        );
      }, 5000);
    }
    let runs = this.resource_list.value;
    for (let run of runs as Run[]) {
      if (run.id === data.run_id) {
        run.status = data.status;
        break;
      }
    }
    this.resource_list.next(runs);
  }
}
