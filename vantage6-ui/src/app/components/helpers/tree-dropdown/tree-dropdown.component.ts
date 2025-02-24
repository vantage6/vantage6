import { Component, Input, OnInit, OnChanges, ElementRef, ViewChild, Output, EventEmitter, SimpleChanges } from '@angular/core';
import { SelectionModel } from '@angular/cdk/collections';
import { MatTreeFlatDataSource, MatTreeFlattener, MatTree, MatTreeNodeDef, MatTreeNode, MatTreeNodePadding } from '@angular/material/tree';
import { ParentTreeControl } from './parent-tree-control';
import { ConnectionPositionPair, CdkOverlayOrigin, CdkConnectedOverlay } from '@angular/cdk/overlay';
import { MatFormField, MatLabel } from '@angular/material/form-field';
import { MatChipGrid, MatChipRow, MatChipRemove, MatChipInput } from '@angular/material/chips';
import { MatIcon } from '@angular/material/icon';
import { MatInput } from '@angular/material/input';
import { ReactiveFormsModule, FormsModule } from '@angular/forms';
import { NgIf, NgClass } from '@angular/common';
import { MatIconButton } from '@angular/material/button';
import { MatCheckbox } from '@angular/material/checkbox';
import { MatRadioButton } from '@angular/material/radio';
import { TranslateModule } from '@ngx-translate/core';
import { HighlightedTextPipe } from '../../../pipes/highlighted-text.pipe';
import { TranslateService } from '@ngx-translate/core';

export interface ITreeInputSearchConfig {
  searchActive: boolean;
  searchInput: string;
}

export interface ITreeInputSearch {
  value: string;
  config: ITreeInputSearchConfig;
}

export interface ITreeInputNode {
  code: string | number;
  label: string;
  isFolder: boolean;
  children: ITreeInputNode[];
  description?: string;
  parentCode?: string | number;
  pathLabel?: string;
}

export interface ITreeInputNodeFlat extends ITreeInputNode {
  visible: boolean;
  level: number;
  expandable: boolean;
}

export interface ITreeSelectedValue {
  code: string | number;
  label: string;
  parentCode?: string | number;
  pathLabel?: string;
}

@Component({
  selector: 'app-tree-dropdown',
  templateUrl: './tree-dropdown.component.html',
  styleUrls: ['./tree-dropdown.component.scss'],
  imports: [
    CdkOverlayOrigin,
    MatFormField,
    MatLabel,
    MatChipGrid,
    MatChipRow,
    MatChipRemove,
    MatIcon,
    MatInput,
    MatChipInput,
    ReactiveFormsModule,
    FormsModule,
    CdkConnectedOverlay,
    NgIf,
    MatIconButton,
    MatTree,
    NgClass,
    MatTreeNodeDef,
    MatTreeNode,
    MatTreeNodePadding,
    MatCheckbox,
    MatRadioButton,
    TranslateModule,
    HighlightedTextPipe
  ]
})
export class TreeDropdownComponent implements OnInit, OnChanges {
  @Input() isMultiSelect = false;
  @Input() nodes: ITreeInputNode[] = [];
  @Input() selectedTreeNodes: ITreeSelectedValue[] = [];
  @Input() filterPlaceholder: string = '';
  @Output() valueChanged: EventEmitter<ITreeSelectedValue[]> = new EventEmitter();
  @ViewChild('searchInput')
  searchInput?: ElementRef<HTMLInputElement>;
  @ViewChild(MatFormField) formField?: MatFormField;

  private getLevel = (treeNode: ITreeInputNodeFlat) => treeNode.level;
  private isExpandable = (treeNode: ITreeInputNodeFlat) => treeNode.expandable;
  private getChildren = (treeNode: ITreeInputNode): ITreeInputNode[] => treeNode.children;
  private transformer = (treeNode: ITreeInputNode, level: number) => {
    const existingNode = this.nestedTreeNodeMap.get(treeNode);
    const flatNode = existingNode && existingNode.code === treeNode.code ? existingNode : <ITreeInputNodeFlat>{};
    flatNode.code = treeNode.code;
    flatNode.label = treeNode.label;
    flatNode.description = treeNode.description;
    flatNode.visible = true;
    flatNode.level = level;
    flatNode.expandable = !!treeNode.children?.length;
    flatNode.isFolder = treeNode.isFolder;
    flatNode.parentCode = treeNode.parentCode;
    flatNode.pathLabel = treeNode.pathLabel;
    this.flatTreeNodeMap.set(flatNode, treeNode);
    this.nestedTreeNodeMap.set(treeNode, flatNode);
    return flatNode;
  };
  private flatTreeNodeMap = new Map<ITreeInputNodeFlat, ITreeInputNode>();
  private nestedTreeNodeMap = new Map<ITreeInputNode, ITreeInputNodeFlat>();
  private treeFlattener: MatTreeFlattener<ITreeInputNode, ITreeInputNodeFlat> = new MatTreeFlattener(
    this.transformer,
    this.getLevel,
    this.isExpandable,
    this.getChildren
  );
  public treeControl: ParentTreeControl<ITreeInputNodeFlat> = new ParentTreeControl<ITreeInputNodeFlat>(this.getLevel, this.isExpandable);
  public dataSource: MatTreeFlatDataSource<ITreeInputNode, ITreeInputNodeFlat> = new MatTreeFlatDataSource(
    this.treeControl,
    this.treeFlattener
  );
  public checklistSelection: SelectionModel<ITreeInputNodeFlat> = new SelectionModel();
  public hasChild = (_: number, _nodeData: ITreeInputNodeFlat) => _nodeData.expandable;
  public treeSearch: ITreeInputSearch = { value: '', config: { searchActive: false, searchInput: '' } };
  public isOverlayOpen = false;
  public overlayPosition: ConnectionPositionPair[] = [
    { originX: 'start', originY: 'bottom', overlayX: 'start', overlayY: 'top' },
    { originX: 'start', originY: 'top', overlayX: 'start', overlayY: 'bottom' }
  ];
  public overlayWidth: string = '100%';

