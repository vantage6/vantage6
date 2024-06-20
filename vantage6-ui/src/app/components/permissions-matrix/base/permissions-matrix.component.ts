/* eslint-disable @typescript-eslint/no-explicit-any */

import { SelectionChange, SelectionModel } from '@angular/cdk/collections';
import { Component, EventEmitter, Input, OnChanges, OnDestroy, OnInit, Output, SimpleChanges } from '@angular/core';
import { Subscription } from 'rxjs';
import { isEqualString } from 'src/app/helpers/general.helper';
import { OperationType, ResourceType, Rule, Rule_, ScopeType, StoreResourceType, StoreRule } from 'src/app/models/api/rule.model';

type ResourceType_ = ResourceType | StoreResourceType;

export class ServerResourcePermission {
  constructor(
    public resource: ResourceType,
    public scopes: ScopePermission[]
  ) {}
}

export class StoreResourcePermission {
  constructor(
    public resource: StoreResourceType,
    public operations: OperationPermission[]
  ) {}
}

export type ResourcePermission = ServerResourcePermission | StoreResourcePermission;

export class ScopePermission {
  constructor(
    public scope: ScopeType,
    public operations: OperationPermission[]
  ) {}
}

export class OperationPermission {
  constructor(
    public resource: ResourceType_,
    public scope: ScopeType | null,
    public operation: OperationType,
    public state: CellState,
    public displayClass: DisplayClass
  ) {}
}

export enum DisplayClass {
  FixedSelectedPrimary,
  FixedSelectedSecondary,
  Other
}

export enum CellState {
  NotApplicable,
  FixedSelected,
  FixedNotSelected,
  NotSelected,
  Selected
}

export class OperationPermissionDictionary {
  private _dictionary: { [key: string]: OperationPermission } = {};
  public add(permission: OperationPermission): void {
    if (!permission) return;
    const hash = this.getHash(permission.resource, permission.scope, permission.operation);
    this._dictionary[hash] = permission;
  }

  public get(resource: ResourceType_, scope: ScopeType | null, operation: OperationType): OperationPermission {
    const hash = this.getHash(resource, scope, operation);
    return this._dictionary[hash];
  }

  public getAllOperationTypes(resource: ResourceType_, scope: ScopeType | null): OperationPermission[] {
    const all: OperationPermission[] = [];
    for (const key in this._dictionary) if (key.startsWith(this.getHash(resource, scope))) all.push(this._dictionary[key]);
    return all;
  }

  private getHash(resource: ResourceType_, scope: ScopeType | null, operation?: OperationType): string {
    const operationKey = operation ?? '';
    const scopeKey = scope ?? '';
    return `${resource}#${scopeKey}#${operationKey}`;
  }
}

@Component({
  selector: 'app-permissions-matrix',
  templateUrl: './permissions-matrix.component.html',
  styleUrls: ['./permissions-matrix.component.scss']
})
export abstract class BasePermissionsMatrixComponent implements OnInit, OnChanges, OnDestroy {
  /* Rules that are visualised as selected and cannot be unselected by the user. */
  @Input() fixedSelectedPrimary: Rule_[] = [];
  /* Same as fixedSelectedPrimary, but with a different visual display. */
  @Input() fixedSelectedSecondary: Rule_[] = [];
  /* Rules that can be selected or unselected.  */
  @Input() selectable: Rule_[] = [];
  /* Selections that can be edited */
  @Input() preselected: Rule_[] = [];

  @Output() changed: EventEmitter<Rule_[]> = new EventEmitter();

  // get resources, scopes and operations from enums, but filter out the ones with no rules attached to them
  CellState = CellState;

  abstract resourcePermissions: ResourcePermission[];

  /* A handy variable that is the merge of fixedSelectedPrimary and fixedSelectedSecondary. */
  get fixedSelected(): Rule_[] {
    return this.fixedSelectedPrimary.concat(this.fixedSelectedSecondary);
  }

  public selection: SelectionModel<OperationPermission> = new SelectionModel<OperationPermission>(true, []);

  private selectionSubscription?: Subscription;
  protected operationPermissionDictionary = new OperationPermissionDictionary();

