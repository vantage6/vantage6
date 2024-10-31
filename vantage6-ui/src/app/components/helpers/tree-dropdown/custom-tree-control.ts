import { FlatTreeControl } from '@angular/cdk/tree';
export class CustomTreeControl<T> extends FlatTreeControl<T> {
  public expandParents(node: T): void {
    const parent = this.getParent(node);
    this.expand(parent);
    if (parent && this.getLevel(parent) > 0) {
      this.expandParents(parent);
    }
  }
  
  public getParent(node: T): T {
    const currentLevel = this.getLevel(node);
    if (currentLevel < 1) {
      return null as any;
    }

    const startIndex = this.dataNodes.indexOf(node) - 1;
    for (let i = startIndex; i >= 0; i--) {
      const currentNode = this.dataNodes[i];
      if (this.getLevel(currentNode) < currentLevel) {
        return currentNode;
      }
    }
    return null as any
  }
}
