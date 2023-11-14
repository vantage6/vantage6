/* eslint-disable @typescript-eslint/no-explicit-any */

import { Component, EventEmitter, Input, OnChanges, OnInit, Output, SimpleChanges } from '@angular/core';
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
  public state: CellState = CellState.Preselect;
  constructor(
    public resource: ResourceType,
    public scope: ScopeType,
    public operation: OperationType
  ) {}
}

enum CellState {
  Preselect,
  NotSelected,
  Selected
}

@Component({
  selector: 'app-roles-table',
  templateUrl: './roles-table.component.html',
  styleUrls: ['./roles-table.component.scss']
})
export class RolesTableComponent implements OnInit, OnChanges {
  @Input() rules: Rule[] = [];
  @Input() editable: boolean = false;

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

  public resourcePermissions: ResourcePermission[] = [];

  ngOnInit(): void {
    this.resourcePermissions = this.updateTable(this.rules);
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['rules']) {
      this.resourcePermissions = this.updateTable(changes['rules'].currentValue);
    }
  }

  private updateTable(rules: Rule[]) {
    return this.allResources.map((resource) => {
      const scopePermissions = this.allScopes.map((scope) => {
        const operationPermissions = this.allOperations.map((operation) => new OperationPermission(resource, scope, operation));
        return new ScopePermission(scope, operationPermissions);
      });

      const resourcePermission = new ResourcePermission(resource, scopePermissions);
      return resourcePermission;
    });
  }
}
