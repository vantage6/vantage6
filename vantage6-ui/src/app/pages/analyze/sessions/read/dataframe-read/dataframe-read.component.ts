import { NgIf } from '@angular/common';
import { Component, HostBinding, Input, OnDestroy, OnInit } from '@angular/core';
import { MatCard, MatCardContent, MatCardHeader, MatCardTitle } from '@angular/material/card';
import { MatIcon } from '@angular/material/icon';
import { MatMenu, MatMenuTrigger } from '@angular/material/menu';
import { MatProgressSpinner } from '@angular/material/progress-spinner';
import { ActivatedRoute } from '@angular/router';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { Subject, takeUntil } from 'rxjs';
import { PageHeaderComponent } from 'src/app/components/page-header/page-header.component';
import { OperationType, ResourceType } from 'src/app/models/api/rule.model';
import { Dataframe } from 'src/app/models/api/session.models';
import { ChosenCollaborationService } from 'src/app/services/chosen-collaboration.service';
import { PermissionService } from 'src/app/services/permission.service';
import { SessionService } from 'src/app/services/session.service';

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
    MatCardTitle
  ]
})
export class DataframeReadComponent implements OnInit, OnDestroy {
  @HostBinding('class') class = 'card-container';
  @Input() id = '';

  destroy$ = new Subject();

  isLoading = true;
  dataframe: Dataframe | null = null;
  canDelete = false;
  canEdit = false;

  constructor(
    private translateService: TranslateService,
    private activatedRoute: ActivatedRoute,
    private sessionService: SessionService,
    private chosenCollaborationService: ChosenCollaborationService,
    private permissionService: PermissionService
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
    this.isLoading = false;
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