  constructor(private translateService: TranslateService) {}

  public ngOnInit(): void {
    this.setTreeNodes();
    if (!this.filterPlaceholder) {
      this.filterPlaceholder = this.translateService.instant('general.filter');
    }
  }

  public ngOnChanges(changes: SimpleChanges): void {
    if (changes['nodes']) {
      this.setTreeNodes();
    }
  }

  private getSelectedFlatNodes(selectedNodes: ITreeSelectedValue[], flattenedData: ITreeInputNodeFlat[]): ITreeInputNodeFlat[] {
    return selectedNodes
      ? selectedNodes.map((selectedValueItem: ITreeSelectedValue) => {
          const currentFlatTreeItem = flattenedData.find((item: ITreeInputNodeFlat) => item.code === selectedValueItem.code);
          return currentFlatTreeItem ? currentFlatTreeItem : <ITreeInputNodeFlat>{};
        })
      : [];
  }

  private setTreeNodes() {
    const clonedNodes = JSON.parse(JSON.stringify(this.nodes));
    const treeNodes = this.formatTreeNodes(clonedNodes);
    this.dataSource.data = [...treeNodes];
    const selectedNodes: ITreeInputNodeFlat[] = this.getSelectedFlatNodes(this.selectedTreeNodes, this.treeControl.dataNodes)?.filter(
      () => {
        return this.selectedTreeNodes.find((item) => item.code !== undefined);
      }
    );
    this.checklistSelection = new SelectionModel(true, selectedNodes);

    this.resetTree();
    this.checklistSelection.selected.forEach((item) => {
      this.treeControl.expandParents(item);
    });
  }

  private formatTreeNodes(treeNodes: ITreeInputNode[], parentCode?: string, parentPathLabel?: string): ITreeInputNode[] {
    const parentCodeFormatted = parentCode ? parentCode : '';
    const formattedTree = treeNodes.map((treeNode: ITreeInputNode) => {
      const pathLabelFormatted = parentPathLabel ? parentPathLabel.concat(` / ${treeNode.label}`) : treeNode.label;
      if (treeNode.children && treeNode.children.length > 0) {
        treeNode.children = this.formatTreeNodes(treeNode.children, treeNode.code.toString(), pathLabelFormatted);
      }
      return { ...treeNode, pathLabel: pathLabelFormatted, parentCode: parentCodeFormatted };
    });
    return formattedTree;
  }

  private filterTreeNodesByName(term: string): void {
    const foundLabels: string[] = [];
    const highestLevelNumber: number = this.uniqTreeNodes(this.treeControl.dataNodes, 'level')
      .map((item) => item.level)
      .reduce(function (p, v) {
        return p > v ? p : v;
      });

    this.treeControl.dataNodes.forEach((treeInputNode: ITreeInputNodeFlat) => {
      const isSearchTerm = treeInputNode?.label?.toLowerCase().indexOf(term.toLowerCase()) > -1;
      if (isSearchTerm) {
        foundLabels.push(treeInputNode.label);
        let parent;
        for (let i = highestLevelNumber; i >= 0; i--) {
          const iterateetreeInputNode = parent ? parent : treeInputNode;
          parent = this.treeControl.getParent(iterateetreeInputNode);
          if (parent !== null) {
            foundLabels.push(parent.label);
          }
        }
      }
      return;
    });

    this.treeControl.dataNodes.map((treeNode: ITreeInputNodeFlat) => {
      const treeNodeLevel = this.getLevel(treeNode);
      let isParentMatch = false;
      let curTreeNode = treeNode;
      for (let i = treeNodeLevel; i > 0 && !isParentMatch; i--) {
        const parent = this.treeControl.getParent(curTreeNode);
        if (parent !== null) {
          isParentMatch = foundLabels.indexOf(parent.label) !== -1;
          curTreeNode = parent;
        }
      }
      treeNode.visible = foundLabels.indexOf(treeNode.label) !== -1 || isParentMatch;
      if (treeNode.visible) {
        this.treeControl.expand(treeNode);
      }
      return treeNode;
    });
  }

