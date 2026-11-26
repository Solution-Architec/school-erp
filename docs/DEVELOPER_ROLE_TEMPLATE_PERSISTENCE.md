# Developer Role Template Persistence

This change adds the persistence foundation for Developer-governed role templates.

## Data model

- `rbac_role_templates` stores stable template identity, key, display metadata, active state and creator.
- `rbac_role_template_versions` stores version number, institution-type applicability, permission policy, lifecycle status and publication metadata.
- Published versions are immutable through the lifecycle service. Corrections and policy changes require a new draft version.

## Policy validation

A template version can reference only:
- Active, registered institution types.
- Active, non-platform-only modules.
- Actions enabled for the selected module in the canonical module/action registry.
- Supported data scopes: `own`, `assigned`, `class_section`, `department`, `institution`, `selected_records`, and `parent_student_relationship`.

The template service revalidates policy both when a draft is saved and when it is published. Developer Control Centre and institution-management platform modules cannot be placed in tenant templates.

## Lifecycle service

`backend/app/rbac_templates.py` provides:
- `create_role_template`
- `create_template_version`
- `replace_draft_policy`
- `publish_template_version`

The functions are persistence/domain helpers only. This PR does not add public API endpoints, institution adoption, custom institution roles, user-role assignments, or switch runtime authorization to templates. Those are later roadmap steps. Existing `User.role`, `RolePermission`, and all current authorization behavior remain unchanged.

## Compatibility and rollout

The models are additive and are included in SQLAlchemy metadata initialization. Existing role permissions and users are not rewritten. No template is automatically granted to an institution or user. Published template versions are retained for future adoption history; later adoption work must explicitly record which version an institution selected.

## Tests

`backend/tests/test_rbac_templates.py` covers draft creation, version numbering, publication, published-version immutability, new-version creation, platform-only module rejection, action/scope validation and duplicate template keys.
