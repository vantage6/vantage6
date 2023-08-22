import { Component, OnInit } from '@angular/core';
import { PageEvent } from '@angular/material/paginator';
import { PaginationLinks } from 'src/app/models/api/pagination.model';
import { OperationType, ResourceType, ScopeType } from 'src/app/models/api/rule.model';
import { BaseTask } from 'src/app/models/api/task.models';
import { routePaths } from 'src/app/routes';
import { AuthService } from 'src/app/services/auth.service';
import { TaskService } from 'src/app/services/task.service';

enum TableRows {
  ID = 'id',
  Name = 'name',
  Description = 'description',
  Status = 'status'
}

@Component({
  selector: 'app-tasks',
  templateUrl: './tasks.component.html',
  styleUrls: ['./tasks.component.scss'],
  host: { '[class.card-container]': 'true' }
})
export class TasksComponent implements OnInit {
  tableRows = TableRows;
  routes = routePaths;
  tasks: BaseTask[] = [];
  displayedColumns: string[] = [TableRows.ID, TableRows.Name, TableRows.Description, TableRows.Status];
  isLoading: boolean = true;
  pagination: PaginationLinks | null = null;
  currentPage: number = 1;
  canCreateTask: boolean = false;

  constructor(
    private taskService: TaskService,
    authService: AuthService
  ) {
    this.canCreateTask = authService.isOperationAllowed(ResourceType.TASK, ScopeType.COLLABORATION, OperationType.CREATE);
  }

  ngOnInit() {
    this.initData();
  }

  async handlePageEvent(e: PageEvent) {
    this.currentPage = e.pageIndex + 1;
    await this.getTasks();
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
