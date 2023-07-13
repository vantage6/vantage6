import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { NodeApiService } from 'src/app/services/api/node-api.service';
import { ConvertJsonService } from 'src/app/services/common/convert-json.service';
import { BaseDataService } from 'src/app/services/data/base-data.service';
import { Node, NodeWithOrg } from 'src/app/interfaces/node';
import { SocketioConnectService } from '../common/socketio-connect.service';
import {
  Pagination,
  allPages,
  defaultFirstPage,
} from 'src/app/interfaces/utils';

/**
 * Service for retrieving and updating node data.
 */
@Injectable({
  providedIn: 'root',
})
export class NodeDataService extends BaseDataService {
  constructor(
    protected apiService: NodeApiService,
    protected convertJsonService: ConvertJsonService,
    private socketService: SocketioConnectService
  ) {
    super(apiService, convertJsonService);
    this.socketService.getNodeStatusUpdates().subscribe((update) => {
      this.updateNodeStatus(update);
    });
  }

  /**
   * Get a node by id. If the node is not in the cache, it will be requested
   * from the vantage6 server.
   *
   * @param id The id of the node to get.
   * @param force_refresh Whether to force a refresh of the cache.
   * @returns An observable of the node.
   */
  async get(
    id: number,
    force_refresh: boolean = false
  ): Promise<Observable<Node>> {
    return (
      await super.get_base(id, this.convertJsonService.getNode, force_refresh)
    ).asObservable() as Observable<Node>;
  }

  /**
   * Get all nodes. If the nodes are not in the cache, they will be requested
   * from the vantage6 server.
   *
   * @param force_refresh Whether to force a refresh of the cache.
   * @param pagination The pagination parameters to use.
   * @returns An observable of the nodes.
   */
  async list(
    force_refresh: boolean = false,
    pagination: Pagination = defaultFirstPage()
  ): Promise<Observable<Node[]>> {
    return (await super.list_base(
      this.convertJsonService.getNode,
      pagination,
      force_refresh
    )).asObservable() as Observable<Node[]>;
  }

  /**
   * Get all nodes for an organization. If the nodes are not in the cache,
   * they will be requested from the vantage6 server.
   *
   * @param organization_id The id of the organization to get the nodes for.
   * @param force_refresh Whether to force a refresh of the cache.
   * @param pagination The pagination parameters to use.
   * @returns An observable of the nodes.
   */
  async org_list(
    organization_id: number,
    force_refresh: boolean = false,
    pagination: Pagination = allPages()
  ): Promise<Observable<Node[]>> {
    return (await this.org_list_base(
      organization_id,
      this.convertJsonService.getNode,
      pagination,
      force_refresh
    )).asObservable() as Observable<Node[]>;
  }

  /**
   * Get all nodes for a collaboration. If the nodes are not in the cache,
   * they will be requested from the vantage6 server.
   *
   * @param collaboration_id The id of the collaboration to get the nodes for.
   * @param force_refresh Whether to force a refresh of the cache.
   * @param pagination The pagination parameters to use.
   * @returns An observable of the nodes.
   */
  async collab_list(
    collaboration_id: number,
    force_refresh: boolean = false,
    pagination: Pagination = allPages()
  ): Promise<Observable<Node[]>> {
    return (await super.collab_list_base(
      collaboration_id,
      this.convertJsonService.getNode,
      pagination,
      force_refresh
    )) as Observable<Node[]>;
  }

  /**
   * Get all nodes with the given parameters. If the nodes are not in the
   * cache, they will be requested from the vantage6 server.
   *
   * @param pagination The pagination parameters to use.
   * @param request_params The parameters to use in the request.
   * @returns An observable of the nodes.
   */
  async list_with_params(
    pagination: Pagination = allPages(),
    request_params: any = {}
  ): Promise<Observable<Node[]>> {
    return (await super.list_with_params_base(
      this.convertJsonService.getNode,
      request_params,
      pagination,
    )).asObservable() as Observable<Node[]>;
  }

  /**
   * Update whether a node is offline/offline.
   *
   * @param status_update The status update to apply.
   */
  updateNodeStatus(status_update: any): void {
    let resources = this.resource_list.value as Node[];
    for (let r of resources) {
      if (r.id === status_update.id) {
        r.is_online = status_update.online;
      }
    }
    this.resource_list.next(resources);
  }

  /**
   * Save a node to the cache.
   *
   * @param node The node to save.
   * @returns The saved node.
   */
  save(node: NodeWithOrg): void {
    // remove organization and collaboration properties - these should be set
    // within components where needed
    if (node.organization) node.organization = undefined;
    if (node.collaboration) node.collaboration = undefined;
    super.save(node);
  }
}
