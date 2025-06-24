import { Component, HostBinding, Input, OnDestroy, OnInit } from '@angular/core';
import { FormControl, Validators, ReactiveFormsModule } from '@angular/forms';
import { MatDialog } from '@angular/material/dialog';
import { Router, RouterLink } from '@angular/router';
import { TranslateService, TranslateModule } from '@ngx-translate/core';
import { Subject, takeUntil } from 'rxjs';
import { ConfirmDialogComponent } from 'src/app/components/dialogs/confirm/confirm-dialog.component';
import { AlgorithmStore, EditAlgorithmStore } from 'src/app/models/api/algorithmStore.model';
import { Collaboration, CollaborationLazyProperties } from 'src/app/models/api/collaboration.model';
import { Study } from 'src/app/models/api/study.model';
import { NodeStatus } from 'src/app/models/api/node.model';
import { OperationType, ResourceType, ScopeType } from 'src/app/models/api/rule.model';
import { TableData } from 'src/app/models/application/table.model';
import { routePaths } from 'src/app/routes';
import { AlgorithmStoreService } from 'src/app/services/algorithm-store.service';
import { CollaborationService } from 'src/app/services/collaboration.service';
import { PermissionService } from 'src/app/services/permission.service';
import { ChosenCollaborationService } from 'src/app/services/chosen-collaboration.service';
import { NgIf, NgFor } from '@angular/common';
import { PageHeaderComponent } from '../../../../components/page-header/page-header.component';
import { MatIconButton, MatButton } from '@angular/material/button';
import { MatMenuTrigger, MatMenu, MatMenuItem } from '@angular/material/menu';
import { MatIcon } from '@angular/material/icon';
import { MatCard, MatCardHeader, MatCardTitle, MatCardContent } from '@angular/material/card';
import { ChipComponent } from '../../../../components/helpers/chip/chip.component';
import { NodeAdminCardComponent } from '../../../../components/helpers/node-admin-card/node-admin-card.component';
import {
  MatAccordion,
  MatExpansionPanel,
  MatExpansionPanelHeader,
  MatExpansionPanelTitle,
  MatExpansionPanelContent
} from '@angular/material/expansion';
import { MatProgressSpinner } from '@angular/material/progress-spinner';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatInput } from '@angular/material/input';
import { TableComponent } from '../../../../components/table/table.component';
import { ConfirmDialogOption } from 'src/app/models/application/confirmDialog.model';

@Component({
  selector: 'app-collaboration-read',
  templateUrl: './collaboration-read.component.html',
  styleUrls: ['./collaboration-read.component.scss'],
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
    NgFor,
    ChipComponent,
    NodeAdminCardComponent,
    MatButton,
    MatAccordion,
    MatExpansionPanel,
    MatExpansionPanelHeader,
    MatExpansionPanelTitle,
    MatExpansionPanelContent,
    MatProgressSpinner,
    MatFormField,
    MatLabel,
    MatInput,
    ReactiveFormsModule,
    TableComponent,
    TranslateModule
  ]
})
export class CollaborationReadComponent implements OnInit, OnDestroy {
  @HostBinding('class') class = 'card-container';
  destroy$ = new Subject();
  nodeStatus = NodeStatus;
  routes = routePaths;

  @Input() id = '';

  isLoading = true;
  collaboration?: Collaboration;
  canDelete = false;
  canEdit = false;
  canCreateStudy = false;

  isEditAlgorithmStore = false;
  selectedAlgoStore?: AlgorithmStore;
  algoStoreNewName = new FormControl<string>('', [Validators.required]);

  isEditStudy = false;
  selectedStudy?: Study;
  studyTable?: TableData;

  constructor(
    private dialog: MatDialog,
    private router: Router,
    private collaborationService: CollaborationService,
    private algorithmStoreService: AlgorithmStoreService,
    private translateService: TranslateService,
    private permissionService: PermissionService,
    private chosenCollaborationService: ChosenCollaborationService
  ) {}

  async ngOnInit(): Promise<void> {
    await this.initData();
    this.setPermissions();
  }

  ngOnDestroy(): void {
    this.destroy$.next(true);
  }

