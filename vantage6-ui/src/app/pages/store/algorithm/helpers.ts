import { AlgorithmForm } from 'src/app/models/api/algorithm.model';
import { Algorithm } from 'src/app/models/api/algorithm.model';

export function convertAlgorithmToAlgorithmForm(algorithm: Algorithm): AlgorithmForm {
  return {
    name: algorithm.name,
    description: algorithm.description,
    partitioning: algorithm.partitioning,
    image: algorithm.image,
    vantage6_version: algorithm.vantage6_version,
    code_url: algorithm.code_url,
    documentation_url: algorithm.documentation_url,
    submission_comments: algorithm.submission_comments,
    functions: algorithm.functions.map((func) => {
      return {
        name: func.name,
        display_name: func.display_name,
        description: func.description,
        step_type: func.step_type,
        standalone: func.standalone,
        arguments: func.arguments.map((arg) => {
          const conditionalArgName =
            arg.conditional_on_id === undefined ? undefined : func.arguments.find((a) => a.id === arg.conditional_on_id)?.name;
          return {
            name: arg.name,
            display_name: arg.display_name,
            type: arg.type,
            allowed_values: arg.allowed_values,
            description: arg.description,
            has_default_value: arg.has_default_value,
            default_value: arg.default_value || null,
            is_default_value_null: arg.default_value === null ? 'true' : 'false',
            hasCondition: arg.conditional_on_id !== null,
            conditional_on: conditionalArgName,
            conditional_operator: arg.conditional_operator,
            conditional_value: arg.conditional_value,
            conditionalValueNull: arg.conditional_value === null ? 'true' : 'false',
            is_frontend_only: arg.is_frontend_only
          };
        }),
        databases: func.databases.map((db) => {
          return {
            name: db.name,
            description: db.description,
            multiple: db.multiple
          };
        }),
        ui_visualizations: func.ui_visualizations.map((vis) => {
          return {
            name: vis.name,
            description: vis.description,
            type: vis.type,
            schema: vis.schema
          };
        })
      };
    })
  };
}
