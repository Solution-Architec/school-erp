# Developer Role Template APIs

## Access boundary

All endpoints are mounted under `/api/developer/rbac` and require the authenticated platform Developer role (`super_admin`). A platform-owner client-workspace token is intentionally represented as tenant `admin` and is therefore denied. School and institution administrators cannot create or publish master templates.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/catalog` | Read canonical institution types, modules and actions, including platform-only catalogue metadata for Developer use |
| GET | `/templates` | List active templates and their versions; `include_inactive=true` includes paused templates |
| POST | `/templates` | Create a Developer-owned template identity |
| GET | `/templates/{template_id}` | Read one template and its version history |
| PATCH | `/templates/{template_id}` | Update display metadata or pause/reactivate the template |
| POST | `/templates/{template_id}/versions` | Create the next immutable-history draft version |
| PATCH | `/versions/{version_id}` | Replace policy on a draft only |
| POST | `/versions/{version_id}/publish` | Revalidate and publish a draft |
| POST | `/versions/{version_id}/retire` | Retire a published version without rewriting its policy |

## Governance behavior

- Template keys are unique and immutable after creation.
- Each new version receives the next version number; published versions are not editable.
- Draft creation and publication both validate institution types, active modules, allowed module/action combinations, data scopes and platform-only module exclusions.
- Retiring a version prevents it from being adopted for new institution roles. Existing institution roles keep their source version reference and their currently stored permissions; this API does not silently rewrite or revoke them.
- Pausing a template prevents new versions through the existing service lifecycle and removes it from the default active listing. It does not delete history.
- Mutations write audit events: `rbac.template.created`, `rbac.template.updated`, `rbac.template.version.created`, `rbac.template.version.updated`, `rbac.template.version.published`, and `rbac.template.version.retired`.
- Validation failures return 422, missing resources return 404, and lifecycle conflicts return 409.

## Compatibility and safety

- No institution role assignments or permissions are modified.
- Existing `User.role`, `RolePermission`, and the live authorization path are unchanged.
- APIs do not expose secrets or user authentication data.
- This PR provides backend APIs only; the Developer Role Designer UI is a later stage.
