import { FlatTreeControl } from '@angular/cdk/tree';
export class ParentTreeControl<T> extends FlatTreeControl<T> {
  // Expand all parent folders. This is used to expand parent folders of selected items when the tree is loaded.
  public expandParents(treeNode: T): void {
    const parent = this.getParent(treeNode);
    if (parent) {
      this.expand(parent);
      if (this.getLevel(parent) > 0) {
        this.expandParents(parent);
      }
    }
  }

  public getParent(treeNode: T): T | null {
    const currentLevel = this.getLevel(treeNode);
    if (currentLevel < 1) {
      return null;
    }

    const startIndex = this.dataNodes.indexOf(treeNode) - 1;
    for (let i = startIndex; i >= 0; i--) {
      const currentNode = this.dataNodes[i];
      if (this.getLevel(currentNode) < currentLevel) {
        return currentNode;
      }
    }
    return null;
  }
}
