import { ResourceInOrg } from 'src/app/shared/types';
import { removeMatchedIdFromArray } from 'src/app/shared/utils';

export function add_to_org(
  resource: ResourceInOrg,
  resource_dict_by_org: { [org_id: number]: ResourceInOrg[] }
) {
  if (resource.organization_id in resource_dict_by_org) {
    const updated_list = [
      ...resource_dict_by_org[resource.organization_id],
      resource,
    ];
    resource_dict_by_org[resource.organization_id] = updated_list;
  } else {
    resource_dict_by_org[resource.organization_id] = [resource];
  }
}

export function remove_from_org(
  resource: ResourceInOrg,
  resource_dict_by_org: { [org_id: number]: ResourceInOrg[] }
) {
  if (resource.organization_id in resource_dict_by_org) {
    resource_dict_by_org[resource.organization_id] = removeMatchedIdFromArray(
      resource_dict_by_org[resource.organization_id],
      resource.id
    );
  }
}
