import { Component, Input, OnDestroy, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { Subject, takeUntil } from 'rxjs';
import { Study, StudyLazyProperties } from 'src/app/models/api/study.model';
import { OperationType, ResourceType, ScopeType } from 'src/app/models/api/rule.model';
import { routePaths } from 'src/app/routes';
import { PermissionService } from 'src/app/services/permission.service';
import { StudyService } from 'src/app/services/study.service';
import { MatDialog } from '@angular/material/dialog';
import { ConfirmDialogComponent } from 'src/app/components/dialogs/confirm/confirm-dialog.component';

@Component({
  selector: 'app-study-read',
  templateUrl: './study-read.component.html',
  styleUrls: ['./study-read.component.scss']
})
export class StudyReadComponent implements OnInit, OnDestroy {
  destroy$ = new Subject();
  routes = routePaths;

  @Input() id = '';

  isLoading = true;
  study?: Study;

  canDelete = false;
  canEdit = false;

  constructor(
    private dialog: MatDialog,
    private router: Router,
    private translateService: TranslateService,
    private permissionService: PermissionService,
    private studyService: StudyService
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
    this.isLoading = false;
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
        if (result === true) {
          if (!this.study) return;
          this.isLoading = true;
          await this.studyService.deleteStudy(this.study.id.toString());
          this.router.navigate([routePaths.collaboration, this.study.collaboration?.id]);
        }
      });
  }
}
