import { DatePipe, NgFor, NgIf } from '@angular/common';
import { Component, HostBinding, Input, OnDestroy, OnInit } from '@angular/core';
import { MatCard, MatCardContent, MatCardHeader, MatCardTitle } from '@angular/material/card';
import { MatIcon } from '@angular/material/icon';
import { MatMenu, MatMenuTrigger } from '@angular/material/menu';
import { MatPaginator, PageEvent } from '@angular/material/paginator';
import { MatProgressSpinner } from '@angular/material/progress-spinner';
import { ActivatedRoute, Router } from '@angular/router';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { Subject, takeUntil } from 'rxjs';
import { PageHeaderComponent } from 'src/app/components/page-header/page-header.component';
import { SearchRequest, TableComponent } from 'src/app/components/table/table.component';
import { getApiSearchParameters } from 'src/app/helpers/api.helper';
import { getChipTypeForStatus, getTaskStatusTranslation } from 'src/app/helpers/task.helper';
import { PaginationLinks } from 'src/app/models/api/pagination.model';
import { OperationType, ResourceType } from 'src/app/models/api/rule.model';
import { Dataframe, DataframeColumnTableDisplay } from 'src/app/models/api/session.models';
import { BaseTask, GetTaskParameters } from 'src/app/models/api/task.models';
import { TableData } from 'src/app/models/application/table.model';
import { routePaths } from 'src/app/routes';
import { ChosenCollaborationService } from 'src/app/services/chosen-collaboration.service';
import { PermissionService } from 'src/app/services/permission.service';
import { SessionService } from 'src/app/services/session.service';
import { TaskService } from 'src/app/services/task.service';
import { AlertComponent } from '../../../../../components/alerts/alert/alert.component';
import { BaseNode } from 'src/app/models/api/node.model';
import { NodeService } from 'src/app/services/node.service';

@Component({
  selector: 'app-dataframe-read',
  templateUrl: './dataframe-read.component.html',
  styleUrl: './dataframe-read.component.scss',
  imports: [
    PageHeaderComponent,
    MatIcon,
    MatMenuTrigger,
    TranslateModule,
    MatMenu,
    NgIf,
    MatCard,
    MatCardContent,
    MatProgressSpinner,
    MatCardHeader,
    MatCardTitle,
    TableComponent,
    MatPaginator,
    AlertComponent,
    NgFor
  ]
})
export class DataframeReadComponent implements OnInit, OnDestroy {
  @HostBinding('class') class = 'card-container';
  @Input() id = '';

  destroy$ = new Subject();

  dataframeColumnsTable: TableData | undefined;
  currentPageColumnTable: number = 1;
  paginationColumnTable: PaginationLinks | null = null;
  columnAlerts: string[] = [];

  dataframeTasksTable: TableData | undefined;
  currentPageTaskTable: number = 1;
  getDataframeTasksParameters: GetTaskParameters = {};
  paginationTaskTable: PaginationLinks | null = null;

  isLoading = true;
  dataframe: Dataframe | null = null;
  nodes: BaseNode[] = [];
  canDelete = false;
  canEdit = false;

  constructor(
    private translateService: TranslateService,
    private activatedRoute: ActivatedRoute,
    private sessionService: SessionService,
    private chosenCollaborationService: ChosenCollaborationService,
    private permissionService: PermissionService,
    private taskService: TaskService,
    private datePipe: DatePipe,
    private router: Router,
    private nodeService: NodeService
  ) {}

