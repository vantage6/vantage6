import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { EMPTY_NODE, Node } from 'src/app/interfaces/node';
import { removeMatchedIdFromArray } from 'src/app/shared/utils';

@Injectable({
  providedIn: 'root',
})
export class NodeStoreService {
  node = new BehaviorSubject<Node>(EMPTY_NODE);
  nodes = new BehaviorSubject<Node[]>([]);

  constructor() {}

  setNode(node: Node) {
    this.node.next(node);
  }

  setNodes(nodes: Node[]) {
    this.nodes.next(nodes);
  }

  getNode() {
    return this.node.asObservable();
  }

  getNodes() {
    return this.nodes.asObservable();
  }

  add(node: Node) {
    const updated_list = [...this.nodes.value, node];
    this.nodes.next(updated_list);
  }

  remove(node: Node) {
    this.nodes.next(removeMatchedIdFromArray(this.nodes.value, node.id));
  }

  hasNodesStored(): boolean {
    console.log(this.nodes.value);
    return this.nodes.value.length > 0;
  }
}
