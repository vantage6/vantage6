import { Injectable } from '@angular/core';

import { Role } from 'src/app/interfaces/role';
import { Rule } from 'src/app/interfaces/rule';
import { User } from 'src/app/interfaces/user';
import { Node } from 'src/app/interfaces/node';
import { Organization } from 'src/app/interfaces/organization';
import { deepcopy, getById } from 'src/app/shared/utils';
import { Collaboration } from 'src/app/interfaces/collaboration';
import { ResType } from 'src/app/shared/enum';

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
    };
  }

  getCollaboration(
    coll_json: any,
    organizations: Organization[]
  ): Collaboration {
    let orgs: Organization[] = [];
    if (coll_json.organizations) {
      coll_json.organizations.forEach((org: any) => {
        let o = deepcopy(getById(organizations, org.id));
        if (o !== undefined) {
          orgs.push(o);
        }
      });
    }
    return {
      id: coll_json.id,
      name: coll_json.name,
      encrypted: coll_json.encrypted,
      organizations: orgs,
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
}
