/* eslint-disable @typescript-eslint/no-explicit-any */

import { SelectionModel } from '@angular/cdk/collections';
import { Component, EventEmitter, Input, OnChanges, OnInit, Output, SimpleChanges } from '@angular/core';
import { isEqualString } from 'src/app/helpers/task.helper';
import { OperationType, ResourceType, Rule, ScopeType } from 'src/app/models/api/rule.model';
import { PermissionService } from 'src/app/services/permission.service';

class ResourcePermission {
  constructor(
    public resource: ResourceType,
    public scopes: ScopePermission[]
  ) {}
}

class ScopePermission {
  constructor(
    public scope: ScopeType,
    public operations: OperationPermission[]
  ) {}
}

class OperationPermission {
  constructor(
    public resource: ResourceType,
    public scope: ScopeType,
    public operation: OperationType,
    public state: CellState
  ) {}
}

enum CellState {
  NotApplicable,
  Disabled,
  FixedSelected,
  FixedNotSelected,
  NotSelected,
  Selected
}

@Component({
  selector: 'app-roles-table',
  templateUrl: './roles-table.component.html',
  styleUrls: ['./roles-table.component.scss']
})
export class RolesTableComponent implements OnInit, OnChanges {
  /* Rules that are visualised as selected and cannot be unselected by the user */
  @Input() fixedSelected: Rule[] = [];
  /* Rules that can be selected or unselected.  */
  @Input() selectable: Rule[] = [];
  /* Selections that can be edited */
  @Input() preselected: Rule[] = [];
  @Input() userRules: Rule[] = [];

  @Output() edited: EventEmitter<Rule[]> = new EventEmitter();

  constructor(private permissionService: PermissionService) {}

  allResources = [
    ResourceType.USER,
    ResourceType.ORGANIZATION,
    ResourceType.COLLABORATION,
    ResourceType.ROLE,
    ResourceType.NODE,
    ResourceType.TASK,
    ResourceType.RUN,
    ResourceType.EVENT,
    ResourceType.PORT
  ];

  allScopes = [ScopeType.OWN, ScopeType.ORGANIZATION, ScopeType.COLLABORATION, ScopeType.GLOBAL];

  allOperations = [
    OperationType.CREATE,
    OperationType.DELETE,
    OperationType.EDIT,
    OperationType.VIEW,
    OperationType.SEND,
    OperationType.RECEIVE
  ];

  CellState = CellState;

  public resourcePermissions: ResourcePermission[] = [];

  public selection: SelectionModel<OperationPermission> = new SelectionModel<OperationPermission>(true, []);

  ngOnInit(): void {
    this.resourcePermissions = this.updateTable(this.fixedSelected, this.preselected, this.selectable);
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['fixedSelected'] || changes['preselected'] || changes['selectable']) {
      this.resourcePermissions = this.updateTable(this.fixedSelected, this.preselected, this.selectable);
    }
  }

  private updateTable(fixedSelected: Rule[], preSelected: Rule[], selectable: Rule[]) {
    return this.allResources.map((resource) => {
      const scopePermissions = this.allScopes
        .filter((scope) => this.hasSelectableOperations(resource, scope, selectable))
        .map((scope) => {
          const operationPermissions = this.allOperations.map((operation) => {
            const cellState = this.getCellState(fixedSelected, preSelected, selectable, resource, scope, operation);
            const operationPermission = new OperationPermission(resource, scope, operation, cellState);
            if (cellState === CellState.Selected) this.selection.select(operationPermission);
            return operationPermission;
          });
          return new ScopePermission(scope, operationPermissions);
        });

      const resourcePermission = new ResourcePermission(resource, scopePermissions);
      return resourcePermission;
    });
  }

  private hasSelectableOperations(resource: ResourceType, scope: ScopeType, selectable: Rule[]): boolean {
    return !!selectable.find((rule) => isEqualString(rule.name, resource) && isEqualString(rule.scope, scope));
  }

  private getCellState(
    fixedSelected: Rule[],
    preselected: Rule[],
    selectable: Rule[],
    resource: ResourceType,
    scope: ScopeType,
    operation: OperationType
  ): CellState {
    if (!this.containsRule(selectable, resource, scope, operation)) return CellState.NotApplicable;

    if (this.containsRule(fixedSelected, resource, scope, operation)) return CellState.FixedSelected;

    const isAllowed = this.permissionService.isAllowedToAssignRuleToRole(scope, resource, operation);
    const isPreselected = this.containsRule(preselected, resource, scope, operation);

    if (isAllowed && isPreselected) return CellState.Selected;
    if (isAllowed && !isPreselected) return CellState.NotSelected;
    if (!isAllowed && isPreselected) return CellState.FixedSelected;

    return CellState.FixedNotSelected;
  }

  private containsRule(rules: Rule[], resource: ResourceType, scope: ScopeType, operation: OperationType): boolean {
    return !!rules.find(
      (rule) => isEqualString(rule.name, resource) && isEqualString(rule.scope, scope) && isEqualString(rule.operation, operation)
    );
  }

  public showCheckBox(operationPermission: OperationPermission): boolean {
    return (
      operationPermission.state !== CellState.Disabled &&
      operationPermission.state !== CellState.FixedSelected &&
      operationPermission.state !== CellState.NotApplicable
    );
  }

  public isDisabled(operationPermission: OperationPermission): boolean {
    return operationPermission.state === CellState.Disabled || operationPermission.state === CellState.FixedNotSelected;
  }

  public showCheckIcon(operationPermission: OperationPermission): boolean {
    return operationPermission.state === CellState.FixedSelected;
  }

  public rowClass(permissionIndex: number): string {
    return permissionIndex % 2 === 0 ? 'roles-table__even-row' : 'roles-table__uneven-row';
  }
}
