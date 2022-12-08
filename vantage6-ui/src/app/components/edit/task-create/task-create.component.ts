import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, ParamMap, Router } from '@angular/router';
import { UserPermissionService } from 'src/app/auth/services/user-permission.service';
import { Collaboration } from 'src/app/interfaces/collaboration';
import { Organization } from 'src/app/interfaces/organization';
import {
  Task,
  getEmptyTask,
  TaskInput,
  getEmptyTaskInput,
} from 'src/app/interfaces/task';
import { TaskApiService } from 'src/app/services/api/task-api.service';
import { ModalService } from 'src/app/services/common/modal.service';
import { UtilsService } from 'src/app/services/common/utils.service';
import { CollabDataService } from 'src/app/services/data/collab-data.service';
import { OrgDataService } from 'src/app/services/data/org-data.service';
import { ResultDataService } from 'src/app/services/data/result-data.service';
import { TaskDataService } from 'src/app/services/data/task-data.service';
import {
  deepcopy,
  filterArrayByProperty,
  getById,
  removeMatchedIdFromArray,
  removeValueFromArray,
} from 'src/app/shared/utils';
import { BaseEditComponent } from '../base-edit/base-edit.component';

@Component({
  selector: 'app-task-create',
  templateUrl: './task-create.component.html',
  styleUrls: [
    '../../../shared/scss/buttons.scss',
    './task-create.component.scss',
  ],
})
export class TaskCreateComponent extends BaseEditComponent implements OnInit {
  task: Task = getEmptyTask();
  repeatable_tasks: Task[] = [];
  has_selected_previous_task: boolean = false;
  task_input: TaskInput = getEmptyTaskInput();
  collaborations: Collaboration[] = [];
  organizations: Organization[] = [];
  selected_orgs: Organization[] = [];
  deselected_orgs: Organization[] = [];
  warning_message: string = '';

  constructor(
    protected router: Router,
    protected activatedRoute: ActivatedRoute,
    public userPermission: UserPermissionService,
    protected taskApiService: TaskApiService,
    protected taskDataService: TaskDataService,
    protected modalService: ModalService,
    protected utilsService: UtilsService,
    private collabDataService: CollabDataService,
    private orgDataService: OrgDataService,
    private resultDataService: ResultDataService
  ) {
    super(
      router,
      activatedRoute,
      userPermission,
      utilsService,
      taskApiService,
      taskDataService,
      modalService
    );
  }

  ngOnInit(): void {
    this.userPermission.isInitialized().subscribe((ready) => {
      if (ready) {
        super.ngOnInit();
      }
    });
  }

  async init(): Promise<void> {
    this.organizations = await this.orgDataService.list();
    this.collaborations = await this.collabDataService.list(this.organizations);

    // subscribe to id parameter in route to change edited role if required
    this.readRoute();

    // set previous tasks, so user can create tasks they have done before.
    // Only include task for the logged-in user, and no subtasks
    let repeatable_tasks = await this.taskDataService.list();
    repeatable_tasks = filterArrayByProperty(
      repeatable_tasks,
      'init_user_id',
      this.userPermission.user.id
    );
    repeatable_tasks = filterArrayByProperty(
      repeatable_tasks,
      'parent_id',
      null
    );
    this.repeatable_tasks = repeatable_tasks;

    // set defaults
    // this.task.data_format = 'legacy';
    this.task.database = 'default';
    this.initializeTaskInput();
  }

  async setup(params: ParamMap) {
    if (this.router.url.includes('repeat')) {
      let id = Number(params.get('id'));
      let task = await this.taskDataService.get(id);
      this.selectPreviousTask(task);
    }
    super.setup(params);
  }

  initializeTaskInput() {
    this.task_input = getEmptyTaskInput();
    this.task_input.args = [''];
    this.task_input.kwargs = [{ key: '', value: '' }];
    // TODO UI task now always have JSON output format. Should we create option
    // to change this?
    this.task_input.output_format = 'json';
  }

  async setupCreate() {}

  async setupEdit(id: number): Promise<void> {
    // edit tasks is not possible: this is a dummy implementation of super func
  }

  public getNameCollabDropdown(): string {
    return this.task.collaboration === undefined
      ? 'Select collaboration'
      : this.task.collaboration.name;
  }