  ngOnInit(): void {
    this.resourcePermissions = this.updateTable(this.fixedSelected, this.preselected, this.selectable);
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['fixedSelectedPrimary'] || changes['fixedSelectedSecondary'] || changes['preselected'] || changes['selectable']) {
      this.resourcePermissions = this.updateTable(this.fixedSelected, this.preselected, this.selectable);
    }
  }

  protected abstract updateTable(fixedSelected: Rule_[], preSelected: Rule_[], selectable: Rule_[]): ResourcePermission[];

  ngOnDestroy(): void {
    this.selectionUnsubscribe();
  }

  protected selectionUnsubscribe(): void {
    this.selectionSubscription?.unsubscribe();
  }

  protected selectionSubscribe(): void {
    this.selectionSubscription = this.selection.changed.subscribe((change: SelectionChange<OperationPermission>) =>
      this.handleSelectionChange(change)
    );
  }

  protected addRelatedRules(operationPermissions: OperationPermission[]): void {
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

  protected removeRelatedRules(operationPermissions: OperationPermission[]): void {
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
    const rules: Rule_[] = [];
    this.addRelatedRules(change.added);
    this.removeRelatedRules(change.removed);
    this.selection.selected.forEach((permission) => {
      const rule = this.findRule(this.selectable, permission.resource, permission.scope, permission.operation);
      if (rule) rules.push(rule);
    });
    this.changed.emit(rules);
  }

  private isStoreRule(rule: Rule_): rule is StoreRule {
    return (rule as Rule).scope === undefined;
  }

  private scopeMatches(rule: Rule_, scope: ScopeType | null): boolean {
    // note that algorithm store rules have no scope so they are not checked
    return this.isStoreRule(rule) || (scope != null && isEqualString(rule.scope, scope));
  }

  protected hasOperationsForDisplay(resource: ResourceType_, scope: ScopeType, rules: Rule_[]): boolean {
    return !!rules.find((rule) => isEqualString(rule.name, resource) && this.scopeMatches(rule, scope));
  }

  protected getDisplayClass(
    fixedSelectedPrimary: Rule_[],
    fixedSelectedSecondary: Rule_[],
    resource: ResourceType_,
    scope: ScopeType | null,
    operation: OperationType
  ): DisplayClass {
    if (this.containsRule(fixedSelectedPrimary, resource, scope, operation)) return DisplayClass.FixedSelectedPrimary;
    if (this.containsRule(fixedSelectedSecondary, resource, scope, operation)) return DisplayClass.FixedSelectedSecondary;
    return DisplayClass.Other;
  }

  protected getCellState(
    fixedSelected: Rule_[],
    preselected: Rule_[],
    selectable: Rule_[],
    resource: ResourceType_,
    scope: ScopeType | null,
    operation: OperationType
  ): CellState {
    if (!this.containsRule([...selectable, ...fixedSelected], resource, scope, operation)) return CellState.NotApplicable;

    if (this.containsRule(fixedSelected, resource, scope, operation)) return CellState.FixedSelected;

    const isAllowed = this.isAllowedToAssignRuleToRole(resource, scope, operation);
    const isPreselected = this.containsRule(preselected, resource, scope, operation);

    if (isAllowed && isPreselected) return CellState.Selected;
    if (isAllowed && !isPreselected) return CellState.NotSelected;
    if (!isAllowed && isPreselected) return CellState.FixedSelected;

    return CellState.FixedNotSelected;
  }

  protected abstract isAllowedToAssignRuleToRole(resourceType: ResourceType_, scope: ScopeType | null, operation: OperationType): boolean;

  protected containsRule(rules: Rule_[], resource: ResourceType_, scope: ScopeType | null, operation: OperationType): boolean {
    return !!this.findRule(rules, resource, scope, operation);
  }

  protected findRule(rules: Rule_[], resource: ResourceType_, scope: ScopeType | null, operation: OperationType): Rule_ | undefined {
    return rules.find(
      (rule) => isEqualString(rule.name, resource) && this.scopeMatches(rule, scope) && isEqualString(rule.operation, operation)
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

  public getIconClass(permission: OperationPermission): string {
    // Cellstate is always selected
    return permission.displayClass === DisplayClass.FixedSelectedSecondary ? 'roles-table__check--secondary' : '';
  }
}
