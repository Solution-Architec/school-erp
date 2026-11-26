# Developer Role Designer UI

## Access and navigation

- Adds a Developer-only **Role Template Designer** workspace module.
- Navigation is exposed only to the authenticated platform Developer (`super_admin`) role.
- The component uses the `/api/developer/rbac` endpoints; backend authorization remains authoritative.
- Institution client-workspace sessions are tenant `admin` sessions and do not receive this module.

## Designer capabilities

- Load the canonical institution-type, module and action catalogue.
- Create reusable master role templates with a unique key, display name, category and description.
- Browse active and paused templates and their version history.
- Create a draft policy version for one or more institution types.
- Configure module/action grants and one data scope per selected module.
- Exclude platform-only modules from tenant role templates.
- Edit draft versions, publish validated drafts and retire published versions.
- Pause or reactivate a template without deleting its history.

## Governance and safety

- The UI submits only module/action combinations returned by the active canonical catalogue. It does not infer or invent permission combinations.
- Institution-type compatibility is shown while editing; incompatible modules cannot be selected.
- The backend revalidates every draft and revalidates again at publication.
- Published and retired policies are presented read-only. Only drafts can be edited.
- Confirmation is required before publish, retire or pause/reactivate operations.
- Retiring a published version prevents new adoption; it does not rewrite existing institution roles.
- The UI does not grant permissions to users and does not change live route authorization.

## Validation

The repository CI workflow is expected to run the frontend TypeScript/Vite build, backend tests and PostgreSQL backup/restore verification for this PR.