  async ngOnInit(): Promise<void> {
    this.setPermissions();

    // subscribe to reload task data when url changes (i.e. other task is viewed)
    this.activatedRoute.params.pipe(takeUntil(this.destroy$)).subscribe(async (params) => {
      this.id = params['id'];
      this.isLoading = true;
      await this.initData();
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next(true);
  }

  async initData(): Promise<void> {
    if (!this.id) return;
    this.dataframe = await this.sessionService.getDataframe(Number(this.id));
    if (this.dataframe) {
      await Promise.all([this.getDataframeTasks(), this.setDataframeColumnsTable()]);
    }
    this.isLoading = false;
  }

  private async setDataframeColumnsTable(): Promise<void> {
    if (!this.dataframe || this.chosenCollaborationService.collaboration$.value === null) return;
    this.nodes = await this.nodeService.getNodes({ session_id: this.dataframe.session.id.toString() });
    this.dataframe.columns[0].dtype = 'Something else';
    delete this.dataframe.columns[1];

    // condense array to go from [{name: x, node_id: 1, dtype: string}, {name: x, node_id: 2, dtype: string}] to
    // [{name: x, node_names: [1,2], dtype: string}]
    const condensedColumnDataObj = this.dataframe.columns.reduce((acc: { [key: string]: any }, column: Dataframe['columns'][number]) => {
      const node = this.nodes.find((node) => node.id === column.node_id);
      if (node) {
        const existingEntry = acc[`${column.name}${column.dtype}`];
        if (!existingEntry) {
          acc[`${column.name}${column.dtype}`] = { name: column.name, node_names: [node.name], type: column.dtype };
        } else {
          if (!existingEntry.node_names.includes(node.name)) {
            existingEntry.node_names.push(node.name);
          }
        }
      }
      return acc;
    }, {});
    // convert object with keys to array and sort by name
    const condensedColumnData: DataframeColumnTableDisplay[] = Object.values(condensedColumnDataObj).sort((a, b) =>
      a.name.localeCompare(b.name)
    );

    this.compileColumnWarnings(condensedColumnData);

    this.dataframeColumnsTable = {
      columns: [
        { id: 'name', label: this.translateService.instant('dataframe-read.columns.name') },
        { id: 'type', label: this.translateService.instant('dataframe-read.columns.type') },
        { id: 'node_names', label: this.translateService.instant('dataframe-read.columns.node-names') }
      ],
      rows: condensedColumnData.map((column_: DataframeColumnTableDisplay) => {
        return {
          id: column_.name,
          columnData: {
            name: column_.name,
            type: column_.type,
            node_names: column_.node_names.join(', ')
          }
        };
      })
    };
  }

  private compileColumnWarnings(columnData: DataframeColumnTableDisplay[]) {
    if (!this.dataframe || columnData.length === 0) return;
    // reset to empty alerts
    this.columnAlerts = [];

    const uniqueColumnNames = Array.from(new Set(columnData.map((column) => column.name)));
    // generate alerts for columns missing for certain nodes. First, check if there are
    // any nodes entirely without columns, and if there are nodes that do not have a
    // certain column that is present for other nodes
    for (const node of this.nodes) {
      const nodeColumns = columnData.filter((column) => column.node_names.includes(node.name));
      if (nodeColumns.length === 0) {
        this.columnAlerts.push(this.translateService.instant('dataframe-read.columns.alerts.no-columns-for-node', { node: node.name }));
      } else if (nodeColumns.length < uniqueColumnNames.length) {
        const missingColumns = uniqueColumnNames.filter((columnName) => {
          return !nodeColumns.some((column) => column.name === columnName);
        });
        for (const columnName of missingColumns) {
          this.columnAlerts.push(
            this.translateService.instant('dataframe-read.columns.alerts.missing-column', { node: node.name, column: columnName })
          );
        }
      }
    }

    // also generate errors for columns that have mixed types
    const columnTypeMap = new Map<string, string[]>();
    for (const column of columnData) {
      if (!columnTypeMap.has(column.name)) {
        columnTypeMap.set(column.name, []);
      }
      columnTypeMap.get(column.name)?.push(`'${column.type}'`);
    }
    for (const [columnName, types] of columnTypeMap.entries()) {
      if (types.length > 1) {
        this.columnAlerts.push(
          this.translateService.instant('dataframe-read.columns.alerts.mixed-types', { column: columnName, types: types.join(', ') })
        );
      }
    }
  }

  private async getDataframeTasks(): Promise<void> {
    this.isLoading = true;
    const dataframeTasks = await this.taskService.getPaginatedTasks(this.currentPageTaskTable, {
      dataframe_id: this.dataframe?.id
    });
    this.paginationTaskTable = dataframeTasks.links;

    this.dataframeTasksTable = {
      columns: [
        { id: 'id', label: this.translateService.instant('general.id') },
        { id: 'name', label: this.translateService.instant('general.name'), searchEnabled: true },
        {
          id: 'status',
          label: this.translateService.instant('task.status'),
          filterEnabled: true,
          isChip: true,
          chipTypeProperty: 'statusType'
        }
      ],
      rows: dataframeTasks.data.map((task) => {
        return {
          id: task.id.toString(),
          columnData: {
            id: task.id,
            name: task.name,
            status: getTaskStatusTranslation(this.translateService, task.status),
            statusType: getChipTypeForStatus(task.status),
            created_date: this.datePipe.transform(task.created_at, 'yyyy-MM-dd HH:mm')
          }
        };
      })
    };
  }

  handleTaskTableClick(task_id: string) {
    this.router.navigate([routePaths.task, task_id]);
  }

  handleSearchChanged(searchRequests: SearchRequest[]): void {
    this.getDataframeTasksParameters = getApiSearchParameters<GetTaskParameters>(searchRequests);
    this.currentPageTaskTable = 1;
    this.getDataframeTasks();
  }

  async handleTaskTablePageEvent(e: PageEvent) {
    this.currentPageTaskTable = e.pageIndex + 1;
    await this.getDataframeTasks();
  }

  private setPermissions() {
    this.permissionService
      .isInitialized()
      .pipe(takeUntil(this.destroy$))
      .subscribe((initialized) => {
        if (initialized) {
          this.canDelete = this.permissionService.isAllowedForCollab(
            ResourceType.SESSION,
            OperationType.DELETE,
            this.chosenCollaborationService.collaboration$.value
          );
          this.canEdit = this.permissionService.isAllowedForCollab(
            ResourceType.SESSION,
            OperationType.EDIT,
            this.chosenCollaborationService.collaboration$.value
          );
        }
      });
  }
}