  public getNamePrevTaskDropdown(): string {
    return this.has_selected_previous_task
      ? `${this.task.id} - ${this.task.name}`
      : 'Select task';
  }

  public selectCollab(collab: Collaboration): void {
    this.task.collaboration = collab;
    this.selected_orgs = [];
    this.deselected_orgs = collab.organizations;
    this.checkMasterMultiOrg();
  }

  async selectPreviousTask(task: Task): Promise<void> {
    this.has_selected_previous_task = true;
    this.task = task;
    this.selectCollab(getById(this.collaborations, task.collaboration_id));

    // Get also the task results as this includes the input and the organization
    let results = await this.resultDataService.get_by_task_id(this.task.id);
    // set organizations
    for (let r of results) {
      this.addOrg(getById(this.organizations, r.organization_id));
    }
    // set input
    let first_result = results[0];
    let decoded_input = atob(first_result.input);
    if (decoded_input.startsWith('json.')) {
      let input = JSON.parse(decoded_input.slice(5));
      this.task_input.master = input.master;
      this.task_input.method = input.method;
      if (input.args) {
        this.task_input.args = input.args;
      }
      if (input.kwargs) {
        this.task_input.kwargs = [];
        for (let key in input.kwargs) {
          this.task_input.kwargs.push({ key: key, value: input.kwargs[key] });
        }
      }
    } else {
      // input was not encoded in JSON, so we don't know how to read it...
      // we should still reset the input though
      this.initializeTaskInput();
    }
  }

  public addOrg(org: Organization): void {
    this.selected_orgs.push(org);
    this.deselected_orgs = removeMatchedIdFromArray(
      this.deselected_orgs,
      org.id
    );
    this.checkMasterMultiOrg();
  }

  public removeOrg(org: Organization) {
    this.deselected_orgs.push(org);
    this.selected_orgs = removeMatchedIdFromArray(this.selected_orgs, org.id);
    this.checkMasterMultiOrg();
  }

  async save(task: Task) {
    // set input, then remove empty args and kwargs
    this.task.input = deepcopy(this.task_input) as TaskInput;
    this.task.input.args = removeValueFromArray(this.task.input.args, '');
    this.task.input.kwargs = this.task.input.kwargs.filter(
      (elem) => elem.key !== '' || elem.value != ''
    );

    // check input validity
    if (this.task.input.kwargs.some((elem) => elem.key === '')) {
      this.modalService.openErrorModal(
        'Some kwargs have an undefined key. Cannot create task!'
      );
      return;
    } else if (this.task.collaboration === undefined) {
      this.modalService.openErrorModal(
        'You have not selected a collaboration to create the task for!'
      );
      return;
    } else if (this.selected_orgs.length === 0) {
      this.modalService.openErrorModal(
        'You have not selected which organizations should run this task!'
      );
      return;
    } else if (this.task.image === '') {
      this.modalService.openErrorModal(
        'You have not specified a Docker image for the algorithm!'
      );
      return;
    } else if (this.task.input.method === '') {
      this.modalService.openErrorModal(
        'You have not specified which method in the algorithm should be run!'
      );
      return;
    }

    // set selected organizations
    this.task.organizations = this.selected_orgs;

    // create tasks
    super.save(task);
  }

  trackArgsFunc(index: any, item: any) {
    // function to track input index
    // see https://forum.ionicframework.com/t/how-to-put-ngfor-value-in-input-element/133127/5
    return index;
  }

  checkAddArgsBox(): void {
    // add new input box for args if last box is filled
    if (this.task_input.args[this.task_input.args.length - 1] != '') {
      this.task_input.args.push('');
    }
  }

  checkAddKwargsBox(): void {
    let last_kwarg = this.task_input.kwargs[this.task_input.kwargs.length - 1];
    if (last_kwarg.key !== '' || last_kwarg.value !== '') {
      this.task_input.kwargs.push({ key: '', value: '' });
    }
  }

  checkMasterMultiOrg(): void {
    if (this.task_input.master && this.selected_orgs.length > 1) {
      this.warning_message =
        'You have selected a master task for multiple organizations. ' +
        'Usually master tasks are run on one organzation and then ' +
        'it creates subtasks for others. Are you sure?';
    } else {
      this.warning_message = '';
    }
  }
}
