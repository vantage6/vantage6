import { Component } from '@angular/core';
import {
  BasePermissionsMatrixComponent,
  OperationPermission,
  ResourcePermission,
  StoreResourcePermission
} from '../base/permissions-matrix.component';
import { OperationType, ScopeType, StoreResourceType, StoreRule } from 'src/app/models/api/rule.model';
import { StorePermissionService } from 'src/app/services/store-permission.service';
import { NgFor, NgClass, NgIf } from '@angular/common';
import { MatCheckbox } from '@angular/material/checkbox';
import { MatIcon } from '@angular/material/icon';
import { TranslateModule } from '@ngx-translate/core';

@Component({
  selector: 'app-permissions-matrix-store',
  templateUrl: './permissions-matrix-store.component.html',
  styleUrl: '../base/permissions-matrix.component.scss',
  standalone: true,
  imports: [NgFor, NgClass, NgIf, MatCheckbox, MatIcon, TranslateModule]
})
export class PermissionsMatrixStoreComponent extends BasePermissionsMatrixComponent {
  allResources = Object.values(StoreResourceType).filter((resource) => ![StoreResourceType.ANY].includes(resource));
  allOperations = Object.values(OperationType).filter(
    (operation) => ![OperationType.ANY, OperationType.SEND, OperationType.RECEIVE].includes(operation)
  );
  public resourcePermissions: StoreResourcePermission[] = [];

  constructor(private storePermissionService: StorePermissionService) {
    super();
  }

  protected updateTable(fixedSelected: StoreRule[], preSelected: StoreRule[], selectable: StoreRule[]): ResourcePermission[] {
    this.selectionUnsubscribe();
    this.selection.clear();

    const result = this.allResources.map((resource) => {
      const operationPermissions = this.allOperations.map((operation) => {
        const scope = null; // -> scope is not defined in algorithm store
        const cellState = this.getCellState(fixedSelected, preSelected, selectable, resource, scope, operation);
        const displayClass = this.getDisplayClass(this.fixedSelectedPrimary, this.fixedSelectedSecondary, resource, scope, operation);
        const operationPermission = new OperationPermission(resource, scope, operation, cellState, displayClass);
        this.operationPermissionDictionary.add(operationPermission);
        if (cellState === this.CellState.Selected) this.selection.select(operationPermission);
        return operationPermission;
      });

      const resourcePermission = new StoreResourcePermission(resource, operationPermissions);
      return resourcePermission;
    });

    this.selectionSubscribe();

    return result;
  }

  protected isAllowedToAssignRuleToRole(resourceType: StoreResourceType, scope: ScopeType | null, operation: OperationType): boolean {
    // TODO implement this method
    return this.storePermissionService.isAllowed(resourceType, operation);
  }
}
