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
import { Result } from 'src/app/interfaces/result';

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

  getRole(role_json: any, all_rules: Rule[]): Role {
    let rules: Rule[] = [];
    if (role_json.rules) {
      for (let rule of role_json.rules) {
        rules.push(getById(all_rules, rule.id));
      }
    }
    return {
      id: role_json.id,
      type: ResType.ROLE,
      name: role_json.name,
      description: role_json.description,
      organization_id: role_json.organization
        ? role_json.organization.id
        : null,
      rules: rules,
    };
  }

  getUser(user_json: any, roles: Role[], rules: Rule[]): User {
    let user_roles: Role[] = [];
    if (user_json.roles) {
      user_json.roles.forEach((role: any) => {
        let r = getById(roles, role.id);
        if (r !== undefined) {
          user_roles.push(r);
        }
      });
    }
    let user_rules: Rule[] = [];
    if (user_json.rules) {
      user_json.rules.forEach((rule: any) => {
        let r = getById(rules, rule.id);
        user_rules.push(r);
      });
    }
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
    if (org_json.collaborations) {
      for (let col of org_json.collaborations) {
        col_ids.push(col.id);
      }
    }
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
    organizations: Organization[]
  ): Collaboration {
    let orgs: Organization[] = [];
    let org_ids: number[] = [];
    if (coll_json.organizations) {
      coll_json.organizations.forEach((org_json: any) => {
        let org = getById(organizations, org_json.id);
        if (org) {
          orgs.push(deepcopy(org));
        }
        org_ids.push(org_json.id);
      });
    }
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
    return {
      id: node_json.id,
      type: ResType.NODE,
      name: node_json.name,
      collaboration_id: node_json.collaboration.id,
      organization_id: node_json.organization.id,
      ip: node_json.ip,
      is_online: node_json.status === 'online' ? true : false,
      last_seen: node_json.last_seen ? new Date(node_json.last_seen) : null,
    };
  }

  getTask(json: any): Task {
    let child_ids = [];
    if (json.children) {
      for (let child of json.children) {
        child_ids.push(child.id);
      }
    }
    return {
      id: json.id,
      type: ResType.TASK,
      name: json.name,
      description: json.description,
      image: json.image,
      collaboration_id: json.collaboration.id,
      init_org_id: json.init_org,
      init_user_id: json.init_user,
      run_id: json.run_id,
      parent_id: json.parent ? json.parent.id : null,
      database: json.database,
      complete: json.complete,
      children_ids: child_ids,
    };
  }

  getResult(json: any): Result {
    let port_ids = [];
    if (json.port_ids) {
      for (let port of json.port_ids) {
        port_ids.push(port.id);
      }
    }
    return {
      id: json.id,
      type: ResType.RESULT,
      name: json.name,
      input: json.input,
      result: json.result,
      log: json.log,
      task_id: json.task_id,
      organization_id: json.organization,
      port_ids: port_ids,
      started_at: json.started_at,
      assigned_at: json.assigned_at,
      finished_at: json.finished_at,
    };
  }
}
