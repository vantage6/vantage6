import { Component, Input, OnInit } from '@angular/core';
import { getChipTypeForStatus } from 'src/app/helpers/task.helper';
import { Algorithm } from 'src/app/models/api/algorithm.model';
import { Task, TaskLazyProperties, TaskStatus } from 'src/app/models/api/task.models';
import { routePaths } from 'src/app/routes';
import { AlgorithmService } from 'src/app/services/algorithm.service';
import { TaskService } from 'src/app/services/task.service';

@Component({
  selector: 'app-task-read',
  templateUrl: './task-read.component.html',
  styleUrls: ['./task-read.component.scss'],
  host: { '[class.card-container]': 'true' }
})
export class TaskReadComponent implements OnInit {
  @Input() id = '';

  routes = routePaths;

  task: Task | null = null;
  algorithm: Algorithm | null = null;
  isLoading = true;

  constructor(
    private taskService: TaskService,
    private algorithmService: AlgorithmService
  ) {}

  ngOnInit(): void {
    this.initData();
  }

  async initData(): Promise<void> {
    this.task = await this.taskService.getTask(this.id, [TaskLazyProperties.InitOrg, TaskLazyProperties.InitUser]);
    this.algorithm = await this.algorithmService.getAlgorithmByUrl(this.task.image);
    this.isLoading = false;
  }

  getChipTypeForStatus(status: TaskStatus) {
    return getChipTypeForStatus(status);
  }
}