  public deselectNodeByCode(code: string) {
    if (this.checklistSelection) {
      const treeNode = this.checklistSelection.selected?.find((flatNode) => flatNode.code == code);
      if (treeNode) {
        this.isMultiSelect ? this.checklistSelection.deselect(treeNode) : this.checklistSelection.clear();
      }
    }
    this.changedSelectedValues();
  }

  public changedNode(treeNode: ITreeInputNodeFlat): void {
    if (treeNode.isFolder) {
      return;
    }
    if (this.checklistSelection) {
      if (!this.isMultiSelect) {
        this.checklistSelection.clear();
        this.checklistSelection.select(treeNode);
      } else {
        this.checklistSelection.toggle(treeNode);
      }
    }
    this.changedSelectedValues();
  }

  public changedSearchInput() {
    const curSearchInput = this.treeSearch.value;
    const searchActive = curSearchInput.length > -1;
    if (!searchActive && this.treeSearch.config.searchActive) {
      this.resetTree();
    }
    this.treeSearch = { value: curSearchInput, config: { searchActive, searchInput: curSearchInput } };

    if (searchActive) {
      this.filterTreeNodesByName(curSearchInput);
    }
  }

  private changedSelectedValues() {
    const values: ITreeInputNodeFlat[] = this.checklistSelection ? this.checklistSelection.selected : [];
    const selectedValues =
      values && values.length !== 0
        ? values.map((item) => {
            return { code: item.code, label: item.label, parentCode: item.parentCode, pathLabel: item.pathLabel };
          })
        : [];
    if (this.isOverlayOpen) {
      window.dispatchEvent(new Event('resize'));
    }
    this.valueChanged.emit([...selectedValues]);
  }

  private resetTree(): void {
    this.treeControl.collapseAll();
    if (this.treeControl.dataNodes) {
      this.treeControl.dataNodes.map((treeInputNode: ITreeInputNodeFlat) => {
        treeInputNode.visible = true;
        return treeInputNode;
      });
    }
  }

  public expandOrCollapseAll() {
    if (this.isSomeCollapsed()) {
      this.treeControl.expandAll();
    } else {
      this.treeControl.collapseAll();
    }
  }

  public expandOrCollapse(treeNode: ITreeInputNodeFlat) {
    this.treeControl.toggle(treeNode);
  }

  public isSomeCollapsed(): boolean {
    return this.treeControl.dataNodes.some((treeNodeFlat: ITreeInputNodeFlat) => !this.treeControl.isExpanded(treeNodeFlat));
  }

  public isSomeDescendentSelected(treeNode: ITreeInputNodeFlat): boolean {
    const isTreeNodeSelected = this.isTreeNodeSelected(treeNode);
    const anyChildNodeSelected = this.treeControl?.getDescendants(treeNode)?.filter((child) => this.isTreeNodeSelected(child))?.length > 0;
    return isTreeNodeSelected || anyChildNodeSelected;
  }

  public isTreeNodeSelected(treeNode: ITreeInputNodeFlat): boolean {
    if (this.checklistSelection) {
      return this.checklistSelection && this.checklistSelection.isSelected(treeNode);
    } else {
      return false;
    }
  }

  public isTreeLayered(): boolean {
    return this.treeControl && this.treeControl.dataNodes && this.uniqTreeNodes(this.treeControl.dataNodes, 'level').length > 1;
  }

  public openOverlay(event: Event) {
    this.setOverlayWidth();
    this.isOverlayOpen = true;
    event.stopPropagation();
  }

  public setOverlayWidth() {
    const formFieldWidth = this.formField?._elementRef.nativeElement.offsetWidth ?? 'auto';
    this.overlayWidth = formFieldWidth;
  }

  private uniqTreeNodes = (treeNodes: ITreeInputNodeFlat[], param: string) => {
    const cb = typeof param === 'function' ? param : (treeNode: ITreeInputNodeFlat) => treeNode[param as keyof ITreeInputNodeFlat];
    return [
      ...treeNodes
        .reduce((map, treeNode) => {
          const key = treeNode === null || treeNode === undefined ? treeNode : cb(treeNode);
          map.has(key) || map.set(key, treeNode);
          return map;
        }, new Map())
        .values()
    ];
  };
}