  private async initData(): Promise<void> {
    this.collaboration = await this.collaborationService.getCollaboration(this.id, [
      CollaborationLazyProperties.Organizations,
      CollaborationLazyProperties.Nodes,
      CollaborationLazyProperties.AlgorithmStores,
      CollaborationLazyProperties.Studies
    ]);
    this.studyTable = {
      columns: [
        {
          id: 'name',
          label: this.translateService.instant('collaboration.name')
        }
      ],
      rows: this.collaboration.studies.map((study) => ({
        id: study.id.toString(),
        columnData: {
          name: study.name
        }
      }))
    };
    this.isLoading = false;
  }

  private setPermissions() {
    this.permissionService
      .isInitialized()
      .pipe(takeUntil(this.destroy$))
      .subscribe((initialized) => {
        if (initialized) {
          this.canDelete = this.permissionService.isAllowed(ScopeType.ANY, ResourceType.COLLABORATION, OperationType.DELETE);
          this.canEdit = this.permissionService.isAllowed(ScopeType.ANY, ResourceType.COLLABORATION, OperationType.EDIT);
          this.canCreateStudy = this.permissionService.isAllowedForCollab(
            ResourceType.STUDY,
            OperationType.CREATE,
            this.collaboration || null
          );
        }
      });
  }

  onUpdatedNodes(): void {
    this.initData();
  }

  selectAlgoStore(id: number): void {
    this.selectedAlgoStore = this.collaboration?.algorithm_stores.find((algoStore) => algoStore.id === id);
  }

  handleStudyClick(id: string): void {
    this.router.navigate([routePaths.study, id]);
  }

  async handleDelete(): Promise<void> {
    if (!this.collaboration) return;

    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      data: {
        title: this.translateService.instant('collaboration-read.delete-dialog.title', { name: this.collaboration.name }),
        content: this.translateService.instant('collaboration-read.delete-dialog.content'),
        confirmButtonText: this.translateService.instant('general.delete'),
        confirmButtonType: 'warn'
      }
    });

    dialogRef
      .afterClosed()
      .pipe(takeUntil(this.destroy$))
      .subscribe(async (result) => {
        if (result === ConfirmDialogOption.PRIMARY) {
          if (!this.collaboration) return;
          this.isLoading = true;
          await this.collaborationService.deleteCollaboration(this.collaboration.id.toString());
          this.router.navigate([routePaths.collaborations]);
        }
      });
  }

  handleAlgoStoreEditStart(): void {
    this.isEditAlgorithmStore = true;
  }

  async handleAlgoStoreEditSubmit(): Promise<void> {
    if (!this.collaboration || !this.selectedAlgoStore || !this.algoStoreNewName.value) return;
    this.isEditAlgorithmStore = false;

    const algoStoreEdit: EditAlgorithmStore = {
      name: this.algoStoreNewName.value
    };
    const result = await this.algorithmStoreService.edit(this.selectedAlgoStore.id.toString(), algoStoreEdit);
    if (result.id) {
      this.selectedAlgoStore.name = result.name;
      const storeToUpdate = this.collaboration.algorithm_stores.find((store) => store.id === result.id);
      if (storeToUpdate) {
        storeToUpdate.name = result.name;
      }
    }
    // refresh the chosen collaboration
    this.chosenCollaborationService.refresh(this.collaboration.id.toString());
  }

  handleAlgoStoreEditCancel(): void {
    this.isEditAlgorithmStore = false;
  }

  handleAlgoStoreDelete(): void {
    if (!this.collaboration || !this.selectedAlgoStore) return;

    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      data: {
        title: this.translateService.instant('collaboration.algorithm-store.delete-dialog.title', {
          name: this.selectedAlgoStore.name,
          collaboration: this.collaboration.name
        }),
        content: this.translateService.instant('collaboration.algorithm-store.delete-dialog.content'),
        confirmButtonText: this.translateService.instant('general.delete'),
        confirmButtonType: 'warn'
      }
    });

    dialogRef
      .afterClosed()
      .pipe(takeUntil(this.destroy$))
      .subscribe(async (result) => {
        if (result === ConfirmDialogOption.PRIMARY) {
          if (!this.collaboration || !this.selectedAlgoStore) return;
          await this.algorithmStoreService.delete(this.selectedAlgoStore.id.toString());

          // update list of stores
          this.collaboration.algorithm_stores = this.collaboration.algorithm_stores.filter(
            (store) => store.id !== this.selectedAlgoStore?.id
          );
          this.selectedAlgoStore = undefined;

          // refresh the chosen collaboration. Don't specify the collaboration id to
          // force refresh, as the store may be part of other collaborations as well
          this.chosenCollaborationService.refresh();
        }
      });
  }
}
