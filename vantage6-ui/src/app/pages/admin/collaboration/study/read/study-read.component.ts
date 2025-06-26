import { Component, Input, OnDestroy, OnInit } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { TranslateService, TranslateModule } from '@ngx-translate/core';
import { Subject, takeUntil } from 'rxjs';
import { Study, StudyLazyProperties } from 'src/app/models/api/study.model';
import { OperationType, ResourceType, ScopeType } from 'src/app/models/api/rule.model';
import { routePaths } from 'src/app/routes';
import { PermissionService } from 'src/app/services/permission.service';
import { StudyService } from 'src/app/services/study.service';
import { MatDialog } from '@angular/material/dialog';
import { ConfirmDialogComponent } from 'src/app/components/dialogs/confirm/confirm-dialog.component';
import { ChosenCollaborationService } from 'src/app/services/chosen-collaboration.service';
import { BaseNode } from 'src/app/models/api/node.model';
import { NodeService } from 'src/app/services/node.service';
import { Collaboration, CollaborationLazyProperties } from 'src/app/models/api/collaboration.model';
import { CollaborationService } from 'src/app/services/collaboration.service';
import { NgIf, NgFor } from '@angular/common';
import { PageHeaderComponent } from '../../../../../components/page-header/page-header.component';
import { MatIconButton } from '@angular/material/button';
import { MatMenuTrigger, MatMenu, MatMenuItem } from '@angular/material/menu';
import { MatIcon } from '@angular/material/icon';
import { MatCard, MatCardHeader, MatCardTitle, MatCardContent } from '@angular/material/card';
import { ChipComponent } from '../../../../../components/helpers/chip/chip.component';
import { NodeAdminCardComponent } from '../../../../../components/helpers/node-admin-card/node-admin-card.component';
import { MatProgressSpinner } from '@angular/material/progress-spinner';
import { ConfirmDialogOption } from 'src/app/models/application/confirmDialog.model';

@Component({
  selector: 'app-study-read',
  templateUrl: './study-read.component.html',
  styleUrls: ['./study-read.component.scss'],
  imports: [
    NgIf,
    PageHeaderComponent,
    MatIconButton,
    MatMenuTrigger,
    MatIcon,
    MatMenu,
    MatMenuItem,
    RouterLink,
    MatCard,
    MatCardHeader,
    MatCardTitle,
    MatCardContent,
    ChipComponent,
    NgFor,
    NodeAdminCardComponent,
    MatProgressSpinner,
    TranslateModule
  ]
})
export class StudyReadComponent implements OnInit, OnDestroy {
  destroy$ = new Subject();
  routes = routePaths;

  @Input() id = '';

  isLoading = true;
  study?: Study;
  collaboration?: Collaboration;
  nodes?: BaseNode[];

  canDelete = false;
  canEdit = false;

  constructor(
    private dialog: MatDialog,
    private router: Router,
    private translateService: TranslateService,
    private permissionService: PermissionService,
    private studyService: StudyService,
    private nodeService: NodeService,
    private collaborationService: CollaborationService,
    private chosenCollaborationService: ChosenCollaborationService
  ) {}

  async ngOnInit(): Promise<void> {
    this.setPermissions();
    this.initData();
  }

  ngOnDestroy(): void {
    this.destroy$.next(true);
  }

  private setPermissions() {
    this.permissionService
      .isInitialized()
      .pipe(takeUntil(this.destroy$))
      .subscribe((initialized) => {
        if (initialized) {
          this.canDelete = this.permissionService.isAllowed(ScopeType.ANY, ResourceType.STUDY, OperationType.DELETE);
          this.canEdit = this.permissionService.isAllowed(ScopeType.ANY, ResourceType.STUDY, OperationType.EDIT);
        }
      });
  }

  private async initData(): Promise<void> {
    this.study = await this.studyService.getStudy(this.id, [StudyLazyProperties.Collaboration, StudyLazyProperties.Organizations]);
    this.nodes = await this.nodeService.getNodes({ study_id: this.id });
    if (this.study.collaboration) {
      this.collaboration = await this.collaborationService.getCollaboration(this.study.collaboration?.id.toString(), [
        CollaborationLazyProperties.Organizations
      ]);
    }
    this.isLoading = false;
  }

  onUpdatedNodes(): void {
    this.initData();
  }

  handleDelete(): void {
    if (!this.study) return;

    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      data: {
        title: this.translateService.instant('study-read.delete-dialog.title', { name: this.study.name }),
        content: this.translateService.instant('study-read.delete-dialog.content'),
        confirmButtonText: this.translateService.instant('general.delete'),
        confirmButtonType: 'warn'
      }
    });

    dialogRef
      .afterClosed()
      .pipe(takeUntil(this.destroy$))
      .subscribe(async (result) => {
        if (result === ConfirmDialogOption.PRIMARY) {
          if (!this.study) return;
          this.isLoading = true;
          await this.studyService.deleteStudy(this.study.id.toString());
          // update the chosen collaboration to remove the deleted study
          this.chosenCollaborationService.refresh(this.study.collaboration?.id.toString());
          this.router.navigate([routePaths.collaboration, this.study.collaboration?.id]);
        }
      });
  }
}
