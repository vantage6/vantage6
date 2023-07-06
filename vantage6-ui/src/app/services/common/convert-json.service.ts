import { Injectable } from '@angular/core';

import { Role } from 'src/app/interfaces/role';
import { Rule } from 'src/app/interfaces/rule';
import { User } from 'src/app/interfaces/user';
import { Node } from 'src/app/interfaces/node';
import { Task } from 'src/app/interfaces/task';
import { Organization } from 'src/app/interfaces/organization';
import { deepcopy, getById } from 'src/app/shared/utils';
import { Collaboration } from 'src/app/interfaces/collaboration';
import { ResType } from 'src/app/shared/enum';
import { Run } from 'src/app/interfaces/run';

@Injectable({
  providedIn: 'root',
})
export class ConvertJsonService {
  // Service to cast JSONs from API calls to their respective interfaces

  constructor() {}

  getRule(rule_json: any): Rule {
    return {
      id: rule_json.id,
      type: ResType.RULE,
      operation: rule_json.operation.toLowerCase(),
      resource: rule_json.name.toLowerCase(),
      scope: rule_json.scope.toLowerCase(),
    };
  }

  getRole(role_json: any): Role {
    return {
      id: role_json.id,
      type: ResType.ROLE,
      name: role_json.name,
      description: role_json.description,
      organization_id: role_json.organization
        ? role_json.organization.id
        : null,
      rules: [], // rules are added later
    };
  }

  getUser(user_json: any, roles: Role[], rules: Rule[]): User {
    let user_roles: Role[] = [];
    // if (user_json.roles) {
    //   user_json.roles.forEach((role: any) => {
    //     let r = getById(roles, role.id);
    //     if (r !== undefined) {
    //       user_roles.push(r);
    //     }
    //   });
    // }
    let user_rules: Rule[] = [];
    // if (user_json.rules) {
    //   user_json.rules.forEach((rule: any) => {
    //     let r = getById(rules, rule.id);
    //     user_rules.push(r);
    //   });
    // }
    return {
      id: user_json.id,
      type: ResType.USER,
      username: user_json.username,
      first_name: user_json.firstname,
      last_name: user_json.lastname,
      email: user_json.email,
      organization_id: user_json.organization.id,
      roles: user_roles,
      rules: user_rules,
    };
  }

  getOrganization(org_json: any): Organization {
    let col_ids: number[] = [];
    // if (org_json.collaborations) {
    //   for (let col of org_json.collaborations) {
    //     col_ids.push(col.id);
    //   }
    // }
    return {
      id: org_json.id,
      type: ResType.ORGANIZATION,
      name: org_json.name,
      address1: org_json.address1,
      address2: org_json.address2,
      zipcode: org_json.zipcode,
      country: org_json.country,
      domain: org_json.domain,
      public_key: org_json.public_key,
      collaboration_ids: col_ids,
    };
  }

  // TODO we have to come up with something where we can also obtain the
  // collaborations without first obtaining the organizations. Especially because
  // we don't now how many organizations there may be (could be hundreds)
  getCollaboration(
    coll_json: any,
    organizations: Organization[],
    nodes: Node[] = []
  ): Collaboration {
    let orgs: Organization[] = [];
    let org_ids: number[] = [];
    // if (coll_json.organizations) {
    //   coll_json.organizations.forEach((org_json: any) => {
    //     let org = getById(organizations, org_json.id);
    //     if (org) {
    //       org = deepcopy(org);
    //       for (let node of nodes) {
    //         if (
    //           node.organization_id === org.id &&
    //           node.collaboration_id === coll_json.id
    //         ) {
    //           org.node = node;
    //           break;
    //         }
    //       }
    //       orgs.push(org);
    //     }
    //     org_ids.push(org_json.id);
    //   });
    // }
    return {
      id: coll_json.id,
      name: coll_json.name,
      encrypted: coll_json.encrypted,
      organizations: orgs,
      organization_ids: org_ids,
      type: ResType.COLLABORATION,
    };
  }

  getNode(node_json: any): Node {
    let config: { [key: string]: string[] } = {};
    if (node_json.config && node_json.config.length > 0) {
      for (let c of node_json.config) {
        c.key = c.key.replace(/_/g, ' '); // replace underscore with space
        // replace numerical values with their boolean representation
        if (c.key === 'encryption') {
          c.value = c.value === '0' ? false : true;
        }
        // add configuration key/value
        if (!(c.key in config)) {
          config[c.key] = [c.value];
        } else {
          config[c.key].push(c.value);
        }
      }
    }

    return {
      id: node_json.id,
      type: ResType.NODE,
      name: node_json.name,
      collaboration_id: node_json.collaboration.id,
      organization_id: node_json.organization.id,
      ip: node_json.ip,
      is_online: node_json.status === 'online' ? true : false,
      last_seen: node_json.last_seen ? new Date(node_json.last_seen) : null,
      config: config,
    };
  }

  getTask(json: any): Task {
    return {
      id: json.id,
      type: ResType.TASK,
      name: json.name,
      description: json.description,
      image: json.image,
      collaboration_id: json.collaboration.id,
      initiator_id: json.init_org.id,
      init_user_id: json.init_user.id,
      job_id: json.job_id,
      parent_id: json.parent ? json.parent.id : null,
      databases: json.databases,
      complete: json.complete,
      children_ids: [],
      status: json.status,
    };
  }

  getAlgorithmRun(json: any): Run {
    let port_ids = [];
    if (json.port_ids) {
      for (let port of json.port_ids) {
        port_ids.push(port.id);
      }
    }
    // task id can be in different places depending on which result endpoint
    // is called in which manner
    let task_id: number;
    if (json.task_id) {
      task_id = json.task_id;
    } else if (json.task.id) {
      task_id = json.task.id;
    } else {
      task_id = json.task;
    }
    let organization_id: number = json.organization.id
      ? json.organization.id
      : json.organization;

    return {
      id: json.id,
      type: ResType.RUN,
      input: json.input,
      result: json.result,
      log: json.log,
      task_id: task_id,
      organization_id: organization_id,
      port_ids: port_ids,
      started_at: json.started_at,
      assigned_at: json.assigned_at,
      finished_at: json.finished_at,
      status: json.status,
    };
  }
}
