import { Injectable } from '@angular/core';

import { Role } from '../interfaces/role';
import { Rule } from '../interfaces/rule';
import { User } from '../interfaces/user';
import { Organization } from '../interfaces/organization';
import { getById } from '../utils';

@Injectable({
  providedIn: 'root',
})
export class ConvertJsonService {
  // Service to cast JSONs from API calls to their respective interfaces

  constructor() {}

  getRule(rule_json: any): Rule {
    return {
      id: rule_json.id,
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
      username: user_json.username,
      first_name: user_json.firstname,
      last_name: user_json.lastname,
      email: user_json.email,
      organization_id: user_json.organization.id,
      roles: user_roles,
      rules: user_rules,
      is_being_created: false,
    };
  }

  getOrganization(org_json: any): Organization {
    return {
      id: org_json.id,
      name: org_json.name,
      address1: org_json.address1,
      address2: org_json.address2,
      zipcode: org_json.zipcode,
      country: org_json.country,
      domain: org_json.domain,
      public_key: org_json.public_key,
    };
  }
}
