import { Component, OnInit } from '@angular/core';
import { PageEvent } from '@angular/material/paginator';
import { Router } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { getChipTypeForStatus, getTaskStatusTranslation } from 'src/app/helpers/task.helper';
import { PaginationLinks } from 'src/app/models/api/pagination.model';
import { OperationType, ResourceType, ScopeType } from 'src/app/models/api/rule.model';
import { BaseTask, TaskStatus } from 'src/app/models/api/task.models';
import { routePaths } from 'src/app/routes';
import { AuthService } from 'src/app/services/auth.service';
import { TaskService } from 'src/app/services/task.service';

enum TableRows {
  ID = 'id',
  Name = 'name',
  Status = 'status'
}

@Component({
  selector: 'app-task-list',
  templateUrl: './task-list.component.html',
  styleUrls: ['./task-list.component.scss'],
  host: { '[class.card-container]': 'true' }
})
export class TaskListComponent implements OnInit {
  tableRows = TableRows;
  routes = routePaths;
  tasks: BaseTask[] = [];
  displayedColumns: string[] = [TableRows.ID, TableRows.Name, TableRows.Status];
  isLoading: boolean = true;
  pagination: PaginationLinks | null = null;
  currentPage: number = 1;
  canCreateTask: boolean = false;

  constructor(
    private router: Router,
    private translateService: TranslateService,
    private taskService: TaskService,
    authService: AuthService
  ) {
    this.canCreateTask = authService.isOperationAllowed(ScopeType.COLLABORATION, ResourceType.TASK, OperationType.CREATE);
  }

  ngOnInit() {
    this.initData();
  }

  async handlePageEvent(e: PageEvent) {
    this.currentPage = e.pageIndex + 1;
    await this.getTasks();
  }

  handleRowClick(task: BaseTask) {
    this.router.navigate([routePaths.task, task.id]);
  }

  handleRowKeyPress(event: KeyboardEvent, task: BaseTask) {
    if (event.key === 'Enter' || event.key === ' ') {
      this.handleRowClick(task);
    }
  }

  getChipTypeForStatus(status: TaskStatus) {
    return getChipTypeForStatus(status);
  }

  getTaskStatusTranslation(status: TaskStatus) {
    return getTaskStatusTranslation(this.translateService, status);
  }

  private async initData() {
    await this.getTasks();
    this.isLoading = false;
  }

  private async getTasks() {
    const taskData = await this.taskService.getTasks(this.currentPage);
    this.tasks = taskData.data;
    this.pagination = taskData.links;
  }
}
