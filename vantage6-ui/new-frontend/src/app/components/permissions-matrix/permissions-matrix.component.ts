/* eslint-disable @typescript-eslint/no-explicit-any */

import { SelectionChange, SelectionModel } from '@angular/cdk/collections';
import { Component, EventEmitter, Input, OnChanges, OnDestroy, OnInit, Output, SimpleChanges } from '@angular/core';
import { Subscription } from 'rxjs';
import { isEqualString } from 'src/app/helpers/general.helper';
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
  FixedSelected,
  FixedNotSelected,
  NotSelected,
  Selected
}

class OperationPermissionDictionary {
  private _dictionary: { [key: string]: OperationPermission } = {};
  public add(permission: OperationPermission): void {
    if (!permission) return;
    const hash = this.getHash(permission.resource, permission.scope, permission.operation);
    this._dictionary[hash] = permission;
  }

  public get(resource: ResourceType, scope: ScopeType, operation: OperationType): OperationPermission {
    const hash = this.getHash(resource, scope, operation);
    return this._dictionary[hash];
  }

  public getAllOperationTypes(resource: ResourceType, scope: ScopeType): OperationPermission[] {
    const all: OperationPermission[] = [];
    for (const key in this._dictionary) if (key.startsWith(this.getHash(resource, scope))) all.push(this._dictionary[key]);
    return all;
  }

  private getHash(resource: ResourceType, scope: ScopeType, operation?: OperationType): string {
    const operationKey = operation ?? '';
    return `${resource}#${scope}#${operationKey}`;
  }
}

@Component({
  selector: 'app-permissions-matrix',
  templateUrl: './permissions-matrix.component.html',
  styleUrls: ['./permissions-matrix.component.scss']
})
export class PermissionsMatrixComponent implements OnInit, OnChanges, OnDestroy {
  /* Rules that are visualised as selected and cannot be unselected by the user */
  @Input() fixedSelected: Rule[] = [];
  /* Rules that can be selected or unselected.  */
  @Input() selectable: Rule[] = [];
  /* Selections that can be edited */
  @Input() preselected: Rule[] = [];
  @Input() userRules: Rule[] = [];

  @Output() changed: EventEmitter<Rule[]> = new EventEmitter();

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
    OperationType.VIEW,
    OperationType.CREATE,
    OperationType.DELETE,
    OperationType.EDIT,
    OperationType.SEND,
    OperationType.RECEIVE
  ];

  CellState = CellState;

  public resourcePermissions: ResourcePermission[] = [];

  public selection: SelectionModel<OperationPermission> = new SelectionModel<OperationPermission>(true, []);

  private selectionSubscription?: Subscription;
  private operationPermissionDictionary = new OperationPermissionDictionary();

  ngOnInit(): void {
    this.resourcePermissions = this.updateTable(this.fixedSelected, this.preselected, this.selectable);
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['fixedSelected'] || changes['preselected'] || changes['selectable']) {
      this.resourcePermissions = this.updateTable(this.fixedSelected, this.preselected, this.selectable);
    }
  }

  ngOnDestroy(): void {
    this.selectionUnsubscribe();
  }

  private selectionUnsubscribe(): void {
    this.selectionSubscription?.unsubscribe();
  }

  private selectionSubscribe(): void {
    this.selectionSubscription = this.selection.changed.subscribe((change: SelectionChange<OperationPermission>) =>
      this.handleSelectionChange(change)
    );
  }

  private addRelatedRules(operationPermissions: OperationPermission[]): void {
    this.selectionUnsubscribe();

    operationPermissions.forEach((operationPermission) => {
      if ([OperationType.CREATE, OperationType.EDIT, OperationType.DELETE].includes(operationPermission.operation)) {
        const viewPermission = this.operationPermissionDictionary.get(
          operationPermission.resource,
          operationPermission.scope,
          OperationType.VIEW
        );
        if (viewPermission && this.isEditable(viewPermission)) this.selection.select(viewPermission);
      }
    });

    this.selectionSubscribe();
  }

  private removeRelatedRules(operationPermissions: OperationPermission[]): void {
    this.selectionUnsubscribe();

    operationPermissions.forEach((operationPermission) => {
      if (operationPermission.operation === OperationType.VIEW) {
        const permissions = this.operationPermissionDictionary.getAllOperationTypes(
          operationPermission.resource,
          operationPermission.scope
        );
        permissions.forEach((permission) => {
          if (this.isEditable(permission)) this.selection.deselect(permission);
        });
      }
    });

    this.selectionSubscribe();
  }

  private isEditable(permission: OperationPermission): boolean {
    return permission.state === CellState.NotSelected || permission.state === CellState.Selected;
  }
  private handleSelectionChange(change: SelectionChange<OperationPermission>): void {
    const rules: Rule[] = [];
    this.addRelatedRules(change.added);
    this.removeRelatedRules(change.removed);
    this.selection.selected.forEach((permission) => {
      const rule = this.findRule(this.selectable, permission.resource, permission.scope, permission.operation);
      if (rule) rules.push(rule);
    });
    this.changed.emit(rules);
  }

  private updateTable(fixedSelected: Rule[], preSelected: Rule[], selectable: Rule[]): ResourcePermission[] {
    this.selectionUnsubscribe();
    this.selection.clear();

    const result = this.allResources
      .map((resource) => {
        const scopePermissions = this.allScopes
          .filter((scope) => this.hasSelectableOperations(resource, scope, selectable))
          .map((scope) => {
            const operationPermissions = this.allOperations.map((operation) => {
              const cellState = this.getCellState(fixedSelected, preSelected, selectable, resource, scope, operation);
              const operationPermission = new OperationPermission(resource, scope, operation, cellState);
              this.operationPermissionDictionary.add(operationPermission);
              if (cellState === CellState.Selected) this.selection.select(operationPermission);
              return operationPermission;
            });
            return new ScopePermission(scope, operationPermissions);
          });

        const resourcePermission = new ResourcePermission(resource, scopePermissions);
        return resourcePermission;
      })
      .filter((resourcePermission) => resourcePermission.scopes.length > 0);

    this.selectionSubscribe();

    return result;
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
    return !!this.findRule(rules, resource, scope, operation);
  }

  private findRule(rules: Rule[], resource: ResourceType, scope: ScopeType, operation: OperationType): Rule | undefined {
    return rules.find(
      (rule) => isEqualString(rule.name, resource) && isEqualString(rule.scope, scope) && isEqualString(rule.operation, operation)
    );
  }

  public showCheckBox(operationPermission: OperationPermission): boolean {
    return [CellState.Selected, CellState.NotSelected, CellState.FixedNotSelected].includes(operationPermission.state);
  }

  public isDisabled(operationPermission: OperationPermission): boolean {
    return operationPermission.state === CellState.FixedNotSelected;
  }

  public showCheckIcon(operationPermission: OperationPermission): boolean {
    return operationPermission.state === CellState.FixedSelected;
  }

  public rowClass(permissionIndex: number): string {
    return permissionIndex % 2 === 0 ? 'roles-table__even-row' : 'roles-table__uneven-row';
  }

  public selectPermission(permission: OperationPermission): void {
    this.selection.select(permission);
  }
}
