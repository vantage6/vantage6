/* eslint-disable @typescript-eslint/no-explicit-any */

import { SelectionModel } from '@angular/cdk/collections';
import { Component, EventEmitter, Input, OnChanges, OnInit, Output, SimpleChanges } from '@angular/core';
import { isEqualString } from 'src/app/helpers/task.helper';
import { OperationType, ResourceType, Rule, ScopeType } from 'src/app/models/api/rule.model';

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
  Preselected,
  NotSelected,
  Selected
}

@Component({
  selector: 'app-roles-table',
  templateUrl: './roles-table.component.html',
  styleUrls: ['./roles-table.component.scss']
})
export class RolesTableComponent implements OnInit, OnChanges {
  @Input() preselected: Rule[] = [];
  @Input() rules: Rule[] = [];

  @Output() edited: EventEmitter<Rule[]> = new EventEmitter();

  allResources = [ResourceType.COLLABORATION, ResourceType.ORGANIZATION, ResourceType.TASK, ResourceType.USER];
  allScopes = [ScopeType.OWN, ScopeType.ORGANIZATION, ScopeType.COLLABORATION, ScopeType.GLOBAL];
  allOperations = [
    OperationType.CREATE,
    OperationType.DELETE,
    OperationType.EDIT,
    OperationType.RECEIVE,
    OperationType.VIEW,
    OperationType.SEND,
    OperationType.RECEIVE
  ];

  CellState = CellState;

  public resourcePermissions: ResourcePermission[] = [];

  public selection: SelectionModel<OperationPermission> = new SelectionModel<OperationPermission>(true, []);

  ngOnInit(): void {
    this.resourcePermissions = this.updateTable(this.preselected, this.rules);
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['preselected'] || changes['rules']) {
      this.resourcePermissions = this.updateTable(this.preselected, this.rules);
    }
  }

  private updateTable(preselected: Rule[], rules: Rule[]) {
    return this.allResources.map((resource) => {
      const scopePermissions = this.allScopes.map((scope) => {
        const operationPermissions = this.allOperations.map((operation) => {
          const cellState = this.getCellState(preselected, rules, resource, scope, operation);
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

  private getCellState(preselected: Rule[], rules: Rule[], resource: ResourceType, scope: ScopeType, operation: OperationType): CellState {
    if (this.containsRule(preselected, resource, scope, operation)) return CellState.Preselected;

    if (this.containsRule(rules, resource, scope, operation)) return CellState.Selected;

    return CellState.NotSelected;
  }

  private containsRule(rules: Rule[], resource: ResourceType, scope: ScopeType, operation: OperationType): boolean {
    return !!rules.find(
      (rule) => isEqualString(rule.name, resource) && isEqualString(rule.scope, scope) && isEqualString(rule.operation, operation)
    );
  }
}
