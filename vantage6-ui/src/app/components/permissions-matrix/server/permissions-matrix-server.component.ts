import { Component } from '@angular/core';
import {
  BasePermissionsMatrixComponent,
  OperationPermission,
  ResourcePermission,
  ScopePermission,
  ServerResourcePermission
} from '../base/permissions-matrix.component';
import { OperationType, ResourceType, Rule, ScopeType } from 'src/app/models/api/rule.model';
import { PermissionService } from 'src/app/services/permission.service';
import { NgFor, NgClass, NgIf } from '@angular/common';
import { MatCheckbox } from '@angular/material/checkbox';
import { MatIcon } from '@angular/material/icon';
import { TranslateModule } from '@ngx-translate/core';

@Component({
  selector: 'app-permissions-matrix-server',
  templateUrl: './permissions-matrix-server.component.html',
  styleUrl: '../base/permissions-matrix.component.scss',
  standalone: true,
  imports: [NgFor, NgClass, NgIf, MatCheckbox, MatIcon, TranslateModule]
})
export class PermissionsMatrixServerComponent extends BasePermissionsMatrixComponent {
  allResources = Object.values(ResourceType).filter(
    (resource) => ![ResourceType.ANY, ResourceType.RESULT, ResourceType.RULE].includes(resource)
  );
  allScopes = Object.values(ScopeType).filter((scope) => scope !== ScopeType.ANY);
  allOperations = Object.values(OperationType).filter((operation) => ![OperationType.ANY].includes(operation));

  public resourcePermissions: ServerResourcePermission[] = [];

  constructor(private permissionService: PermissionService) {
    super();
  }

  protected updateTable(fixedSelected: Rule[], preSelected: Rule[], selectable: Rule[]): ResourcePermission[] {
    this.selectionUnsubscribe();
    this.selection.clear();

    const result = this.allResources
      .map((resource) => {
        const scopePermissions = this.allScopes
          .filter((scope) => this.hasOperationsForDisplay(resource, scope, [...fixedSelected, ...preSelected, ...selectable]))
          .map((scope) => {
            const operationPermissions = this.allOperations.map((operation) => {
              const cellState = this.getCellState(fixedSelected, preSelected, selectable, resource, scope, operation);
              const displayClass = this.getDisplayClass(this.fixedSelectedPrimary, this.fixedSelectedSecondary, resource, scope, operation);
              const operationPermission = new OperationPermission(resource, scope, operation, cellState, displayClass);
              this.operationPermissionDictionary.add(operationPermission);
              if (cellState === this.CellState.Selected) this.selection.select(operationPermission);
              return operationPermission;
            });
            return new ScopePermission(scope, operationPermissions);
          });

        const resourcePermission = new ServerResourcePermission(resource, scopePermissions);
        return resourcePermission;
      })
      .filter((resourcePermission) => resourcePermission.scopes.length > 0);

    this.selectionSubscribe();

    return result;
  }

  protected isAllowedToAssignRuleToRole(resource: ResourceType, scope: ScopeType | null, operation: OperationType): boolean {
    if (!scope) return false;
    return this.permissionService.isAllowedToAssignRuleToRole(scope, resource, operation);
  }
}
