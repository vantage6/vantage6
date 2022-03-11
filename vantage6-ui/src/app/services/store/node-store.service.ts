import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { EMPTY_NODE, Node } from 'src/app/interfaces/node';
import { removeMatchedIdFromArray } from 'src/app/shared/utils';
import { StoreBaseService } from './store-base.service';

@Injectable({
  providedIn: 'root',
})
export class NodeStoreService extends StoreBaseService {
  node = new BehaviorSubject<Node>(EMPTY_NODE);
  nodes = new BehaviorSubject<Node[]>([]);

  constructor() {
    super();
  }

  setSingle(node: Node) {
    this.node.next(node);
  }

  setList(nodes: Node[]) {
    this.nodes.next(nodes);
  }

  getSingle() {
    return this.node.asObservable();
  }

  getList() {
    return this.nodes.asObservable();
  }

  add(node: Node) {
    const updated_list = [...this.nodes.value, node];
    this.nodes.next(updated_list);
  }

  remove(node: Node) {
    this.nodes.next(removeMatchedIdFromArray(this.nodes.value, node.id));
  }

  hasListStored(): boolean {
    return this.nodes.value.length > 0;
  }
}
