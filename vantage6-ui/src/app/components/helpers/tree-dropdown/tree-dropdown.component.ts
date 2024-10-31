// TODO markupNodeLabel needs to be replaced by HighlightedTextPipe introduced in task #1361 (PR in review)
// TODO check if multiselect works properly

import { Component, Input, OnInit, ElementRef, ViewChild, Output, EventEmitter, SimpleChanges } from '@angular/core';
import { SelectionModel } from '@angular/cdk/collections';
import { MatTreeFlatDataSource, MatTreeFlattener } from '@angular/material/tree';
import { CustomTreeControl } from './custom-tree-control';

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
  styleUrls: ['./tree-dropdown.component.scss']
})
export class TreeDropdownComponent implements OnInit {
  @Input() isMultiSelect = false;
  @Input() nodes: ITreeInputNode[] = [];
  @Input() selectedNodes: ITreeSelectedValue[] = [];
  @Output() valueChanged: EventEmitter<ITreeSelectedValue[]> = new EventEmitter();
  @ViewChild('searchInput')
  searchInput?: ElementRef<HTMLInputElement>;

  private getLevel = (node: ITreeInputNodeFlat) => node.level;
  private isExpandable = (node: ITreeInputNodeFlat) => node.expandable;
  private getChildren = (node: ITreeInputNode): ITreeInputNode[] => node.children;
  private transformer = (node: ITreeInputNode, level: number) => {
    const existingNode = this.nestedNodeMap.get(node);
    const flatNode = existingNode && existingNode.code === node.code ? existingNode : <ITreeInputNodeFlat>{};
    flatNode.code = node.code;
    flatNode.label = node.label;
    flatNode.description = node.description;
    flatNode.visible = true;
    flatNode.level = level;
    flatNode.expandable = !!node.children?.length;
    flatNode.isFolder = node.isFolder;
    flatNode.parentCode = node.parentCode;
    flatNode.pathLabel = node.pathLabel;
    this.flatNodeMap.set(flatNode, node);
    this.nestedNodeMap.set(node, flatNode);
    return flatNode;
  };
  private flatNodeMap = new Map<ITreeInputNodeFlat, ITreeInputNode>();
  private nestedNodeMap = new Map<ITreeInputNode, ITreeInputNodeFlat>();
  private treeFlattener: MatTreeFlattener<ITreeInputNode, ITreeInputNodeFlat> = new MatTreeFlattener(
    this.transformer,
    this.getLevel,
    this.isExpandable,
    this.getChildren
  );
  public treeControl: CustomTreeControl<ITreeInputNodeFlat> = new CustomTreeControl<ITreeInputNodeFlat>(this.getLevel, this.isExpandable);
  public dataSource: MatTreeFlatDataSource<ITreeInputNode, ITreeInputNodeFlat> = new MatTreeFlatDataSource(
    this.treeControl,
    this.treeFlattener
  );
  public checklistSelection: SelectionModel<ITreeInputNodeFlat> = new SelectionModel();
  public hasChild = (_: number, _nodeData: ITreeInputNodeFlat) => _nodeData.expandable;
  public treeSearch: ITreeInputSearch = {
    value: '',
    config: {
      searchActive: false,
      searchInput: ''
    }
  };

  constructor() {}

  public ngOnInit(): void {
    this.setTreeNodes();
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
    const selectedNodes: ITreeInputNodeFlat[] = this.getSelectedFlatNodes(this.selectedNodes, this.treeControl.dataNodes)?.filter(
      () => {
        return this.selectedNodes.find((item) => item.code !== undefined);
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
      return {
        ...treeNode,
        pathLabel: pathLabelFormatted,
        parentCode: parentCodeFormatted
      };
    });
    return formattedTree;
  }

  private filterTreeNodesByName(term: string): void {
    const foundLabels: string[] = [];
    const highestLevelNumber: number = this.uniqDataNodes(this.treeControl.dataNodes, 'level')
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

    this.treeControl.dataNodes.map((node: ITreeInputNodeFlat) => {
      node.visible = foundLabels.indexOf(node.label) !== -1;
      if (node.visible) {
        this.treeControl.expand(node);
      }
      return node;
    });
  }

  public deselectNodeByCode(code: string) {
    if (this.checklistSelection) {
      const node = this.checklistSelection.selected?.find((flatNode) => flatNode.code == code);
      if (node) {
        this.isMultiSelect ? this.checklistSelection.deselect(node) : this.checklistSelection.clear();
      }
    }
    this.changedSelectedValues();
  }

  public changedNode(node: ITreeInputNodeFlat): void {
    if (node.isFolder) {
      return;
    }
    if (this.checklistSelection) {
      if (!this.isMultiSelect) {
        this.checklistSelection.clear();
        this.checklistSelection.select(node);
      } else {
        this.checklistSelection.toggle(node);
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
    this.treeSearch = {
      value: curSearchInput,
      config: {
        searchActive,
        searchInput: curSearchInput
      }
    };

    if (searchActive) {
      this.filterTreeNodesByName(curSearchInput);
    }
  }

  private changedSelectedValues() {
    const values: ITreeInputNodeFlat[] = this.checklistSelection ? this.checklistSelection.selected : [];
    const selectedValue = values && values.length !== 0
      ? values.map((item) => {
          return {
            code: item.code,
            label: item.label,
            parentCode: item.parentCode,
            pathLabel: item.pathLabel
          }
        })
      : [];
    this.valueChanged.emit([...selectedValue]);
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

  public isSomeCollapsed(): boolean {
    return this.treeControl.dataNodes.some((e: any) => !this.treeControl.isExpanded(e));
  }

  public isSomeDescendentSelected(node: ITreeInputNodeFlat): boolean {
    const isNodeSelected = this.isNodeSelected(node);
    const anyChildNodeSelected = this.treeControl?.getDescendants(node)?.filter((child) => this.isNodeSelected(child))?.length > 0;
    return isNodeSelected || anyChildNodeSelected;
  }

  public isNodeSelected(node: ITreeInputNodeFlat): boolean {
    if (this.checklistSelection) {
      return this.checklistSelection && this.checklistSelection.isSelected(node);
    } else {
      return false;
    }
  }

  public isTreeLayered(): boolean {
    return this.treeControl && this.treeControl.dataNodes && this.uniqDataNodes(this.treeControl.dataNodes, 'level').length > 1;
  }

  public markupNodeLabel(node: ITreeInputNodeFlat): string {
    if (this.treeSearch?.config && this.treeSearch?.config?.searchActive !== false) {
      const searchIndex = node?.label?.toLowerCase()?.indexOf(this.treeSearch?.config?.searchInput?.toLowerCase());
      if (searchIndex !== -1) {
        const startIndex = searchIndex;
        const endIndex = searchIndex + this.treeSearch?.config?.searchInput?.length;
        const firstPart = node?.label?.substring(0, startIndex);
        const searchPart = node?.label?.substring(startIndex, endIndex);
        const lastPart = node?.label?.substring(endIndex, node?.label?.length);
        return `${firstPart}<strong>${searchPart}</strong>${lastPart}`.split(' ').join('&nbsp;');
      }
    }
    return `${node?.label}`;
  }

  private uniqDataNodes = (dataNodes: ITreeInputNodeFlat[], param: string) => {
    const cb = typeof param === 'function' ? param : (o: any) => o[param];
    return [
      ...dataNodes
        .reduce((map, node) => {
          const key = node === null || node === undefined ? node : cb(node);
          map.has(key) || map.set(key, node);
          return map;
        }, new Map())
        .values()
    ];
  }
}