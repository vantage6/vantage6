import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { EMPTY_NODE, Node } from 'src/app/interfaces/node';

@Injectable({
  providedIn: 'root',
})
export class NodeEditService {
  node = new BehaviorSubject<Node>(EMPTY_NODE);

  constructor() {}

  setNode(node: Node) {
    this.node.next(node);
  }

  getNode() {
    return this.node.asObservable();
  }
}
